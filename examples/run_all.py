import os
import sys
import logging
import numpy as np

# Adjust python path to find phse package
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from phse.config import load_config
from phse.logger import setup_logger
from phse.models import RasterLayer
from phse.loaders.dfsar import DFSARLoader
from phse.loaders.ohrc import OHRCLoader
from phse.processing.preprocessing import preprocess_layer
from phse.processing.alignment import align_rasters
from phse.analysis.radar import extract_radar_features
from phse.analysis.terrain import extract_terrain_features
from phse.reasoning import PHSEReasoningEngine
from phse.mission import MissionPlanner, RoverPathfinder, ResourceEstimator
from phse.utils.raster import create_synthetic_raster, save_raster_to_tiff
from phse.utils.file import ensure_dir

def main():
    # 1. Paths and setup
    workspace_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    config_file = os.path.join(workspace_dir, "config", "default_config.yaml")
    config = load_config(config_file)
    
    # Initialize logger
    logger = setup_logger(config.paths.log_dir, level="INFO")
    logger.info("======================================================================")
    logger.info("PHSE INTEGRATION RUNNER: STARTING END-TO-END PIPELINE SYSTEM")
    logger.info("======================================================================")
    
    ensure_dir(config.paths.output_dir)
    ensure_dir(config.paths.dfsar_path)
    ensure_dir(config.paths.ohrc_path)
    
    dfsar_filename = os.path.join(config.paths.dfsar_path, "dfsar_backscatter.tif")
    ohrc_filename = os.path.join(config.paths.ohrc_path, "ohrc_panchromatic.tif")
    dem_filename = os.path.join(config.paths.ohrc_path, "dem.tif")
    
    # Coordinates parameters
    lunar_crs_wkt = (
        'PROJCS["Moon_South_Pole_Stereographic",'
        'GEOGCS["GCS_Moon_2000",'
        'DATUM["D_Moon_2000",SPHEROID["Moon_2000_Spheroid",1737400.0,0.0]],'
        'UNIT["Degree",0.017453292519943295]],'
        'PROJECTION["Stereographic"],'
        'PARAMETER["latitude_of_origin",-90.0],'
        'PARAMETER["central_meridian",0.0],'
        'PARAMETER["scale_factor",1.0],'
        'PARAMETER["false_easting",0.0],'
        'PARAMETER["false_northing",0.0],'
        'UNIT["Meter",1.0]]'
    )
    transform = [1.0, 0.0, 1000.0, 0.0, -1.0, -2000.0]
    
    # 2. Generate Synthetic Inputs if missing
    logger.info("Verifying mock datasets...")
    create_synthetic_raster(dfsar_filename, 200, 200, lunar_crs_wkt, transform, -9999.0, (-30.0, 0.0), seed=123)
    create_synthetic_raster(ohrc_filename, 200, 200, lunar_crs_wkt, transform, 0.0, (0.0, 255.0), seed=202)
    
    # Generate elevation DEM (sombrero crater + noise)
    x = np.linspace(-3, 3, 200)
    y = np.linspace(-3, 3, 200)
    xx, yy = np.meshgrid(x, y)
    r = np.sqrt(xx**2 + yy**2)
    crater = -15.0 * np.exp(-r**2) * (1.0 - 0.5 * r**2)
    hills = 5.0 * np.sin(xx) * np.cos(yy)
    np.random.seed(42)
    noise = np.random.normal(0.0, 0.2, (200, 200))
    dem_data = (100.0 + crater + hills + noise).astype(np.float32)
    
    import rasterio
    from rasterio.transform import Affine
    with rasterio.open(
        dem_filename, 'w', driver='GTiff', height=200, width=200, count=1,
        dtype='float32', crs=rasterio.crs.CRS.from_wkt(lunar_crs_wkt),
        transform=Affine(*transform), nodata=-9999.0
    ) as dst:
        dst.write(dem_data, 1)
        
    # 3. Load inputs
    logger.info("Loading inputs...")
    dfsar_loader = DFSARLoader(nodata_value=-9999.0)
    ohrc_loader = OHRCLoader(nodata_value=0.0)
    
    dfsar_layer = dfsar_loader.load(dfsar_filename)
    ohrc_layer = ohrc_loader.load(ohrc_filename)
    dem_layer = RasterLayer("elevation_dem", dem_data, dfsar_layer.metadata.model_copy(deep=True), [dem_filename])
    
    # 4. Preprocessing & Alignment
    logger.info("Running preprocessing & grid alignment...")
    pre_dfsar = preprocess_layer(dfsar_layer, normalize=True, min_val=-30.0, max_val=0.0)
    pre_ohrc = preprocess_layer(ohrc_layer, normalize=True, min_val=0.0, max_val=255.0)
    
    # Align DFSAR grid (resampled)
    aligned_dfsar = align_rasters(pre_dfsar, pre_ohrc, "bilinear")
    
    # Setup complex radar vectors for feature extraction
    np.random.seed(12)
    amp_h = np.random.uniform(0.5, 2.0, (200, 200))
    amp_v = np.random.uniform(0.5, 2.0, (200, 200))
    phase_h = np.random.uniform(-np.pi, np.pi, (200, 200))
    phase_v = np.random.uniform(-np.pi, np.pi, (200, 200))
    
    # Inject spatial anomalies inside the crater region (r < 1.0) to simulate water ice
    crater_mask = r < 1.0
    eh = (amp_h * np.exp(1j * phase_h)).astype(np.complex64)
    ev = (amp_v * np.exp(1j * phase_v)).astype(np.complex64)
    eh[crater_mask] = np.abs(eh[crater_mask]) * np.exp(1j * 0.0)
    ev[crater_mask] = np.abs(ev[crater_mask]) * np.exp(1j * (np.pi / 2.0))
    
    complex_meta = dfsar_layer.metadata.model_copy(deep=True)
    complex_meta.dtype = "complex64"
    radar_lh = RasterLayer("eh_complex", eh, complex_meta, [dfsar_filename])
    radar_lv = RasterLayer("ev_complex", ev, complex_meta, [dfsar_filename])
    
    # 5. Extract Scientific Features (Radar & Terrain)
    logger.info("Running Stage 2 Scientific Feature Extraction...")
    radar_features = extract_radar_features(radar_lh, radar_lv, config.analysis.radar, mode="hybrid_complex")
    terrain_features = extract_terrain_features(dem_layer, pre_ohrc, config.analysis.terrain)
    
    pfr = {}
    pfr.update(radar_features)
    pfr.update(terrain_features)
    
    # 6. Execute Bayesian Reasoning Engine
    logger.info("Executing Stage 3B Bayesian Reasoning Engine state machine...")
    engine = PHSEReasoningEngine()
    reasoning_result = engine.execute(pfr, entropy_threshold=0.01)
    
    # 7. Execute Mission Planning (Landing site, rover path, resources)
    logger.info("Executing Stage 4 Mission Planning Engine...")
    planner = MissionPlanner(
        max_landing_slope=config.analysis.terrain.slope_threshold_critical,
        max_landing_roughness=config.analysis.terrain.roughness_threshold_critical
    )
    suitability, opt_x, opt_y, score = planner.evaluate_landing_zones(
        terrain_features["terrain_slope"],
        terrain_features["terrain_roughness"],
        terrain_features["terrain_hazard"],
        reasoning_result.probability_layers["pure_water_ice"]
    )
    
    estimator = ResourceEstimator()
    ice_density, total_vol, total_tons = estimator.estimate_ice_resources(
        reasoning_result.probability_layers["pure_water_ice"]
    )
    
    # Compute goal coordinate of highest ice concentration (avoiding cliffs)
    valid_ice = reasoning_result.probability_layers["pure_water_ice"].data.copy()
    valid_ice[terrain_features["terrain_slope"].data > 18.0] = 0.0
    goal_y, goal_x = np.unravel_index(np.argmax(valid_ice), valid_ice.shape)
    
    pathfinder = RoverPathfinder(max_rover_slope=20.0)
    rover_path = pathfinder.find_path(
        terrain_features["terrain_slope"],
        terrain_features["terrain_roughness"],
        opt_x, opt_y, int(goal_x), int(goal_y)
    )
    
    # 8. Save output layers
    logger.info("Saving refined geological map and mission grids to outputGeoTIFFs...")
    save_raster_to_tiff(reasoning_result.geological_map, os.path.join(config.paths.output_dir, "refined_geological_map.tif"))
    save_raster_to_tiff(reasoning_result.entropy_layer, os.path.join(config.paths.output_dir, "reasoning_entropy.tif"))
    save_raster_to_tiff(suitability, os.path.join(config.paths.output_dir, "landing_suitability.tif"))
    save_raster_to_tiff(ice_density, os.path.join(config.paths.output_dir, "subsurface_ice_density.tif"))
    
    logger.info("======================================================================")
    logger.info("PHSE END-TO-END PIPELINE SYSTEM RUN COMPLETED")
    logger.info(f" -> RECOMMENDED LANDING COORDINATES: X={opt_x}, Y={opt_y}")
    logger.info(f" -> LANDING SUITABILITY SCORE: {score * 100.0:.2f}%")
    logger.info(f" -> TOTAL INTEGRATED ICE VOLUME: {total_vol:.2f} m3")
    logger.info(f" -> TOTAL INTEGRATED ICE MASS: {total_tons:.2f} Metric Tons")
    logger.info(f" -> ROVER PATH WAYPOINTS: {len(rover_path)} waypoints")
    logger.info("======================================================================")

if __name__ == "__main__":
    main()
