import numpy as np
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class ProvenanceStep(BaseModel):
    """
    Represents a single step in the data processing pipeline for tracking data provenance.
    """
    module: str = Field(description="Name of the producing module")
    action: str = Field(description="Action/operation performed")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Parameters used during the operation")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat(), description="UTC timestamp of the action")
    config_version: str = Field(default="1.0.0", description="Configuration schema version")

class RasterMetadata(BaseModel):
    """
    Structured metadata representing spatial coordinate frame and attributes of a raster.
    """
    crs_wkt: str = Field(description="WKT (Well-Known Text) representation of the CRS")
    transform: List[float] = Field(description="Affine transform parameters: [a, b, c, d, e, f]")
    width: int = Field(description="Width in pixels")
    height: int = Field(description="Height in pixels")
    dtype: str = Field(description="Data type of the raster array (e.g. float32)")
    bounds: Dict[str, float] = Field(description="Bounding box dict with keys 'left', 'bottom', 'right', 'top'")
    nodata: float = Field(description="Value indicating no-data or missing pixels")
    additional_metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom metadata key-values")

class RasterLayer:
    """
    In-memory representation of a single physical raster layer.
    Combines the underlying numpy array, spatial metadata, and processing history (provenance).
    """
    def __init__(
        self,
        name: str,
        data: np.ndarray,
        metadata: RasterMetadata,
        sources: Optional[List[str]] = None,
        provenance: Optional[List[ProvenanceStep]] = None
    ):
        """
        Initializes a RasterLayer.
        
        Args:
            name (str): Distinct name of the layer (e.g., 'ohrc_pan', 'dfsar_cpr')
            data (np.ndarray): 2D numeric numpy array of shape (height, width)
            metadata (RasterMetadata): Spatial coordinate/transform metadata
            sources (List[str], optional): List of raw source files contributing to this layer
            provenance (List[ProvenanceStep], optional): List of prior processing steps
        """
        self.name = name
        self.data = data
        self.metadata = metadata
        self.sources = sources or []
        self.provenance = provenance or []

    def record_step(self, module: str, action: str, parameters: Dict[str, Any]):
        """
        Appends a processing step to this layer's data provenance.
        """
        step = ProvenanceStep(
            module=module,
            action=action,
            parameters=parameters
        )
        self.provenance.append(step)

    def clone(self) -> 'RasterLayer':
        """
        Creates a deep copy of the layer including the array and metadata.
        """
        return RasterLayer(
            name=self.name,
            data=self.data.copy(),
            metadata=self.metadata.model_copy(deep=True),
            sources=list(self.sources),
            provenance=[p.model_copy(deep=True) for p in self.provenance]
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Returns a dictionary summary of the layer's metadata and provenance.
        """
        return {
            "name": self.name,
            "metadata": self.metadata.model_dump(),
            "sources": self.sources,
            "provenance": [step.model_dump() for step in self.provenance]
        }

class DatasetGroup:
    """
    A collection of spatially aligned RasterLayers that share a common coordinate framework.
    Suitable for feeding into down-stream scientific reasoning and physics representation layers.
    """
    def __init__(self, name: str, layers: Optional[Dict[str, RasterLayer]] = None):
        self.name = name
        self.layers = layers or {}

    def add_layer(self, layer: RasterLayer):
        """Adds or overwrites a raster layer inside the dataset group."""
        self.layers[layer.name] = layer

    def get_layer(self, name: str) -> Optional[RasterLayer]:
        """Retrieves a layer by name, returning None if not found."""
        return self.layers.get(name)

    def keys(self) -> List[str]:
        """Returns the list of layer names in the group."""
        return list(self.layers.keys())
