<p align="center">
  <img src="frontend/public/favicon.svg" width="80" alt="PHSE Logo" />
</p>

<h1 align="center">🌌 PHSE — Planetary Habitability & Site Evaluation Engine</h1>

<p align="center">
  <strong>A research-grade scientific mission analysis platform for autonomous lunar landing site evaluation</strong>
</p>

<p align="center">
  <a href="#-quick-start"><img src="https://img.shields.io/badge/Quick_Start-3_Steps-00e5ff?style=for-the-badge&labelColor=030508" alt="Quick Start" /></a>
  <a href="#-architecture"><img src="https://img.shields.io/badge/Architecture-PHSE_Pipeline-ff9100?style=for-the-badge&labelColor=030508" alt="Architecture" /></a>
  <a href="#-features"><img src="https://img.shields.io/badge/Features-12+_Modules-00e676?style=for-the-badge&labelColor=030508" alt="Features" /></a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/React-19-61DAFB?style=flat-square&logo=react&logoColor=black" alt="React" />
  <img src="https://img.shields.io/badge/TypeScript-5.6-3178C6?style=flat-square&logo=typescript&logoColor=white" alt="TypeScript" />
  <img src="https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat-square&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/TailwindCSS-3.4-06B6D4?style=flat-square&logo=tailwindcss&logoColor=white" alt="Tailwind" />
  <img src="https://img.shields.io/badge/Three.js-R3F-000000?style=flat-square&logo=three.js&logoColor=white" alt="Three.js" />
</p>

---

## 🛰️ What is PHSE?

**PHSE** (Planetary Habitability & Site Evaluation Engine) is a full-stack scientific computing platform that evaluates lunar surface sites for optimal landing zone selection. It combines physics-based terrain analysis with Bayesian reasoning and AI-assisted hypothesis testing to produce actionable mission plans.

The platform processes multi-modal remote sensing data (radar backscatter from DFSAR, high-resolution imagery from OHRC) through a rigorous scientific pipeline, producing confidence-weighted landing site recommendations with full explainability.

```
 ┌─────────────────────────────────────────────────────────────────┐
 │                     PHSE SCIENTIFIC PIPELINE                    │
 │                                                                 │
 │  📡 Data Ingest  →  🔬 Feature Extraction  →  🧠 Reasoning    │
 │       DFSAR            Terrain Analysis          LGHL           │
 │       OHRC             Radar Processing          AHS            │
 │       DEM              Slope/Roughness           Bayesian       │
 │                                                                 │
 │  →  🎯 Constraint Matching  →  🚀 Mission Planning            │
 │         Safety Gates             Resource Optimization          │
 │         Ice Confidence           Traversal Planning             │
 │         Power Analysis           Risk Assessment                │
 └─────────────────────────────────────────────────────────────────┘
```

---

## ⚡ Quick Start

### Prerequisites

