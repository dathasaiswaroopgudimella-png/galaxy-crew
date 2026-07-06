import os
import sys
import json
import logging
import matplotlib.pyplot as plt
import numpy as np

# Adjust python path to find phse package
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from phse.config import load_config
from phse.logger import setup_logger
from phse.models import RasterLayer, RasterMetadata
from phse.analysis import (
    RadarConfig,
    TerrainConfig,
    AnalysisConfig,
    PhysicsFeatureRepresentation,
    extract_radar_features,
    extract_terrain_features
)
from phse.utils.raster import create_synthetic_raster, save_raster_to_tiff
from phse.utils.file import ensure_dir

def generate_complex_synthetic_radar(base_path: str, width: int, height: int, crs_wkt: str, transform: list, nodata: float, seed: int):
    """
    Generates synthetic complex electric field components Eh and Ev.
    """
    np.random.seed(seed)
    
    # Base amplitude
    amp_h = np.random.uniform(0.5, 2.0, (height, width))
    amp_v = np.random.uniform(0.5, 2.0, (height, width))
    
    # Phase components
    phase_h = np.random.uniform(-np.pi, np.pi, (height, width))
    phase_v = np.random.uniform(-np.pi, np.pi, (height, width))
    
    # Form complex arrays
    eh = (amp_h * np.exp(1j * phase_h)).astype(np.complex64)
    ev = (amp_v * np.exp(1j * phase_v)).astype(np.complex64)
    
    # Inject 5% nodata values
    nodata_mask = np.random.choice([True, False], size=(height, width), p=[0.05, 0.95])
    eh[nodata_mask] = nodata
    ev[nodata_mask] = nodata
    
    # Save as separate physical real/imag files, or simulate single-band loaders
    # Here, for the in-memory loader representation, we can instantiate layers directly.
    meta = RasterMetadata(
        crs_wkt=crs_wkt,
        transform=transform,
        width=width,
        height=height,
        dtype="complex64",
        bounds={"left": transform[2], "bottom": transform[5] + transform[4]*height, "right": transform[2] + transform[0]*width, "top": transform[5]},
        nodata=nodata,
        additional_metadata={}
    )
    
    layer_h = RasterLayer("eh_complex", eh, meta, [os.path.join(base_path, "eh_complex.tif")])
    layer_v = RasterLayer("ev_complex", ev, meta, [os.path.join(base_path, "ev_complex.tif")])
    
    return layer_h, layer_v

def generate_synthetic_dem(width: int, height: int) -> np.ndarray:
    """
    Generates a realistic synthetic DEM featuring a central crater and rolling topography.
    """
    x = np.linspace(-3, 3, width)
    y = np.linspace(-3, 3, height)
    xx, yy = np.meshgrid(x, y)
    r = np.sqrt(xx**2 + yy**2)
    
    # Crater profile: sombrero-like shape
    crater = -15.0 * np.exp(-r**2) * (1.0 - 0.5 * r**2)
    
    # Rolling hills (low-frequency noise)
    hills = 5.0 * np.sin(xx) * np.cos(yy)
    
    # High-frequency micro-topography (roughness)
    np.random.seed(42)
    noise = np.random.normal(0.0, 0.2, (height, width))
    
    dem = 100.0 + crater + hills + noise
    return dem.astype(np.float32)

def generate_synthetic_pan(width: int, height: int) -> np.ndarray:
    """
    Generates a synthetic high-resolution panchromatic image with bright boulder shapes.
    """
    # Background texture
    np.random.seed(99)
    pan = np.random.normal(120.0, 10.0, (height, width))
    
    # Inject 5 boulders (bright pixels with adjacent shadows)
    boulder_coords = [(20, 30), (50, 75), (80, 20), (120, 140), (150, 50)]
    for y, x in boulder_coords:
        if 0 < y < height-1 and 0 < x < width-1:
            pan[y, x] = 240.0      # Bright sunlit side
            pan[y+1, x+1] = 40.0   # Shadow side
            
    return np.clip(pan, 0.0, 255.0).astype(np.float32)

