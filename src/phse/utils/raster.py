import os
import logging
from typing import List, Tuple, Optional
import numpy as np
import rasterio
from rasterio.transform import Affine, from_origin
from phse.models import RasterLayer, RasterMetadata

logger = logging.getLogger("phse")

def save_raster_to_tiff(layer: RasterLayer, file_path: str) -> str:
    """
    Saves a RasterLayer instance to a standard physical GeoTIFF file.
    
    Args:
        layer (RasterLayer): The in-memory raster layer.
        file_path (str): Target file path.
        
    Returns:
        str: Absolute path to the saved file.
    """
    # Ensure directory exists
    dir_name = os.path.dirname(file_path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
        
    abs_path = os.path.abspath(file_path)
    logger.info(f"Saving raster layer '{layer.name}' to GeoTIFF at {abs_path}")
    
    try:
        crs = rasterio.crs.CRS.from_wkt(layer.metadata.crs_wkt)
        transform = Affine(*layer.metadata.transform)
        
        with rasterio.open(
            abs_path,
            'w',
            driver='GTiff',
            height=layer.metadata.height,
            width=layer.metadata.width,
            count=1,
            dtype=layer.metadata.dtype,
            crs=crs,
            transform=transform,
            nodata=layer.metadata.nodata
        ) as dst:
            dst.write(layer.data.astype(layer.metadata.dtype), 1)
            
            # Save additional tags if any
            if layer.metadata.additional_metadata:
                tags = {k: str(v) for k, v in layer.metadata.additional_metadata.items() if isinstance(v, (str, int, float))}
                dst.update_tags(**tags)
                
    except Exception as e:
        logger.error(f"Failed to save raster to {abs_path}. Error: {e}")
        raise RuntimeError(f"Failed to save raster file: {e}")
        
    return abs_path

def create_synthetic_raster(
    file_path: str,
    width: int = 100,
    height: int = 100,
    crs_wkt: Optional[str] = None,
    transform: Optional[List[float]] = None,
    nodata: float = -9999.0,
    val_range: Tuple[float, float] = (0.0, 1.0),
    seed: int = 42
) -> str:
    """
    Generates a georeferenced synthetic GeoTIFF file with random noise and some nodata regions.
    Used for testing the pipeline when actual satellite datasets are unavailable.
    
    Args:
        file_path (str): Target output file path.
        width (int): Target width in pixels.
        height (int): Target height in pixels.
        crs_wkt (str, optional): Target coordinate reference system.
        transform (List[float], optional): Target affine transformation.
        nodata (float): Pixel value representing no-data.
        val_range (Tuple[float, float]): Min and max values for random generation.
        seed (int): Random seed.
        
    Returns:
        str: Absolute path to the generated file.
    """
    os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
    np.random.seed(seed)
    
    # Generate random continuous floating point array
    data = np.random.uniform(val_range[0], val_range[1], (height, width)).astype(np.float32)
    
    # Inject 5% nodata values
    nodata_mask = np.random.choice([True, False], size=data.shape, p=[0.05, 0.95])
    data[nodata_mask] = nodata
    
    # Default Moon 2000 Geographic CRS if none provided
    if crs_wkt is None:
        crs_wkt = (
            'GEOGCS["GCS_Moon_2000",'
            'DATUM["D_Moon_2000",SPHEROID["Moon_2000_Spheroid",1737400.0,0.0]],'
            'PRIMEM["Reference_Meridian",0.0],'
            'UNIT["Degree",0.017453292519943295]]'
        )
        
    # Default coordinate transform if none provided
    if transform is None:
        # Origin near polar regions: 0.0 longitude, -80.0 latitude (Lunar polar regions)
        t = from_origin(0.0, -80.0, 0.0001, 0.0001)
        transform = [t.a, t.b, t.c, t.d, t.e, t.f]
        
    abs_path = os.path.abspath(file_path)
    logger.debug(f"Creating synthetic raster at {abs_path} ({width}x{height})")
    
    with rasterio.open(
        abs_path,
        'w',
        driver='GTiff',
        height=height,
        width=width,
        count=1,
        dtype='float32',
        crs=rasterio.crs.CRS.from_wkt(crs_wkt),
        transform=Affine(*transform),
        nodata=nodata
    ) as dst:
        dst.write(data, 1)
        
    return abs_path
