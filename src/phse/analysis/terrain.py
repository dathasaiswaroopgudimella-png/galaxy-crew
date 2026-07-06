import logging
import numpy as np
from typing import Dict, Tuple, Optional
from scipy.ndimage import uniform_filter
from skimage.feature import blob_log
from phse.models import RasterLayer, RasterMetadata
from phse.analysis.config import TerrainConfig

logger = logging.getLogger("phse")

def compute_gradients(data: np.ndarray, cell_size_x: float, cell_size_y: float) -> Tuple[np.ndarray, np.ndarray]:
    """
    Computes horizontal and vertical gradients of a 2D elevation grid using Horn's method.
    Handles boundaries by padding with edge values.
    """
    # Pad array boundary by 1 pixel using edge replication
    padded = np.pad(data, 1, mode='edge')
    
    # Extract 3x3 neighbor slices
    # a b c
    # d e f
    # g h i
    a = padded[0:-2, 0:-2]
    b = padded[0:-2, 1:-1]
    c = padded[0:-2, 2:]
    d = padded[1:-1, 0:-2]
    f = padded[1:-1, 2:]
    g = padded[2:, 0:-2]
    h = padded[2:, 1:-1]
    i = padded[2:, 2:]
    
    # Compute rate of change in X (horizontal) and Y (vertical)
    dz_dx = ((c + 2.0*f + i) - (a + 2.0*d + g)) / (8.0 * cell_size_x)
    dz_dy = ((g + 2.0*h + i) - (a + 2.0*b + c)) / (8.0 * cell_size_y)
    
    return dz_dx, dz_dy

