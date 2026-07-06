import logging
import numpy as np
from typing import Dict, Tuple, Optional
from scipy.ndimage import uniform_filter
from phse.models import RasterLayer, RasterMetadata
from phse.analysis.config import RadarConfig

logger = logging.getLogger("phse")

def _apply_boxcar(arr: np.ndarray, mask: np.ndarray, window_size: int) -> np.ndarray:
    """
    Applies a boxcar spatial average filter (multilooking) to a 2D numpy array,
    handling nodata masked regions correctly without boundary/nodata pollution.
    """
    if window_size <= 1:
        return arr.copy()
        
    # Replace masked values with zero for uniform filter calculation
    clean_arr = arr.copy()
    clean_arr[mask] = 0.0
    
    # Count of valid pixels in each window
    weights = np.ones_like(arr)
    weights[mask] = 0.0
    
    # Compute local sum and local weights
    local_sum = uniform_filter(clean_arr, size=window_size, mode='constant', cval=0.0) * (window_size ** 2)
    local_weight = uniform_filter(weights, size=window_size, mode='constant', cval=0.0) * (window_size ** 2)
    
    # Avoid division by zero
    result = np.zeros_like(arr)
    valid_mask = local_weight > 0
    result[valid_mask] = local_sum[valid_mask] / local_weight[valid_mask]
    
    # Preserve original mask
    result[mask] = 0.0
    return result

