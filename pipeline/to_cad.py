"""Build OBJ/MTL scene files from detected geometry.

Objects are generic meshes: {name, material, verts: [(x,y,z)], faces: [(i,...)]}
(face indices are 0-based within the object's own verts). write_obj() handles
the global vertex offsets and per-object `usemtl` lines.
Modeled on hackathonBuckets to_cad.py.
"""
import logging
import math

logger = logging.getLogger(__name__)

MATERIALS = {
    "asphalt":  (0.13, 0.13, 0.15),
    "concrete": (0.80, 0.78, 0.72),
    "grass":    (0.36, 0.50, 0.28),
    "car":      (0.30, 0.38, 0.50),
    "glass":    (0.15, 0.18, 0.22),
    "trunk":    (0.36, 0.26, 0.18),
    "canopy":   (0.20, 0.45, 0.20),
    "pole":     (0.45, 0.45, 0.48),
    "hydrant":  (0.75, 0.15, 0.12),
    "metal":    (0.35, 0.35, 0.38),
    "signal":   (0.12, 0.12, 0.12),
    "misc":     (0.62, 0.58, 0.30),
    "wall":     (0.72, 0.66, 0.58),
    "roof":     (0.45, 0.40, 0.38),
}


def write_mtl(path):
    """Write an OBJ material library file."""
    lines = []
    for name, (r, g, b) in MATERIALS.items():
        lines += [f"newmtl {name}", f"Kd {r:.3f} {g:.3f} {b:.3f}",
                  "Ka 0 0 0", "Ks 0.05 0.05 0.05", "Ns 10", ""]
    with open(path, "w") as f:
        f.write("\n".join(lines))
    logger.info("Wrote MTL: %s (%d materials)", path, len(MATERIALS))


def write_obj(path, objects, mtl_filename="scene.mtl", origin=None):
    """Write an OBJ scene file from a list of mesh objects.

    Args:
        path: Output OBJ file path.
        objects: List of dicts with keys: name, material, verts, faces.
        mtl_filename: Name of the companion MTL file.
        origin: Optional (ox, oy) to subtract from XY coords (local origin shift).
    """
    ox, oy = origin if origin else (0.0, 0.0)
    lines = [f"mtllib {mtl_filename}", ""]
    offset = 1  # OBJ vertex indices are 1-based

    for obj in objects:
        lines.append(f"o {obj['name']}")
        lines.append(f"usemtl {obj['material']}")

        for v in obj["verts"]:
            lines.append(f"v {v[0] - ox:.6f} {v[1] - oy:.6f} {v[2]:.6f}")

        for face in obj["faces"]:
            idx_str = " ".join(str(i + offset) for i in face)
            lines.append(f"f {idx_str}")

        offset += len(obj["verts"])
        lines.append("")

    with open(path, "w") as f:
        f.write("\n".join(lines))

    total_verts = sum(len(o["verts"]) for o in objects)
    total_faces = sum(len(o["faces"]) for o in objects)
    logger.info("Wrote OBJ: %s (%d objects, %d verts, %d faces)",
                path, len(objects), total_verts, total_faces)


# ---------- Mesh primitives (verts 0-indexed, faces reference local verts) ----------

def mesh_box(center, size, yaw=0.0):
    """Create a box mesh centered at `center` with given `size` and optional rotation."""
    cx, cy, cz = center
    sx, sy, sz = size
    c, s = math.cos(yaw), math.sin(yaw)
    verts = []
    for ox, oy, oz in [(-.5, -.5, -.5), (.5, -.5, -.5), (.5, .5, -.5), (-.5, .5, -.5),
                       (-.5, -.5, .5), (.5, -.5, .5), (.5, .5, .5), (-.5, .5, .5)]:
        x, y, z = ox * sx, oy * sy, oz * sz
        verts.append((cx + x * c - y * s, cy + x * s + y * c, cz + z))
    faces = [(0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4),
             (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    return verts, faces


def mesh_cylinder(cx, cy, z0, radius, height, n=12):
    """Create a cylinder mesh standing upright."""
    verts, faces = [], []
    for i in range(n):
        a = 2 * math.pi * i / n
        x, y = cx + radius * math.cos(a), cy + radius * math.sin(a)
        verts.append((x, y, z0))
        verts.append((x, y, z0 + height))
    for i in range(n):
        j = (i + 1) % n
        faces.append((2 * i, 2 * j, 2 * j + 1, 2 * i + 1))
    faces.append(tuple(2 * i for i in range(n)))          # bottom cap
    faces.append(tuple(2 * i + 1 for i in range(n)))      # top cap
    return verts, faces


def mesh_cone(cx, cy, z0, radius, height, n=12):
    """Create a cone mesh (for tree canopies)."""
    verts = [(cx + radius * math.cos(2 * math.pi * i / n),
              cy + radius * math.sin(2 * math.pi * i / n),
              z0) for i in range(n)]
    verts.append((cx, cy, z0 + height))  # apex
    apex = len(verts) - 1
    faces = [(i, (i + 1) % n, apex) for i in range(n)]
    faces.append(tuple(range(n)))  # base cap
    return verts, faces
