"""Pure geometry helpers (no ROS dependency, unit-testable).

Conventions
-----------
* Camera points are expressed in the *optical* frame (REP 103 / REP 105):
  x to the right, y down, z forward (along the optical axis).
* Planar poses are (x, y, yaw) in the ``map`` frame, yaw in radians.
"""
from __future__ import annotations

import math
from typing import Optional, Tuple

import numpy as np


def pixel_to_camera_point(
    u: float, v: float, depth: float,
    fx: float, fy: float, cx: float, cy: float,
) -> Tuple[float, float, float]:
    """Back-project a pixel with known depth using the pinhole model.

    X = (u - cx) * Z / fx ,  Y = (v - cy) * Z / fy ,  Z = depth
    """
    if depth <= 0 or not math.isfinite(depth):
        raise ValueError(f"invalid depth: {depth}")
    x = (u - cx) * depth / fx
    y = (v - cy) * depth / fy
    return float(x), float(y), float(depth)


def depth_to_meters(depth_img: np.ndarray) -> np.ndarray:
    """Convert a depth image to float32 meters.

    Handles the two usual ROS encodings:
    * ``32FC1``: already meters (NaN / inf for invalid pixels)
    * ``16UC1``: millimeters (0 for invalid pixels)
    """
    if depth_img.dtype == np.uint16:
        out = depth_img.astype(np.float32) / 1000.0
        out[depth_img == 0] = np.nan
        return out
    out = depth_img.astype(np.float32)
    out[~np.isfinite(out)] = np.nan
    out[out <= 0] = np.nan
    return out


def robust_bbox_depth(
    depth_m: np.ndarray,
    cx: float, cy: float, w: float, h: float,
    center_fraction: float = 0.3,
    min_valid: int = 10,
    max_range: float = 8.0,
) -> Optional[float]:
    """Median depth over the central part of a bounding box.

    Using the central patch (not the whole box) limits the influence of
    background pixels around the object; the median rejects outliers and
    holes. Returns None when too few valid pixels remain.
    """
    H, W = depth_m.shape[:2]
    pw = max(1.0, w * center_fraction) / 2.0
    ph = max(1.0, h * center_fraction) / 2.0
    x0, x1 = int(max(0, cx - pw)), int(min(W, cx + pw + 1))
    y0, y1 = int(max(0, cy - ph)), int(min(H, cy + ph + 1))
    patch = depth_m[y0:y1, x0:x1]
    vals = patch[np.isfinite(patch) & (patch > 0) & (patch < max_range)]
    if vals.size < min_valid:
        return None
    return float(np.median(vals))


def yaw_to_quaternion(yaw: float) -> Tuple[float, float, float, float]:
    """Quaternion (x, y, z, w) for a pure rotation about z."""
    return 0.0, 0.0, math.sin(yaw / 2.0), math.cos(yaw / 2.0)


def quaternion_to_yaw(x: float, y: float, z: float, w: float) -> float:
    return math.atan2(2.0 * (w * z + x * y), 1.0 - 2.0 * (y * y + z * z))


def approach_pose(
    robot_xy: Tuple[float, float],
    object_xy: Tuple[float, float],
    standoff: float = 0.6,
) -> Tuple[float, float, float]:
    """Goal pose placed ``standoff`` meters in front of the object.

    The goal lies on the segment object -> robot, and the robot faces the
    object. Sending the object position itself as a goal would fail, since
    the object is an obstacle in the costmap.
    """
    dx = robot_xy[0] - object_xy[0]
    dy = robot_xy[1] - object_xy[1]
    dist = math.hypot(dx, dy)
    if dist < 1e-6:  # robot already on the object: pick an arbitrary side
        dx, dy, dist = 1.0, 0.0, 1.0
    gx = object_xy[0] + standoff * dx / dist
    gy = object_xy[1] + standoff * dy / dist
    yaw = math.atan2(object_xy[1] - gy, object_xy[0] - gx)
    return gx, gy, yaw