| Tool | Version | Download |
|------|---------|----------|
| **Python** | 3.10+ | [python.org](https://www.python.org/downloads/) |
| **Node.js** | 18+ | [nodejs.org](https://nodejs.org/) |
| **npm** | 9+ | Included with Node.js |

### 3-Step Setup

```bash
# 1️⃣  Install Python dependencies
pip install -r requirements.txt

# 2️⃣  Build the frontend
cd frontend && npm install && npm run build && cd ..

# 3️⃣  Launch the server
# Windows PowerShell:
$env:PYTHONPATH="src"; python -m uvicorn phse.api.server:app --host 0.0.0.0 --port 8000

# Linux / macOS:
PYTHONPATH=src python -m uvicorn phse.api.server:app --host 0.0.0.0 --port 8000
```

Open **http://localhost:8000** in your browser. 🎉

---

## 🏗️ Architecture

```
galaxy-crew/
├── 🐍 src/phse/                     # Python backend — Scientific Engine
│   ├── api/
│   │   ├── server.py                # FastAPI server (serves frontend + REST API)
│   │   └── integrations/            # AI client adapters (OpenRouter, Gemini, OpenAI)
│   ├── analysis/                    # Feature extraction & terrain analysis
│   │   ├── terrain.py               # Slope, roughness, elevation processing
│   │   ├── radar.py                 # DFSAR backscatter analysis
│   │   └── feature_set.py           # Multi-modal feature fusion
│   ├── reasoning/                   # Scientific reasoning engine
│   │   ├── lghl.py                  # Layered Generative Hypothesis Logic
│   │   ├── ahs.py                   # Adaptive Hypothesis Separation
│   │   ├── bayesian.py              # Bayesian Evidence Assimilation
│   │   ├── matcher.py               # Physics-based Constraint Matching
│   │   └── state.py                 # Reasoning state management
│   ├── mission/                     # Mission planning & optimization
│   │   ├── planner.py               # Landing site selection & scoring
│   │   ├── resource.py              # Resource budget optimization
│   │   └── traversal.py             # Surface traversal planning
│   ├── loaders/                     # Scientific data loaders (DFSAR, OHRC, DEM)
│   ├── processing/                  # Data preprocessing & validation
│   └── utils/                       # Raster I/O, timing, file utilities
│
├── ⚛️  frontend/                     # React 19 + TypeScript — Mission Control UI
│   └── src/
│       ├── components/
│       │   ├── scientific/          # ScientificCard, MetricCard, ConfidenceBadge
│       │   ├── reasoning/           # ReasoningInspector, ExplainabilityTimeline
│       │   ├── mission/             # DecisionTree constraint visualization
│       │   ├── engineering/         # TelemetryTerminal, DiagnosticPanel
│       │   └── viewer3d/            # ThreeViewer — 3D lunar terrain renderer
│       ├── layouts/                 # MissionLayout — aerospace HUD grid
│       ├── pages/                   # MissionControl — mode switching
│       ├── stores/                  # Zustand state management
│       ├── hooks/                   # WebSocket + data hooks
│       ├── types/                   # TypeScript type definitions
│       └── constants/               # Scientific constants & thresholds
│
├── 📊 config/                       # Pipeline configuration (YAML)
├── 🧪 tests/                        # 22 unit tests (pytest)
├── 📚 examples/                     # Example scripts & usage demos
└── 📦 datasets/                     # Scientific dataset directory (gitignored)
```

---

## 🎯 Features

### 🔬 Scientific Pipeline
- **LGHL** (Layered Generative Hypothesis Logic) — multi-layer hypothesis generation from physical observations
- **AHS** (Adaptive Hypothesis Separation) — dynamic hypothesis pruning and conflict resolution
- **Bayesian Evidence Assimilation** — continuous confidence updates as new evidence arrives
- **Physics-Based Constraint Matching** — safety, power, ice confidence gate evaluation

### 🖥️ Mission Control Interface
- **3D Terrain Viewer** — React Three Fiber with orbit controls, layer overlays, and rover path animation
- **Reasoning Inspector** — real-time hypothesis tracking, AHS decisions, Bayesian update workflow
- **Explainability Timeline** — step-by-step observation updates with interactive Plotly charts
- **Evidence Viewer** — per-layer physical explanations with confidence metrics
- **Decision Tree** — hierarchical safety/power/ice constraint visualization
- **Telemetry Terminal** — live WebSocket streaming with CRT scanline effects

### 🎨 Flagship Visual Identity
- **Aerospace HUD Theme** — deep space background with neon cyan, amber, and emerald accents
- **Beveled Panel Design** — tactical corner clips, targeting reticles, and coordinate grids
- **Typography** — Inter (UI) + IBM Plex Sans (headings) + JetBrains Mono (data readouts)
- **Micro-Animations** — scanline overlays, pulse effects, and smooth state transitions

---

## 🔑 API Keys (Optional)

The PHSE pipeline runs **fully offline without any API keys**. AI-assisted features (scientific Q&A, enhanced reasoning) are optional enhancements.

To enable them:
1. Copy `.env.example` → `.env`
2. Fill in your API keys (OpenRouter, Gemini, OpenAI)
3. Restart the server

---

## 🧪 Testing

```bash
# Set Python path
$env:PYTHONPATH="src"          # Windows PowerShell
# export PYTHONPATH=src        # Linux/macOS

# Run all 22 tests
pytest tests/ -v

# Run specific test modules
pytest tests/test_reasoning.py -v
pytest tests/test_mission.py -v
```

---

## 🔌 API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Serves the React frontend |
| `/api/run` | POST | Execute the full PHSE pipeline |
| `/api/status` | GET | Server health & pipeline status |
| `/ws/telemetry` | WS | Real-time telemetry WebSocket stream |

### Example: Run Pipeline
```bash
curl -X POST http://localhost:8000/api/run
```

Response:
```json
{
  "success": true,
  "landing_x": 155,
  "landing_y": 106,
  "landing_score": 0.7742,
  "ice_estimate": 301.08,
  "constraints_passed": true
}
```

---

## 📄 License

Galaxy Crew — PHSE Engine. All rights reserved.

---

<p align="center">
  <sub>Built with 🧬 science and ☕ caffeine by <strong>Galaxy Crew</strong></sub>
</p>
