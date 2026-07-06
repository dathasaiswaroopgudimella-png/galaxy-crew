import logging
import numpy as np
from typing import Dict, List, Tuple
from phse.reasoning.models import LunarGeologicalHypothesis

logger = logging.getLogger("phse")

class BayesianAssimilator:
    """
    Performs sequential Bayesian updating to estimate the posterior probabilities
    of geological hypotheses based on physical remote sensing evidence.
    """
    def __init__(self, hypotheses: List[LunarGeologicalHypothesis]):
        self.hypotheses = {h.id: h for h in hypotheses}

    def compute_likelihood(self, val: float, h_id: str, feature: str) -> float:
        """
        Computes the Gaussian likelihood P(Obs_f | H_i) for a single observation.
        """
        hyp = self.hypotheses.get(h_id)
        if not hyp or feature not in hyp.constraints:
            return 1e-6 # Small epsilon for out-of-bounds or missing constraints
            
        min_val, max_val = hyp.constraints[feature]
        midpoint = (min_val + max_val) / 2.0
        sigma = (max_val - min_val) / 4.0
        if sigma == 0.0:
            sigma = 0.05
            
        # Standard Gaussian PDF
        exponent = -0.5 * ((val - midpoint) / sigma) ** 2
        likelihood = (1.0 / (sigma * np.sqrt(2.0 * np.pi))) * np.exp(exponent)
        return float(max(likelihood, 1e-6))

    def update_probabilities(
        self,
        current_probs: Dict[str, float],
        observation: float,
        feature_name: str,
        pruning_threshold: float = 0.01
    ) -> Dict[str, float]:
        """
        Performs a sequential Bayesian update for a single pixel location.
        """
        posteriors = {}
        total_evidence = 0.0
        
        # Calculate unnormalized posteriors: Likelihood * Prior
        for h_id, prior in current_probs.items():
            likelihood = self.compute_likelihood(observation, h_id, feature_name)
            posterior = likelihood * prior
            posteriors[h_id] = posterior
            total_evidence += posterior
            
        if total_evidence == 0:
            logger.warning("Bayesian update encountered zero total evidence. Bypassing update.")
            return current_probs.copy()
            
        # Normalize and apply pruning threshold
        normalized = {}
        rem_sum = 0.0
        for h_id, post in posteriors.items():
            prob = post / total_evidence
            if prob >= pruning_threshold:
                normalized[h_id] = prob
                rem_sum += prob
            else:
                normalized[h_id] = 0.0
                
        # Renormalize after pruning
        if rem_sum > 0:
            for h_id in normalized:
                normalized[h_id] /= rem_sum
        else:
            return current_probs.copy()
            
        return normalized

    def compute_entropy(self, probabilities: Dict[str, float]) -> float:
        """
        Calculates Shannon entropy of the probability distribution in bits.
        H(P) = -sum( P(x) * log2(P(x)) )
        """
        probs = [p for p in probabilities.values() if p > 0]
        if not probs:
            return 0.0
        return float(-np.sum(probs * np.log2(probs)))

    def update_grid(
        self,
        prior_grids: Dict[str, np.ndarray],
        observation_grid: np.ndarray,
        feature_name: str,
        nodata_mask: np.ndarray
    ) -> Dict[str, np.ndarray]:
        """
        Runs high-performance vectorized Bayesian grid updating across the entire raster spatial extent.
        """
        logger.info(f"Executing vectorized Bayesian evidence assimilation for layer '{feature_name}'")
        shape = observation_grid.shape
        posteriors: Dict[str, np.ndarray] = {}
        total_evidence = np.zeros(shape, dtype=np.float32)
        
        # 1. Compute unnormalized posteriors (Prior * Likelihood) for each hypothesis
        for h_id, prior in prior_grids.items():
            hyp = self.hypotheses.get(h_id)
            if not hyp or feature_name not in hyp.constraints:
                # Default to uniform small likelihood
                likelihood = np.full(shape, 1e-6, dtype=np.float32)
            else:
                min_val, max_val = hyp.constraints[feature_name]
                midpoint = (min_val + max_val) / 2.0
                sigma = (max_val - min_val) / 4.0
                if sigma == 0.0:
                    sigma = 0.05
                    
                # Vectorized Gaussian PDF
                exponent = -0.5 * ((observation_grid - midpoint) / sigma) ** 2
                likelihood = (1.0 / (sigma * np.sqrt(2.0 * np.pi))) * np.exp(exponent)
                likelihood = np.clip(likelihood, 1e-6, None)
                
            post = prior * likelihood
            posteriors[h_id] = post
            total_evidence += post
            
        # 2. Normalize posteriors
        valid_mask = (total_evidence > 0) & (~nodata_mask)
        final_posteriors: Dict[str, np.ndarray] = {}
        
        for h_id, post in posteriors.items():
            normalized = np.zeros(shape, dtype=np.float32)
            normalized[valid_mask] = post[valid_mask] / total_evidence[valid_mask]
            
            # Apply nodata masking
            normalized[nodata_mask] = 0.0
            final_posteriors[h_id] = normalized
            
        return final_posteriors

    def compute_grid_entropy(self, probability_grids: Dict[str, np.ndarray]) -> np.ndarray:
        """
        Computes Shannon entropy in bits for every pixel in the spatial grid.
        """
        shape = next(iter(probability_grids.values())).shape
        entropy = np.zeros(shape, dtype=np.float32)
        
        for p_grid in probability_grids.values():
            # Avoid log2(0) by using a small epsilon
            p_safe = np.clip(p_grid, 1e-10, 1.0)
            entropy += -p_grid * np.log2(p_safe)
            
        return entropy
