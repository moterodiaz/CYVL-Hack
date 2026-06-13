# APS Setup & Pipeline Run Instructions

After cloning the repo, follow these steps in order.

---

## 1. Move the LAZ file

The pipeline reads from `data/raw/`. Move the source point cloud:

```bash
mv data/MiddleSex_PC.laz data/raw/
```

---

## 2. Install PDAL (conda required)

PDAL does not install reliably via pip. Use conda:

```bash
conda install -y -c conda-forge pdal python-pdal
```

Then install the rest of the Python deps:

```bash
pip install -r requirements.txt
```

---

## 3. Get APS credentials

1. Go to [https://aps.autodesk.com](https://aps.autodesk.com)
2. Sign in → **My Apps** → **Create Application**
3. Enable these APIs:
   - Data Management API
   - Model Derivative API
4. Copy your **Client ID** and **Client Secret**

---

## 4. Configure `.env`

Create a `.env` file in the project root (it is gitignored):

```
APS_CLIENT_ID=your_client_id_here
APS_CLIENT_SECRET=your_client_secret_here
APS_BUCKET_KEY=cyvl-hack-lidar
```

Optional overrides:

```
LAZ_DIR=data/raw
OUTPUT_DIR=data/output
VOXEL_SIZE=0.10
ROI_M=200.0
CONTOUR_INTERVAL=1.0
```

---

## 5. Run the pipeline

```bash
python run.py
```

This will:
1. Read all `.laz` files from `data/raw/`
2. Run PDAL SMRF ground classification
3. Voxel downsample
4. Build ground mesh → `data/output/*_scene.obj` + `.mtl`
5. Generate contours → `data/output/*_contours.dxf` + `.geojson`
6. Authenticate with APS
7. Upload `*_scene.zip` to APS OSS
8. Submit SVF2 translation job and wait for completion

To skip the APS upload and only generate local files:

```bash
python run.py --no-aps
```

---

## 6. Paste the URN into the viewer

At the end of `run.py` output, look for:

```
APS translation complete! URN: <your_urn_here>
```

Copy that URN and paste it into `viewer/viewer.js` line 9:

```js
const MODEL_URN = "paste_urn_here";
```

---

## 7. Start the viewer

```bash
python viewer/token_server.py
```

Open [http://localhost:8000](http://localhost:8000) in your browser.

The viewer fetches a `data:read` scoped token from the local server and loads the translated model from APS.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `No .laz files in data/raw` | Step 1 — move the LAZ file |
| `APS auth failed: HTTP 401` | Check `APS_CLIENT_ID` / `APS_CLIENT_SECRET` in `.env` |
| `Translation timed out` | APS can take 5–10 min for large files. Re-run `run.py` — it reuses the uploaded object. URN is printed before timeout. |
| `No viewable geometry found` | Translation still in progress. Wait, then refresh the viewer. |
| `pdal not found` | Installed via pip, not conda. Follow Step 2. |
| Viewer shows blank page | Check browser console. Token server must be running on port 8000. |

---

## File outputs

| File | Purpose |
|---|---|
| `data/output/*_contours.dxf` | Import into AutoCAD / Civil 3D |
| `data/output/*_contours.geojson` | GIS use, overlay with Somerville utility data |
| `data/output/*_scene.obj` + `.mtl` | 3D mesh (uploaded to APS) |
| `data/output/*_scene.zip` | OBJ+MTL bundle sent to APS OSS |
