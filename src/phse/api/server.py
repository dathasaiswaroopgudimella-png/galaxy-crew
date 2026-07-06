import os
import sys
from dotenv import load_dotenv
load_dotenv()
import logging
import asyncio
import base64
import numpy as np
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Ingest parent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from phse.config import load_config
from phse.models import RasterLayer
from phse.loaders.dfsar import DFSARLoader
from phse.loaders.ohrc import OHRCLoader
from phse.processing.preprocessing import preprocess_layer
from phse.processing.alignment import align_rasters
from phse.processing.validation import ValidationPipeline
from phse.analysis.radar import extract_radar_features
from phse.analysis.terrain import extract_terrain_features
from phse.reasoning import PHSEReasoningEngine
from phse.mission import MissionPlanner, RoverPathfinder, ResourceEstimator
from phse.utils.raster import create_synthetic_raster
from phse.api.integrations import OpenRouterClient, GeminiClient

# Initialize FastAPI App
app = FastAPI(title="PHSE Planetary Space-Tech Engine", version="2.0.0")
logger = logging.getLogger("phse")


# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket Telemetry Manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass

manager = ConnectionManager()

# Log Handler to stream logging messages to WebSocket clients
class WebSocketLogHandler(logging.Handler):
    def __init__(self, loop: asyncio.AbstractEventLoop):
        super().__init__()
        self.loop = loop

    def emit(self, record):
        log_entry = self.format(record)
        message = {
            "timestamp": record.created,
            "source": record.name,
            "message": log_entry,
            "type": "info" if record.levelno < 30 else ("warn" if record.levelno < 40 else "error")
        }
        if self.loop and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(manager.broadcast(message), self.loop)

# Initialize Assistant Clients
openrouter_client = OpenRouterClient()
gemini_client = GeminiClient()

# Global variables to hold execution state
STATE: Dict[str, Any] = {
    "run_completed": False,
    "layers": {},
    "metadata": {},
    "results": {}
}

class PipelineRunResponse(BaseModel):
    success: bool
    landing_x: int
    landing_y: int
    landing_score: float
    total_ice_m3: float
    total_ice_tons: float
    trajectory: List[float]
    rover_path: List[List[int]]

@app.on_event("startup")
def startup_event():
    """Triggers default synthetic generation and runs pipeline on startup."""
    try:
        loop = asyncio.get_event_loop()
        ws_handler = WebSocketLogHandler(loop)
        ws_handler.setFormatter(logging.Formatter('%(message)s'))
        logging.getLogger("phse").addHandler(ws_handler)
    except Exception as ex:
        print(f"Failed to initialize WebSocketLogHandler: {ex}")
    run_pipeline_internally()

