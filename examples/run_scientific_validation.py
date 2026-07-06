import os
import sys
import json
import logging
import numpy as np
from typing import Dict, List, Any, Tuple

# Adjust python path to find phse package
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from phse.config import load_config
from phse.models import RasterLayer, RasterMetadata
from phse.loaders.dfsar import DFSARLoader
from phse.loaders.ohrc import OHRCLoader
from phse.processing.preprocessing import preprocess_layer
from phse.processing.alignment import align_rasters
from phse.analysis.radar import extract_radar_features
from phse.analysis.terrain import extract_terrain_features
from phse.reasoning import PHSEReasoningEngine
from phse.mission import MissionPlanner, RoverPathfinder, ResourceEstimator
from phse.utils.raster import create_synthetic_raster

def setup_validation_logger():
    logger = logging.getLogger("phse_val")
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('[%(levelname)s] %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger

logger = setup_validation_logger()

class SingleWorldBaseline:
    """
    Baseline 1: Single-World Planning.
    Decides immediately after constraint matching using the argmax of initial matching scores.
    Does not run any sequential information gathering or Bayesian updates.
    """
    def execute(self, matching_grids: Dict[str, np.ndarray], nodata_mask: np.ndarray) -> np.ndarray:
        shape = next(iter(matching_grids.values())).shape
        stack = np.stack([matching_grids[h_id] for h_id in matching_grids], axis=0)
        argmax_grid = np.argmax(stack, axis=0).astype(np.float32)
        geo_map = np.zeros(shape, dtype=np.float32)
        geo_map[~nodata_mask] = argmax_grid[~nodata_mask] + 1.0
        geo_map[nodata_mask] = -9999.0
        return geo_map

class RandomExperimentalDesignBaseline:
    """
    Baseline 2: Random Experimental Design.
    Runs sequential Bayesian updates but selects layers randomly instead of using AHS.
    """
    def __init__(self, hypotheses: List[Any]):
        from phse.reasoning.bayesian import BayesianAssimilator
        self.assimilator = BayesianAssimilator(hypotheses)
        self.hyp_ids = [h.id for h in hypotheses]

    def execute(
        self,
        pfr_layers: Dict[str, np.ndarray],
        initial_grids: Dict[str, np.ndarray],
        nodata_mask: np.ndarray,
        max_steps: int = 5
    ) -> Tuple[np.ndarray, List[float]]:
        shape = next(iter(pfr_layers.values())).shape
        current_grids = {h_id: grid.copy() for h_id, grid in initial_grids.items()}
        trajectory = []
        
        # Initial entropy
        ent = self.assimilator.compute_grid_entropy(current_grids)
        trajectory.append(float(np.mean(ent[~nodata_mask])))
        
        features = list(pfr_layers.keys())
        np.random.seed(42) # Deterministic random
        np.random.shuffle(features)
        
        for i in range(min(max_steps, len(features))):
            feat = features[i]
            obs_grid = pfr_layers[feat]
            current_grids = self.assimilator.update_grid(current_grids, obs_grid, feat, nodata_mask)
            ent = self.assimilator.compute_grid_entropy(current_grids)
            trajectory.append(float(np.mean(ent[~nodata_mask])))
            
        stack = np.stack([current_grids[h_id] for h_id in self.hyp_ids], axis=0)
        argmax_grid = np.argmax(stack, axis=0).astype(np.float32)
        geo_map = np.zeros(shape, dtype=np.float32)
        geo_map[~nodata_mask] = argmax_grid[~nodata_mask] + 1.0
        geo_map[nodata_mask] = -9999.0
        return geo_map, trajectory

def run_evaluation():
    workspace_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    config_file = os.path.join(workspace_dir, "config", "default_config.yaml")
    config = load_config(config_file)
    
    # 1. Setup Mock Input
    dfsar_filename = os.path.join(config.paths.dfsar_path, "dfsar_backscatter.tif")
    ohrc_filename = os.path.join(config.paths.ohrc_path, "ohrc_panchromatic.tif")
    dem_filename = os.path.join(config.paths.ohrc_path, "dem.tif")
    
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
    
    dfsar_loader = DFSARLoader(nodata_value=-9999.0)
    ohrc_loader = OHRCLoader(nodata_value=0.0)
    
    dfsar_layer = dfsar_loader.load(dfsar_filename)
    ohrc_layer = ohrc_loader.load(ohrc_filename)
    
    x = np.linspace(-3, 3, 200)
    y = np.linspace(-3, 3, 200)
    xx, yy = np.meshgrid(x, y)
    r = np.sqrt(xx**2 + yy**2)
    crater = -15.0 * np.exp(-r**2) * (1.0 - 0.5 * r**2)
    hills = 5.0 * np.sin(xx) * np.cos(yy)
    np.random.seed(42)
    noise = np.random.normal(0.0, 0.2, (200, 200))
    dem_data = (100.0 + crater + hills + noise).astype(np.float32)
    
    # Create realistic physical layers matching geological properties:
    # 1. Background (Dry Regolith, code 5.0)
    # 2. Crater center (r < 1.0) (Pure Water Ice, code 1.0)
    # 3. Crater rim (1.0 <= r < 1.5) (Blocky Ejecta, code 3.0)
    
    shape = (200, 200)
    cpr_data = np.full(shape, 0.3, dtype=np.float32) # Regolith background CPR
    dop_data = np.full(shape, 0.8, dtype=np.float32) # Regolith background DOP
    slope_data = np.full(shape, 3.0, dtype=np.float32) # Regolith background Slope
    illum_data = np.full(shape, 0.5, dtype=np.float32) # Regolith background Illum
    rough_data = np.full(shape, 0.25, dtype=np.float32) # Regolith background Roughness
    
    # Crater mask (Pure Water Ice)
    crater_mask = r < 1.0
    cpr_data[crater_mask] = 1.6
    dop_data[crater_mask] = 0.15
    slope_data[crater_mask] = 4.0
    illum_data[crater_mask] = 0.02
    rough_data[crater_mask] = 0.08
    
    # Ejecta mask (Blocky Ejecta)
    ejecta_mask = (r >= 1.0) & (r < 1.5)
    cpr_data[ejecta_mask] = 1.1
    dop_data[ejecta_mask] = 0.3
    slope_data[ejecta_mask] = 12.0
    illum_data[ejecta_mask] = 0.4
    rough_data[ejecta_mask] = 0.35
    
    # Save custom DEM (derived from slope and crater depth)
    dem_layer = RasterLayer("elevation_dem", dem_data, dfsar_layer.metadata.model_copy(deep=True), [dem_filename])
    
    # Convert arrays to RasterLayers
    meta = dfsar_layer.metadata.model_copy(deep=True)
    meta.dtype = "float32"
    meta.nodata = -9999.0
    
    radar_features = {
        "radar_cpr": RasterLayer("radar_cpr", cpr_data, meta),
        "radar_dop": RasterLayer("radar_dop", dop_data, meta)
    }
    terrain_features = {
        "terrain_slope": RasterLayer("terrain_slope", slope_data, meta),
        "terrain_roughness": RasterLayer("terrain_roughness", rough_data, meta),
        "terrain_illumination": RasterLayer("terrain_illumination", illum_data, meta),
        "terrain_hazard": RasterLayer("terrain_hazard", (slope_data/30.0 + rough_data)/2.0, meta)
    }
    
    pfr = {}
    pfr.update(radar_features)
    pfr.update(terrain_features)
    
    # 2. Run Engine (PHSE)
    engine = PHSEReasoningEngine()
    phse_result = engine.execute(pfr, entropy_threshold=0.01)
    
    # 3. Create ground truth for validation
    ground_truth = np.full(shape, 5.0, dtype=np.float32) # default dry regolith
    ground_truth[crater_mask] = 1.0 # pure water ice inside crater
    ground_truth[ejecta_mask] = 3.0 # blocky ejecta on rim
    
    nodata_mask = (dem_data == -9999.0)
    
    # Eval PHSE Acc
    phse_geo = phse_result.geological_map.data
    valid_pixels = ~nodata_mask
    phse_acc = float(np.mean(phse_geo[valid_pixels] == ground_truth[valid_pixels]))
    
    # 4. Baselines execution
    # Baseline 1: Single-world planning
    sw_planner = SingleWorldBaseline()
    
    raw_pfr = {k: v.data for k, v in pfr.items()}
    matching_grades = engine.matcher.evaluate_grid(raw_pfr, nodata_mask)
    sw_geo = sw_planner.execute(matching_grades, nodata_mask)
    sw_acc = float(np.mean(sw_geo[valid_pixels] == ground_truth[valid_pixels]))
    
    # Baseline 2: Random sequential
    rand_planner = RandomExperimentalDesignBaseline(engine.hypotheses)
    rand_geo, rand_trajectory = rand_planner.execute(raw_pfr, matching_grades, nodata_mask, max_steps=5)
    rand_acc = float(np.mean(rand_geo[valid_pixels] == ground_truth[valid_pixels]))
    
    # 5. Mission planner comparison
    # Run mission planner on PHSE
    planner = MissionPlanner(max_landing_slope=15.0, max_landing_roughness=0.5)
    _, opt_x, opt_y, score = planner.evaluate_landing_zones(
        terrain_features["terrain_slope"],
        terrain_features["terrain_roughness"],
        terrain_features["terrain_hazard"],
        phse_result.probability_layers["pure_water_ice"]
    )
    
    # Run mission planner on Single-world (using single-world confidence map for ice)
    # Define a mock single-world ice probability layer (matching_grades["pure_water_ice"])
    sw_ice_prob = RasterLayer("sw_ice_prob", matching_grades["pure_water_ice"], dfsar_layer.metadata.model_copy(deep=True))
    _, sw_opt_x, sw_opt_y, sw_score = planner.evaluate_landing_zones(
        terrain_features["terrain_slope"],
        terrain_features["terrain_roughness"],
        terrain_features["terrain_hazard"],
        sw_ice_prob
    )
    
    # 6. Save validation metrics to JSON
    metrics = {
        "accuracy": {
            "phse": phse_acc,
            "single_world": sw_acc,
            "random_sequential": rand_acc
        },
        "entropy_trajectory": {
            "phse": phse_result.convergence_trajectory,
            "random_sequential": rand_trajectory
        },
        "landing_site": {
            "phse": {
                "x": opt_x,
                "y": opt_y,
                "score": score
            },
            "single_world": {
                "x": sw_opt_x,
                "y": sw_opt_y,
                "score": sw_score
            }
        }
    }
    
    output_path = os.path.join(workspace_dir, "outputs", "validation_metrics.json")
    with open(output_path, "w") as f:
        json.dump(metrics, f, indent=4)
        
    logger.info("=========================================================")
    logger.info("VALIDATION SUITE RUN SUCCESSFULLY")
    logger.info(f"PHSE Accuracy: {phse_acc * 100.0:.2f}% | Baseline 1 (Single World): {sw_acc * 100.0:.2f}% | Baseline 2 (Random Sequential): {rand_acc * 100.0:.2f}%")
    logger.info(f"PHSE Landing Score: {score * 100.0:.2f}% | Single-World Landing Score: {sw_score * 100.0:.2f}%")
    logger.info("=========================================================")

if __name__ == "__main__":
    run_evaluation()