def main():
    # 1. Setup paths and load configuration
    workspace_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    config_file = os.path.join(workspace_dir, "config", "default_config.yaml")
    config = load_config(config_file)
    
    # Initialize logger
    logger = setup_logger(config.paths.log_dir, level="INFO")
    logger.info("======================================================================")
    logger.info("PHSE STAGE 2 - PHYSICS & SCIENTIFIC FEATURE ENGINE RUN")
    logger.info("======================================================================")
    
    ensure_dir(config.paths.output_dir)
    
    # 2. Coordinate settings
    lunar_crs_wkt = (
        'PROJCS["Moon_South_Pole_Stereographic",'
        'GEOGCS["GCS_Moon_2000",'
        'DATUM["D_Moon_2000",SPHEROID["Moon_2000_Spheroid",1737400.0,0.0]],'
        'PRIMEM["Reference_Meridian",0.0],'
        'UNIT["Degree",0.017453292519943295]],'
        'PROJECTION["Stereographic"],'
        'PARAMETER["latitude_of_origin",-90.0],'
        'PARAMETER["central_meridian",0.0],'
        'PARAMETER["scale_factor",1.0],'
        'PARAMETER["false_easting",0.0],'
        'PARAMETER["false_northing",0.0],'
        'UNIT["Meter",1.0]]'
    )
    
    # 200m x 200m area at 1m resolution (200x200 grid)
    transform = [1.0, 0.0, 1000.0, 0.0, -1.0, -2000.0]
    
    # 3. Generate Scientific Mock inputs
    logger.info("Generating synthetic complex radar data...")
    dfsar_lh, dfsar_lv = generate_complex_synthetic_radar(
        config.paths.dfsar_path, 200, 200, lunar_crs_wkt, transform, -9999.0, seed=123
    )
    
    logger.info("Generating synthetic DEM (height) and PAN (optical) layers...")
    dem_data = generate_synthetic_dem(200, 200)
    pan_data = generate_synthetic_pan(200, 200)
    
    meta_dem = RasterMetadata(
        crs_wkt=lunar_crs_wkt,
        transform=transform,
        width=200,
        height=200,
        dtype="float32",
        bounds={"left": 1000.0, "bottom": -2200.0, "right": 1200.0, "top": -2000.0},
        nodata=-9999.0,
        additional_metadata={}
    )
    
    dem_layer = RasterLayer("elevation_dem", dem_data, meta_dem, [os.path.join(config.paths.ohrc_path, "dem.tif")])
    pan_layer = RasterLayer("optical_pan", pan_data, meta_dem, [os.path.join(config.paths.ohrc_path, "pan.tif")])
    
    # 4. Run Radar and Terrain Feature Extraction
    logger.info("Extracting Polarimetric Radar features (CPR, DOP, m-chi decomposition)...")
    radar_features = extract_radar_features(
        dfsar_lh, dfsar_lv, config.analysis.radar, mode="hybrid_complex"
    )
    
    logger.info("Extracting Terrain features (Slope, Roughness, Illumination, Boulder Density, Hazards)...")
    terrain_features = extract_terrain_features(
        dem_layer, pan_layer, config.analysis.terrain
    )
    
    # 5. Compile into Physics Feature Representation (PFR)
    logger.info("Compiling all derived features into Physics Feature Representation (PFR)...")
    pfr = PhysicsFeatureRepresentation(config_version="2.0.0")
    
    # Add all extracted layers
    for layer in radar_features.values():
        pfr.add_layer(layer)
    for layer in terrain_features.values():
        pfr.add_layer(layer)
        
    # Serialize metadata summary to file
    pfr_metadata_path = os.path.join(config.paths.output_dir, "pfr_metadata.json")
    with open(pfr_metadata_path, "w") as f:
        json.dump(pfr.to_dict(), f, indent=4)
    logger.info(f"PFR serialization completed. Metadata stored at {pfr_metadata_path}")
    
    # 6. Save derived scientific layers as physical GeoTIFFs
    logger.info("Saving derived scientific layers as GeoTIFF files...")
    for name, layer in pfr.layers.items():
        out_path = os.path.join(config.paths.output_dir, f"{name}.tif")
        save_raster_to_tiff(layer, out_path)
        
    # 7. Render Visualization Dashboard
    logger.info("Generating scientific visualization dashboard...")
    fig, axes = plt.subplots(3, 3, figsize=(18, 15))
    
    def get_masked(layer):
        mask = (layer.data == layer.metadata.nodata)
        return np.ma.masked_where(mask, layer.data)
        
    # Row 1: Inputs
    ax = axes[0, 0]
    im = ax.imshow(np.abs(dfsar_lh.data), cmap="gray")
    ax.set_title("Input DFSAR LH Amplitude")
    fig.colorbar(im, ax=ax)
    
    ax = axes[0, 1]
    im = ax.imshow(get_masked(dem_layer), cmap="terrain")
    ax.set_title("Input DEM Elevation (m)")
    fig.colorbar(im, ax=ax)
    
    ax = axes[0, 2]
    im = ax.imshow(get_masked(pan_layer), cmap="gray")
    ax.set_title("Input PAN Image (OHRC)")
    fig.colorbar(im, ax=ax)
    
    # Row 2: Radar Derived
    ax = axes[1, 0]
    im = ax.imshow(get_masked(pfr.layers["radar_cpr"]), cmap="coolwarm", vmin=0.0, vmax=2.0)
    ax.set_title("Derived Radar CPR")
    fig.colorbar(im, ax=ax)
    
    ax = axes[1, 1]
    im = ax.imshow(get_masked(pfr.layers["radar_dop"]), cmap="inferno", vmin=0.0, vmax=1.0)
    ax.set_title("Derived Radar DOP")
    fig.colorbar(im, ax=ax)
    
    ax = axes[1, 2]
    im = ax.imshow(get_masked(pfr.layers["radar_decomposition_volume"]), cmap="magma")
    ax.set_title("Volume Scattering Power")
    fig.colorbar(im, ax=ax)
    
    # Row 3: Terrain Derived
    ax = axes[2, 0]
    im = ax.imshow(get_masked(pfr.layers["terrain_slope"]), cmap="plasma")
    ax.set_title("Surface Slope (degrees)")
    fig.colorbar(im, ax=ax)
    
    ax = axes[2, 1]
    im = ax.imshow(get_masked(pfr.layers["terrain_roughness"]), cmap="viridis")
    ax.set_title("Surface Roughness (RMS height)")
    fig.colorbar(im, ax=ax)
    
    ax = axes[2, 2]
    im = ax.imshow(get_masked(pfr.layers["terrain_hazard"]), cmap="RdYlGn_r", vmin=0.0, vmax=1.0)
    ax.set_title("Landing Hazard Map")
    fig.colorbar(im, ax=ax)
    
    plt.tight_layout()
    viz_path = os.path.join(config.paths.output_dir, "scientific_visualization.png")
    plt.savefig(viz_path, dpi=300)
    plt.close()
    logger.info(f"Visualization saved to: {viz_path}")
    logger.info("======================================================================")
    logger.info("PHSE STAGE 2 - FEATURE ENGINE RUN COMPLETED SUCCESSFULLY")
    logger.info("======================================================================")

if __name__ == "__main__":
    main()
