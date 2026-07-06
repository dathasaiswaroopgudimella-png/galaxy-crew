import pytest
import numpy as np
from phse.models import RasterLayer, RasterMetadata
from phse.analysis.config import AnalysisConfig, RadarConfig, TerrainConfig
from phse.analysis.feature_set import PhysicsFeatureRepresentation, LayerQualityMetrics
from phse.analysis.radar import extract_radar_features
from phse.analysis.terrain import extract_terrain_features

@pytest.fixture
def base_metadata():
    """
    Returns standard mock metadata for test raster layers.
    """
    return RasterMetadata(
        crs_wkt="GEOGCS[\"GCS_Moon_2000\",DATUM[\"D_Moon_2000\",SPHEROID[\"Moon_2000_Spheroid\",1737400.0,0.0]],UNIT[\"Degree\",0.01745]]",
        transform=[1.0, 0.0, 0.0, 0.0, -1.0, 0.0],
        width=10,
        height=10,
        dtype="float32",
        bounds={"left": 0.0, "bottom": -10.0, "right": 10.0, "top": 0.0},
        nodata=-9999.0,
        additional_metadata={}
    )

def test_stokes_and_cpr_computation(base_metadata):
    """
    Verifies circular polarization ratio (CPR) and degree of polarization (DOP)
    calculations from complex radar inputs.
    """
    # Create simple complex inputs: Eh = 1 + 0j, Ev = 0 + 1j (orthogonal, circular-like)
    eh_data = np.ones((10, 10), dtype=np.complex64)
    ev_data = np.ones((10, 10), dtype=np.complex64) * 1j
    
    layer_h = RasterLayer("eh", eh_data, base_metadata, ["mock_h.tif"])
    layer_v = RasterLayer("ev", ev_data, base_metadata, ["mock_v.tif"])
    
    config = RadarConfig(cpr_window_size=3, dop_window_size=3)
    results = extract_radar_features(layer_h, layer_v, config, mode="hybrid_complex")
    
    assert "radar_backscatter" in results
    assert "radar_cpr" in results
    assert "radar_dop" in results
    assert "radar_decomposition_even" in results
    
    # S1 = |Eh|^2 + |Ev|^2 = 1 + 1 = 2
    # S4 = -2 * Im(Eh * Ev*) = -2 * Im(1 * -i) = -2 * 1 = -2
    # SC = (S1 - S4)/2 = (2 - (-2))/2 = 2
    # OC = (S1 + S4)/2 = (2 + (-2))/2 = 0
    # CPR = SC / OC = 2 / 0 -> infinity/nodata handling or very large value
    # Let's check that backscatter is indeed 2.0
    np.testing.assert_allclose(results["radar_backscatter"].data, 2.0, rtol=1e-5)
    
    # Check that DOP is computed and bounded
    assert np.all(results["radar_dop"].data >= 0.0)
    assert np.all(results["radar_dop"].data <= 1.0)

def test_radar_intensity_modes(base_metadata):
    """
    Tests intensity-only radar feature extraction.
    """
    sc_data = np.full((10, 10), 4.0, dtype=np.float32)
    oc_data = np.full((10, 10), 2.0, dtype=np.float32)
    
    layer_a = RasterLayer("sc", sc_data, base_metadata, ["sc.tif"])
    layer_b = RasterLayer("oc", oc_data, base_metadata, ["oc.tif"])
    
    config = RadarConfig()
    
    # 1. Circular Intensity Mode (CPR = SC / OC = 4.0 / 2.0 = 2.0)
    circ_results = extract_radar_features(layer_a, layer_b, config, mode="circular_intensity")
    np.testing.assert_allclose(circ_results["radar_cpr"].data, 2.0, rtol=1e-5)
    np.testing.assert_allclose(circ_results["radar_backscatter"].data, 6.0, rtol=1e-5)
    
    # 2. Linear Intensity Mode (Cross-pol ratio = HV / HH = 2.0 / 4.0 = 0.5)
    lin_results = extract_radar_features(layer_a, layer_b, config, mode="linear_intensity")
    np.testing.assert_allclose(lin_results["radar_cpr"].data, 0.5, rtol=1e-5)
    np.testing.assert_allclose(lin_results["radar_backscatter"].data, 6.0, rtol=1e-5)

