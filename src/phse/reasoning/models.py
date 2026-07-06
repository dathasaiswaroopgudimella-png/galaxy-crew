from pydantic import BaseModel, Field
from typing import Dict, List, Tuple, Optional

class LunarGeologicalHypothesis(BaseModel):
    """
    Scientific description of a candidate geological model, including its physical bounds.
    """
    id: str = Field(description="Unique identifier for the hypothesis")
    name: str = Field(description="Descriptive name")
    description: str = Field(description="Geological description")
    constraints: Dict[str, Tuple[float, float]] = Field(description="Expected min/max value bounds for physical features")
    prior_probability: float = Field(default=0.2, description="A priori likelihood of this geological model")

class ActiveHypothesisSet(BaseModel):
    """
    Set of active hypotheses under evaluation at a specific location and their probability distribution.
    """
    probabilities: Dict[str, float] = Field(description="Map of hypothesis IDs to posterior probabilities")
    entropy: float = Field(description="Shannon entropy of the probability distribution")

class Observation(BaseModel):
    """
    A single feature observation assimilated into the reasoning engine.
    """
    feature_name: str = Field(description="Name of the physical feature (e.g. 'radar_cpr')")
    value: float = Field(description="Observed value of the feature")
    uncertainty: float = Field(default=0.1, description="Acquisition or processing measurement uncertainty")

class MissionRecommendation(BaseModel):
    """
    Final landing site recommendation and resource localization metrics.
    """
    landing_x: int = Field(description="Optimal landing site X pixel coordinate")
    landing_y: int = Field(description="Optimal landing site Y pixel coordinate")
    landing_score: float = Field(description="Safety/Scientific suitability score [0, 1]")
    estimated_ice_volume_m3: float = Field(description="Estimated subsurface water ice volume in cubic meters")
    max_slope_deg: float = Field(description="Maximum slope at landing zone")
    max_roughness_m: float = Field(description="Maximum RMS roughness at landing zone")
    rover_path: List[Tuple[int, int]] = Field(description="Calculated optimal rover traversal coordinates")
    confidence: float = Field(description="Overall mission confidence score")
