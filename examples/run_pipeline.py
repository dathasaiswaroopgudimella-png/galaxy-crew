import os
import sys
import logging
import matplotlib.pyplot as plt
import numpy as np

# Adjust python path to find phse package
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from phse.config import load_config
from phse.logger import setup_logger
from phse.loaders.dfsar import DFSARLoader
from phse.loaders.ohrc import OHRCLoader
from phse.processing.preprocessing import preprocess_layer
from phse.processing.alignment import align_rasters
from phse.processing.validation import ValidationPipeline
from phse.utils.raster import create_synthetic_raster, save_raster_to_tiff
from phse.utils.timing import Timer
from phse.utils.file import ensure_dir

def main():
    # 1. Setup paths
    workspace_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    config_file = os.path.join(workspace_dir, "config", "default_config.yaml")
    
    # 2. Load Configuration and Setup Logger
    config = load_config(config_file)
    logger = setup_logger(config.paths.log_dir, level="INFO")
    logger.info("Starting PHSE Foundation & Data Pipeline Example Run...")
    
    # Ensure output and dataset paths exist
    ensure_dir(config.paths.output_dir)
    ensure_dir(config.paths.dfsar_path)
    ensure_dir(config.paths.ohrc_path)
    
    # Define filenames
    dfsar_filename = os.path.join(config.paths.dfsar_path, "dfsar_backscatter.tif")
    ohrc_filename = os.path.join(config.paths.ohrc_path, "ohrc_panchromatic.tif")
    
    # 3. Generate Scientific Mock Datasets
    # Simulated Lunar South Pole Stereographic projection WKT
    lunar_polar_crs_wkt = (
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
    
    # OHRC (1m resolution, 200m x 200m area)
    # Affine parameters: [a, b, c, d, e, f] where transform maps: x' = a*x + b*y + c, y' = d*x + e*y + f
    # For OHRC: resolution=1.0m, False Easting=5000.0, False Northing=-10000.0
    ohrc_transform = [1.0, 0.0, 5000.0, 0.0, -1.0, -10000.0]
    
    # DFSAR (5m resolution, covering the same footprint)
    # For DFSAR: resolution=5.0m, False Easting=5000.0, False Northing=-10000.0
    dfsar_transform = [5.0, 0.0, 5000.0, 0.0, -5.0, -10000.0]
    
    logger.info("Generating synthetic spatial datasets...")
    with Timer("Generating Synthetic DFSAR (5m)", "INFO"):
        create_synthetic_raster(
            file_path=dfsar_filename,
            width=40,  # 40 * 5m = 200m
            height=40, # 40 * 5m = 200m
            crs_wkt=lunar_polar_crs_wkt,
            transform=dfsar_transform,
            nodata=-9999.0,
            val_range=(-30.0, 0.0),  # Backscatter in dB
            seed=101
        )
        
    with Timer("Generating Synthetic OHRC (1m)", "INFO"):
        create_synthetic_raster(
            file_path=ohrc_filename,
            width=200, # 200 * 1m = 200m
            height=200,# 200 * 1m = 200m
            crs_wkt=lunar_polar_crs_wkt,
            transform=ohrc_transform,
            nodata=0.0,
            val_range=(0.0, 255.0),  # Grayscale pixel counts
            seed=202
        )
        
    # 4. Initialize Loaders & Validation Pipeline
    validator = ValidationPipeline(config)
    dfsar_loader = DFSARLoader(nodata_value=config.preprocessing.nodata_value)
    ohrc_loader = OHRCLoader(nodata_value=0.0)
    
    # 5. Run Validation
    logger.info("Running dataset validation checks...")
    with Timer("Validating DFSAR & OHRC Files", "INFO"):
        dfsar_ok = validator.validate_raster_integrity(dfsar_filename)
        ohrc_ok = validator.validate_raster_integrity(ohrc_filename)
        
    if not (dfsar_ok and ohrc_ok):
        logger.error("Dataset validation failed. Halting pipeline execution.")
        sys.exit(1)
        
    logger.info("All inputs validated successfully. Continuing to load.")
    
    # 6. Load Datasets
    with Timer("Loading DFSAR & OHRC", "INFO"):
        dfsar_layer = dfsar_loader.load(dfsar_filename)
        ohrc_layer = ohrc_loader.load(ohrc_filename)
        
    # Check data density
    if not (validator.validate_data_density(dfsar_layer) and validator.validate_data_density(ohrc_layer)):
        logger.error("Data density thresholds not met. Halting pipeline.")
        sys.exit(1)
        
    # Check CRS compatibility
    validator.validate_crs_compatibility(dfsar_layer, ohrc_layer)
    
    # 7. Preprocessing & Normalization
    logger.info("Preprocessing layers (normalization and NaN mitigation)...")
    with Timer("Preprocessing DFSAR (Min/Max dB scaling)", "INFO"):
        preprocessed_dfsar = preprocess_layer(
            dfsar_layer,
            normalize=config.preprocessing.normalize,
            min_val=config.preprocessing.dfsar_backscatter_min_db,
            max_val=config.preprocessing.dfsar_backscatter_max_db
        )
        
    with Timer("Preprocessing OHRC (0-255 scaling)", "INFO"):
        preprocessed_ohrc = preprocess_layer(
            ohrc_layer,
            normalize=config.preprocessing.normalize,
            min_val=0.0,
            max_val=255.0
        )
        
    # 8. Coordinate Alignment (Align DFSAR 5m to OHRC 1m reference grid)
    logger.info("Aligning DFSAR grid to match high-resolution OHRC frame...")
    with Timer("Raster Reprojection and Resampling", "INFO"):
        aligned_dfsar = align_rasters(
            source=preprocessed_dfsar,
            reference=preprocessed_ohrc,
            resampling_method=config.alignment.resampling_method
        )
        
    # 9. Save Preprocessed & Aligned Outputs
    output_dfsar_path = os.path.join(config.paths.output_dir, "aligned_dfsar_normalized.tif")
    output_ohrc_path = os.path.join(config.paths.output_dir, "preprocessed_ohrc_normalized.tif")
    
    logger.info("Saving preprocessed datasets to outputs directory...")
    save_raster_to_tiff(aligned_dfsar, output_dfsar_path)
    save_raster_to_tiff(preprocessed_ohrc, output_ohrc_path)
    
    # 10. Generate Visualization
    logger.info("Rendering pipeline visualization dashboard...")
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    
    # Helper to mask nodata for visualization
    def get_masked_data(layer, nodata_val):
        mask = (layer.data == nodata_val)
        return np.ma.masked_where(mask, layer.data)
        
    # Subplot 1: Raw DFSAR backscatter (5m)
    ax1 = axes[0, 0]
    im1 = ax1.imshow(get_masked_data(dfsar_layer, dfsar_layer.metadata.nodata), cmap="gray")
    ax1.set_title(f"Raw DFSAR Backscatter (5m)\nShape: {dfsar_layer.data.shape}")
    fig.colorbar(im1, ax=ax1, label="dB")
    
    # Subplot 2: Raw OHRC Panchromatic (1m)
    ax2 = axes[0, 1]
    im2 = ax2.imshow(get_masked_data(ohrc_layer, ohrc_layer.metadata.nodata), cmap="inferno")
    ax2.set_title(f"Raw OHRC Panchromatic (1m)\nShape: {ohrc_layer.data.shape}")
    fig.colorbar(im2, ax=ax2, label="DN")
    
    # Subplot 3: Preprocessed & Aligned DFSAR (1m grid)
    ax3 = axes[1, 0]
    im3 = ax3.imshow(get_masked_data(aligned_dfsar, aligned_dfsar.metadata.nodata), cmap="gray")
    ax3.set_title(f"Aligned DFSAR (1m Grid)\nShape: {aligned_dfsar.data.shape}")
    fig.colorbar(im3, ax=ax3, label="Normalized [0, 1]")
    
    # Subplot 4: Preprocessed OHRC (1m Grid)
    ax4 = axes[1, 1]
    im4 = ax4.imshow(get_masked_data(preprocessed_ohrc, preprocessed_ohrc.metadata.nodata), cmap="inferno")
    ax4.set_title(f"Normalized OHRC (1m Grid)\nShape: {preprocessed_ohrc.data.shape}")
    fig.colorbar(im4, ax=ax4, label="Normalized [0, 1]")
    
    plt.tight_layout()
    plot_filename = os.path.join(config.paths.output_dir, "pipeline_visualization.png")
    plt.savefig(plot_filename, dpi=300)
    plt.close()
    
    logger.info(f"Pipeline execution completed. Visualization saved to: {plot_filename}")
    logger.info("Data Provenance for aligned DFSAR Layer:")
    for step in aligned_dfsar.provenance:
        logger.info(f" - [{step.timestamp}] Module: {step.module} | Action: {step.action} | Parameters: {step.parameters}")

if __name__ == "__main__":
    main()
