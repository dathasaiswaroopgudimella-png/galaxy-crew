from pydantic import BaseModel, Field

class RadarConfig(BaseModel):
    """
    Configuration parameters for radar feature extraction.
    """
    cpr_window_size: int = Field(default=5, description="Local averaging window size (odd integer) for Stokes parameters and CPR")
    dop_window_size: int = Field(default=5, description="Local averaging window size (odd integer) for DOP")
    transmit_hand: str = Field(default="left", description="Hand of transmitted circular polarization ('left' or 'right')")

class TerrainConfig(BaseModel):
    """
    Configuration parameters for terrain feature extraction.
    """
    slope_threshold_critical: float = Field(default=15.0, description="Slope angle in degrees above which terrain is highly hazardous")
    roughness_window_size: int = Field(default=5, description="Local window size (odd integer) for RMS roughness computation")
    roughness_threshold_critical: float = Field(default=0.5, description="RMS roughness in meters above which terrain is highly hazardous")
    sun_elevation_deg: float = Field(default=10.0, description="Elevation angle of the sun in degrees (for illumination/hillshade)")
    sun_azimuth_deg: float = Field(default=45.0, description="Azimuth angle of the sun in degrees (for illumination/hillshade)")
    boulder_min_sigma: float = Field(default=1.0, description="Minimum sigma for Laplacian of Gaussian boulder detection")
    boulder_max_sigma: float = Field(default=4.0, description="Maximum sigma for Laplacian of Gaussian boulder detection")
    boulder_num_sigma: int = Field(default=5, description="Number of intermediate sigmas for Laplacian of Gaussian boulder detection")
    boulder_threshold: float = Field(default=0.02, description="Intensity threshold for boulder detection")
    boulder_density_window_size: int = Field(default=21, description="Moving window size (in pixels) to compute boulder density")
    boulder_density_threshold_critical: float = Field(default=5.0, description="Boulder count per density window above which terrain is highly hazardous")
    weight_slope: float = Field(default=0.4, description="Weight of slope hazard in the total terrain hazard index")
    weight_roughness: float = Field(default=0.3, description="Weight of roughness hazard in the total terrain hazard index")
    weight_boulder: float = Field(default=0.3, description="Weight of boulder hazard in the total terrain hazard index")

class AnalysisConfig(BaseModel):
    """
    Consolidated configuration for the scientific feature extraction engine.
    """
    radar: RadarConfig = Field(default_factory=RadarConfig)
    terrain: TerrainConfig = Field(default_factory=TerrainConfig)