def compute_stokes(
    eh: np.ndarray, 
    ev: np.ndarray, 
    window_size: int, 
    nodata: float
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Computes Stokes parameters from complex-valued electric field components Eh and Ev.
    
    Mathematical Formulation:
        S1 = <|Eh|^2 + |Ev|^2>
        S2 = <|Eh|^2 - |Ev|^2>
        S3 = 2 * Re(<Eh * Ev*>)
        S4 = -2 * Im(<Eh * Ev*>) (for Left Circular polarization transmit)
    
    Where <.> represents the spatial multilooking boxcar average.
    
    Returns:
        Tuple[S1, S2, S3, S4, mask]
    """
    mask = (eh == nodata) | (ev == nodata) | np.isnan(eh) | np.isnan(ev)
    
    # Compute instantaneous power and cross-products
    p_h = np.abs(eh) ** 2
    p_v = np.abs(ev) ** 2
    cross = eh * np.conj(ev)
    
    # Multilooking boxcar filtering
    S1 = _apply_boxcar(p_h + p_v, mask, window_size)
    S2 = _apply_boxcar(p_h - p_v, mask, window_size)
    S3 = _apply_boxcar(2.0 * np.real(cross), mask, window_size)
    S4 = _apply_boxcar(-2.0 * np.imag(cross), mask, window_size)
    
    return S1, S2, S3, S4, mask

def extract_radar_features(
    layer_a: RasterLayer,
    layer_b: RasterLayer,
    config: RadarConfig,
    mode: str = "hybrid_complex"
) -> Dict[str, RasterLayer]:
    """
    Transforms raw radar raster layers into derived scientific radar layers:
      - Radar Backscatter (S1 or Total Power)
      - Circular Polarization Ratio (CPR)
      - Degree of Polarization (DOP)
      - Polarimetric Decompositions (Even-bounce, Odd-bounce, Volume scattering)
      
    Args:
        layer_a (RasterLayer): First polarization layer (e.g. Eh complex or SC intensity)
        layer_b (RasterLayer): Second polarization layer (e.g. Ev complex or OC intensity)
        config (RadarConfig): Configuration parameters
        mode (str): Polarimetric mode: 'hybrid_complex', 'circular_intensity', 'linear_intensity'
        
    Returns:
        Dict[str, RasterLayer]: Map of feature names to scientific RasterLayers
    """
    logger.info(f"Extracting radar features using mode={mode}")
    
    # Ensure spatial alignment matches
    if layer_a.data.shape != layer_b.data.shape:
        raise ValueError(f"Radar layers must have identical shape for feature extraction. Found {layer_a.data.shape} and {layer_b.data.shape}")
        
    metadata = layer_a.metadata.model_copy(deep=True)
    nodata = metadata.nodata
    
    # Initialize output dictionary
    features: Dict[str, RasterLayer] = {}
    
    if mode == "hybrid_complex":
        # Inputs are complex electric field vectors
        eh = layer_a.data.astype(np.complex64)
        ev = layer_b.data.astype(np.complex64)
        
        S1, S2, S3, S4, mask = compute_stokes(eh, ev, config.cpr_window_size, nodata)
        
        # 1. Backscatter (Total Power / S1)
        backscatter = S1.copy()
        backscatter[mask] = nodata
        
        # 2. Circular Polarization Ratio (CPR)
        # Same-sense SC = (S1 - S4) / 2
        # Opposite-sense OC = (S1 + S4) / 2
        # CPR = SC / OC = (S1 - S4) / (S1 + S4)
        denominator = S1 + S4
        cpr = np.zeros_like(S1)
        valid_cpr = (denominator != 0) & (~mask)
        cpr[valid_cpr] = (S1[valid_cpr] - S4[valid_cpr]) / denominator[valid_cpr]
        cpr[~valid_cpr] = nodata
        
        # 3. Degree of Polarization (DOP)
        # DOP = sqrt(S2^2 + S3^2 + S4^2) / S1
        dop = np.zeros_like(S1)
        valid_dop = (S1 != 0) & (~mask)
        polarized_power = np.sqrt(S2**2 + S3**2 + S4**2)
        dop[valid_dop] = polarized_power[valid_dop] / S1[valid_dop]
        # Clip DOP to physical [0, 1] bounds
        dop = np.clip(dop, 0.0, 1.0)
        dop[~valid_dop] = nodata
        
        # 4. Polarimetric Decompositions (m-chi / m-delta)
        # m = DOP. chi = Poincare ellipticity angle.
        # sin(2*chi) = -S4 / (m * S1)
        # Even-bounce (double-bounce) scattering: P_db = m * S1 * (1 - sin(2*chi)) / 2
        # Odd-bounce (surface) scattering: P_sb = m * S1 * (1 + sin(2*chi)) / 2
        # Diffuse (volume) scattering: P_vol = S1 * (1 - m)
        p_vol = S1 * (1.0 - dop)
        p_vol[mask] = nodata
        
        m_s1 = dop * S1
        sin_2chi = np.zeros_like(S1)
        valid_chi = (m_s1 != 0) & (~mask)
        # Avoid division by zero and sign flipping
        if config.transmit_hand == "left":
            sin_2chi[valid_chi] = -S4[valid_chi] / m_s1[valid_chi]
        else: # right circular transmit
            sin_2chi[valid_chi] = S4[valid_chi] / m_s1[valid_chi]
        sin_2chi = np.clip(sin_2chi, -1.0, 1.0)
        
        p_db = 0.5 * m_s1 * (1.0 - sin_2chi)
        p_sb = 0.5 * m_s1 * (1.0 + sin_2chi)
        
        p_db[mask] = nodata
        p_sb[mask] = nodata
        
        # Construct layers
        features["radar_backscatter"] = RasterLayer("radar_backscatter", backscatter, metadata, [layer_a.sources[0], layer_b.sources[0]])
        features["radar_cpr"] = RasterLayer("radar_cpr", cpr, metadata, [layer_a.sources[0], layer_b.sources[0]])
        features["radar_dop"] = RasterLayer("radar_dop", dop, metadata, [layer_a.sources[0], layer_b.sources[0]])
        features["radar_decomposition_even"] = RasterLayer("radar_decomposition_even", p_db, metadata, [layer_a.sources[0], layer_b.sources[0]])
        features["radar_decomposition_odd"] = RasterLayer("radar_decomposition_odd", p_sb, metadata, [layer_a.sources[0], layer_b.sources[0]])
        features["radar_decomposition_volume"] = RasterLayer("radar_decomposition_volume", p_vol, metadata, [layer_a.sources[0], layer_b.sources[0]])

    elif mode == "circular_intensity":
        # Inputs are same-sense (SC) and opposite-sense (OC) backscatter intensity maps
        sc = layer_a.data
        oc = layer_b.data
        mask = (sc == nodata) | (oc == nodata) | np.isnan(sc) | np.isnan(oc)
        
        # 1. Total Backscatter
        backscatter = sc + oc
        backscatter[mask] = nodata
        
        # 2. CPR = SC / OC
        cpr = np.zeros_like(sc)
        valid_cpr = (oc != 0) & (~mask)
        cpr[valid_cpr] = sc[valid_cpr] / oc[valid_cpr]
        cpr[~valid_cpr] = nodata
        
        # 3. DOP (Approximated from intensity ratio)
        # Since phase is missing, we approximate DOP assuming a partially polarized wave
        # DOP = |sc - oc| / (sc + oc)
        denominator = sc + oc
        dop = np.zeros_like(sc)
        valid_dop = (denominator != 0) & (~mask)
        dop[valid_dop] = np.abs(sc[valid_dop] - oc[valid_dop]) / denominator[valid_dop]
        dop[~valid_dop] = nodata
        
        features["radar_backscatter"] = RasterLayer("radar_backscatter", backscatter, metadata, [layer_a.sources[0], layer_b.sources[0]])
        features["radar_cpr"] = RasterLayer("radar_cpr", cpr, metadata, [layer_a.sources[0], layer_b.sources[0]])
        features["radar_dop"] = RasterLayer("radar_dop", dop, metadata, [layer_a.sources[0], layer_b.sources[0]])

    elif mode == "linear_intensity":
        # Inputs are HH and HV backscatter intensities
        hh = layer_a.data
        hv = layer_b.data
        mask = (hh == nodata) | (hv == nodata) | np.isnan(hh) | np.isnan(hv)
        
        # 1. Total Backscatter (HH + HV)
        backscatter = hh + hv
        backscatter[mask] = nodata
        
        # 2. Cross-Polarization Ratio = HV / HH
        cpr = np.zeros_like(hh)
        valid_cpr = (hh != 0) & (~mask)
        cpr[valid_cpr] = hv[valid_cpr] / hh[valid_cpr]
        cpr[~valid_cpr] = nodata
        
        features["radar_backscatter"] = RasterLayer("radar_backscatter", backscatter, metadata, [layer_a.sources[0], layer_b.sources[0]])
        features["radar_cpr"] = RasterLayer("radar_cpr", cpr, metadata, [layer_a.sources[0], layer_b.sources[0]]) # Acts as cross-polarization ratio here
        
    else:
        raise ValueError(f"Unknown radar polarimetric extraction mode: {mode}")
        
    # Record provenance step on all generated layers
    for name, layer in features.items():
        layer.record_step(
            module="phse.analysis.radar",
            action="extract_radar_features",
            parameters={
                "mode": mode,
                "cpr_window_size": config.cpr_window_size,
                "dop_window_size": config.dop_window_size,
                "transmit_hand": config.transmit_hand
            }
        )
        
    return features
