import os
import pytest
import numpy as np
from phse.loaders.dfsar import DFSARLoader
from phse.loaders.ohrc import OHRCLoader
from phse.utils.raster import create_synthetic_raster
from phse.models import RasterLayer

def test_dfsar_loader_success(tmp_path):
    """
    Verifies that DFSARLoader correctly loads a valid GeoTIFF file.
    """
    raster_file = os.path.join(tmp_path, "dfsar_sample.tif")
    create_synthetic_raster(raster_file, width=40, height=30, nodata=-9999.0)
    
    loader = DFSARLoader(nodata_value=-9999.0)
    assert loader.validate(raster_file) is True
    
    layer = loader.load(raster_file)
    assert isinstance(layer, RasterLayer)
    assert layer.name == "dfsar_sample"
    assert layer.data.shape == (30, 40)  # height, width
    assert layer.metadata.nodata == -9999.0
    assert len(layer.provenance) == 1
    assert layer.provenance[0].module == "phse.loaders.dfsar"
    assert layer.provenance[0].action == "load"

def test_dfsar_loader_invalid_file(tmp_path):
    """
    Verifies that DFSARLoader raises ValueError for non-existent or corrupt files.
    """
    loader = DFSARLoader()
    
    # Test non-existent file
    with pytest.raises(ValueError):
        loader.load(os.path.join(tmp_path, "missing_file.tif"))
        
    # Test corrupt file
    corrupt_file = os.path.join(tmp_path, "corrupt_file.tif")
    with open(corrupt_file, "w") as f:
        f.write("This is definitely not a GeoTIFF image")
        
    assert loader.validate(corrupt_file) is False
    with pytest.raises(ValueError):
        loader.load(corrupt_file)

def test_ohrc_loader_success(tmp_path):
    """
    Verifies that OHRCLoader correctly loads a valid optical imagery file.
    """
    raster_file = os.path.join(tmp_path, "ohrc_sample.tif")
    create_synthetic_raster(raster_file, width=20, height=20, nodata=0.0)
    
    loader = OHRCLoader(nodata_value=0.0)
    assert loader.validate(raster_file) is True
    
    layer = loader.load(raster_file)
    assert isinstance(layer, RasterLayer)
    assert layer.name == "ohrc_sample"
    assert layer.data.shape == (20, 20)
    assert layer.metadata.nodata == 0.0
