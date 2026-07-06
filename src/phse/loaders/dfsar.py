import os
import logging
import numpy as np
import rasterio
from phse.loaders.base import BaseLoader
from phse.models import RasterLayer, RasterMetadata

logger = logging.getLogger("phse")

class DFSARLoader(BaseLoader):
    """
    Loader for Chandrayaan-2 DFSAR (Dual-Frequency Synthetic Aperture Radar) datasets.
    DFSAR products contain multi-polarized backscatter layers used to compute CPR and DOP.
    """
    
    def __init__(self, nodata_value: float = -9999.0):
        self.nodata_value = nodata_value

    def validate(self, file_path: str) -> bool:
        """
        Quick check of file existence, format validation, and structure.
        """
        if not os.path.exists(file_path):
            logger.warning(f"DFSAR validation failed: File not found at {file_path}")
            return False
            
        try:
            with rasterio.open(file_path) as src:
                if src.width <= 0 or src.height <= 0:
                    logger.warning(f"DFSAR validation failed: Invalid raster size in {file_path}")
                    return False
                if src.count < 1:
                    logger.warning(f"DFSAR validation failed: No bands found in {file_path}")
                    return False
                if src.crs is None:
                    logger.warning(f"DFSAR validation failed: CRS is missing in {file_path}")
                    return False
        except Exception as e:
            logger.warning(f"DFSAR validation failed: Failed to read {file_path}. Exception: {e}")
            return False
            
        return True

    def load(self, file_path: str) -> RasterLayer:
        """
        Loads the first band of DFSAR data from a georeferenced file.
        
        Args:
            file_path (str): File path to the DFSAR raster dataset.
            
        Returns:
            RasterLayer: Loaded raster dataset.
        """
        if not self.validate(file_path):
            raise ValueError(f"Invalid DFSAR raster dataset: {file_path}")
            
        logger.info(f"Loading DFSAR dataset from: {file_path}")
        
        with rasterio.open(file_path) as src:
            data = src.read(1)  # Load the primary polarization / intensity channel
            
            # Map rasterio metadata
            crs_wkt = src.crs.to_wkt()
            transform = [
                src.transform.a, src.transform.b, src.transform.c,
                src.transform.d, src.transform.e, src.transform.f
            ]
            bounds = {
                "left": src.bounds.left,
                "bottom": src.bounds.bottom,
                "right": src.bounds.right,
                "top": src.bounds.top
            }
            nodata = src.nodata if src.nodata is not None else self.nodata_value
            
            additional = {
                "driver": src.driver,
                "indexes": list(src.indexes),
                "count": src.count,
                "tags": src.tags()
            }
            
            meta = RasterMetadata(
                crs_wkt=crs_wkt,
                transform=transform,
                width=src.width,
                height=src.height,
                dtype=str(data.dtype),
                bounds=bounds,
                nodata=nodata,
                additional_metadata=additional
            )
            
            layer = RasterLayer(
                name=os.path.basename(file_path).split('.')[0],
                data=data.astype(np.float32),
                metadata=meta,
                sources=[os.path.abspath(file_path)]
            )
            
            layer.record_step(
                module="phse.loaders.dfsar",
                action="load",
                parameters={"filepath": os.path.abspath(file_path), "band": 1}
            )
            
            return layer
