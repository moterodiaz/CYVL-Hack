"""
Fetch all layers from Somerville's public ArcGIS REST API and save as GeoJSON.

Base: https://maps.somervillema.gov/arcgis/rest/services/UtilitiesAndAssets2/MapServer
No API key required.

Usage:
    python scripts/fetch_somerville_utilities.py           # all layers
    python scripts/fetch_somerville_utilities.py 23        # water mains only
    python scripts/fetch_somerville_utilities.py 23 5 12   # specific layers
"""

import json
import sys
import time
from pathlib import Path

import requests

BASE = "https://maps.somervillema.gov/arcgis/rest/services/UtilitiesAndAssets2/MapServer"
DATA_DIR = Path(__file__).parent.parent / "data" / "somerville"
PAGE_SIZE = 1000
RETRY_DELAY = 2


def slugify(name: str) -> str:
    return name.lower().replace(" ", "_").replace("/", "_").replace("(", "").replace(")", "")


def discover_layers() -> list[dict]:
    r = requests.get(f"{BASE}?f=json", timeout=30)
    r.raise_for_status()
    layers = r.json().get("layers", [])
    print(f"Discovered {len(layers)} layers")
    return layers


def fetch_layer(layer_id: int, layer_name: str) -> dict:
    """Page through all features and return merged GeoJSON FeatureCollection."""
    url = f"{BASE}/{layer_id}/query"
    all_features = []
    offset = 0

    while True:
        params = {
            "where": "1=1",
            "outFields": "*",
            "f": "geojson",
            "outSR": "4326",
            "resultOffset": offset,
            "resultRecordCount": PAGE_SIZE,
        }
        for attempt in range(3):
            try:
                r = requests.get(url, params=params, timeout=60)
                r.raise_for_status()
                data = r.json()
                break
            except Exception as e:
                if attempt == 2:
                    raise
                print(f"  retry {attempt+1}: {e}")
                time.sleep(RETRY_DELAY)

        features = data.get("features", [])
        all_features.extend(features)
        print(f"  layer {layer_id} | offset {offset} | +{len(features)} features")

        # ArcGIS signals more pages via exceededTransferLimit
        if not data.get("exceededTransferLimit") or len(features) == 0:
            break
        offset += PAGE_SIZE

    return {
        "type": "FeatureCollection",
        "name": layer_name,
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "features": all_features,
    }


def save(geojson: dict, layer_id: int, layer_name: str):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    slug = slugify(layer_name)
    path = DATA_DIR / f"{layer_id:03d}_{slug}.geojson"
    path.write_text(json.dumps(geojson, separators=(",", ":")))
    size_kb = path.stat().st_size / 1024
    print(f"  saved -> {path} ({size_kb:.1f} KB, {len(geojson['features'])} features)")
    return path


def run(target_ids: list[int] | None = None):
    layers = discover_layers()
    if target_ids:
        layers = [l for l in layers if l["id"] in target_ids]
        if not layers:
            print(f"No layers matched IDs: {target_ids}")
            return

    for layer in layers:
        lid, lname = layer["id"], layer["name"]
        print(f"\nFetching layer {lid}: {lname}")
        try:
            geojson = fetch_layer(lid, lname)
            save(geojson, lid, lname)
        except Exception as e:
            print(f"  ERROR: {e}")


if __name__ == "__main__":
    ids = [int(a) for a in sys.argv[1:]] if len(sys.argv) > 1 else None
    run(ids)
