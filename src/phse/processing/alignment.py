import logging
from typing import Dict, Any, List
import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling
from rasterio.transform import Affine
from phse.models import RasterLayer, RasterMetadata

logger = logging.getLogger("phse")

def align_rasters(
    source: RasterLayer, 
    reference: RasterLayer, 
    resampling_method: str = "bilinear"
) -> RasterLayer:
    """
    Reprojects and resamples a source raster layer to align perfectly with the spatial
    bounds, pixel size, dimensions, and coordinate reference system (CRS) of a reference raster layer.
    
    This process is performed entirely in-memory using rasterio's warp.reproject.
    
    Args:
        source (RasterLayer): The layer to be reprojected/aligned.
        reference (RasterLayer): The template layer defining the target geometry.
        resampling_method (str): The resampling algorithm ('nearest', 'bilinear', 'cubic', 'lanczos').
        
    Returns:
        RasterLayer: A new aligned raster layer.
    """
    logger.info(f"Aligning raster '{source.name}' to match geometry of '{reference.name}' using '{resampling_method}' resampling.")
    
    # Map string to rasterio Resampling enumeration
    resampling_map = {
        "nearest": Resampling.nearest,
        "bilinear": Resampling.bilinear,
        "cubic": Resampling.cubic,
        "lanczos": Resampling.lanczos
    }
    
    resample_algo = resampling_map.get(resampling_method.lower(), Resampling.bilinear)
    
    # Build CRS objects
    try:
        src_crs = rasterio.crs.CRS.from_wkt(source.metadata.crs_wkt)
        dst_crs = rasterio.crs.CRS.from_wkt(reference.metadata.crs_wkt)
    except Exception as e:
        logger.error(f"Error parsing coordinate reference systems: {e}")
        raise ValueError(f"Failed to parse CRS from metadata. Source CRS: {source.metadata.crs_wkt[:100]}... Reference CRS: {reference.metadata.crs_wkt[:100]}")
        
    # Reconstruct Affine transforms from [a, b, c, d, e, f] format
    src_transform = Affine(*source.metadata.transform)
    dst_transform = Affine(*reference.metadata.transform)
    
    # Initialize output array filled with target nodata
    dst_data = np.full(
        (reference.metadata.height, reference.metadata.width), 
        reference.metadata.nodata, 
        dtype=np.float32
    )
    
    # Execute reprojection in-memory
    try:
        reproject(
            source=source.data,
            destination=dst_data,
            src_transform=src_transform,
            src_crs=src_crs,
            src_nodata=source.metadata.nodata,
            dst_transform=dst_transform,
            dst_crs=dst_crs,
            dst_nodata=reference.metadata.nodata,
            resampling=resample_algo
        )
    except Exception as e:
        logger.error(f"Reprojection failed: {e}")
        raise RuntimeError(f"Reprojection execution failed: {e}")
        
    # Create aligned metadata copying target attributes
    aligned_metadata = RasterMetadata(
        crs_wkt=reference.metadata.crs_wkt,
        transform=list(reference.metadata.transform),
        width=reference.metadata.width,
        height=reference.metadata.height,
        dtype=str(dst_data.dtype),
        bounds=dict(reference.metadata.bounds),
        nodata=reference.metadata.nodata,
        additional_metadata={
            "source_original_name": source.name,
            "alignment_resampling": resampling_method
        }
    )
    
    # Merge source files for provenance tracking
    combined_sources = list(set(source.sources + reference.sources))
    
    # Combine provenance steps
    combined_provenance = [p.model_copy(deep=True) for p in source.provenance]
    
    aligned_layer = RasterLayer(
        name=f"{source.name}_aligned",
        data=dst_data,
        metadata=aligned_metadata,
        sources=combined_sources,
        provenance=combined_provenance
    )
    
    aligned_layer.record_step(
        module="phse.processing.alignment",
        action="align_rasters",
        parameters={
            "resampling_method": resampling_method,
            "target_dimensions": [reference.metadata.width, reference.metadata.height],
            "reference_layer": reference.name
        }
    )
    
    logger.info(f"Successfully aligned raster. New shape: {dst_data.shape}")
    return aligned_layer