def test_terrain_features(base_metadata):
    """
    Verifies slope, roughness, hillshade, and hazard computations from elevation inputs.
    """
    # Create an artificial slope: elevation decreases in x direction (1m resolution)
    x = np.arange(10, dtype=np.float32)
    dem_data = np.tile(10.0 - x, (10, 1)) # dz/dx = -1.0, dz/dy = 0.0
    
    dem_layer = RasterLayer("dem", dem_data, base_metadata, ["dem.tif"])
    
    # Create simple panchromatic camera image with 1 bright pixel (a boulder)
    pan_data = np.zeros((10, 10), dtype=np.float32)
    pan_data[5, 5] = 100.0  # Local peak / boulder
    pan_layer = RasterLayer("pan", pan_data, base_metadata, ["pan.tif"])
    
    config = TerrainConfig(
        slope_threshold_critical=30.0,
        roughness_threshold_critical=1.0,
        boulder_threshold=0.01,
        boulder_density_window_size=3
    )
    
    results = extract_terrain_features(dem_layer, pan_layer, config)
    
    assert "terrain_slope" in results
    assert "terrain_roughness" in results
    assert "terrain_illumination" in results
    assert "terrain_boulder_density" in results
    assert "terrain_hazard" in results
    
    # Slope test: dz/dx = -1.0, dz/dy = 0.0 -> slope angle is arctan(1.0) = 45 degrees
    # Horn's method at boundaries will use padding, but central pixels should be near 45 deg.
    # Note: Horn's formula dz_dx = ((c + 2f + i) - (a + 2d + g)) / 8
    # Since columns differ by -1: (col_i+1 - col_i-1) = -2
    # (c + 2f + i) - (a + 2d + g) = (-2 + 2*-2 + -2) = -8 -> dz_dx = -8 / 8 = -1.0. Correct!
    # Arctan(1.0) = 45 degrees.
    np.testing.assert_allclose(results["terrain_slope"].data[4, 4], 45.0, rtol=1e-5)
    
    # Illumination (Hillshade) should be bounded in [0, 1]
    assert np.all(results["terrain_illumination"].data >= 0.0)
    assert np.all(results["terrain_illumination"].data <= 1.0)
    
    # Hazard index should be computed and bounded
    assert np.all(results["terrain_hazard"].data >= 0.0)
    assert np.all(results["terrain_hazard"].data <= 1.0)

def test_physics_feature_representation(base_metadata):
    """
    Verifies that the PFR aggregates layers and computes metrics correctly.
    """
    cpr_data = np.array([
        [1.0, 2.0, -9999.0],
        [1.5, 3.0, 2.5],
        [0.5, -9999.0, 1.0]
    ], dtype=np.float32)
    
    meta = RasterMetadata(
        crs_wkt=base_metadata.crs_wkt,
        transform=base_metadata.transform,
        width=3,
        height=3,
        dtype="float32",
        bounds=base_metadata.bounds,
        nodata=-9999.0,
        additional_metadata={}
    )
    
    layer = RasterLayer("cpr", cpr_data, meta, ["input.tif"])
    layer.record_step("mod", "act", {"p": 1})
    
    pfr = PhysicsFeatureRepresentation(config_version="1.2.3")
    pfr.add_layer(layer)
    
    assert "cpr" in pfr.layers
    assert "cpr" in pfr.quality_metrics
    
    metrics = pfr.quality_metrics["cpr"]
    # Valid elements: 1.0, 2.0, 1.5, 3.0, 2.5, 0.5, 1.0 (7 elements)
    # Nodata elements: 2 elements
    assert metrics.nodata_count == 2
    assert metrics.valid_percentage == pytest.approx(77.77777)
    assert metrics.min_val == 0.5
    assert metrics.max_val == 3.0
    assert metrics.mean == pytest.approx(np.mean([1.0, 2.0, 1.5, 3.0, 2.5, 0.5, 1.0]))
    
    # Test JSON serialization dict representation
    pfr_dict = pfr.to_dict()
    assert pfr_dict["config_version"] == "1.2.3"
    assert "cpr" in pfr_dict["layers"]
    assert "cpr" in pfr_dict["quality_metrics"]
