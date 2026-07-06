import os
import pytest
from pydantic import ValidationError
from phse.config import load_config, PHSEConfig

def test_load_valid_config(tmp_path):
    """
    Verifies that a valid YAML configuration is correctly parsed.
    """
    config_yaml = """
    seed: 42
    paths:
      dfsar_path: "datasets/raw/dfsar"
      ohrc_path: "datasets/raw/ohrc"
      output_dir: "outputs"
      log_dir: "logs"
    preprocessing:
      target_resolution_m: 5.0
      nodata_value: -9999.0
      normalize: true
      dfsar_backscatter_min_db: -40.0
      dfsar_backscatter_max_db: 5.0
    alignment:
      target_crs: "auto"
      resampling_method: "bilinear"
    validation:
      allowed_formats:
        - ".tif"
        - ".tiff"
      min_data_percentage: 10.0
      crs_check: true
    """
    config_file = tmp_path / "default_config.yaml"
    config_file.write_text(config_yaml)
    
    config = load_config(str(config_file))
    assert isinstance(config, PHSEConfig)
    assert config.seed == 42
    assert config.paths.dfsar_path == "datasets/raw/dfsar"
    assert config.preprocessing.target_resolution_m == 5.0
    assert config.preprocessing.normalize is True
    assert config.alignment.resampling_method == "bilinear"

def test_load_invalid_config(tmp_path):
    """
    Verifies that an incomplete or invalid YAML configuration raises a Pydantic ValidationError.
    """
    # Missing 'paths' entirely, which is required
    config_yaml = """
    seed: 100
    preprocessing:
      target_resolution_m: 10.0
      nodata_value: -999.0
    """
    config_file = tmp_path / "invalid_config.yaml"
    config_file.write_text(config_yaml)
    
    with pytest.raises(ValidationError):
        load_config(str(config_file))

def test_non_existent_config():
    """
    Verifies that trying to load a non-existent config path raises a FileNotFoundError.
    """
    with pytest.raises(FileNotFoundError):
        load_config("non_existent_file.yaml")
