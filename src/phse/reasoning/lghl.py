import os
import yaml
import logging
from typing import List, Dict, Optional
from phse.reasoning.models import LunarGeologicalHypothesis

logger = logging.getLogger("phse")

DEFAULT_HYPOTHESES = [
    LunarGeologicalHypothesis(
        id="pure_water_ice",
        name="Pure Subsurface Water Ice",
        description="High-concentration water ice deposit located inside a permanently shadowed polar cold trap.",
        constraints={
            "radar_cpr": (1.1, 5.0),
            "radar_dop": (0.0, 0.4),
            "terrain_slope": (0.0, 10.0),
            "terrain_illumination": (0.0, 0.1),
            "terrain_roughness": (0.0, 0.2)
        },
        prior_probability=0.05
    ),
    LunarGeologicalHypothesis(
        id="ice_regolith_mixture",
        name="Ice-Regolith Mixture",
        description="Subsurface ice grains mixed with standard lunar regolith, displaying moderate polarimetric anomalies.",
        constraints={
            "radar_cpr": (0.6, 1.2),
            "radar_dop": (0.2, 0.6),
            "terrain_slope": (0.0, 12.0),
            "terrain_illumination": (0.0, 0.15),
            "terrain_roughness": (0.0, 0.3)
        },
        prior_probability=0.15
    ),
    LunarGeologicalHypothesis(
        id="blocky_ejecta",
        name="Blocky Impact Ejecta",
        description="Rough, boulder-strewn impact crater ejecta blankets causing strong surface double-bounce returns.",
        constraints={
            "radar_cpr": (0.8, 2.5),
            "radar_dop": (0.5, 0.9),
            "terrain_slope": (0.0, 30.0),
            "terrain_illumination": (0.0, 1.0),
            "terrain_roughness": (0.3, 1.2)
        },
        prior_probability=0.25
    ),
    LunarGeologicalHypothesis(
        id="pyroclastic_deposits",
        name="Pyroclastic Deposits",
        description="Fine-grained volcanic ash or glass beads exhibiting extremely low radar backscatter and smooth slopes.",
        constraints={
            "radar_cpr": (0.0, 0.3),
            "radar_dop": (0.7, 1.0),
            "terrain_slope": (0.0, 8.0),
            "terrain_illumination": (0.0, 1.0),
            "terrain_roughness": (0.0, 0.15)
        },
        prior_probability=0.10
    ),
    LunarGeologicalHypothesis(
        id="dry_regolith",
        name="Standard Dry Lunar Regolith",
        description="Typical weathered lunar soil layer, displaying baseline radar and moderate roughness profiles.",
        constraints={
            "radar_cpr": (0.1, 0.5),
            "radar_dop": (0.6, 1.0),
            "terrain_slope": (0.0, 20.0),
            "terrain_illumination": (0.0, 1.0),
            "terrain_roughness": (0.1, 0.4)
        },
        prior_probability=0.45
    )
]

class HypothesisLibrary:
    """
    Manages loading, filtering, and retrieving geological hypotheses from the LGHL catalog.
    """
    def __init__(self, catalog_path: Optional[str] = None):
        self.hypotheses: Dict[str, LunarGeologicalHypothesis] = {}
        
        if catalog_path and os.path.exists(catalog_path):
            self.load_from_yaml(catalog_path)
        else:
            logger.info("Using default Lunar Geological Hypothesis Library (LGHL)")
            for hyp in DEFAULT_HYPOTHESES:
                self.hypotheses[hyp.id] = hyp

    def load_from_yaml(self, file_path: str):
        """
        Loads the hypothesis library from a YAML configuration file.
        """
        try:
            with open(file_path, "r") as f:
                data = yaml.safe_load(f)
                
            for item in data.get("hypotheses", []):
                hyp = LunarGeologicalHypothesis(**item)
                self.hypotheses[hyp.id] = hyp
            logger.info(f"Loaded {len(self.hypotheses)} hypotheses from LGHL file: {file_path}")
        except Exception as e:
            logger.error(f"Failed to load LGHL catalog from {file_path}. Error: {e}")
            raise RuntimeError(f"Failed to parse LGHL catalog: {e}")

    def get_all(self) -> List[LunarGeologicalHypothesis]:
        """
        Returns all registered hypotheses.
        """
        return list(self.hypotheses.values())

    def get_by_id(self, hypothesis_id: str) -> Optional[LunarGeologicalHypothesis]:
        """
        Retrieves a hypothesis by its unique ID.
        """
        return self.hypotheses.get(hypothesis_id)
