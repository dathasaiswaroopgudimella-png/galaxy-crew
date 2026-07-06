import pytest
import numpy as np
from phse.models import RasterLayer, RasterMetadata
from phse.reasoning import (
    HypothesisLibrary,
    ConstraintMatcher,
    AdaptiveSeparator,
    BayesianAssimilator,
    PHSEReasoningEngine,
    DEFAULT_HYPOTHESES
)

@pytest.fixture
def mock_raster_metadata():
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

def test_lghl_library_load():
    """Verifies that the hypothesis library loads default geological classes."""
    lib = HypothesisLibrary()
    all_hyp = lib.get_all()
    assert len(all_hyp) == 5
    assert lib.get_by_id("pure_water_ice") is not None
    assert lib.get_by_id("pure_water_ice").name == "Pure Subsurface Water Ice"

def test_constraint_matcher(mock_raster_metadata):
    """Verifies single-pixel and grid-based constraint matching."""
    matcher = ConstraintMatcher(DEFAULT_HYPOTHESES)
    
    # Test single pixel: High CPR, Low DOP, Low Illumination (favors Pure Water Ice)
    pixel_obs = {
        "radar_cpr": 1.5,
        "radar_dop": 0.1,
        "terrain_slope": 3.0,
        "terrain_illumination": 0.0,
        "terrain_roughness": 0.1
    }
    grades = matcher.evaluate_pixel(pixel_obs)
    assert grades["pure_water_ice"] > grades["dry_regolith"]
    assert grades["pure_water_ice"] > grades["blocky_ejecta"]
    
    # Test grid-based matching
    shape = (5, 5)
    layers = {
        "radar_cpr": np.full(shape, 1.5, dtype=np.float32),
        "radar_dop": np.full(shape, 0.1, dtype=np.float32),
        "terrain_slope": np.full(shape, 3.0, dtype=np.float32),
        "terrain_illumination": np.full(shape, 0.0, dtype=np.float32),
        "terrain_roughness": np.full(shape, 0.1, dtype=np.float32)
    }
    nodata_mask = np.zeros(shape, dtype=bool)
    
    grid_grades = matcher.evaluate_grid(layers, nodata_mask)
    assert grid_grades["pure_water_ice"].shape == shape
    assert np.all(grid_grades["pure_water_ice"] > 0.01)

def test_ahs_selection():
    """Verifies that AHS optimizes feature selection based on active set entropy."""
    ahs = AdaptiveSeparator(DEFAULT_HYPOTHESES)
    
    # Active set contains ice and blocky ejecta as equally likely
    active_set = {
        "pure_water_ice": 0.5,
        "blocky_ejecta": 0.5,
        "dry_regolith": 0.0
    }
    
    # Evaluate features:
    # 'terrain_illumination' differs heavily: pure ice is strictly 0.0, blocky ejecta is variable (0-1).
    # 'radar_cpr' is high for both.
    # Therefore, 'terrain_illumination' should yield high separation.
    available = ["radar_cpr", "terrain_illumination"]
    selected = ahs.select_next_feature(active_set, available)
    assert selected == "terrain_illumination"

def test_bayesian_assimilator(mock_raster_metadata):
    """Verifies Bayesian updating and Shannon entropy calculations."""
    assimilator = BayesianAssimilator(DEFAULT_HYPOTHESES)
    
    # Simple probability distribution
    probs = {"pure_water_ice": 0.2, "dry_regolith": 0.8}
    
    # High CPR observation (supports ice, discounts regolith)
    updated = assimilator.update_probabilities(probs, 1.8, "radar_cpr")
    assert updated["pure_water_ice"] > 0.2
    
    # Entropy calculation
    ent_before = assimilator.compute_entropy(probs)
    ent_after = assimilator.compute_entropy(updated)
    # Since confidence shifted towards pure ice, entropy should decrease
    assert ent_after < ent_before

def test_reasoning_engine_state_machine(mock_raster_metadata):
    """Verifies end-to-end execution of the reasoning engine state machine."""
    engine = PHSEReasoningEngine()
    
    # Generate mock inputs
    shape = (5, 5)
    cpr = np.full(shape, 1.4, dtype=np.float32)
    dop = np.full(shape, 0.15, dtype=np.float32)
    slope = np.full(shape, 2.0, dtype=np.float32)
    illum = np.full(shape, 0.0, dtype=np.float32)
    rough = np.full(shape, 0.1, dtype=np.float32)
    
    # Package into layers
    layers = {
        "radar_cpr": RasterLayer("radar_cpr", cpr, mock_raster_metadata, ["mock.tif"]),
        "radar_dop": RasterLayer("radar_dop", dop, mock_raster_metadata, ["mock.tif"]),
        "terrain_slope": RasterLayer("terrain_slope", slope, mock_raster_metadata, ["mock.tif"]),
        "terrain_illumination": RasterLayer("terrain_illumination", illum, mock_raster_metadata, ["mock.tif"]),
        "terrain_roughness": RasterLayer("terrain_roughness", rough, mock_raster_metadata, ["mock.tif"])
    }
    
    # Use extremely small entropy threshold to force AHS iterations
    result = engine.execute(layers, entropy_threshold=0.001)
    
    assert isinstance(result.geological_map, RasterLayer)
    assert isinstance(result.entropy_layer, RasterLayer)
    assert len(result.convergence_trajectory) > 1
    # Check that final classification at central pixel is indeed Pure Water Ice (value code 1.0)
    # The first registered hypothesis in DEFAULT_HYPOTHESES is pure_water_ice, which maps to code 1.0
    assert result.geological_map.data[2, 2] == 1.0
