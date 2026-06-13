"""End-to-end driver: Cyvl LiDAR LAZ → classified scene → DXF + APS Viewer.

Flow:
  1. Read LAZ via laspy, optionally crop to ROI
  2. PDAL SMRF ground classification
  3. Voxel downsample
  4. Build ground mesh → OBJ + MTL (for APS Viewer)
  5. Generate contours → DXF (for AutoCAD / Civil 3D)
  6. APS: auth → ensure bucket → upload ZIP → translate → wait

Usage:
    python run.py
    python run.py --no-aps          # skip APS upload
    ROI_M=100 python run.py         # custom ROI size
"""
import glob
import json
import logging
import os
import sys
import zipfile
from pathlib import Path

import numpy as np

import config
from pipeline.crop import las_crs, get_center
from pipeline.segment import ground_mask_pdal, split_ground, voxel_downsample
from pipeline.ground_mesh import ground_grid_mesh
from pipeline.to_cad import write_obj, write_mtl
from pipeline.contours import generate_contours, contours_to_geojson
from pipeline.to_dxf import contours_to_dxf

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("run")


def find_laz_files():
    """Find all LAZ files in the configured data directory."""
    patterns = [
        os.path.join(config.LAZ_DIR, "*.laz"),
        os.path.join(config.LAZ_DIR, "*.LAS"),
        os.path.join(config.LAZ_DIR, "*.las"),
        os.path.join(config.LAZ_DIR, "*.LAZ"),
    ]
    files = []
    for p in patterns:
        files.extend(glob.glob(p))
    if not files:
        logger.error("No LAZ/LAS files found in %s", config.LAZ_DIR)
        sys.exit(1)
    logger.info("Found %d LAZ file(s) in %s", len(files), config.LAZ_DIR)
    return sorted(set(files))


def process_file(laz_path, output_dir):
    """Process a single LAZ file through the full pipeline.

    Returns:
        Tuple of (dxf_path, obj_path, mtl_path)
    """
    stem = Path(laz_path).stem
    logger.info("=" * 60)
    logger.info("Processing: %s", laz_path)
    logger.info("=" * 60)

    # Get CRS and center
    crs = las_crs(laz_path)
    cx, cy = get_center(laz_path)
    logger.info("CRS: %s", crs)
    logger.info("Center: (%.2f, %.2f)", cx, cy)

    # Optional ROI crop
    roi_m = config.DEFAULT_ROI_M
    roi_cx = float(os.environ.get("ROI_CX", cx))
    roi_cy = float(os.environ.get("ROI_CY", cy))
    bbox = (roi_cx - roi_m / 2, roi_cy - roi_m / 2,
            roi_cx + roi_m / 2, roi_cy + roi_m / 2)
    logger.info("ROI bbox: %s (%.0fm)", bbox, roi_m)

    # Step 1: PDAL SMRF ground classification
    xyz, gmask = ground_mask_pdal(laz_path, roi_bbox=bbox)
    ground, nonground = split_ground(xyz, gmask)
    logger.info("Points: %d total, %d ground, %d non-ground",
                len(xyz), len(ground), len(nonground))

    # Step 2: Voxel downsample
    ground_ds = voxel_downsample(ground, config.DEFAULT_VOXEL_SIZE)

    # Step 3: Simple ground labeling (all "grass" without Cyvl overlays)
    # With Cyvl data overlays, you'd classify road/sidewalk/grass here
    labels = ["grass"] * len(ground_ds)

    # Step 4: Build ground mesh → OBJ
    mesh_objects = ground_grid_mesh(ground_ds, labels, bbox, cell=0.5)

    origin = (roi_cx, roi_cy)
    obj_path = os.path.join(output_dir, f"{stem}_scene.obj")
    mtl_path = os.path.join(output_dir, f"{stem}_scene.mtl")
    write_mtl(mtl_path)
    write_obj(obj_path, mesh_objects, mtl_filename=f"{stem}_scene.mtl", origin=origin)

    # Step 5: Generate contours → DXF
    contour_lines = generate_contours(
        ground_ds, bbox,
        interval=config.DEFAULT_CONTOUR_INTERVAL,
        cell=0.5,
    )

    geojson_path = os.path.join(output_dir, f"{stem}_contours.geojson")
    contours_to_geojson(contour_lines, geojson_path)

    dxf_path = os.path.join(output_dir, f"{stem}_contours.dxf")
    contours_to_dxf(contour_lines, dxf_path)

    logger.info("Outputs: DXF=%s, OBJ=%s, MTL=%s", dxf_path, obj_path, mtl_path)
    return dxf_path, obj_path, mtl_path


def zip_scene(obj_path, mtl_path, zip_path):
    """Bundle OBJ + MTL into a ZIP for APS upload."""
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(obj_path, os.path.basename(obj_path))
        zf.write(mtl_path, os.path.basename(mtl_path))
    size_kb = os.path.getsize(zip_path) / 1024
    logger.info("Zipped scene: %s (%.1f KB)", zip_path, size_kb)
    return zip_path


def upload_to_aps(zip_path, root_filename):
    """Upload a scene ZIP to APS and start translation."""
    from aps.auth import get_token
    from aps.upload import ensure_bucket, upload_object
    from aps.translate import start_translation, wait_until_done

    token = get_token()
    bucket_key = config.APS_BUCKET_KEY

    ensure_bucket(token, bucket_key)

    object_key = os.path.basename(zip_path)
    urn = upload_object(token, bucket_key, object_key, zip_path)

    start_translation(token, urn, root_filename=root_filename)

    try:
        wait_until_done(token, urn, timeout=600)
        logger.info("APS translation complete! URN: %s", urn)
    except TimeoutError:
        logger.warning("Translation still in progress — check APS dashboard. URN: %s", urn)

    return urn


def main():
    skip_aps = "--no-aps" in sys.argv

    # Ensure output directory exists
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)

    laz_files = find_laz_files()

    for laz_path in laz_files:
        dxf_path, obj_path, mtl_path = process_file(laz_path, config.OUTPUT_DIR)

        if not skip_aps and config.APS_CLIENT_ID and config.APS_CLIENT_SECRET:
            stem = Path(laz_path).stem
            zip_path = os.path.join(config.OUTPUT_DIR, f"{stem}_scene.zip")
            zip_scene(obj_path, mtl_path, zip_path)
            root_filename = os.path.basename(obj_path)
            upload_to_aps(zip_path, root_filename)
        elif not skip_aps:
            logger.info("Skipping APS upload (no credentials configured)")

    logger.info("All files processed successfully!")


if __name__ == "__main__":
    main()
