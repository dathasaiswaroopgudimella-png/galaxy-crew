import logging
import numpy as np
from typing import Dict, Tuple, Optional
from phse.models import RasterLayer, RasterMetadata

logger = logging.getLogger("phse")

class ResourceEstimator:
    """
    Estimates subsurface water ice volume and mass distributions based on
    probabilistic reasoning maps, soil parameters, and radar penetration limits.
    """
    def __init__(
        self,
        default_penetration_depth_m: float = 2.0,
        regolith_porosity: float = 0.4,
        ice_pore_saturation: float = 0.25,
        ice_density_kg_m3: float = 917.0
    ):
        self.default_penetration_depth_m = default_penetration_depth_m
        self.regolith_porosity = regolith_porosity
        self.ice_pore_saturation = ice_pore_saturation
        self.ice_density_kg_m3 = ice_density_kg_m3

    def estimate_ice_resources(
        self,
        ice_probability_layer: RasterLayer
    ) -> Tuple[RasterLayer, float, float]:
        """
        Computes spatial distribution of ice volume density and returns total integrated volume and mass.
        
        Returns:
            Tuple[ice_density_layer, total_volume_m3, total_mass_metric_tons]
        """
        logger.info("Estimating subsurface water ice resource distributions...")
        
        prob_data = ice_probability_layer.data
        metadata = ice_probability_layer.metadata
        nodata = metadata.nodata
        
        # Calculate pixel area in square meters from affine transform: |a * e|
        cell_size_x = abs(metadata.transform[0])
        cell_size_y = abs(metadata.transform[4])
        pixel_area = cell_size_x * cell_size_y
        
        mask = (prob_data == nodata) | np.isnan(prob_data) | np.isinf(prob_data)
        
        # Compute local ice volume per pixel:
        # Volume (m3) = Area (m2) * Depth (m) * Porosity * Saturation * Probability
        local_volume = np.zeros_like(prob_data, dtype=np.float32)
        local_volume[~mask] = (
            pixel_area *
            self.default_penetration_depth_m *
            self.regolith_porosity *
            self.ice_pore_saturation *
            prob_data[~mask]
        )
        local_volume[mask] = nodata
        
        # Compute total sum (ignoring nodata mask)
        total_volume_m3 = float(np.sum(local_volume[~mask]))
        total_mass_kg = total_volume_m3 * self.ice_density_kg_m3
        total_mass_tons = total_mass_kg / 1000.0 # Convert to metric tons
        
        # Create output density layer representing local mass density in kg/m2
        mass_density = np.zeros_like(prob_data, dtype=np.float32)
        mass_density[~mask] = (local_volume[~mask] * self.ice_density_kg_m3) / pixel_area
        mass_density[mask] = nodata
        
        density_metadata = metadata.model_copy(deep=True)
        density_metadata.dtype = "float32"
        density_metadata.nodata = nodata
        
        ice_density_layer = RasterLayer(
            name="subsurface_ice_mass_density",
            data=mass_density,
            metadata=density_metadata,
            sources=list(ice_probability_layer.sources)
        )
        
        ice_density_layer.record_step(
            module="phse.mission.resource",
            action="estimate_ice_resources",
            parameters={
                "penetration_depth_m": self.default_penetration_depth_m,
                "regolith_porosity": self.regolith_porosity,
                "ice_pore_saturation": self.ice_pore_saturation,
                "total_volume_m3": total_volume_m3,
                "total_mass_metric_tons": total_mass_tons
            }
        )
        
        logger.info(f"Subsurface resource analysis complete. Total Volume: {total_volume_m3:.2f} m3, Total Mass: {total_mass_tons:.2f} metric tons.")
        return ice_density_layer, total_volume_m3, total_mass_tons