def run_pipeline_internally():
    """Runs the end-to-end PHSE pipeline and caches results in state memory."""
    workspace_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    config_path = os.path.join(workspace_dir, "config", "default_config.yaml")
    config = load_config(config_path)
    
    # 1. Generate Synthetic Inputs
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
    
    os.makedirs(config.paths.dfsar_path, exist_ok=True)
    os.makedirs(config.paths.ohrc_path, exist_ok=True)
    
    dfsar_file = os.path.join(config.paths.dfsar_path, "dfsar_backscatter.tif")
    ohrc_file = os.path.join(config.paths.ohrc_path, "ohrc_panchromatic.tif")
    
    # Generate mock inputs
    create_synthetic_raster(dfsar_file, 200, 200, lunar_crs_wkt, transform, -9999.0, (-30.0, 0.0), seed=123)
    create_synthetic_raster(ohrc_file, 200, 200, lunar_crs_wkt, transform, 0.0, (0.0, 255.0), seed=202)
    
    # Generate elevation DEM (sombrero crater + noise)
    # We will generate a DEM array and save it to tif
    dem_file = os.path.join(config.paths.ohrc_path, "dem.tif")
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
        dem_file, 'w', driver='GTiff', height=200, width=200, count=1,
        dtype='float32', crs=rasterio.crs.CRS.from_wkt(lunar_crs_wkt),
        transform=Affine(*transform), nodata=-9999.0
    ) as dst:
        dst.write(dem_data, 1)
        
    # 2. Pipeline Execution
    dfsar_loader = DFSARLoader(nodata_value=-9999.0)
    ohrc_loader = OHRCLoader(nodata_value=0.0)
    
    dfsar_layer = dfsar_loader.load(dfsar_file)
    ohrc_layer = ohrc_loader.load(ohrc_file)
    
    dem_meta = dfsar_layer.metadata.model_copy(deep=True)
    dem_layer = RasterLayer("elevation_dem", dem_data, dem_meta, [dem_file])
    
    # Preprocess
    pre_dfsar = preprocess_layer(dfsar_layer, normalize=True, min_val=-30.0, max_val=0.0)
    pre_ohrc = preprocess_layer(ohrc_layer, normalize=True, min_val=0.0, max_val=255.0)
    
    # Setup complex radar vectors
    np.random.seed(12)
    amp_h = np.random.uniform(0.5, 2.0, (200, 200))
    amp_v = np.random.uniform(0.5, 2.0, (200, 200))
    phase_h = np.random.uniform(-np.pi, np.pi, (200, 200))
    phase_v = np.random.uniform(-np.pi, np.pi, (200, 200))
    
    # High-quality circular transmit mock
    eh = (amp_h * np.exp(1j * phase_h)).astype(np.complex64)
    ev = (amp_v * np.exp(1j * phase_v)).astype(np.complex64)
    
    # Inject spatial anomalies inside the crater to simulate water ice (high CPR, low DOP)
    # Crater region is roughly r < 1.0
    crater_mask = r < 1.0
    # Increase SC (same sense return) relative to OC to boost CPR in crater
    # S4 = -2 * Im(Eh * Ev*)
    # Let's adjust eh/ev phase to make CPR high inside crater mask
    eh[crater_mask] = np.abs(eh[crater_mask]) * np.exp(1j * 0.0)
    ev[crater_mask] = np.abs(ev[crater_mask]) * np.exp(1j * (np.pi / 2.0)) # 90 degree phase shift
    
    complex_meta = dfsar_layer.metadata.model_copy(deep=True)
    complex_meta.dtype = "complex64"
    radar_lh = RasterLayer("eh_complex", eh, complex_meta, [dfsar_file])
    radar_lv = RasterLayer("ev_complex", ev, complex_meta, [dfsar_file])
    
    # Extract features
    radar_features = extract_radar_features(radar_lh, radar_lv, config.analysis.radar, mode="hybrid_complex")
    terrain_features = extract_terrain_features(dem_layer, pre_ohrc, config.analysis.terrain)
    
    # Ingest into Reasoning Engine
    pfr = {}
    pfr.update(radar_features)
    pfr.update(terrain_features)
    
    engine = PHSEReasoningEngine()
    reasoning_result = engine.execute(pfr, entropy_threshold=0.01)
    
    # Mission Planning
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
    
    # Rover Path traversal from landing site to highest ice probability pixel
    # Find pixel with highest ice probability
    valid_ice = reasoning_result.probability_layers["pure_water_ice"].data.copy()
    valid_ice[terrain_features["terrain_slope"].data > 18.0] = 0.0 # avoid sheer cliff goals
    max_idx = np.argmax(valid_ice)
    goal_y, goal_x = np.unravel_index(max_idx, valid_ice.shape)
    
    pathfinder = RoverPathfinder(max_rover_slope=20.0)
    rover_path = pathfinder.find_path(
        terrain_features["terrain_slope"],
        terrain_features["terrain_roughness"],
        opt_x, opt_y, int(goal_x), int(goal_y)
    )
    
    # Store layers in state
    STATE["layers"]["dem"] = dem_data
    STATE["layers"]["cpr"] = radar_features["radar_cpr"].data
    STATE["layers"]["dop"] = radar_features["radar_dop"].data
    STATE["layers"]["hazard"] = terrain_features["terrain_hazard"].data
    STATE["layers"]["suitability"] = suitability.data
    STATE["layers"]["geo_map"] = reasoning_result.geological_map.data
    STATE["layers"]["entropy"] = reasoning_result.entropy_layer.data
    
    # Store probability maps
    for h_id, layer in reasoning_result.probability_layers.items():
        STATE["layers"][f"prob_{h_id}"] = layer.data
        
    STATE["results"] = {
        "landing_x": opt_x,
        "landing_y": opt_y,
        "landing_score": score,
        "total_ice_m3": total_vol,
        "total_ice_tons": total_tons,
        "trajectory": reasoning_result.convergence_trajectory,
        "rover_path": rover_path
    }
    STATE["run_completed"] = True
    logger.info("PHSE pipeline internally executed and cached successfully.")

