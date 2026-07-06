import pytest
import numpy as np
from phse.models import RasterLayer, RasterMetadata
from phse.mission import MissionPlanner, RoverPathfinder, ResourceEstimator

@pytest.fixture
def base_metadata():
    return RasterMetadata(
        crs_wkt="GEOGCS[\"GCS_Moon_2000\",DATUM[\"D_Moon_2000\",SPHEROID[\"Moon_2000_Spheroid\",1737400.0,0.0]],UNIT[\"Degree\",0.01745]]",
        transform=[1.0, 0.0, 0.0, 0.0, -1.0, 0.0],
        width=5,
        height=5,
        dtype="float32",
        bounds={"left": 0.0, "bottom": -5.0, "right": 5.0, "top": 0.0},
        nodata=-9999.0,
        additional_metadata={}
    )

def test_landing_suitability_ranking(base_metadata):
    """Verifies that the mission planner correctly ranks safe pixels and handles envelopes."""
    planner = MissionPlanner(
        max_landing_slope=15.0,
        max_landing_roughness=0.5,
        landing_safety_radius_px=1
    )
    
    # 5x5 test grids
    # We will make pixel (2, 2) safe with high ice prob
    slope_data = np.full((5, 5), 20.0, dtype=np.float32) # unsafe by default
    slope_data[1:4, 1:4] = 5.0 # center region is safe
    
    roughness_data = np.full((5, 5), 0.8, dtype=np.float32) # unsafe
    roughness_data[1:4, 1:4] = 0.1 # center safe
    
    hazard_data = np.full((5, 5), 0.5, dtype=np.float32)
    hazard_data[2, 2] = 0.1 # best center
    
    ice_prob_data = np.full((5, 5), 0.1, dtype=np.float32)
    ice_prob_data[2, 2] = 0.9 # high ice prob at center
    
    slope_layer = RasterLayer("slope", slope_data, base_metadata)
    roughness_layer = RasterLayer("roughness", roughness_data, base_metadata)
    hazard_layer = RasterLayer("hazard", hazard_data, base_metadata)
    ice_prob_layer = RasterLayer("ice_prob", ice_prob_data, base_metadata)
    
    suitability, opt_x, opt_y, score = planner.evaluate_landing_zones(
        slope_layer, roughness_layer, hazard_layer, ice_prob_layer
    )
    
    # Optimal landing site should be exactly at center (2, 2)
    assert opt_x == 2
    assert opt_y == 2
    assert score > 0.5
    
    # Outer pixels should be marked as unsafe (suitability score 0.0)
    assert suitability.data[0, 0] == 0.0

def test_rover_pathfinder_a_star(base_metadata):
    """Verifies that the pathfinder computes traversable paths around obstacles."""
    pathfinder = RoverPathfinder(max_rover_slope=15.0)
    
    # 5x5 grids
    slope_data = np.zeros((5, 5), dtype=np.float32)
    # Put a barrier of high slope at row 2, except at column 4
    slope_data[2, 0:4] = 30.0
    
    roughness_data = np.zeros((5, 5), dtype=np.float32)
    
    slope_layer = RasterLayer("slope", slope_data, base_metadata)
    roughness_layer = RasterLayer("roughness", roughness_data, base_metadata)
    
    # Start at (0, 0) and goal at (4, 0).
    # Since row 2 has a slope barrier in columns 0-3, the pathfinder MUST go around through col 4.
    path = pathfinder.find_path(slope_layer, roughness_layer, 0, 0, 0, 4)
    
    assert len(path) > 0
    # The path must pass through the gap at (4, 2)
    assert (4, 2) in path

def test_resource_estimator(base_metadata):
    """Verifies ice mass and volume integration."""
    estimator = ResourceEstimator(
        default_penetration_depth_m=2.0,
        regolith_porosity=0.5,
        ice_pore_saturation=0.5
    )
    
    # 5x5 grid with probability 0.8 everywhere
    prob_data = np.full((5, 5), 0.8, dtype=np.float32)
    prob_layer = RasterLayer("prob", prob_data, base_metadata)
    
    density_layer, vol, mass = estimator.estimate_ice_resources(prob_layer)
    
    # Total area: 5 * 5 = 25 m2
    # Expected Volume: 25 * 2.0 * 0.5 * 0.5 * 0.8 = 10.0 m3
    assert vol == pytest.approx(10.0)
    # Expected Mass: 10.0 * 917.0 = 9170.0 kg = 9.17 metric tons
    assert mass == pytest.approx(9.17)
