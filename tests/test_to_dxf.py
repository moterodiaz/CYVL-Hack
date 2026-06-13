"""Tests for pipeline/to_dxf.py — DXF generation from contour data."""
import os
import tempfile

import ezdxf
import pytest

from pipeline.to_dxf import contours_to_dxf


class TestContoursToDxf:
    def _sample_contours(self):
        return [
            {
                "elevation": 10.0,
                "coordinates": [[0, 0], [1, 0], [2, 1], [3, 1]],
            },
            {
                "elevation": 20.0,
                "coordinates": [[0, 2], [1, 2], [2, 3], [3, 3], [4, 4]],
            },
            {
                "elevation": 30.0,
                "coordinates": [[5, 5], [6, 6]],
            },
        ]

    def test_creates_valid_dxf(self):
        contours = self._sample_contours()
        with tempfile.NamedTemporaryFile(suffix=".dxf", delete=False) as f:
            out_path = f.name

        try:
            result = contours_to_dxf(contours, out_path)
            assert os.path.exists(result)
            assert os.path.getsize(result) > 0

            # Verify DXF is readable
            doc = ezdxf.readfile(result)
            msp = doc.modelspace()
            entities = list(msp)
            assert len(entities) == 3

            # Verify entity types
            for e in entities:
                assert e.dxftype() == "LWPOLYLINE"
                assert e.dxf.layer == "CONTOURS"

            # Verify elevations
            elevations = sorted(e.dxf.elevation for e in entities)
            assert elevations == [10.0, 20.0, 30.0]
        finally:
            os.unlink(out_path)

    def test_skips_single_point_contour(self):
        contours = [
            {"elevation": 10.0, "coordinates": [[0, 0]]},  # too short
            {"elevation": 20.0, "coordinates": [[0, 0], [1, 1]]},  # valid
        ]
        with tempfile.NamedTemporaryFile(suffix=".dxf", delete=False) as f:
            out_path = f.name

        try:
            contours_to_dxf(contours, out_path)
            doc = ezdxf.readfile(out_path)
            entities = list(doc.modelspace())
            assert len(entities) == 1
            assert entities[0].dxf.elevation == 20.0
        finally:
            os.unlink(out_path)

    def test_empty_contours(self):
        with tempfile.NamedTemporaryFile(suffix=".dxf", delete=False) as f:
            out_path = f.name

        try:
            contours_to_dxf([], out_path)
            doc = ezdxf.readfile(out_path)
            entities = list(doc.modelspace())
            assert len(entities) == 0
        finally:
            os.unlink(out_path)

    def test_dxf_format_r2010(self):
        contours = self._sample_contours()
        with tempfile.NamedTemporaryFile(suffix=".dxf", delete=False) as f:
            out_path = f.name

        try:
            contours_to_dxf(contours, out_path)
            doc = ezdxf.readfile(out_path)
            assert doc.dxfversion == "AC1024"  # R2010
            assert doc.header["$INSUNITS"] == 6  # meters
        finally:
            os.unlink(out_path)
