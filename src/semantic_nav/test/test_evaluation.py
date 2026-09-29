import pytest

from semantic_nav.evaluation import match_objects


def test_perfect_map():
    gt = [{"label": "chair", "x": 1.0, "y": 0.0}, {"label": "couch", "x": 0.0, "y": 2.0}]
    r = match_objects(gt, gt)
    assert r["precision"] == 1.0 and r["recall"] == 1.0 and r["mean_error_m"] == 0.0


def test_false_positive_and_error():
    gt = [{"label": "chair", "x": 1.0, "y": 0.0}]
    pred = [{"label": "chair", "x": 1.3, "y": 0.4}, {"label": "chair", "x": 9.0, "y": 9.0}]
    r = match_objects(pred, gt, max_dist=1.0)
    assert r["matched"] == 1
    assert r["precision"] == pytest.approx(0.5) and r["recall"] == 1.0
    assert r["mean_error_m"] == pytest.approx(0.5)
