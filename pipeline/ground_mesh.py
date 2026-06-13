"""Build a triangulated heightfield mesh from classified ground points.

Grids the ROI into square cells, computes mean Z per cell, fills empty
cells from nearest neighbors, and emits OBJ-compatible vertex/face data.
Modeled on hackathonBuckets ground_mesh.py.
"""
import logging

import numpy as np
from scipy.spatial import cKDTree

logger = logging.getLogger(__name__)


def ground_grid_mesh(ground_pts, labels, bbox, cell=0.5):
    """Build a solid ground mesh grouped by surface material.

    Args:
        ground_pts: ndarray[N, 3] of ground XYZ.
        labels: list[str] of length N — "road", "sidewalk", or "grass".
        bbox: (xmin, ymin, xmax, ymax) of the region.
        cell: Grid cell size in meters.

    Returns:
        List of dicts: [{"name": str, "material": str,
                         "verts": [(x,y,z),...], "faces": [(i,j,k,l),...]}]
    """
    xmin, ymin, xmax, ymax = bbox
    nx = max(int(np.ceil((xmax - xmin) / cell)), 1)
    ny = max(int(np.ceil((ymax - ymin) / cell)), 1)

    ix = np.clip(((ground_pts[:, 0] - xmin) / cell).astype(int), 0, nx - 1)
    iy = np.clip(((ground_pts[:, 1] - ymin) / cell).astype(int), 0, ny - 1)
    flat = ix * ny + iy

    CLASSES = ["road", "sidewalk", "grass"]
    zsum = np.zeros(nx * ny)
    cnt = np.zeros(nx * ny)
    cls_cnt = np.zeros((3, nx * ny))
    np.add.at(zsum, flat, ground_pts[:, 2])
    np.add.at(cnt, flat, 1)
    lab_idx = np.array([CLASSES.index(l) if l in CLASSES else 2 for l in labels])
    for c in range(3):
        np.add.at(cls_cnt[c], flat[lab_idx == c], 1)

    filled = cnt > 0
    zcell = np.full(nx * ny, np.nan)
    zcell[filled] = zsum[filled] / cnt[filled]
    matcell = np.argmax(cls_cnt, axis=0)

    # Fill empty cells from nearest filled cell
    if not filled.all():
        filled_idx = np.nonzero(filled)[0]
        empty_idx = np.nonzero(~filled)[0]
        filled_coords = np.column_stack([filled_idx // ny, filled_idx % ny])
        empty_coords = np.column_stack([empty_idx // ny, empty_idx % ny])
        tree = cKDTree(filled_coords)
        _, nearest = tree.query(empty_coords)
        zcell[empty_idx] = zcell[filled_idx[nearest]]
        matcell[empty_idx] = matcell[filled_idx[nearest]]

    MAT_NAMES = {0: "asphalt", 1: "concrete", 2: "grass"}
    objects = []
    for cls_id, mat_name in MAT_NAMES.items():
        verts, faces = [], []
        vert_map = {}

        for idx in np.nonzero(matcell == cls_id)[0]:
            ci, cj = idx // ny, idx % ny
            z = zcell[idx]

            # Four corners of the cell
            corners = [
                (xmin + ci * cell, ymin + cj * cell, z),
                (xmin + (ci + 1) * cell, ymin + cj * cell, z),
                (xmin + (ci + 1) * cell, ymin + (cj + 1) * cell, z),
                (xmin + ci * cell, ymin + (cj + 1) * cell, z),
            ]
            face_idx = []
            for corner in corners:
                key = (round(corner[0], 4), round(corner[1], 4), round(corner[2], 4))
                if key not in vert_map:
                    vert_map[key] = len(verts)
                    verts.append(corner)
                face_idx.append(vert_map[key])
            faces.append(tuple(face_idx))

        if verts:
            objects.append({
                "name": f"ground_{mat_name}",
                "material": mat_name,
                "verts": verts,
                "faces": faces,
            })

    logger.info("Ground mesh: %d objects, grid %dx%d (cell=%.2f)",
                len(objects), nx, ny, cell)
    return objects
