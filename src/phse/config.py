import os
from typing import List
import yaml
from pydantic import BaseModel, Field

class PathsConfig(BaseModel):
    dfsar_path: str = Field(description="Directory path containing raw DFSAR files")
    ohrc_path: str = Field(description="Directory path containing raw OHRC files")
    output_dir: str = Field(default="outputs", description="Directory to save output files")
    log_dir: str = Field(default="logs", description="Directory to save execution logs")

class PreprocessingConfig(BaseModel):
    target_resolution_m: float = Field(default=5.0, description="Target pixel resolution in meters")
    nodata_value: float = Field(default=-9999.0, description="Value used for missing/invalid data representation")
    normalize: bool = Field(default=True, description="Whether to scale raster inputs between 0 and 1")
    dfsar_backscatter_min_db: float = Field(default=-40.0, description="Minimum threshold for DFSAR backscatter in dB")
    dfsar_backscatter_max_db: float = Field(default=5.0, description="Maximum threshold for DFSAR backscatter in dB")

class AlignmentConfig(BaseModel):
    target_crs: str = Field(default="auto", description="CRS string for output, or 'auto' to align to one of the sensors")
    resampling_method: str = Field(default="bilinear", description="Resampling algorithm: nearest, bilinear, cubic")

class ValidationConfig(BaseModel):
    allowed_formats: List[str] = Field(default_factory=lambda: [".tif", ".tiff", ".img"])
    min_data_percentage: float = Field(default=10.0, description="Minimum percentage of valid pixels required in input")
    crs_check: bool = Field(default=True, description="Enforce CRS match/readability check")

from phse.analysis.config import AnalysisConfig

class PHSEConfig(BaseModel):
    seed: int = Field(default=42, description="Random seed for reproducibility")
    paths: PathsConfig
    preprocessing: PreprocessingConfig
    alignment: AlignmentConfig
    validation: ValidationConfig
    analysis: AnalysisConfig = Field(default_factory=AnalysisConfig)


def load_config(config_path: str) -> PHSEConfig:
    """
    Loads and validates configuration from a YAML file.
    
    Args:
        config_path (str): Path to the config file.
        
    Returns:
        PHSEConfig: Validated application configuration model.
        
    Raises:
        FileNotFoundError: If the configuration file does not exist.
        ValidationError: If the YAML structure violates the Pydantic schemas.
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
    with open(config_path, "r") as f:
        data = yaml.safe_load(f)
        
    return PHSEConfig(**data)
