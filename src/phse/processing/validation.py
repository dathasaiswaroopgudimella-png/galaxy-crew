import os
import logging
from typing import List, Dict, Any
import rasterio
import numpy as np
from phse.config import PHSEConfig
from phse.models import RasterLayer

logger = logging.getLogger("phse")

class ValidationPipeline:
    """
    Validates Chandrayaan-2 inputs, preprocessed outputs, and alignments
    to prevent pipeline crashes and scientific errors.
    """
    
    def __init__(self, config: PHSEConfig):
        """
        Initializes the validation pipeline with configuration parameters.
        """
        self.config = config

    def validate_file_path(self, file_path: str) -> bool:
        """
        Checks if the file exists and has an allowed format.
        """
        if not os.path.exists(file_path):
            logger.error(f"Validation Error: File does not exist at {file_path}")
            return False
            
        ext = os.path.splitext(file_path)[1].lower()
        if ext not in self.config.validation.allowed_formats:
            logger.error(f"Validation Error: File extension '{ext}' for file {file_path} is not in allowed formats: {self.config.validation.allowed_formats}")
            return False
            
        return True

    def validate_raster_integrity(self, file_path: str) -> bool:
        """
        Verifies that a raster file can be opened and contains valid data bands and size.
        """
        if not self.validate_file_path(file_path):
            return False
            
        try:
            with rasterio.open(file_path) as src:
                if src.width <= 0 or src.height <= 0:
                    logger.error(f"Validation Error: Raster '{file_path}' has invalid dimensions: {src.width}x{src.height}")
                    return False
                if src.count == 0:
                    logger.error(f"Validation Error: Raster '{file_path}' contains zero data bands")
                    return False
                if self.config.validation.crs_check and src.crs is None:
                    logger.error(f"Validation Error: Raster '{file_path}' does not contain coordinate reference system (CRS)")
                    return False
        except Exception as e:
            logger.error(f"Validation Error: Raster '{file_path}' is corrupted or unreadable. Detail: {e}")
            return False
            
        return True

    def validate_data_density(self, layer: RasterLayer) -> bool:
        """
        Validates if the layer contains a sufficient percentage of valid (non-nodata) data pixels.
        
        Args:
            layer (RasterLayer): The loaded raster layer.
            
        Returns:
            bool: True if valid pixel density is equal or greater than threshold.
        """
        nodata = layer.metadata.nodata
        total_pixels = layer.data.size
        
        # Mask valid pixels (not nodata and not nan/inf)
        invalid_mask = (layer.data == nodata) | np.isnan(layer.data) | np.isinf(layer.data)
        valid_pixels = total_pixels - np.sum(invalid_mask)
        valid_pct = (valid_pixels / total_pixels) * 100.0
        
        threshold = self.config.validation.min_data_percentage
        
        if valid_pct < threshold:
            logger.error(f"Validation Error: Layer '{layer.name}' has only {valid_pct:.2f}% valid data, which is below the minimum threshold of {threshold:.2f}%")
            return False
            
        logger.info(f"Layer '{layer.name}' data density check passed: {valid_pct:.2f}% valid pixels")
        return True

    def validate_crs_compatibility(self, layer_a: RasterLayer, layer_b: RasterLayer) -> bool:
        """
        Checks if the coordinate systems of two layers are comparable or reprojectable.
        """
        if not layer_a.metadata.crs_wkt or not layer_b.metadata.crs_wkt:
            logger.error("Validation Error: One or both layers are missing WKT CRS definitions.")
            return False
            
        try:
            crs_a = rasterio.crs.CRS.from_wkt(layer_a.metadata.crs_wkt)
            crs_b = rasterio.crs.CRS.from_wkt(layer_b.metadata.crs_wkt)
            
            # They are compatible as long as they represent valid coordinate systems
            if crs_a == crs_b:
                logger.info(f"CRS Match: Both '{layer_a.name}' and '{layer_b.name}' share identical coordinate reference systems.")
            else:
                logger.info(f"CRS Mismatch (Reprojection required): '{layer_a.name}' and '{layer_b.name}' use different coordinate systems. Alignment will reproject.")
        except Exception as e:
            logger.error(f"Validation Error: CRS evaluation failed: {e}")
            return False
            
        return True
