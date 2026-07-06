import logging
import numpy as np
from typing import Dict, List, Tuple
from phse.reasoning.models import LunarGeologicalHypothesis

logger = logging.getLogger("phse")

class AdaptiveSeparator:
    """
    Implements Adaptive Hypothesis Separation (AHS) to select the most informative
    unassimilated physical feature layer for resolving scientific ambiguities.
    """
    def __init__(self, hypotheses: List[LunarGeologicalHypothesis]):
        self.hypotheses = {h.id: h for h in hypotheses}

    def _compute_gaussian_kl(self, mu_a: float, sigma_a: float, mu_b: float, sigma_b: float) -> float:
        """
        Computes the analytical Kullback-Leibler (KL) divergence between two 1D Gaussian distributions.
        DKL(N_a || N_b) = log(sigma_b / sigma_a) + (sigma_a^2 + (mu_a - mu_b)^2) / (2 * sigma_b^2) - 0.5
        """
        if sigma_a <= 0 or sigma_b <= 0:
            return 0.0
            
        term1 = np.log(sigma_b / sigma_a)
        term2 = (sigma_a**2 + (mu_a - mu_b)**2) / (2.0 * sigma_b**2)
        return float(term1 + term2 - 0.5)

    def evaluate_feature_separability(
        self,
        active_set: Dict[str, float],
        feature_name: str
    ) -> float:
        """
        Calculates the expected pairwise symmetrized KL divergence (Jeffrey's divergence)
        for a candidate feature among active hypotheses, weighted by current probabilities.
        """
        active_ids = [h_id for h_id, prob in active_set.items() if prob > 0.01]
        if len(active_ids) <= 1:
            return 0.0
            
        total_divergence = 0.0
        
        # Extract Gaussian parameters for each active hypothesis on this feature
        params = {}
        for h_id in active_ids:
            hyp = self.hypotheses.get(h_id)
            if not hyp or feature_name not in hyp.constraints:
                continue
                
            min_val, max_val = hyp.constraints[feature_name]
            midpoint = (min_val + max_val) / 2.0
            sigma = (max_val - min_val) / 4.0
            if sigma == 0.0:
                sigma = 0.05
            params[h_id] = (midpoint, sigma)
            
        # Compute weighted pairwise symmetrized KL divergence
        for i, id_a in enumerate(active_ids):
            for id_b in active_ids[i+1:]:
                if id_a not in params or id_b not in params:
                    continue
                    
                mu_a, sig_a = params[id_a]
                mu_b, sig_b = params[id_b]
                
                kl_ab = self._compute_gaussian_kl(mu_a, sig_a, mu_b, sig_b)
                kl_ba = self._compute_gaussian_kl(mu_b, sig_b, mu_a, sig_a)
                symmetrized_kl = kl_ab + kl_ba
                
                # Weight by product of current probabilities
                weight = active_set[id_a] * active_set[id_b]
                total_divergence += weight * symmetrized_kl
                
        return total_divergence

    def select_next_feature(
        self,
        active_set: Dict[str, float],
        available_features: List[str]
    ) -> str:
        """
        Selects the feature from the available list that maximizes expected geological separation.
        """
        if not available_features:
            raise ValueError("No available features for AHS evaluation.")
            
        if len(available_features) == 1:
            return available_features[0]
            
        best_feature = available_features[0]
        max_score = -1.0
        
        for feature in available_features:
            score = self.evaluate_feature_separability(active_set, feature)
            logger.debug(f"AHS evaluation: Feature '{feature}' separability score = {score:.4f}")
            if score > max_score:
                max_score = score
                best_feature = feature
                
        logger.info(f"AHS Selected optimal feature: '{best_feature}' with separation score = {max_score:.4f}")
        return best_feature
