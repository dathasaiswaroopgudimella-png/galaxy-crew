from abc import ABC, abstractmethod
from phse.models import RasterLayer

class BaseLoader(ABC):
    """
    Abstract Base Class for Chandrayaan-2 spatial dataset loaders.
    Any custom loader (e.g., DFSAR, OHRC) must implement this interface.
    """
    
    @abstractmethod
    def load(self, file_path: str) -> RasterLayer:
        """
        Loads the dataset at the given filepath into a RasterLayer.
        
        Args:
            file_path (str): Absolute or relative file path to the raster data.
            
        Returns:
            RasterLayer: Loaded raster layer.
            
        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the file has an unsupported format or is corrupt.
        """
        pass

    @abstractmethod
    def validate(self, file_path: str) -> bool:
        """
        Performs quick validation of the file at the given path (existence, structure).
        
        Args:
            file_path (str): Path to the raster file.
            
        Returns:
            bool: True if valid, False otherwise.
        """
        pass
