"""Offline evaluation of the semantic map against Gazebo ground truth.

In simulation the true pose of every object is known (read it from the world
SDF). Predicted objects are matched to ground-truth objects of the same label
with the Hungarian algorithm, then gated by a maximum distance.

Metrics
-------
* mean / median localisation error (m) over matched pairs
* precision = matched / predicted, recall = matched / ground truth
"""
from __future__ import annotations

import math
from collections import defaultdict
from typing import Dict, List

import numpy as np
from scipy.optimize import linear_sum_assignment


def match_objects(pred: List[dict], gt: List[dict], max_dist: float = 1.0) -> Dict:
    by_label_p, by_label_g = defaultdict(list), defaultdict(list)
    for p in pred:
        by_label_p[p["label"]].append(p)
    for g in gt:
        by_label_g[g["label"]].append(g)

    errors, per_label = [], {}
    for label in sorted(set(by_label_p) | set(by_label_g)):
        P, G = by_label_p.get(label, []), by_label_g.get(label, [])
        matched = []
        if P and G:
            cost = np.array([[math.hypot(p["x"] - g["x"], p["y"] - g["y"]) for g in G] for p in P])
            rows, cols = linear_sum_assignment(cost)
            matched = [cost[r, c] for r, c in zip(rows, cols) if cost[r, c] <= max_dist]
        errors.extend(matched)
        per_label[label] = {"pred": len(P), "gt": len(G), "matched": len(matched)}

    n_pred, n_gt, n_match = len(pred), len(gt), len(errors)
    return {
        "matched": n_match,
        "precision": n_match / n_pred if n_pred else 0.0,
        "recall": n_match / n_gt if n_gt else 0.0,
        "mean_error_m": float(np.mean(errors)) if errors else float("nan"),
        "median_error_m": float(np.median(errors)) if errors else float("nan"),
        "per_label": per_label,
    }
