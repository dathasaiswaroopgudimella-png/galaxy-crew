import logging
import numpy as np
from typing import Dict, Tuple, List, Optional
from scipy.ndimage import maximum_filter
from phse.models import RasterLayer, RasterMetadata

logger = logging.getLogger("phse")

class MissionPlanner:
    """
    Ranks landing locations and evaluates safety envelopes based on slope,
    roughness, hazard grids, and resource confidence maps.
    """
    def __init__(
        self,
        max_landing_slope: float = 15.0,
        max_landing_roughness: float = 0.5,
        landing_safety_radius_px: int = 5,
        slope_weight: float = 0.5,
        resource_weight: float = 0.5
    ):
        self.max_landing_slope = max_landing_slope
        self.max_landing_roughness = max_landing_roughness
        self.landing_safety_radius_px = landing_safety_radius_px
        self.slope_weight = slope_weight
        self.resource_weight = resource_weight

    def evaluate_landing_zones(
        self,
        slope_layer: RasterLayer,
        roughness_layer: RasterLayer,
        hazard_layer: RasterLayer,
        ice_probability_layer: RasterLayer
    ) -> Tuple[RasterLayer, int, int, float]:
        """
        Computes a spatial Landing Suitability Score and identifies the optimal landing site.
        Enforces a safety envelope of radius landing_safety_radius_px around the candidate pixel.
        """
        logger.info("Evaluating landing zone suitability grids...")
        
        slope = slope_layer.data
        roughness = roughness_layer.data
        hazard = hazard_layer.data
        ice_prob = ice_probability_layer.data
        
        nodata = slope_layer.metadata.nodata
        mask = (slope == nodata) | (roughness == roughness_layer.metadata.nodata) | np.isnan(slope)
        
        # 1. Compute maximum slope and roughness in the local safety radius (landing ellipse)
        # Using maximum_filter to find the worst hazard in the landing zone
        local_max_slope = maximum_filter(slope, size=self.landing_safety_radius_px * 2 + 1, mode='nearest')
        local_max_roughness = maximum_filter(roughness, size=self.landing_safety_radius_px * 2 + 1, mode='nearest')
        
        # 2. Evaluate safety mask: 1.0 if safe, 0.0 if unsafe
        safety_mask = (local_max_slope <= self.max_landing_slope) & (local_max_roughness <= self.max_landing_roughness) & (~mask)
        
        # 3. Compute suitability score
        # High score corresponds to high ice probability and low hazard index
        suitability = np.zeros_like(slope, dtype=np.float32)
        
        # Normalize inputs for score mapping [0, 1]
        norm_ice = ice_prob
        norm_hazard = 1.0 - hazard
        
        score = (self.resource_weight * norm_ice) + ((1.0 - self.resource_weight) * norm_hazard)
        suitability[safety_mask] = score[safety_mask]
        suitability[~safety_mask] = 0.0
        suitability[mask] = nodata
        
        # 4. Find optimal coordinates
        valid_indices = np.argwhere(safety_mask)
        if valid_indices.size == 0:
            logger.warning("No safe landing zones found meeting the physical safety envelopes. Searching for best unsafe site.")
            # Fallback: search ignoring safety mask but avoiding nodata
            valid_indices = np.argwhere(~mask)
            if valid_indices.size == 0:
                raise RuntimeError("No valid data pixels available for landing zone evaluation.")
                
            flat_idx = np.argmax(score[~mask])
            y, x = valid_indices[flat_idx]
            optimal_score = float(score[y, x])
        else:
            flat_idx = np.argmax(suitability[safety_mask])
            y, x = valid_indices[flat_idx]
            optimal_score = float(suitability[y, x])
            
        logger.info(f"Optimal landing site selected at X: {x}, Y: {y} with Suitability Score: {optimal_score:.4f}")
        
        # Create output RasterLayer
        score_metadata = slope_layer.metadata.model_copy(deep=True)
        score_metadata.dtype = "float32"
        score_metadata.nodata = nodata
        
        suitability_layer = RasterLayer(
            name="landing_suitability_score",
            data=suitability,
            metadata=score_metadata,
            sources=list(set(slope_layer.sources + ice_probability_layer.sources))
        )
        
        suitability_layer.record_step(
            module="phse.mission.planner",
            action="evaluate_landing_zones",
            parameters={
                "max_landing_slope": self.max_landing_slope,
                "max_landing_roughness": self.max_landing_roughness,
                "landing_safety_radius_px": self.landing_safety_radius_px
            }
        )
        
        return suitability_layer, int(x), int(y), optimal_score
