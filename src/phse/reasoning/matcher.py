import logging
import numpy as np
from typing import Dict, List, Tuple
from phse.reasoning.models import LunarGeologicalHypothesis

logger = logging.getLogger("phse")

class ConstraintMatcher:
    """
    Evaluates physical observations against geological constraints in the LGHL.
    Supports both single-pixel evaluation and high-performance vectorized grid matching.
    """
    def __init__(self, hypotheses: List[LunarGeologicalHypothesis]):
        self.hypotheses = hypotheses

    def evaluate_pixel(self, observation: Dict[str, float]) -> Dict[str, float]:
        """
        Computes soft fuzzy membership grades for all hypotheses at a single pixel location.
        Uses a Gaussian membership function centered on the interval midpoint.
        """
        grades = {}
        for hyp in self.hypotheses:
            hyp_grade = 1.0
            matched_any = False
            
            for feature, (min_val, max_val) in hyp.constraints.items():
                if feature not in observation:
                    continue
                    
                val = observation[feature]
                matched_any = True
                
                # Compute Gaussian membership grade
                midpoint = (min_val + max_val) / 2.0
                # Define standard deviation as a quarter of the width
                width = max_val - min_val
                sigma = width / 4.0 if width > 0 else 0.1
                
                # Compute grade
                grade = np.exp(-0.5 * ((val - midpoint) / sigma) ** 2)
                hyp_grade *= grade
                
            grades[hyp.id] = float(hyp_grade) if matched_any else 0.0
            
        return grades

    def evaluate_grid(self, layers: Dict[str, np.ndarray], nodata_mask: np.ndarray) -> Dict[str, np.ndarray]:
        """
        Runs high-performance vectorized constraint matching across the entire raster grid.
        Returns a dictionary mapping hypothesis IDs to 2D membership grade grids.
        """
        logger.info("Executing vectorized constraint matching across spatial grid...")
        shape = next(iter(layers.values())).shape
        grid_grades: Dict[str, np.ndarray] = {}
        
        for hyp in self.hypotheses:
            # Initialize membership matrix with 1.0
            hyp_grade = np.ones(shape, dtype=np.float32)
            matched_any = False
            
            for feature, (min_val, max_val) in hyp.constraints.items():
                if feature not in layers:
                    continue
                    
                val = layers[feature]
                matched_any = True
                
                midpoint = (min_val + max_val) / 2.0
                width = max_val - min_val
                sigma = width / 4.0 if width > 0 else 0.1
                
                # Vectorized Gaussian membership evaluation
                grade = np.exp(-0.5 * ((val - midpoint) / sigma) ** 2)
                hyp_grade *= grade
                
            if matched_any:
                # Mask out nodata regions
                hyp_grade[nodata_mask] = 0.0
                grid_grades[hyp.id] = hyp_grade
            else:
                grid_grades[hyp.id] = np.zeros(shape, dtype=np.float32)
                
        return grid_grades
