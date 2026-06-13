"""Point cloud segmentation and ground classification.

Uses PDAL SMRF for ground classification and provides voxel downsampling,
modeled on the hackathonBuckets reference.
"""
import json
import logging

import numpy as np

logger = logging.getLogger(__name__)


def split_ground(points, ground_mask):
    """Separate points into ground and non-ground arrays.

    Args:
        points: ndarray[N, 3] of XYZ coordinates.
        ground_mask: boolean ndarray[N] where True = ground.

    Returns:
        (ground_points, non_ground_points)
    """
    return points[ground_mask], points[~ground_mask]


def ground_mask_pdal(laz_path, roi_bbox=None):
    """Run PDAL SMRF ground classification on a LAZ file.

    Args:
        laz_path: Path to the LAZ file.
        roi_bbox: Optional (xmin, ymin, xmax, ymax) to crop before classifying.

    Returns:
        Tuple of (xyz: ndarray[N,3], ground_mask: ndarray[N] bool)
    """
    import pdal  # lazy import: pdal is conda-only, not needed for unit tests

    stages = [laz_path]

    if roi_bbox is not None:
        xmin, ymin, xmax, ymax = roi_bbox
        stages.append({
            "type": "filters.crop",
            "bounds": f"([{xmin},{xmax}],[{ymin},{ymax}])",
        })

    stages.append({"type": "filters.smrf"})

    logger.info("Running PDAL SMRF pipeline on %s", laz_path)
    pl = pdal.Pipeline(json.dumps({"pipeline": stages}))
    pl.execute()
    arr = pl.arrays[0]

    xyz = np.column_stack([arr["X"], arr["Y"], arr["Z"]]).astype(np.float64)
    mask = arr["Classification"] == 2
    logger.info("PDAL result: %d points, %d ground", len(xyz), int(mask.sum()))

    return xyz, mask


def voxel_downsample(points, voxel_size):
    """Downsample a point cloud by keeping one point per voxel.

    Args:
        points: ndarray[N, 3+] — at least XYZ columns.
        voxel_size: Grid cell size in the point cloud's units.

    Returns:
        Downsampled points array (same columns as input).
    """
    keys = np.floor(points[:, :3] / voxel_size).astype(np.int64)
    _, idx = np.unique(keys, axis=0, return_index=True)
    result = points[np.sort(idx)]
    logger.info("Voxel downsample: %d → %d points (voxel=%.3f)",
                len(points), len(result), voxel_size)
    return result
