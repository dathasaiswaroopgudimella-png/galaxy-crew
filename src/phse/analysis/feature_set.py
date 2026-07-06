import numpy as np
from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from phse.models import RasterLayer, ProvenanceStep

class LayerQualityMetrics(BaseModel):
    """
    Quality metrics computed for a single scientific feature layer.
    """
    mean: float = Field(description="Arithmetic mean of valid pixels")
    std: float = Field(description="Standard deviation of valid pixels")
    min_val: float = Field(description="Minimum value of valid pixels")
    max_val: float = Field(description="Maximum value of valid pixels")
    valid_percentage: float = Field(description="Percentage of pixels containing valid data")
    nodata_count: int = Field(description="Number of pixels marked as nodata")

class PhysicsFeatureRepresentation:
    """
    Aggregates all derived scientific features, metadata, quality metrics,
    and provenance history into a single structured PFR container.
    """
    def __init__(
        self,
        config_version: str = "1.0.0",
        layers: Optional[Dict[str, RasterLayer]] = None,
        quality_metrics: Optional[Dict[str, LayerQualityMetrics]] = None,
        creation_time: Optional[str] = None
    ):
        self.config_version = config_version
        self.layers = layers or {}
        self.quality_metrics = quality_metrics or {}
        self.creation_time = creation_time or datetime.utcnow().isoformat()

    def add_layer(self, layer: RasterLayer):
        """
        Adds a derived scientific layer and automatically computes its quality metrics.
        """
        self.layers[layer.name] = layer
        self.quality_metrics[layer.name] = self._compute_quality_metrics(layer)

    def _compute_quality_metrics(self, layer: RasterLayer) -> LayerQualityMetrics:
        """
        Calculates descriptive statistical metrics for the given raster layer, ignoring nodata and infs.
        """
        nodata = layer.metadata.nodata
        data = layer.data
        
        # Mask nodata and non-finite values
        mask = (data == nodata) | np.isnan(data) | np.isinf(data)
        valid_data = data[~mask]
        
        nodata_count = int(np.sum(mask))
        total_pixels = data.size
        valid_percentage = (valid_data.size / total_pixels) * 100.0 if total_pixels > 0 else 0.0
        
        if valid_data.size == 0:
            return LayerQualityMetrics(
                mean=0.0,
                std=0.0,
                min_val=0.0,
                max_val=0.0,
                valid_percentage=0.0,
                nodata_count=nodata_count
            )
            
        return LayerQualityMetrics(
            mean=float(np.mean(valid_data)),
            std=float(np.std(valid_data)),
            min_val=float(np.min(valid_data)),
            max_val=float(np.max(valid_data)),
            valid_percentage=valid_percentage,
            nodata_count=nodata_count
        )

    def get_provenance_history(self) -> List[ProvenanceStep]:
        """
        Aggregates all unique provenance steps from all active layers in the representation.
        """
        seen_timestamps = set()
        combined_provenance = []
        
        for layer in self.layers.values():
            for step in layer.provenance:
                # Deduplicate by action and timestamp
                key = (step.action, step.timestamp)
                if key not in seen_timestamps:
                    seen_timestamps.add(key)
                    combined_provenance.append(step)
                    
        # Sort chronologically
        combined_provenance.sort(key=lambda x: x.timestamp)
        return combined_provenance

    def to_dict(self) -> Dict[str, Any]:
        """
        Serializes PFR summary information (excluding massive raw raster arrays) into a dictionary.
        """
        return {
            "config_version": self.config_version,
            "creation_time": self.creation_time,
            "layers": {name: layer.to_dict() for name, layer in self.layers.items()},
            "quality_metrics": {name: metrics.model_dump() for name, metrics in self.quality_metrics.items()},
            "history": [step.model_dump() for step in self.get_provenance_history()]
        }
