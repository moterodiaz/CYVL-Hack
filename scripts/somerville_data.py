"""
Data accessor for Somerville ArcGIS utility layers.

Cache-first: reads from data/somerville/ if file exists, else fetches live.
Other scripts import `get_layer` or `get_layer_live` — never call the API directly.

Layer IDs (common ones):
    3   Street Lights          16  SW Manholes
    7   Sewer Fittings         17  SS Manholes
    8   Catch Basins           19  SW Gravity Mains
    13  Storm Inlets           20  SS Gravity Mains
    14  Catch Basin Laterals   22  Water Fittings
    15  Storm Discharge Points 23  Water Mains
                               31  Street Centerlines With Slopes
                               40  Sidewalk Ramps / 41 Sidewalks
    24-28  MWRA nodes/lines/pipes/meters
    29  1ft Contours
"""

import io
import json
from pathlib import Path

import geopandas as gpd
import requests

BASE = "https://maps.somervillema.gov/arcgis/rest/services/UtilitiesAndAssets2/MapServer"
CACHE_DIR = Path(__file__).parent.parent / "data" / "somerville"
PAGE_SIZE = 1000


def _cache_path(layer_id: int) -> Path | None:
    """Return cache path if it exists, else None."""
    if not CACHE_DIR.exists():
        return None
    matches = list(CACHE_DIR.glob(f"{layer_id:03d}_*.geojson"))
    return matches[0] if matches else None


def _fetch_all_pages(layer_id: int) -> dict:
    url = f"{BASE}/{layer_id}/query"
    features, offset = [], 0
    while True:
        r = requests.get(url, params={
            "where": "1=1", "outFields": "*", "f": "geojson",
            "outSR": "4326", "resultOffset": offset, "resultRecordCount": PAGE_SIZE,
        }, timeout=60)
        r.raise_for_status()
        data = r.json()
        batch = data.get("features", [])
        features.extend(batch)
        if not data.get("exceededTransferLimit") or not batch:
            break
        offset += PAGE_SIZE
    return {"type": "FeatureCollection", "features": features}


def get_layer(layer_id: int) -> gpd.GeoDataFrame:
    """
    Return layer as GeoDataFrame. Reads cache if available, else fetches live.
    Pre-populate cache: python scripts/fetch_somerville_utilities.py <id>
    """
    path = _cache_path(layer_id)
    if path:
        return gpd.read_file(path)
    return get_layer_live(layer_id)


def get_layer_live(layer_id: int) -> gpd.GeoDataFrame:
    """Always fetch from API, bypass cache."""
    geojson = _fetch_all_pages(layer_id)
    return gpd.read_file(io.StringIO(json.dumps(geojson)))


def get_layers(layer_ids: list[int]) -> dict[int, gpd.GeoDataFrame]:
    """Fetch multiple layers. Returns {layer_id: GeoDataFrame}."""
    return {lid: get_layer(lid) for lid in layer_ids}


def spatial_join(base_layer_id: int, overlay_layer_id: int, how: str = "left") -> gpd.GeoDataFrame:
    """Spatial join two layers."""
    left = get_layer(base_layer_id)
    right = get_layer(overlay_layer_id)
    return gpd.sjoin(left, right, how=how, predicate="intersects")


def filter_bbox(layer_id: int, min_lon: float, min_lat: float, max_lon: float, max_lat: float) -> gpd.GeoDataFrame:
    """Query API with bounding box — no full download needed."""
    url = f"{BASE}/{layer_id}/query"
    r = requests.get(url, params={
        "where": "1=1",
        "outFields": "*",
        "f": "geojson",
        "outSR": "4326",
        "geometry": f"{min_lon},{min_lat},{max_lon},{max_lat}",
        "geometryType": "esriGeometryEnvelope",
        "spatialRel": "esriSpatialRelIntersects",
        "resultRecordCount": PAGE_SIZE,
    }, timeout=60)
    r.raise_for_status()
    return gpd.read_file(io.StringIO(r.text))
