"""Object-level semantic map (no ROS dependency, unit-testable).

Each detection projected into the map frame is an *observation*. The map
fuses observations into *objects* with a simple incremental nearest-neighbour
association, gated by class label and distance:

    observation o (label l, position p)
      -> nearest object k with label l and ||p - p_k|| < assoc_radius
         found  : update p_k with a confidence-weighted running mean
         missing: create a new object

This is deliberately simple (a baseline you can defend and then improve).
Known limits, worth discussing in the README:
* two identical objects closer than ``assoc_radius`` get merged;
* moved objects are never removed (no decay / no negative evidence);
* the association is greedy, not globally optimal.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class SemanticObject:
    object_id: int
    label: str
    x: float
    y: float
    z: float
    weight: float = 0.0          # sum of confidences
    n_obs: int = 0
    last_seen: float = 0.0
    max_conf: float = 0.0

    def as_dict(self) -> dict:
        return {
            "id": self.object_id, "label": self.label,
            "x": round(self.x, 3), "y": round(self.y, 3), "z": round(self.z, 3),
            "n_obs": self.n_obs, "confidence": round(self.max_conf, 3),
        }


@dataclass
class SemanticMap:
    assoc_radius: float = 0.5
    min_observations: int = 3
    min_confidence: float = 0.4
    objects: Dict[int, SemanticObject] = field(default_factory=dict)
    _next_id: int = 0

    def add_observation(
        self, label: str, xyz: Tuple[float, float, float],
        confidence: float, stamp: float = 0.0,
    ) -> Optional[int]:
        if confidence < self.min_confidence:
            return None
        x, y, z = xyz
        best, best_d = None, self.assoc_radius
        for obj in self.objects.values():
            if obj.label != label:
                continue
            d = math.hypot(obj.x - x, obj.y - y)
            if d < best_d:
                best, best_d = obj, d
        if best is None:
            best = SemanticObject(self._next_id, label, x, y, z)
            self.objects[best.object_id] = best
            self._next_id += 1
        w_new = best.weight + confidence
        best.x = (best.x * best.weight + x * confidence) / w_new
        best.y = (best.y * best.weight + y * confidence) / w_new
        best.z = (best.z * best.weight + z * confidence) / w_new
        best.weight = w_new
        best.n_obs += 1
        best.last_seen = stamp
        best.max_conf = max(best.max_conf, confidence)
        return best.object_id

    def confirmed(self) -> List[SemanticObject]:
        """Objects seen often enough to be trusted (filters one-off false positives)."""
        return [o for o in self.objects.values() if o.n_obs >= self.min_observations]

    def labels(self) -> List[str]:
        return sorted({o.label for o in self.confirmed()})

    def query(
        self, label: str, robot_xy: Tuple[float, float], criterion: str = "nearest",
    ) -> Optional[SemanticObject]:
        candidates = [o for o in self.confirmed() if o.label == label]
        if not candidates:
            return None
        key = lambda o: math.hypot(o.x - robot_xy[0], o.y - robot_xy[1])
        if criterion == "farthest":
            return max(candidates, key=key)
        return min(candidates, key=key)
