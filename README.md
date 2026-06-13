# CYVL-Hack — LiDAR to DXF + APS Viewer Pipeline

Point-cloud street segmenter: **LAZ → Ground Classification → Contour DXF + 3D OBJ → APS Viewer**.

Two output paths:
- **DXF** — Contour lines for AutoCAD / Civil 3D
- **OBJ + MTL** — 3D scene uploaded to Autodesk Platform Services (APS) Viewer

## Architecture

```
data/raw/*.laz
     │
     ▼
┌─────────────────────────┐
│  PDAL SMRF Ground Class │  pipeline/segment.py
└────────────┬────────────┘
             │
     ┌───────┴───────┐
     ▼               ▼
┌─────────┐   ┌───────────┐
│ Contours│   │Ground Mesh│
│  → DXF  │   │  → OBJ    │
└─────────┘   └─────┬─────┘
                     │
              ┌──────┴──────┐
              │  APS Upload │  aps/upload.py
              │  (Signed S3)│
              └──────┬──────┘
                     │
              ┌──────┴──────┐
              │APS Translate│  aps/translate.py
              │   (SVF2)    │
              └──────┬──────┘
                     │
              ┌──────┴──────┐
              │  APS Viewer │  viewer/
              └─────────────┘
```

## Setup

### macOS (M3)

```bash
# Install system dependencies
brew install python

# Create conda environment (PDAL requires conda)
conda create -n hack python=3.12 pdal python-pdal laspy -c conda-forge -y
conda activate hack

# Install Python packages
pip install -r requirements.txt
```

### APS Credentials

Create a `.env` file in the project root:

```env
APS_CLIENT_ID=your_client_id
APS_CLIENT_SECRET=your_client_secret
APS_BUCKET_KEY=your-bucket-name
```

> **Note:** Use `data:read` scope for viewer tokens; `viewer:read` is invalid for 2-legged OAuth.

## Usage

### Quick Start

1. Place `.laz` files in `data/raw/`
2. Run the pipeline:

```bash
python run.py
```

3. Find outputs in `data/output/`:
   - `*_contours.dxf` — Contour lines for AutoCAD
   - `*_contours.geojson` — Contour lines as GeoJSON
   - `*_scene.obj` + `*_scene.mtl` — 3D scene for APS
   - `*_scene.zip` — Bundled scene for APS upload

### Skip APS Upload

```bash
python run.py --no-aps
```

### Custom ROI

```bash
ROI_M=100 ROI_CX=328000 ROI_CY=4692000 python run.py
```

### View in APS Viewer (local dev)

```bash
# After running the pipeline with APS upload:
python viewer/token_server.py
# Open http://localhost:8000
# Update viewer/viewer.js with the URN from the pipeline output
```

## CI/CD

Push a `.laz` file to `data/raw/` → GitHub Actions automatically:
1. Runs PDAL ground classification
2. Generates contour DXF
3. Builds 3D OBJ scene
4. Uploads artifacts to GitHub
5. Optionally uploads to APS (if secrets are configured)

### Required GitHub Secrets (for APS)

- `APS_CLIENT_ID`
- `APS_CLIENT_SECRET`
- `APS_BUCKET_KEY`

## Tests

```bash
pip install pytest
pytest tests/ -v
```

## Project Structure

```
.
├── config.py                   # Centralized config (dotenv)
├── run.py                      # End-to-end orchestrator
├── conftest.py                 # Pytest config
├── requirements.txt
│
├── pipeline/                   # Point cloud processing
│   ├── crop.py                 # LAZ loading & CRS extraction
│   ├── segment.py              # SMRF ground classification
│   ├── ground_mesh.py          # Heightfield mesh builder
│   ├── to_cad.py               # OBJ/MTL scene export
│   ├── contours.py             # Contour line generation
│   └── to_dxf.py               # DXF export (ezdxf)
│
├── aps/                        # Autodesk Platform Services
│   ├── auth.py                 # 2-legged OAuth2 (Basic header)
│   ├── upload.py               # Signed-S3 object upload
│   └── translate.py            # SVF2 translation + polling
│
├── viewer/                     # APS Viewer frontend
│   ├── index.html
│   ├── viewer.js
│   └── token_server.py         # Local dev token server
│
├── scripts/                    # Somerville utility data scripts
│   ├── somerville_data.py
│   └── fetch_somerville_utilities.py
│
├── data/
│   ├── raw/                    # Input LAZ files
│   └── output/                 # Generated outputs
│
├── tests/
│   ├── test_segment.py
│   ├── test_to_dxf.py
│   └── test_aps.py
│
├── agents/                     # Antigravity side-agent configs
└── .github/workflows/
    └── process-lidar.yml       # CI pipeline
```

## Based On

Architecture adapted from [xavier-cyvl/hackathonBuckets](https://github.com/xavier-cyvl/hackathonBuckets) — proven LAZ → OBJ → APS Viewer pipeline.
