import logging
from typing import Optional
import numpy as np
from phse.models import RasterLayer

logger = logging.getLogger("phse")

def normalize_raster(
    data: np.ndarray, 
    nodata: float, 
    min_val: Optional[float] = None, 
    max_val: Optional[float] = None
) -> np.ndarray:
    """
    Normalizes a 2D numpy array to [0, 1] using min-max scaling, ignoring nodata values.
    
    Args:
        data (np.ndarray): Input 2D numpy array.
        nodata (float): The value representing no-data in the array.
        min_val (float, optional): Custom minimum value for scaling. Defaults to actual min.
        max_val (float, optional): Custom maximum value for scaling. Defaults to actual max.
        
    Returns:
        np.ndarray: Normalized 2D numpy array.
    """
    # Create mask of invalid data
    mask = (data == nodata) | np.isnan(data) | np.isinf(data)
    valid_data = data[~mask]
    
    if valid_data.size == 0:
        logger.warning("Attempted to normalize an empty or completely nodata raster.")
        return data.copy()
        
    actual_min = min_val if min_val is not None else float(np.min(valid_data))
    actual_max = max_val if max_val is not None else float(np.max(valid_data))
    
    if actual_max == actual_min:
        logger.warning(f"Min and Max values are identical ({actual_min}) during normalization.")
        normalized = np.zeros_like(data)
    else:
        normalized = (data - actual_min) / (actual_max - actual_min)
        normalized = np.clip(normalized, 0.0, 1.0)
        
    # Reapply nodata mask
    normalized[mask] = nodata
    return normalized

def preprocess_layer(
    layer: RasterLayer, 
    normalize: bool = True, 
    min_val: Optional[float] = None, 
    max_val: Optional[float] = None
) -> RasterLayer:
    """
    Preprocesses a RasterLayer by casting to float32, replacing NaN/infs with nodata,
    and optionally normalizing valid values to the [0, 1] range.
    
    Args:
        layer (RasterLayer): The input raster layer.
        normalize (bool): Whether to perform [0, 1] min-max normalization.
        min_val (float, optional): Custom minimum value for scaling.
        max_val (float, optional): Custom maximum value for scaling.
        
    Returns:
        RasterLayer: A preprocessed clone of the input layer.
    """
    logger.info(f"Preprocessing raster layer '{layer.name}'")
    processed = layer.clone()
    
    # Cast to float32
    data = processed.data.astype(np.float32)
    nodata = processed.metadata.nodata
    
    # Replace any NaNs or Infinities with nodata
    invalid_mask = np.isnan(data) | np.isinf(data)
    num_invalid = np.sum(invalid_mask)
    if num_invalid > 0:
        logger.warning(f"Replaced {num_invalid} NaN/Inf values with nodata ({nodata}) in layer '{layer.name}'")
        data[invalid_mask] = nodata
        
    # Apply normalization
    if normalize:
        data = normalize_raster(data, nodata, min_val, max_val)
        
    processed.data = data
    processed.metadata.dtype = str(data.dtype)
    
    # Record step in data provenance
    processed.record_step(
        module="phse.processing.preprocessing",
        action="preprocess_layer",
        parameters={
            "normalize": normalize,
            "min_val": min_val,
            "max_val": max_val,
            "had_nan_or_inf": bool(num_invalid > 0)
        }
    )
    
    return processed
