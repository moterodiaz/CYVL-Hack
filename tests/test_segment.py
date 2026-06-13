"""Tests for pipeline/segment.py — ground splitting and voxel downsample."""
import numpy as np
import pytest

from pipeline.segment import split_ground, voxel_downsample


class TestSplitGround:
    def test_basic_split(self):
        points = np.array([
            [1.0, 2.0, 3.0],
            [4.0, 5.0, 6.0],
            [7.0, 8.0, 9.0],
            [10.0, 11.0, 12.0],
        ])
        mask = np.array([True, False, True, False])

        ground, nonground = split_ground(points, mask)

        assert len(ground) == 2
        assert len(nonground) == 2
        np.testing.assert_array_equal(ground[0], [1.0, 2.0, 3.0])
        np.testing.assert_array_equal(ground[1], [7.0, 8.0, 9.0])
        np.testing.assert_array_equal(nonground[0], [4.0, 5.0, 6.0])

    def test_all_ground(self):
        points = np.array([[1, 2, 3], [4, 5, 6]])
        mask = np.array([True, True])
        ground, nonground = split_ground(points, mask)
        assert len(ground) == 2
        assert len(nonground) == 0

    def test_no_ground(self):
        points = np.array([[1, 2, 3], [4, 5, 6]])
        mask = np.array([False, False])
        ground, nonground = split_ground(points, mask)
        assert len(ground) == 0
        assert len(nonground) == 2


class TestVoxelDownsample:
    def test_reduces_count(self):
        # Many points in same voxel
        rng = np.random.default_rng(42)
        points = rng.uniform(0, 0.05, size=(100, 3))  # all in one voxel at size=0.1
        result = voxel_downsample(points, voxel_size=0.1)
        assert len(result) == 1

    def test_preserves_spread_points(self):
        # Points in different voxels should all survive
        points = np.array([
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
        ])
        result = voxel_downsample(points, voxel_size=0.5)
        assert len(result) == 4

    def test_returns_sorted_indices(self):
        points = np.array([
            [0.0, 0.0, 0.0],
            [0.01, 0.01, 0.01],  # same voxel as index 0
            [1.0, 1.0, 1.0],
        ])
        result = voxel_downsample(points, voxel_size=0.5)
        assert len(result) == 2
        # First point from the first voxel, third from the second
        np.testing.assert_array_equal(result[0], [0.0, 0.0, 0.0])
        np.testing.assert_array_equal(result[1], [1.0, 1.0, 1.0])
