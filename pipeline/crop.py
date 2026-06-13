"""Load and crop LAZ point clouds.

Provides CRS extraction and bulk point loading from LAZ files,
modeled on the hackathonBuckets reference.
"""
import glob
import logging
import os

import laspy
import numpy as np

logger = logging.getLogger(__name__)


def las_crs(path):
    """Extract the CRS from a LAZ/LAS file as a pyproj CRS object."""
    import pyproj

    with laspy.open(path) as f:
        vlrs = f.header.vlrs
        for vlr in vlrs:
            if vlr.record_id == 2112:  # WKT
                wkt = vlr.record_data.decode("utf-8", errors="ignore").strip("\x00")
                return pyproj.CRS.from_wkt(wkt)
        # Try GeoTIFF keys
        for vlr in vlrs:
            if vlr.record_id == 34735:
                # Attempt EPSG extraction from GeoTIFF key directory
                data = vlr.record_data
                if len(data) >= 8:
                    # Simple heuristic: look for EPSG in the key entries
                    pass
    # Fallback: assume UTM or ask user
    logger.warning("Could not extract CRS from %s; assuming EPSG:32619 (UTM 19N)", path)
    return pyproj.CRS.from_epsg(32619)


def load_points(laz_dir=None):
    """Read all LAZ files in a directory, return (XYZ, RGB_or_None).

    Args:
        laz_dir: Directory containing .laz files. Falls back to config.LAZ_DIR.

    Returns:
        Tuple of (points: ndarray[N,3], colors: ndarray[N,3] or None)
    """
    if laz_dir is None:
        from config import LAZ_DIR
        laz_dir = LAZ_DIR

    files = sorted(glob.glob(os.path.join(laz_dir, "*.laz")))
    if not files:
        raise FileNotFoundError(f"No .laz files in {laz_dir!r}; set LAZ_DIR in .env")

    xs, rgbs = [], []
    for f in files:
        logger.info("Reading %s", f)
        las = laspy.read(f)
        xs.append(np.column_stack([las.x, las.y, las.z]))
        if hasattr(las, "red"):
            rgbs.append(np.column_stack([las.red, las.green, las.blue]))

    pts = np.vstack(xs).astype(np.float64)
    colors = np.vstack(rgbs).astype(np.uint16) if rgbs and len(rgbs) == len(xs) else None
    logger.info("Loaded %d points from %d file(s)", len(pts), len(files))
    return pts, colors


def get_bounds(laz_path):
    """Get the bounding box of a LAZ file without reading all points.

    Returns:
        (min_x, min_y, max_x, max_y, min_z, max_z)
    """
    with laspy.open(laz_path) as f:
        h = f.header
        return (h.mins[0], h.mins[1], h.maxs[0], h.maxs[1], h.mins[2], h.maxs[2])


def get_center(laz_path):
    """Get the XY center of a LAZ file."""
    with laspy.open(laz_path) as f:
        h = f.header
        return (h.mins[0] + h.maxs[0]) / 2, (h.mins[1] + h.maxs[1]) / 2
