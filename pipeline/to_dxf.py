"""Generate DXF files from contour data.

Creates AutoCAD/Civil 3D compatible DXF files with LWPOLYLINE entities
preserving contour elevations.
"""
import json
import logging
from pathlib import Path

import ezdxf

logger = logging.getLogger(__name__)


def contours_to_dxf(contours, output_path):
    """Create a DXF file from contour line data.

    Args:
        contours: List of dicts with keys 'elevation' and 'coordinates'.
        output_path: Path for the output .dxf file.

    Returns:
        Path to the created DXF file.
    """
    doc = ezdxf.new("R2010")
    doc.header["$INSUNITS"] = 6  # meters

    msp = doc.modelspace()

    # Create a dedicated layer for contour lines
    doc.layers.add("CONTOURS", color=7)

    contour_count = 0
    for contour in contours:
        elevation = contour["elevation"]
        coords = contour["coordinates"]

        # Convert to 2D points for LWPOLYLINE
        points = [(c[0], c[1]) for c in coords]

        if len(points) < 2:
            continue

        try:
            msp.add_lwpolyline(
                points,
                dxfattribs={
                    "layer": "CONTOURS",
                    "elevation": elevation,
                },
            )
            contour_count += 1
        except Exception as e:
            logger.warning("Failed to add contour at elevation %.2f: %s", elevation, e)

    doc.saveas(str(output_path))
    logger.info("DXF saved: %s (%d contour lines)", output_path, contour_count)
    return output_path


def geojson_to_dxf(geojson_path, output_path):
    """Convert a GeoJSON contour file to DXF.

    Args:
        geojson_path: Path to input GeoJSON file.
        output_path: Path for output DXF file.

    Returns:
        Path to the created DXF file.
    """
    with open(geojson_path) as f:
        data = json.load(f)

    contours = []
    for feat in data.get("features", []):
        geom = feat.get("geometry", {})
        props = feat.get("properties", {})
        geom_type = geom.get("type", "")
        elevation = props.get("elevation", 0.0) or 0.0

        if geom_type == "LineString":
            coords = geom.get("coordinates", [])
            if len(coords) >= 2:
                contours.append({"elevation": float(elevation), "coordinates": coords})
        elif geom_type == "MultiLineString":
            for line_coords in geom.get("coordinates", []):
                if len(line_coords) >= 2:
                    contours.append({"elevation": float(elevation), "coordinates": line_coords})

    logger.info("Loaded %d contour lines from %s", len(contours), geojson_path)
    return contours_to_dxf(contours, output_path)
