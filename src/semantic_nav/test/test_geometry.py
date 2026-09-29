import math

import numpy as np
import pytest

from semantic_nav.geometry import (approach_pose, depth_to_meters, pixel_to_camera_point,
                                   quaternion_to_yaw, robust_bbox_depth, yaw_to_quaternion)


def test_principal_point_projects_on_optical_axis():
    assert pixel_to_camera_point(320, 240, 2.0, 500, 500, 320, 240) == (0.0, 0.0, 2.0)


def test_backprojection_matches_pinhole():
    x, y, z = pixel_to_camera_point(420, 140, 2.0, 500, 500, 320, 240)
    assert (x, y, z) == pytest.approx((0.4, -0.4, 2.0))
    # re-projection gives the pixel back
    assert 500 * x / z + 320 == pytest.approx(420)


def test_invalid_depth_raises():
    with pytest.raises(ValueError):
        pixel_to_camera_point(0, 0, float("nan"), 1, 1, 0, 0)


def test_depth_16u_converted_and_zero_invalid():
    d = depth_to_meters(np.array([[0, 1500]], dtype=np.uint16))
    assert math.isnan(d[0, 0]) and d[0, 1] == pytest.approx(1.5)


def test_robust_depth_ignores_holes_and_background():
    depth = np.full((100, 100), 5.0, dtype=np.float32)   # background
    depth[40:60, 40:60] = 2.0                             # object
    depth[48:52, 48:52] = np.nan                          # holes
    assert robust_bbox_depth(depth, 50, 50, 30, 30, min_valid=5) == pytest.approx(2.0)


def test_robust_depth_returns_none_without_data():
    assert robust_bbox_depth(np.full((50, 50), np.nan, np.float32), 25, 25, 10, 10) is None


def test_yaw_quaternion_roundtrip():
    for yaw in (-3.0, -1.0, 0.0, 0.5, 3.0):
        assert quaternion_to_yaw(*yaw_to_quaternion(yaw)) == pytest.approx(yaw)


def test_approach_pose_in_front_of_object_facing_it():
    gx, gy, yaw = approach_pose((0.0, 0.0), (3.0, 0.0), standoff=0.5)
    assert (gx, gy) == pytest.approx((2.5, 0.0))
    assert yaw == pytest.approx(0.0)
