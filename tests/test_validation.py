import os
import pytest
import numpy as np
from phse.config import PHSEConfig, PathsConfig, PreprocessingConfig, AlignmentConfig, ValidationConfig
from phse.processing.validation import ValidationPipeline
from phse.models import RasterLayer, RasterMetadata
from phse.utils.raster import create_synthetic_raster

@pytest.fixture
def test_config():
    """
    Provides a standard configuration fixture for validation testing.
    """
    return PHSEConfig(
        seed=42,
        paths=PathsConfig(
            dfsar_path="datasets/raw/dfsar",
            ohrc_path="datasets/raw/ohrc",
            output_dir="outputs",
            log_dir="logs"
        ),
        preprocessing=PreprocessingConfig(
            target_resolution_m=5.0,
            nodata_value=-9999.0,
            normalize=True,
            dfsar_backscatter_min_db=-40.0,
            dfsar_backscatter_max_db=5.0
        ),
        alignment=AlignmentConfig(
            target_crs="auto",
            resampling_method="bilinear"
        ),
        validation=ValidationConfig(
            allowed_formats=[".tif", ".tiff"],
            min_data_percentage=20.0,
            crs_check=True
        )
    )

def test_validation_file_path(test_config, tmp_path):
    """
    Tests file path existence and format validation.
    """
    validator = ValidationPipeline(test_config)
    
    # Missing file
    assert validator.validate_file_path(os.path.join(tmp_path, "does_not_exist.tif")) is False
    
    # Unsupported extension
    invalid_file = os.path.join(tmp_path, "sample.txt")
    with open(invalid_file, "w") as f:
        f.write("text content")
    assert validator.validate_file_path(invalid_file) is False
    
    # Supported extension, exists
    valid_file = os.path.join(tmp_path, "sample.tif")
    with open(valid_file, "w") as f:
        f.write("")
    assert validator.validate_file_path(valid_file) is True

def test_validation_data_density(test_config):
    """
    Tests checking the ratio of valid data pixels.
    """
    validator = ValidationPipeline(test_config)
    
    meta = RasterMetadata(
        crs_wkt="GEOGCS[\"GCS_Moon_2000\"]",
        transform=[1, 0, 0, 0, 1, 0],
        width=10,
        height=10,
        dtype="float32",
        bounds={"left": 0.0, "bottom": 0.0, "right": 10.0, "top": 10.0},
        nodata=-9999.0
    )
    
    # 1. High density (90% valid, 10% nodata)
    data_high = np.ones((10, 10), dtype=np.float32)
    data_high[0, :] = -9999.0  # 10 nodata pixels
    layer_high = RasterLayer("high_density", data_high, meta)
    assert validator.validate_data_density(layer_high) is True
    
    # 2. Low density (10% valid, 90% nodata)
    data_low = np.full((10, 10), -9999.0, dtype=np.float32)
    data_low[0, :] = 1.0  # only 10 valid pixels (10%)
    layer_low = RasterLayer("low_density", data_low, meta)
    # The config threshold is 20.0%, so this should fail
    assert validator.validate_data_density(layer_low) is False