def extract_terrain_features(
    dem_layer: RasterLayer,
    pan_layer: Optional[RasterLayer],
    config: TerrainConfig
) -> Dict[str, RasterLayer]:
    """
    Computes terrain features from digital elevation models (DEM) and panchromatic camera (PAN) imagery:
      - Surface Slope (degrees)
      - Surface Roughness (RMS height deviation)
      - Illumination modeling (Hillshade)
      - Boulder density (Laplacian of Gaussian blob detection)
      - Terrain hazard map (weighted index of hazards)
      
    Args:
        dem_layer (RasterLayer): Digital Elevation Model representing lunar surface heights (meters)
        pan_layer (RasterLayer, optional): High-resolution panchromatic imagery (e.g. OHRC) for boulder detection
        config (TerrainConfig): Configuration settings
        
    Returns:
        Dict[str, RasterLayer]: Derived scientific terrain layers
    """
    logger.info("Extracting terrain features from DEM and PAN layers...")
    
    metadata = dem_layer.metadata.model_copy(deep=True)
    nodata = metadata.nodata
    data = dem_layer.data
    
    # Get pixel size (cell size) from affine transform
    # transform represents: [a, b, c, d, e, f] where:
    # a = cell_size_x, e = cell_size_y (usually negative)
    cell_size_x = abs(metadata.transform[0])
    cell_size_y = abs(metadata.transform[4])
    
    mask = (data == nodata) | np.isnan(data) | np.isinf(data)
    
    # Initialize output dictionary
    features: Dict[str, RasterLayer] = {}
    
    # 1. Surface Slope
    dz_dx, dz_dy = compute_gradients(data, cell_size_x, cell_size_y)
    slope_rad = np.arctan(np.sqrt(dz_dx**2 + dz_dy**2))
    slope_deg = np.degrees(slope_rad)
    slope_deg[mask] = nodata
    
    # 2. Surface Roughness (RMS Height Deviation in a local moving window)
    # RMS roughness = sqrt( <z^2> - <z>^2 ) which is the local standard deviation
    clean_data = data.copy()
    clean_data[mask] = 0.0
    
    weights = np.ones_like(data)
    weights[mask] = 0.0
    
    local_sum = uniform_filter(clean_data, size=config.roughness_window_size, mode='constant', cval=0.0) * (config.roughness_window_size ** 2)
    local_sum_sq = uniform_filter(clean_data**2, size=config.roughness_window_size, mode='constant', cval=0.0) * (config.roughness_window_size ** 2)
    local_weight = uniform_filter(weights, size=config.roughness_window_size, mode='constant', cval=0.0) * (config.roughness_window_size ** 2)
    
    mean_z = np.zeros_like(data)
    mean_z_sq = np.zeros_like(data)
    valid_weight = local_weight > 0
    
    mean_z[valid_weight] = local_sum[valid_weight] / local_weight[valid_weight]
    mean_z_sq[valid_weight] = local_sum_sq[valid_weight] / local_weight[valid_weight]
    
    variance = mean_z_sq - mean_z**2
    variance = np.clip(variance, 0.0, None)  # Prevent tiny negative numerical noise
    roughness = np.sqrt(variance)
    roughness[mask] = nodata
    
    # 3. Illumination Modeling (Hillshade)
    # Convert sun parameters to radians
    zenith_rad = np.radians(90.0 - config.sun_elevation_deg)
    azimuth_rad = np.radians(config.sun_azimuth_deg)
    
    # Sun vector components
    sun_x = np.sin(zenith_rad) * np.sin(azimuth_rad)
    sun_y = np.sin(zenith_rad) * np.cos(azimuth_rad)
    sun_z = np.cos(zenith_rad)
    
    # Aspect angle (direction of maximum slope)
    aspect_rad = np.arctan2(-dz_dy, dz_dx)
    
    # Standard Lambertian hillshade formula:
    # cos(zenith) * cos(slope) + sin(zenith) * sin(slope) * cos(azimuth - aspect)
    hillshade = np.cos(zenith_rad) * np.cos(slope_rad) + np.sin(zenith_rad) * np.sin(slope_rad) * np.cos(azimuth_rad - aspect_rad)
    hillshade = np.clip(hillshade, 0.0, 1.0)  # Value range [0, 1]
    hillshade[mask] = nodata
    
    # 4. Boulder Density (Blob detection on Panchromatic camera imagery)
    # If no pan_layer is provided, boulder density will be mocked or set to 0.
    boulder_density = np.zeros_like(data)
    
    if pan_layer is not None:
        pan_data = pan_layer.data.copy()
        pan_mask = (pan_data == pan_layer.metadata.nodata) | np.isnan(pan_data) | np.isinf(pan_data)
        
        # Normalize image to [0, 1] for blob detector
        pan_min, pan_max = np.min(pan_data[~pan_mask]), np.max(pan_data[~pan_mask])
        if pan_max > pan_min:
            pan_norm = (pan_data - pan_min) / (pan_max - pan_min)
        else:
            pan_norm = np.zeros_like(pan_data)
            
        # Detect blobs (boulders appear as bright features next to shadows)
        blobs = blob_log(
            pan_norm,
            min_sigma=config.boulder_min_sigma,
            max_sigma=config.boulder_max_sigma,
            num_sigma=config.boulder_num_sigma,
            threshold=config.boulder_threshold
        )
        
        # Generate boulder center count map
        boulder_centers = np.zeros_like(pan_norm)
        for blob in blobs:
            y, x, r = blob
            boulder_centers[int(y), int(x)] += 1.0
            
        # Smooth with sliding window to compute local density map (boulders in neighborhood)
        boulder_density = uniform_filter(boulder_centers, size=config.boulder_density_window_size, mode='constant', cval=0.0) * (config.boulder_density_window_size ** 2)
        boulder_density[mask] = nodata
    else:
        logger.warning("No panchromatic imagery provided. Boulder density defaults to zero.")
        boulder_density[mask] = nodata

    # 5. Terrain Hazard Estimation
    # Compute normalized indicators (values range [0, 1])
    h_slope = np.zeros_like(slope_deg)
    valid_slope = ~mask
    h_slope[valid_slope] = np.clip(slope_deg[valid_slope] / config.slope_threshold_critical, 0.0, 1.0)
    
    h_rough = np.zeros_like(roughness)
    h_rough[valid_slope] = np.clip(roughness[valid_slope] / config.roughness_threshold_critical, 0.0, 1.0)
    
    h_boulder = np.zeros_like(boulder_density)
    h_boulder[valid_slope] = np.clip(boulder_density[valid_slope] / config.boulder_density_threshold_critical, 0.0, 1.0)
    
    # Weighted hazard index
    hazard = (config.weight_slope * h_slope) + (config.weight_roughness * h_rough) + (config.weight_boulder * h_boulder)
    hazard[mask] = nodata
    
    # Construct layers
    features["terrain_slope"] = RasterLayer("terrain_slope", slope_deg, metadata, [dem_layer.sources[0]])
    features["terrain_roughness"] = RasterLayer("terrain_roughness", roughness, metadata, [dem_layer.sources[0]])
    features["terrain_illumination"] = RasterLayer("terrain_illumination", hillshade, metadata, [dem_layer.sources[0]])
    features["terrain_boulder_density"] = RasterLayer("terrain_boulder_density", boulder_density, metadata, [dem_layer.sources[0]] if pan_layer is None else [dem_layer.sources[0], pan_layer.sources[0]])
    features["terrain_hazard"] = RasterLayer("terrain_hazard", hazard, metadata, [dem_layer.sources[0]] if pan_layer is None else [dem_layer.sources[0], pan_layer.sources[0]])
    
    # Record provenance step on all generated layers
    for name, layer in features.items():
        layer.record_step(
            module="phse.analysis.terrain",
            action="extract_terrain_features",
            parameters={
                "slope_threshold_critical": config.slope_threshold_critical,
                "roughness_window_size": config.roughness_window_size,
                "roughness_threshold_critical": config.roughness_threshold_critical,
                "sun_elevation_deg": config.sun_elevation_deg,
                "sun_azimuth_deg": config.sun_azimuth_deg,
                "boulder_min_sigma": config.boulder_min_sigma,
                "boulder_max_sigma": config.boulder_max_sigma,
                "boulder_density_window_size": config.boulder_density_window_size,
                "weight_slope": config.weight_slope,
                "weight_roughness": config.weight_roughness,
                "weight_boulder": config.weight_boulder
            }
        )
        
    return features
