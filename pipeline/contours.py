"""Generate elevation contour lines from gridded ground points.

Uses matplotlib's contour engine on a numpy grid to produce contour
polylines with elevation attributes, output as GeoJSON.
"""
import json
import logging

import matplotlib
matplotlib.use("Agg")  # non-interactive backend
import matplotlib.pyplot as plt
import numpy as np

logger = logging.getLogger(__name__)


def generate_contours(ground_pts, bbox, interval=1.0, cell=0.5):
    """Generate contour lines from ground points.

    Args:
        ground_pts: ndarray[N, 3] of ground XYZ.
        bbox: (xmin, ymin, xmax, ymax) of the region.
        interval: Contour elevation interval.
        cell: Grid cell size for interpolation.

    Returns:
        List of dicts: [{"elevation": float, "coordinates": [[x,y], ...]}, ...]
    """
    xmin, ymin, xmax, ymax = bbox
    nx = max(int(np.ceil((xmax - xmin) / cell)), 2)
    ny = max(int(np.ceil((ymax - ymin) / cell)), 2)

    # Build elevation grid
    xi = np.linspace(xmin, xmax, nx)
    yi = np.linspace(ymin, ymax, ny)
    grid = np.zeros((ny, nx))
    cnt = np.zeros((ny, nx))

    # Bin points into grid cells
    ix = np.clip(((ground_pts[:, 0] - xmin) / (xmax - xmin) * (nx - 1)).astype(int), 0, nx - 1)
    iy = np.clip(((ground_pts[:, 1] - ymin) / (ymax - ymin) * (ny - 1)).astype(int), 0, ny - 1)

    np.add.at(grid, (iy, ix), ground_pts[:, 2])
    np.add.at(cnt, (iy, ix), 1)

    valid = cnt > 0
    grid[valid] /= cnt[valid]
    grid[~valid] = np.nan

    # Fill NaN cells with nearest valid value
    if not valid.all():
        from scipy.ndimage import distance_transform_edt
        _, nearest_idx = distance_transform_edt(~valid, return_distances=True, return_indices=True)
        grid[~valid] = grid[tuple(nearest_idx[:, ~valid])]

    # Determine contour levels
    z_min, z_max = np.nanmin(grid), np.nanmax(grid)
    levels = np.arange(np.floor(z_min / interval) * interval,
                       np.ceil(z_max / interval) * interval + interval,
                       interval)

    logger.info("Generating contours: Z range %.2f–%.2f, %d levels (interval=%.2f)",
                z_min, z_max, len(levels), interval)

    # Generate contours using matplotlib
    fig, ax = plt.subplots()
    cs = ax.contour(xi, yi, grid, levels=levels)
    plt.close(fig)

    contours = []
    for level_idx, level_val in enumerate(cs.levels):
        for seg in cs.allsegs[level_idx]:
            if len(seg) >= 2:
                contours.append({
                    "elevation": float(level_val),
                    "coordinates": seg.tolist(),
                })

    logger.info("Generated %d contour lines", len(contours))
    return contours


def contours_to_geojson(contours, output_path):
    """Write contour lines as a GeoJSON FeatureCollection.

    Args:
        contours: List of contour dicts from generate_contours().
        output_path: Path for the output GeoJSON file.
    """
    features = []
    for i, c in enumerate(contours):
        features.append({
            "type": "Feature",
            "properties": {
                "id": i,
                "elevation": c["elevation"],
            },
            "geometry": {
                "type": "LineString",
                "coordinates": c["coordinates"],
            },
        })

    geojson = {
        "type": "FeatureCollection",
        "features": features,
    }

    with open(output_path, "w") as f:
        json.dump(geojson, f, separators=(",", ":"))

    logger.info("Wrote contours GeoJSON: %s (%d features)", output_path, len(features))
    return output_path
