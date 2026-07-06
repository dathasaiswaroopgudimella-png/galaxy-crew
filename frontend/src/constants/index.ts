import type { GeologicalHypothesis, LayerDetail } from '../types'

export const HYPOTHESES: GeologicalHypothesis[] = [
  {
    id: "pure_water_ice",
    name: "Pure Subsurface Water Ice",
    desc: "High-concentration water ice deposit located inside a permanently shadowed polar cold trap.",
    prior: 5.0,
    constraints: {
      "radar_cpr": "1.1 to 5.0 (High circular polarization return)",
      "radar_dop": "0.0 to 0.4 (Strong depolarizing double-bounce)",
      "terrain_slope": "0.0 to 10.0 degrees (Flat crater floor)",
      "terrain_illumination": "0.0 to 0.1 (PSR conditions)",
      "terrain_roughness": "0.0 to 0.2m (Smooth ice fill)"
    }
  },
  {
    id: "ice_regolith_mixture",
    name: "Ice-Regolith Mixture",
    desc: "Subsurface ice grains mixed with lunar regolith, displaying moderate polarimetric anomalies.",
    prior: 15.0,
    constraints: {
      "radar_cpr": "0.6 to 1.2 (Moderate CPR anomaly)",
      "radar_dop": "0.2 to 0.6 (Medium depolarization)",
      "terrain_slope": "0.0 to 12.0 degrees (Gentle slopes)",
      "terrain_illumination": "0.0 to 0.15 (Shadowed areas)",
      "terrain_roughness": "0.0 to 0.3m (Standard roughness)"
    }
  },
  {
    id: "blocky_ejecta",
    name: "Blocky Impact Ejecta",
    desc: "Rough, boulder-strewn impact crater ejecta blankets causing strong surface double-bounce returns.",
    prior: 15.0,
    constraints: {
      "radar_cpr": "0.8 to 2.5 (High CPR due to surface blocks)",
      "radar_dop": "0.1 to 0.5 (Moderate/low polarization)",
      "terrain_slope": "0.0 to 30.0 degrees (High local slopes)",
      "terrain_illumination": "0.0 to 1.0 (Sunlit or shadowed)",
      "terrain_roughness": "0.3 to 1.2m (Extremely rough/rocky)"
    }
  },
  {
    id: "pyroclastic_deposits",
    name: "Pyroclastic Deposits",
    desc: "Fine-grained volcanic ash or glass beads exhibiting extremely low radar backscatter and smooth slopes.",
    prior: 10.0,
    constraints: {
      "radar_cpr": "0.0 to 0.3 (Very low CPR return)",
      "radar_dop": "0.7 to 1.0 (Extremely polarized single-bounce)",
      "terrain_slope": "0.0 to 8.0 degrees (Very flat plain)",
      "terrain_illumination": "0.0 to 1.0 (Open plain)",
      "terrain_roughness": "0.0 to 0.15m (Powdery/smooth texture)"
    }
  },
  {
    id: "dry_regolith",
    name: "Standard Dry Lunar Regolith",
    desc: "Typical weathered lunar soil layer, displaying baseline radar and moderate roughness profiles.",
    prior: 45.0,
    constraints: {
      "radar_cpr": "0.1 to 0.5 (Baseline CPR return)",
      "radar_dop": "0.6 to 1.0 (High polarization/single-bounce)",
      "terrain_slope": "0.0 to 20.0 degrees (Undulating terrain)",
      "terrain_illumination": "0.0 to 1.0 (Sunlit plains)",
      "terrain_roughness": "0.1 to 0.4m (Moderate micro-relief)"
    }
  }
];

export const LAYERS: LayerDetail[] = [
  {
    id: 'dem',
    name: 'Digital Elevation Model (DEM)',
    units: 'Meters',
    desc: 'Topographic height map of the target region relative to lunar datum.',
    scienceImpact: 'Determines overall topographical constraints. Used to identify crater floors, ridges, and terrain slope hazard bounds.'
  },
  {
    id: 'cpr',
    name: 'Circular Polarization Ratio (CPR)',
    units: 'Ratio (SC/OC)',
    desc: 'The ratio of Same-Sense to Opposite-Sense circular polarization return from radar signals.',
    scienceImpact: 'High CPR (>1.0) inside shadowed craters indicates Coherent Backscatter Opposition Effect (CBOE) caused by subsurface water ice deposits. High CPR on sunlit slopes indicates blocky surface ejecta.'
  },
  {
    id: 'dop',
    name: 'Degree of Polarization (DOP)',
    units: 'Fraction (0.0 to 1.0)',
    desc: 'Measurement of the polarization degree of backscattered radar signal waves.',
    scienceImpact: 'Highly depolarized radar returns (low DOP <0.4) combined with high CPR confirm multiple volume scattering inside pure water ice sheets.'
  },
  {
    id: 'hazard',
    name: 'Landing Hazard Index',
    units: 'Scale (0.0 to 1.0)',
    desc: 'Fused multi-criteria hazard mapping incorporating local terrain slope, roughness, and boulder distributions.',
    scienceImpact: 'Defines safety exclusions for landing zone localization. Safe sites must obtain index scores below 0.35.'
  },
  {
    id: 'suitability',
    name: 'Landing Suitability Map',
    units: 'Score (0% to 100%)',
    desc: 'Overall landing suitability scoring blending hazard limits with water ice resource confidence maps.',
    scienceImpact: 'Directly guides landing site recommendation selection. The coordinate with maximum suitability score is selected.'
  },
  {
    id: 'geo_map',
    name: 'Refined Geological Interpretation Map',
    units: 'Class Codes',
    desc: 'Fitted geological mapping classifying pixels into discrete categories: Ice, Mixture, Ejecta, Pyroclastics, Regolith.',
    scienceImpact: 'Visualizes structural distribution. Shows where pure ice boundaries are concentrated.'
  },
  {
    id: 'entropy',
    name: 'Shannon Information Entropy',
    units: 'Bits',
    desc: 'Measures remaining geological classification uncertainty across all classes.',
    scienceImpact: 'Directly informs the AHS Sequential Planner. High entropy areas indicate areas requiring more observation layers.'
  }
];
