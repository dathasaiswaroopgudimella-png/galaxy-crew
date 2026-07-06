import os
import pytest
import numpy as np
from rasterio.transform import from_origin
from phse.models import RasterLayer, RasterMetadata
from phse.processing.preprocessing import preprocess_layer
from phse.processing.alignment import align_rasters
from phse.utils.raster import create_synthetic_raster
from phse.loaders.dfsar import DFSARLoader

def test_preprocessing_normalization():
    """
    Tests float casting, NaN handling, and min-max normalization.
    """
    # Create manual metadata
    crs_wkt = (
        'GEOGCS["GCS_Moon_2000",'
        'DATUM["D_Moon_2000",SPHEROID["Moon_2000_Spheroid",1737400.0,0.0]],'
        'PRIMEM["Reference_Meridian",0.0],'
        'UNIT["Degree",0.017453292519943295]]'
    )
    t = from_origin(0.0, -80.0, 0.0001, 0.0001)
    transform = [t.a, t.b, t.c, t.d, t.e, t.f]
    
    meta = RasterMetadata(
        crs_wkt=crs_wkt,
        transform=transform,
        width=5,
        height=5,
        dtype="float32",
        bounds={"left": 0.0, "bottom": -80.0005, "right": 0.0005, "top": -80.0},
        nodata=-9999.0
    )
    
    # Grid containing values, NaNs, and nodata
    data = np.array([
        [1.0, 2.0, 3.0, 4.0, 5.0],
        [1.0, np.nan, 2.0, 3.0, 4.0],
        [-9999.0, 1.0, 5.0, 1.0, 1.0],
        [3.0, 3.0, 3.0, np.inf, 3.0],
        [0.0, 1.0, 2.0, 3.0, 4.0]
    ], dtype=np.float32)
    
    layer = RasterLayer(name="raw_layer", data=data, metadata=meta)
    
    # Preprocess with normalization
    processed = preprocess_layer(layer, normalize=True)
    
    # Check that NaN and Inf are replaced by nodata
    assert processed.data[1, 1] == -9999.0
    assert processed.data[3, 3] == -9999.0
    
    # Check bounds of normalized values (excluding nodata)
    valid_mask = processed.data != -9999.0
    valid_data = processed.data[valid_mask]
    assert np.all(valid_data >= 0.0)
    assert np.all(valid_data <= 1.0)
    
    # Verify that maximum value maps to 1.0 (original max was 5.0) and min maps to 0.0 (original min was 0.0)
    assert processed.data[0, 4] == 1.0  # original 5.0
    assert processed.data[4, 0] == 0.0  # original 0.0

def test_raster_alignment(tmp_path):
    """
    Tests reprojection/resampling of a source raster to match a reference raster grid.
    """
    # 1. Create a reference raster (e.g., 20x20 pixels, origin at 0, -80)
    ref_file = os.path.join(tmp_path, "reference.tif")
    ref_crs_wkt = (
        'GEOGCS["GCS_Moon_2000",'
        'DATUM["D_Moon_2000",SPHEROID["Moon_2000_Spheroid",1737400.0,0.0]],'
        'PRIMEM["Reference_Meridian",0.0],'
        'UNIT["Degree",0.017453292519943295]]'
    )
    # pixel resolution 0.0002
    ref_t = from_origin(0.0, -80.0, 0.0002, 0.0002)
    ref_transform = [ref_t.a, ref_t.b, ref_t.c, ref_t.d, ref_t.e, ref_t.f]
    create_synthetic_raster(ref_file, width=20, height=20, crs_wkt=ref_crs_wkt, transform=ref_transform, nodata=-9999.0)
    
    # 2. Create a source raster (e.g., 10x10 pixels, offset origin, different resolution 0.0004)
    src_file = os.path.join(tmp_path, "source.tif")
    src_t = from_origin(0.0001, -80.0001, 0.0004, 0.0004)
    src_transform = [src_t.a, src_t.b, src_t.c, src_t.d, src_t.e, src_t.f]
    create_synthetic_raster(src_file, width=10, height=10, crs_wkt=ref_crs_wkt, transform=src_transform, nodata=-9999.0)
    
    loader = DFSARLoader(nodata_value=-9999.0)
    ref_layer = loader.load(ref_file)
    src_layer = loader.load(src_file)
    
    # Execute alignment
    aligned_layer = align_rasters(src_layer, ref_layer, resampling_method="nearest")
    
    # Assertions
    assert aligned_layer.data.shape == ref_layer.data.shape
    assert aligned_layer.metadata.width == ref_layer.metadata.width
    assert aligned_layer.metadata.height == ref_layer.metadata.height
    assert aligned_layer.metadata.transform == ref_layer.metadata.transform
    assert aligned_layer.metadata.crs_wkt == ref_layer.metadata.crs_wkt
    assert len(aligned_layer.provenance) > len(src_layer.provenance)