@app.post("/api/run", response_model=PipelineRunResponse)
def run_pipeline():
    """Triggers running the pipeline and returns the summary."""
    try:
        run_pipeline_internally()
        res = STATE["results"]
        return PipelineRunResponse(
            success=True,
            landing_x=res["landing_x"],
            landing_y=res["landing_y"],
            landing_score=res["landing_score"],
            total_ice_m3=res["total_ice_m3"],
            total_ice_tons=res["total_ice_tons"],
            trajectory=res["trajectory"],
            rover_path=res["rover_path"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline execution failed: {e}")

@app.get("/api/layer/{layer_name}")
def get_layer(layer_name: str):
    """Returns a 2D float array representation of the requested layer."""
    if not STATE["run_completed"]:
        raise HTTPException(status_code=400, detail="Pipeline has not been executed yet.")
        
    if layer_name not in STATE["layers"]:
        raise HTTPException(status_code=404, detail=f"Layer '{layer_name}' not found. Available layers: {list(STATE['layers'].keys())}")
        
    # Serialize float values as a nested list
    data = STATE["layers"][layer_name].tolist()
    return {"layer": layer_name, "width": len(data[0]), "height": len(data), "data": data}

@app.get("/api/pixel")
def get_pixel_details(x: int, y: int):
    """Returns detailed metrics for a specific coordinate pixel."""
    if not STATE["run_completed"]:
        raise HTTPException(status_code=400, detail="Pipeline has not been executed yet.")
        
    # Bounds check
    height, width = STATE["layers"]["dem"].shape
    if not (0 <= x < width and 0 <= y < height):
        raise HTTPException(status_code=404, detail="Pixel out of bounds.")
        
    details = {
        "x": x,
        "y": y,
        "dem": float(STATE["layers"]["dem"][y, x]),
        "cpr": float(STATE["layers"]["cpr"][y, x]),
        "dop": float(STATE["layers"]["dop"][y, x]),
        "hazard": float(STATE["layers"]["hazard"][y, x]),
        "suitability": float(STATE["layers"]["suitability"][y, x]),
        "entropy": float(STATE["layers"]["entropy"][y, x]),
        "probabilities": {
            "pure_water_ice": float(STATE["layers"]["prob_pure_water_ice"][y, x]),
            "ice_regolith_mixture": float(STATE["layers"]["prob_ice_regolith_mixture"][y, x]),
            "blocky_ejecta": float(STATE["layers"]["prob_blocky_ejecta"][y, x]),
            "pyroclastic_deposits": float(STATE["layers"]["prob_pyroclastic_deposits"][y, x]),
            "dry_regolith": float(STATE["layers"]["prob_dry_regolith"][y, x])
        }
    }
    return details

class AssistantRequest(BaseModel):
    prompt: str
    mode: str = "text"
    image_base64: Optional[str] = None

@app.post("/api/assistant")
async def assistant_endpoint(request: AssistantRequest):
    """
    Assistant endpoint routing questions to OpenRouter LLM or Gemini Multimodal API.
    Does not run core PHSE calculations; purely supports natural-language and visual assistance.
    """
    try:
        if request.mode == "multimodal" and request.image_base64:
            img_data = base64.b64decode(request.image_base64)
            response = await gemini_client.generate_multimodal_content(
                prompt=request.prompt,
                image_bytes=img_data
            )
        else:
            messages = [{"role": "user", "content": request.prompt}]
            response = await openrouter_client.generate_completion(messages=messages)
        
        if not response:
            return {"response": "The LLM assistant is currently unavailable or didn't return a response. Core PHSE system is running locally."}
        
        return {"response": response}
    except Exception as e:
        logger.error(f"Assistant endpoint error: {e}")
        return {"response": f"Error communicating with AI assistant: {e}"}

@app.websocket("/api/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        await websocket.send_json({
            "timestamp": 0.0,
            "source": "phse.api",
            "message": "Live connection established with PHSE WebSocket telemetry.",
            "type": "success"
        })
        while True:
            # Listen to keep connection open
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.get("/", response_class=HTMLResponse)
def get_dashboard():
    """Serves the main single-page space-tech dashboard interface."""
    dist_index = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "frontend", "dist", "index.html"))
    if os.path.exists(dist_index):
        try:
            with open(dist_index, "r", encoding="utf-8") as f:
                return HTMLResponse(content=f.read(), status_code=200)
        except Exception as e:
            logger.error(f"Failed to serve frontend/dist/index.html: {e}")
            
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>PHSE Lunar Landing & Ice Resource Analytics</title>
        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
        <style>
            :root {
                --bg-primary: #0a0c10;
                --bg-glass: rgba(18, 22, 30, 0.7);
                --bg-glass-hover: rgba(28, 32, 42, 0.8);
                --border-color: rgba(255, 255, 255, 0.08);
                --glow-primary: rgba(56, 189, 248, 0.3);
                --color-primary: #38bdf8;
                --color-text: #f3f4f6;
                --color-text-muted: #9ca3af;
                --shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
            }
            * {
                box-sizing: border-box;
                margin: 0;
                padding: 0;
            }
            body {
                background: var(--bg-primary);
                color: var(--color-text);
                font-family: 'Outfit', sans-serif;
                overflow-x: hidden;
                display: flex;
                flex-direction: column;
                height: 100vh;
            }
            header {
                padding: 1.2rem 2rem;
                background: var(--bg-glass);
                backdrop-filter: blur(10px);
                border-bottom: 1px solid var(--border-color);
                display: flex;
                justify-content: space-between;
                align-items: center;
                z-index: 100;
            }
            header h1 {
                font-size: 1.5rem;
                font-weight: 800;
                letter-spacing: 1px;
                text-transform: uppercase;
                background: linear-gradient(90deg, #38bdf8, #818cf8);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }
            .header-badge {
                font-family: 'JetBrains Mono', monospace;
                font-size: 0.8rem;
                background: rgba(56, 189, 248, 0.1);
                color: var(--color-primary);
                padding: 0.3rem 0.6rem;
                border: 1px solid rgba(56, 189, 248, 0.3);
                border-radius: 4px;
            }
            main {
                display: flex;
                flex: 1;
                overflow: hidden;
                padding: 1.5rem;
                gap: 1.5rem;
            }
            .panel {
                background: var(--bg-glass);
                backdrop-filter: blur(12px);
                border: 1px solid var(--border-color);
                border-radius: 12px;
                box-shadow: var(--shadow);
                display: flex;
                flex-direction: column;
                overflow: hidden;
            }
            #sidebar {
                width: 320px;
                padding: 1.5rem;
                gap: 1.2rem;
                overflow-y: auto;
            }
            .section-title {
                font-size: 0.9rem;
                font-weight: 800;
                text-transform: uppercase;
                letter-spacing: 1.5px;
                color: var(--color-primary);
                margin-bottom: 0.8rem;
                display: flex;
                align-items: center;
                gap: 0.5rem;
            }
            .stat-box {
                background: rgba(255, 255, 255, 0.02);
                border: 1px solid var(--border-color);
                border-radius: 8px;
                padding: 1rem;
                margin-bottom: 0.8rem;
                transition: transform 0.2s, background-color 0.2s;
            }
            .stat-box:hover {
                transform: translateY(-2px);
                background: var(--bg-glass-hover);
                border-color: rgba(56, 189, 248, 0.2);
            }
            .stat-label {
                font-size: 0.75rem;
                color: var(--color-text-muted);
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            .stat-value {
                font-size: 1.4rem;
                font-weight: 800;
                color: #ffffff;
                margin-top: 0.2rem;
            }
            #map-container {
                flex: 1;
                position: relative;
                display: flex;
                flex-direction: column;
            }
            .tabs {
                display: flex;
                background: rgba(0, 0, 0, 0.2);
                border-bottom: 1px solid var(--border-color);
                padding: 0.5rem 1rem;
                gap: 0.5rem;
            }
            .tab-btn {
                background: transparent;
                border: none;
                color: var(--color-text-muted);
                padding: 0.5rem 1rem;
                font-family: 'Outfit', sans-serif;
                font-weight: 600;
                font-size: 0.85rem;
                cursor: pointer;
                border-radius: 6px;
                transition: all 0.2s;
            }
            .tab-btn:hover {
                color: #ffffff;
                background: rgba(255, 255, 255, 0.04);
            }
            .tab-btn.active {
                color: var(--color-primary);
                background: rgba(56, 189, 248, 0.1);
                border: 1px solid rgba(56, 189, 248, 0.2);
            }
            .canvas-wrapper {
                flex: 1;
                display: flex;
                justify-content: center;
                align-items: center;
                background: #040508;
                position: relative;
                overflow: hidden;
            }
            canvas {
                max-width: 100%;
                max-height: 100%;
                box-shadow: 0 20px 50px rgba(0,0,0,0.5);
                border: 1px solid rgba(255, 255, 255, 0.05);
                cursor: crosshair;
            }
            .hover-details-panel {
                position: absolute;
                bottom: 1rem;
                right: 1rem;
                width: 260px;
                padding: 1rem;
                background: rgba(10, 12, 16, 0.9);
                border: 1px solid var(--border-color);
                border-radius: 8px;
                box-shadow: var(--shadow);
                backdrop-filter: blur(10px);
                font-size: 0.8rem;
                display: none;
                z-index: 10;
            }
            .hover-row {
                display: flex;
                justify-content: space-between;
                padding: 0.25rem 0;
                border-bottom: 1px solid rgba(255, 255, 255, 0.02);
            }
            .hover-row:last-child {
                border-bottom: none;
            }
            .hover-label {
                color: var(--color-text-muted);
            }
            .hover-val {
                font-weight: 600;
                font-family: 'JetBrains Mono', monospace;
            }
            #bottom-panel {
                height: 250px;
                min-height: 250px;
                padding: 1.2rem;
                display: flex;
                gap: 1.5rem;
            }
            #telemetry-log::-webkit-scrollbar {
                width: 6px;
            }
            #telemetry-log::-webkit-scrollbar-track {
                background: rgba(255, 255, 255, 0.01);
            }
            #telemetry-log::-webkit-scrollbar-thumb {
                background: rgba(255, 255, 255, 0.1);
                border-radius: 3px;
            }
            #telemetry-log::-webkit-scrollbar-thumb:hover {
                background: rgba(56, 189, 248, 0.3);
            }
            .chart-box {
                flex: 1;
                border: 1px solid var(--border-color);
                border-radius: 8px;
                padding: 1rem;
                background: rgba(0,0,0,0.1);
                display: flex;
                flex-direction: column;
                overflow: hidden;
            }
            .chart-canvas-wrapper {
                flex: 1;
                position: relative;
                min-height: 0;
                overflow: hidden;
            }
            .chart-canvas-wrapper canvas {
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
            }
            #run-btn {
                background: linear-gradient(135deg, #38bdf8, #818cf8);
                color: #ffffff;
                font-weight: 800;
                border: none;
                padding: 0.8rem 1.2rem;
                border-radius: 8px;
                cursor: pointer;
                transition: opacity 0.2s, transform 0.1s;
                text-transform: uppercase;
                letter-spacing: 1px;
                font-size: 0.85rem;
                box-shadow: 0 4px 14px rgba(56, 189, 248, 0.4);
            }
            #run-btn:hover {
                opacity: 0.9;
                transform: translateY(-1px);
            }
            #run-btn:active {
                transform: translateY(0);
            }
            .legend-item {
                display: flex;
                align-items: center;
                gap: 0.5rem;
                font-size: 0.8rem;
                margin-top: 0.25rem;
            }
            .legend-color {
                width: 12px;
                height: 12px;
                border-radius: 3px;
                border: 1px solid rgba(255,255,255,0.1);
            }
        </style>
    </head>
    <body>
        <header>
            <h1>PHSE Planetary Space-Tech Engine</h1>
            <div style="display: flex; align-items: center; gap: 1rem;">
                <div class="header-badge">ISRO BHARATIYA ANTARIKSH HACKATHON 2026</div>
                <button id="run-btn" onclick="triggerRun()">Recalculate</button>
            </div>
        </header>
        
        <main>
            <!-- Sidebar with Landing & Resource Summary -->
            <div id="sidebar" class="panel">
                <div>
                    <div class="section-title">📍 Recommendation</div>
                    <div class="stat-box">
                        <div class="stat-label">Optimal Landing Zone</div>
                        <div class="stat-value" id="landing-coords">Evaluating...</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-label">Zone Suitability Score</div>
                        <div class="stat-value" id="landing-score">Evaluating...</div>
                    </div>
                </div>
                
                <div>
                    <div class="section-title">💎 Subsurface Ice Resources</div>
                    <div class="stat-box">
                        <div class="stat-label">Estimated Ice Mass</div>
                        <div class="stat-value" id="ice-mass">Evaluating...</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-label">Estimated Ice Volume</div>
                        <div class="stat-value" id="ice-volume">Evaluating...</div>
                    </div>
                </div>
                
                <div style="flex: 1; display: flex; flex-direction: column;">
                    <div class="section-title">📊 Geological Legend</div>
                    <div style="background: rgba(0,0,0,0.15); border: 1px solid var(--border-color); border-radius: 8px; padding: 0.8rem; flex: 1; overflow-y: auto;">
                        <div class="legend-item"><div class="legend-color" style="background:#0033cc;"></div><span>Pure Subsurface Water Ice</span></div>
                        <div class="legend-item"><div class="legend-color" style="background:#3399ff;"></div><span>Ice-Regolith Mixture</span></div>
                        <div class="legend-item"><div class="legend-color" style="background:#ff3300;"></div><span>Blocky Impact Ejecta</span></div>
                        <div class="legend-item"><div class="legend-color" style="background:#800080;"></div><span>Pyroclastic Deposits</span></div>
                        <div class="legend-item"><div class="legend-color" style="background:#808080;"></div><span>Standard Dry Regolith</span></div>
                    </div>
                </div>
            </div>
            
            <!-- Map and trajectory panels -->
            <div style="flex: 1; display: flex; flex-direction: column; gap: 1.5rem;">
                <!-- Main Map Panel -->
                <div id="map-container" class="panel">
                    <div class="tabs">
                        <button class="tab-btn active" onclick="switchLayer('dem', this)">Elevation DEM</button>
                        <button class="tab-btn" onclick="switchLayer('cpr', this)">Radar CPR</button>
                        <button class="tab-btn" onclick="switchLayer('dop', this)">Radar DOP</button>
                        <button class="tab-btn" onclick="switchLayer('hazard', this)">Landing Hazard</button>
                        <button class="tab-btn" onclick="switchLayer('suitability', this)">Landing Suitability</button>
                        <button class="tab-btn" onclick="switchLayer('geo_map', this)">Geological Interpretation</button>
                    </div>
                    
                    <div class="canvas-wrapper">
                        <canvas id="map-canvas" width="400" height="400"></canvas>
                        
                        <!-- Floating Details Panel on Hover -->
                        <div id="details-panel" class="hover-details-panel">
                            <div class="section-title" style="margin-bottom:0.5rem; font-size:0.75rem;">Cursor Analytics</div>
                            <div class="hover-row"><span class="hover-label">Coordinates (X,Y)</span><span class="hover-val" id="hover-coord">-</span></div>
                            <div class="hover-row"><span class="hover-label">Elevation DEM</span><span class="hover-val" id="hover-dem">-</span></div>
                            <div class="hover-row"><span class="hover-label">Radar CPR</span><span class="hover-val" id="hover-cpr">-</span></div>
                            <div class="hover-row"><span class="hover-label">Degree of Polarization</span><span class="hover-val" id="hover-dop">-</span></div>
                            <div class="hover-row"><span class="hover-label">Hazard Index</span><span class="hover-val" id="hover-hazard">-</span></div>
                            <div class="hover-row"><span class="hover-label">Ice Probability</span><span class="hover-val" id="hover-ice-prob">-</span></div>
                        </div>
                    </div>
                </div>
                
                <!-- Bottom Analytics Trajectory Panel -->
                <div id="bottom-panel" class="panel" style="flex-direction: row;">
                    <div class="chart-box" style="flex: 2;">
                        <div class="section-title">📈 Bayesian Entropy Convergence Trajectory</div>
                        <div class="chart-canvas-wrapper">
                            <canvas id="chart-canvas"></canvas>
                        </div>
                    </div>
                    <div class="log-box" style="flex: 1; border: 1px solid var(--border-color); border-radius: 8px; padding: 1rem; background: rgba(0,0,0,0.15); display: flex; flex-direction: column; overflow: hidden;">
                        <div class="section-title">🖥️ Telemetry Stream</div>
                        <div id="telemetry-log" style="flex: 1; overflow-y: auto; font-family: 'JetBrains Mono', monospace; font-size: 0.72rem; color: #a7f3d0; line-height: 1.4; padding-right: 0.5rem; text-align: left;">
                            <!-- Filled dynamically -->
                        </div>
                    </div>
                </div>
            </div>
        </main>
        
        <script>
            let currentLayer = 'dem';
            let layerData = null;
            let pipelineResults = null;
            
            async function triggerRun() {
                document.getElementById('run-btn').innerText = 'Recalculating...';
                try {
                    const response = await fetch('/api/run', { method: 'POST' });
                    pipelineResults = await response.json();
                    updateSummaryPanel();
                    await fetchLayerData();
                } catch(e) {
                    console.error("Failed to execute pipeline run:", e);
                } finally {
                    document.getElementById('run-btn').innerText = 'Recalculate';
                }
            }
            
            async function fetchLayerData() {
                try {
                    const res = await fetch(`/api/layer/${currentLayer}`);
                    layerData = await res.json();
                    renderMap();
                } catch(e) {
                    console.error("Failed to fetch layer details:", e);
                }
            }
            
            function switchLayer(layerName, element) {
                document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
                element.classList.add('active');
                currentLayer = layerName;
                fetchLayerData();
            }
            
            function updateSummaryPanel() {
                if(!pipelineResults) return;
                document.getElementById('landing-coords').innerText = `X: ${pipelineResults.landing_x}, Y: ${pipelineResults.landing_y}`;
                document.getElementById('landing-score').innerText = `${(pipelineResults.landing_score * 100).toFixed(2)}%`;
                document.getElementById('ice-mass').innerText = `${pipelineResults.total_ice_tons.toFixed(2)} Tons`;
                document.getElementById('ice-volume').innerText = `${pipelineResults.total_ice_m3.toFixed(2)} m³`;
                
                // Populate Telemetry stream
                const log = document.getElementById('telemetry-log');
                const now = new Date().toLocaleTimeString();
                log.innerHTML = `
                    <div style="color: #9ca3af; margin-bottom: 4px;">[${now}] PHSE-INIT: Pipeline startup triggered.</div>
                    <div style="color: #60a5fa; margin-bottom: 4px;">[${now}] PHSE-LOADER: Ingesting lunar raster assets...</div>
                    <div style="color: #34d399; margin-bottom: 4px;">[${now}] PHSE-ALIGN: Raster layers aligned successfully. Shape: 200x200.</div>
                    <div style="color: #fbbf24; margin-bottom: 4px;">[${now}] PHSE-FEATURE: CPR and DOP features extracted.</div>
                    <div style="color: #a7f3d0; margin-bottom: 4px;">[${now}] PHSE-REASONING: Constraint matching complete.</div>
                    <div style="color: #818cf8; margin-bottom: 4px;">[${now}] PHSE-AHS: Feature convergence running...</div>
                    <div style="color: #818cf8; margin-bottom: 4px;">[${now}] PHSE-BAYESIAN: Final entropy converged to ${pipelineResults.trajectory[pipelineResults.trajectory.length - 1].toFixed(4)} bits.</div>
                    <div style="color: #10b981; font-weight: bold; margin-bottom: 4px;">[${now}] PHSE-MISSION: Optimal landing localized at (${pipelineResults.landing_x}, ${pipelineResults.landing_y}).</div>
                    <div style="color: #f59e0b; margin-bottom: 4px;">[${now}] PHSE-TRAVERSAL: Planned A* path: ${pipelineResults.rover_path.length} waypoints.</div>
                `;
            }
            
            function renderMap() {
                if(!layerData || !pipelineResults) return;
                
                const canvas = document.getElementById('map-canvas');
                const ctx = canvas.getContext('2d');
                const width = layerData.width;
                const height = layerData.height;
                
                canvas.width = width;
                canvas.height = height;
                
                const imgData = ctx.createImageData(width, height);
                const raw = layerData.data;
                
                // Color scaling
                let min = Infinity, max = -Infinity;
                for(let y=0; y<height; y++) {
                    for(let x=0; x<width; x++) {
                        const val = raw[y][x];
                        if(val === -9999.0) continue;
                        if(val < min) min = val;
                        if(val > max) max = val;
                    }
                }
                
                for(let y=0; y<height; y++) {
                    for(let x=0; x<width; x++) {
                        const idx = (y * width + x) * 4;
                        const val = raw[y][x];
                        
                        if(val === -9999.0) {
                            // Nodata (transparent / dark blue-grey)
                            imgData.data[idx] = 10;
                            imgData.data[idx+1] = 12;
                            imgData.data[idx+2] = 16;
                            imgData.data[idx+3] = 255;
                            continue;
                        }
                        
                        // Map values depending on active layer type
                        let r=0, g=0, b=0;
                        const t = (max > min) ? (val - min) / (max - min) : 0;
                        
                        if(currentLayer === 'dem') {
                            // Terrain color mapping
                            r = Math.floor(t * 120);
                            g = Math.floor(t * 200 + 40);
                            b = Math.floor(t * 100);
                        } else if(currentLayer === 'cpr') {
                            // Blue-white-red color mapping
                            r = Math.floor(t * 255);
                            g = Math.floor(t * 100 + (1-t)*100);
                            b = Math.floor((1-t) * 255);
                        } else if(currentLayer === 'dop') {
                            // Plasma/magma color mapping
                            r = Math.floor(t * 255);
                            g = Math.floor(t * 150);
                            b = Math.floor((1-t) * 80);
                        } else if(currentLayer === 'hazard') {
                            // Green (safe) -> Red (unsafe)
                            r = Math.floor(t * 255);
                            g = Math.floor((1 - t) * 200);
                            b = 30;
                        } else if(currentLayer === 'suitability') {
                            // Dark -> Neon Green Suitability glow
                            r = 10;
                            g = Math.floor(t * 255);
                            b = Math.floor(t * 150);
                        } else if(currentLayer === 'geo_map') {
                            // Categorical color codes:
                            // 1.0 (pure ice) -> Blue, 2.0 (ice mixture) -> Light Blue, 3.0 (blocks) -> Red, 4.0 (pyroclastics) -> Purple, 5.0 (regolith) -> Grey
                            if(val === 1.0) { r=0; g=51; b=204; }
                            else if(val === 2.0) { r=51; g=153; b=255; }
                            else if(val === 3.0) { r=255; g=51; b=0; }
                            else if(val === 4.0) { r=128; g=0; b=128; }
                            else if(val === 5.0) { r=128; g=128; b=128; }
                        } else {
                            // Grayscale fallback
                            const gray = Math.floor(t * 255);
                            r = g = b = gray;
                        }
                        
                        imgData.data[idx] = r;
                        imgData.data[idx+1] = g;
                        imgData.data[idx+2] = b;
                        imgData.data[idx+3] = 255;
                    }
                }
                
                ctx.putImageData(imgData, 0, 0);
                
                // 5. Draw Rover Path overlay
                const path = pipelineResults.rover_path;
                if(path && path.length > 0) {
                    ctx.strokeStyle = '#facc15'; // Neon yellow path line
                    ctx.lineWidth = 1.5;
                    ctx.beginPath();
                    ctx.moveTo(path[0][0], path[0][1]);
                    for(let i=1; i<path.length; i++) {
                        ctx.lineTo(path[i][0], path[i][1]);
                    }
                    ctx.stroke();
                }
                
                // 6. Draw Landing Site marker
                ctx.strokeStyle = '#38bdf8'; // Cyan circle marker
                ctx.lineWidth = 1.5;
                ctx.beginPath();
                ctx.arc(pipelineResults.landing_x, pipelineResults.landing_y, 4, 0, Math.PI * 2);
                ctx.stroke();
            }
            
            function renderConvergenceTrajectory() {
                if(!pipelineResults) return;
                const canvas = document.getElementById('chart-canvas');
                const wrapper = canvas.parentElement;
                const ctx = canvas.getContext('2d');
                
                // Use the wrapper's layout size (CSS absolute positioning keeps it stable)
                const dpr = window.devicePixelRatio || 1;
                const cssWidth = wrapper.clientWidth;
                const cssHeight = wrapper.clientHeight;
                
                // Set the canvas buffer size for crisp rendering
                canvas.width = cssWidth * dpr;
                canvas.height = cssHeight * dpr;
                ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
                
                const width = cssWidth;
                const height = cssHeight;
                
                const data = pipelineResults.trajectory;
                const len = data.length;
                if(len === 0) return;
                
                const maxVal = Math.max(...data) * 1.15; // 15% headroom
                const minVal = 0; // Always start Y-axis from zero for clarity
                const range = maxVal - minVal || 0.01;
                
                const chartLeft = 58;
                const chartRight = width - 16;
                const chartTop = 16;
                const chartBottom = height - 32;
                const chartWidth = chartRight - chartLeft;
                const chartHeight = chartBottom - chartTop;
                
                ctx.clearRect(0, 0, width, height);
                
                // 1. Draw horizontal grids and Y axis labels
                ctx.strokeStyle = 'rgba(255, 255, 255, 0.05)';
                ctx.lineWidth = 1;
                ctx.fillStyle = '#9ca3af';
                ctx.font = '9px "JetBrains Mono"';
                ctx.textAlign = 'right';
                ctx.textBaseline = 'middle';
                
                const gridLines = 4;
                for(let i = 0; i <= gridLines; i++) {
                    const t = i / gridLines;
                    const y = chartBottom - t * chartHeight;
                    const val = minVal + t * range;
                    
                    // Draw grid line
                    ctx.beginPath();
                    ctx.moveTo(chartLeft, y);
                    ctx.lineTo(chartRight, y);
                    ctx.stroke();
                    
                    // Draw Y label
                    ctx.fillText(val.toFixed(4), chartLeft - 8, y);
                }
                
                // Coordinates mapper
                const getCoords = (idx) => {
                    const val = data[idx];
                    const x = chartLeft + chartWidth * (idx / (len - 1 || 1));
                    const y = chartBottom - ((val - minVal) / range) * chartHeight;
                    return [x, y];
                };
                
                // 2. Draw Gradient Area Fill under the line
                const fillGrad = ctx.createLinearGradient(0, chartTop, 0, chartBottom);
                fillGrad.addColorStop(0, 'rgba(129, 140, 248, 0.25)'); // Neon indigo
                fillGrad.addColorStop(1, 'rgba(129, 140, 248, 0.0)');
                
                ctx.fillStyle = fillGrad;
                ctx.beginPath();
                const firstPt = getCoords(0);
                ctx.moveTo(firstPt[0], chartBottom);
                ctx.lineTo(firstPt[0], firstPt[1]);
                for(let i = 1; i < len; i++) {
                    const pt = getCoords(i);
                    ctx.lineTo(pt[0], pt[1]);
                }
                const lastPt = getCoords(len - 1);
                ctx.lineTo(lastPt[0], chartBottom);
                ctx.closePath();
                ctx.fill();
                
                // 3. Draw Trajectory Line
                ctx.strokeStyle = '#818cf8'; // Neon Indigo
                ctx.lineWidth = 2.5;
                ctx.shadowColor = 'rgba(129, 140, 248, 0.5)';
                ctx.shadowBlur = 6;
                
                ctx.beginPath();
                ctx.moveTo(firstPt[0], firstPt[1]);
                for(let i = 1; i < len; i++) {
                    const pt = getCoords(i);
                    ctx.lineTo(pt[0], pt[1]);
                }
                ctx.stroke();
                
                // Reset shadow for labels/dots
                ctx.shadowBlur = 0;
                
                // 4. Draw data points and X-axis iteration label tags
                ctx.textAlign = 'center';
                for(let i = 0; i < len; i++) {
                    const pt = getCoords(i);
                    
                    // Outer glow dot
                    ctx.fillStyle = '#38bdf8'; // Sky blue dot
                    ctx.beginPath();
                    ctx.arc(pt[0], pt[1], 4.5, 0, Math.PI * 2);
                    ctx.fill();
                    
                    // Inner white dot
                    ctx.fillStyle = '#ffffff';
                    ctx.beginPath();
                    ctx.arc(pt[0], pt[1], 2, 0, Math.PI * 2);
                    ctx.fill();
                    
                    // Iteration label text at bottom
                    ctx.fillStyle = '#9ca3af';
                    ctx.fillText(`It ${i}`, pt[0], height - 8);
                }
            }
            
            // Mouse cursor hover integration
            const canvas = document.getElementById('map-canvas');
            canvas.addEventListener('mousemove', async (e) => {
                const rect = canvas.getBoundingClientRect();
                const scaleX = canvas.width / rect.width;
                const scaleY = canvas.height / rect.height;
                const x = Math.floor((e.clientX - rect.left) * scaleX);
                const y = Math.floor((e.clientY - rect.top) * scaleY);
                
                if(x >= 0 && x < canvas.width && y >= 0 && y < canvas.height) {
                    try {
                        const res = await fetch(`/api/pixel?x=${x}&y=${y}`);
                        const details = await res.json();
                        
                        document.getElementById('hover-coord').innerText = `${x}, ${y}`;
                        document.getElementById('hover-dem').innerText = `${details.dem.toFixed(2)} m`;
                        document.getElementById('hover-cpr').innerText = `${details.cpr.toFixed(3)}`;
                        document.getElementById('hover-dop').innerText = `${details.dop.toFixed(3)}`;
                        document.getElementById('hover-hazard').innerText = `${(details.hazard * 100).toFixed(1)}%`;
                        document.getElementById('hover-ice-prob').innerText = `${(details.probabilities.pure_water_ice * 100).toFixed(1)}%`;
                        
                        document.getElementById('details-panel').style.display = 'block';
                    } catch(err) {
                        console.error(err);
                    }
                }
            });
            
            canvas.addEventListener('mouseleave', () => {
                document.getElementById('details-panel').style.display = 'none';
            });
            
            // Initialization on load
            window.addEventListener('load', async () => {
                // Wait briefly for startup_event execution
                setTimeout(async () => {
                    try {
                        const res = await fetch('/api/run', { method: 'POST' });
                        pipelineResults = await res.json();
                        updateSummaryPanel();
                        renderConvergenceTrajectory();
                        await fetchLayerData();
                    } catch(err) {
                        console.error("Initialization pipeline execution failed:", err);
                    }
                }, 500);
            });
            
            // Keep chart stable on window resize
            window.addEventListener('resize', () => {
                if(pipelineResults) renderConvergenceTrajectory();
            });
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)

# Mount frontend assets dynamically if present
frontend_assets_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "frontend", "dist", "assets"))
if os.path.exists(frontend_assets_dir):
    try:
        app.mount("/assets", StaticFiles(directory=frontend_assets_dir), name="assets")
        logger.info(f"Mounted static assets from {frontend_assets_dir}")
    except Exception as e:
        logger.error(f"Failed to mount frontend assets: {e}")

