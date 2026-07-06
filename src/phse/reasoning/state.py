import logging
import numpy as np
from typing import Dict, List, Tuple, Optional
from phse.models import RasterLayer, RasterMetadata, DatasetGroup
from phse.reasoning.lghl import HypothesisLibrary
from phse.reasoning.matcher import ConstraintMatcher
from phse.reasoning.ahs import AdaptiveSeparator
from phse.reasoning.bayesian import BayesianAssimilator
from phse.reasoning.models import LunarGeologicalHypothesis

logger = logging.getLogger("phse")

class ReasoningEngineRunResult:
    """
    Holds the complete output grids, statistics, and convergence metrics
    returned by the PHSE reasoning state machine execution.
    """
    def __init__(
        self,
        probability_layers: Dict[str, RasterLayer],
        geological_map: RasterLayer,
        entropy_layer: RasterLayer,
        convergence_trajectory: List[float]
    ):
        self.probability_layers = probability_layers
        self.geological_map = geological_map
        self.entropy_layer = entropy_layer
        self.convergence_trajectory = convergence_trajectory

class PHSEReasoningEngine:
    """
    FSM Orchestrator running the complete sequential reasoning pipeline:
    Constraint Matching -> AHS Selection -> Bayesian Assimilation -> Convergence.
    """
    def __init__(self, catalog_path: Optional[str] = None):
        self.library = HypothesisLibrary(catalog_path)
        self.hypotheses = self.library.get_all()
        
        self.matcher = ConstraintMatcher(self.hypotheses)
        self.ahs = AdaptiveSeparator(self.hypotheses)
        self.assimilator = BayesianAssimilator(self.hypotheses)

    def execute(
        self,
        pfr_layers: Dict[str, RasterLayer],
        entropy_threshold: float = 0.5,
        max_iterations: int = 5
    ) -> ReasoningEngineRunResult:
        """
        Executes the reasoning state machine over the spatial feature grids.
        
        Args:
            pfr_layers (Dict[str, RasterLayer]): Extracted physical feature layers
            entropy_threshold (float): Target Shannon entropy value for convergence
            max_iterations (int): Safety limit to prevent infinite iteration loops
            
        Returns:
            ReasoningEngineRunResult: Probabilities, Geological map, and execution metrics
        """
        logger.info("PHSE Reasoning Engine State Machine: [INITIALIZING]")
        
        # 1. Check spatial parameters and construct masks
        ref_layer = next(iter(pfr_layers.values()))
        shape = ref_layer.data.shape
        metadata = ref_layer.metadata.model_copy(deep=True)
        nodata = metadata.nodata
        
        # Nodata mask represents pixels that are invalid across ALL layers
        nodata_mask = np.zeros(shape, dtype=bool)
        for layer in pfr_layers.values():
            nodata_mask |= (layer.data == layer.metadata.nodata) | np.isnan(layer.data) | np.isinf(layer.data)
            
        # 2. State: [HYPOTHESIS RETRIEVAL & PRIORS SETUP]
        logger.info("PHSE Reasoning State Machine: [HYPOTHESIS RETRIEVAL]")
        prior_grids: Dict[str, np.ndarray] = {}
        for hyp in self.hypotheses:
            # Populate with prior probabilities defined in LGHL catalog
            prior_grids[hyp.id] = np.full(shape, hyp.prior_probability, dtype=np.float32)
            prior_grids[hyp.id][nodata_mask] = 0.0
            
        # Normalize priors across active hypotheses
        sum_priors = np.zeros(shape, dtype=np.float32)
        for grid in prior_grids.values():
            sum_priors += grid
            
        valid_mask = sum_priors > 0
        for h_id in prior_grids:
            prior_grids[h_id][valid_mask] /= sum_priors[valid_mask]

        # 3. State: [CONSTRAINT MATCHING]
        logger.info("PHSE Reasoning State Machine: [CONSTRAINT MATCHING]")
        raw_layers = {name: layer.data for name, layer in pfr_layers.items()}
        matching_grades = self.matcher.evaluate_grid(raw_layers, nodata_mask)
        
        # Update priors with matching grades (soft fuzzy filter)
        for h_id in prior_grids:
            prior_grids[h_id] *= matching_grades[h_id]
            
        # Re-normalize
        sum_grids = np.zeros(shape, dtype=np.float32)
        for grid in prior_grids.values():
            sum_grids += grid
        valid_sum = sum_grids > 0
        for h_id in prior_grids:
            prior_grids[h_id][valid_sum] /= sum_grids[valid_sum]

        # 4. State: [ASSIMILATION LOOP]
        logger.info("PHSE Reasoning State Machine: [ASSIMILATION LOOP]")
        available_features = list(pfr_layers.keys())
        current_grids = {h_id: grid.copy() for h_id, grid in prior_grids.items()}
        
        trajectory: List[float] = []
        
        # Compute starting entropy
        initial_entropy = self.assimilator.compute_grid_entropy(current_grids)
        mean_entropy = float(np.mean(initial_entropy[~nodata_mask])) if np.any(~nodata_mask) else 0.0
        trajectory.append(mean_entropy)
        
        iteration = 0
        logger.info(f"Iteration 0 (Prior State): Mean Entropy = {mean_entropy:.4f} bits")
        
        # We loop until convergence or feature depletion
        while mean_entropy > entropy_threshold and available_features and iteration < max_iterations:
            iteration += 1
            logger.info(f"PHSE Reasoning Loop: [ITERATION {iteration}]")
            
            # Step A: AHS Selection
            # Evaluate average active set across valid grid to feed AHS
            avg_probs = {}
            for h_id, grid in current_grids.items():
                valid_data = grid[~nodata_mask]
                avg_probs[h_id] = float(np.mean(valid_data)) if valid_data.size > 0 else 0.0
                
            selected_feature = self.ahs.select_next_feature(avg_probs, available_features)
            available_features.remove(selected_feature)
            
            # Step B: Bayesian Update
            obs_grid = pfr_layers[selected_feature].data
            current_grids = self.assimilator.update_grid(current_grids, obs_grid, selected_feature, nodata_mask)
            
            # Step C: Entropy Check
            entropy_grid = self.assimilator.compute_grid_entropy(current_grids)
            mean_entropy = float(np.mean(entropy_grid[~nodata_mask])) if np.any(~nodata_mask) else 0.0
            trajectory.append(mean_entropy)
            logger.info(f"Iteration {iteration}: Feature assimilated = '{selected_feature}' | Mean Entropy = {mean_entropy:.4f} bits")
            
        logger.info("PHSE Reasoning State Machine: [CONVERGED / COMPLETE]")
        
        # 5. Build final output models
        prob_layers = {}
        sources = [ref_layer.sources[0]] if ref_layer.sources else ["unknown_source"]
        
        for h_id, grid in current_grids.items():
            prob_meta = metadata.model_copy(deep=True)
            prob_meta.nodata = 0.0
            prob_meta.dtype = "float32"
            prob_layers[h_id] = RasterLayer(
                name=f"probability_{h_id}",
                data=grid,
                metadata=prob_meta,
                sources=sources
            )
            prob_layers[h_id].record_step(
                module="phse.reasoning.state",
                action="reasoning_probability_output",
                parameters={"hypothesis": h_id, "iterations_run": iteration}
            )
            
        # Geological Refined Interpretation map (argmax of probabilities)
        geo_map_data = np.zeros(shape, dtype=np.float32)
        # Create mapping of hypothesis index to ID
        hyp_list = list(current_grids.keys())
        # Compile stacks to argmax
        stack = np.stack([current_grids[h_id] for h_id in hyp_list], axis=0)
        argmax_grid = np.argmax(stack, axis=0).astype(np.float32)
        geo_map_data[~nodata_mask] = argmax_grid[~nodata_mask] + 1.0 # 1-indexed codes
        geo_map_data[nodata_mask] = nodata
        
        # Add integer-to-hypothesis description in additional metadata
        geo_meta = metadata.model_copy(deep=True)
        geo_meta.dtype = "float32"
        geo_meta.additional_metadata = {
            "hypothesis_codes": {idx+1: h_id for idx, h_id in enumerate(hyp_list)}
        }
        
        geological_map = RasterLayer("refined_geological_map", geo_map_data, geo_meta, sources)
        geological_map.record_step(
            module="phse.reasoning.state",
            action="refined_geological_interpretation",
            parameters={"class_codes": geo_meta.additional_metadata["hypothesis_codes"]}
        )
        
        # Final Entropy Map
        final_entropy_data = self.assimilator.compute_grid_entropy(current_grids)
        final_entropy_data[nodata_mask] = nodata
        entropy_meta = metadata.model_copy(deep=True)
        entropy_meta.dtype = "float32"
        entropy_layer = RasterLayer("reasoning_entropy", final_entropy_data, entropy_meta, sources)
        entropy_layer.record_step(
            module="phse.reasoning.state",
            action="reasoning_entropy_output",
            parameters={"final_mean_entropy": mean_entropy}
        )
        
        return ReasoningEngineRunResult(
            probability_layers=prob_layers,
            geological_map=geological_map,
            entropy_layer=entropy_layer,
            convergence_trajectory=trajectory
        )
