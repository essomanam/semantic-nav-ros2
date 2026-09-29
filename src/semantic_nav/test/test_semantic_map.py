from semantic_nav.semantic_map import SemanticMap


def test_close_observations_fuse_into_one_object():
    m = SemanticMap(assoc_radius=0.5, min_observations=3)
    for dx in (0.0, 0.1, -0.1):
        m.add_observation("chair", (2.0 + dx, 1.0, 0.4), 0.9)
    assert len(m.objects) == 1
    obj = m.confirmed()[0]
    assert abs(obj.x - 2.0) < 1e-6 and obj.n_obs == 3


def test_same_label_far_apart_gives_two_objects():
    m = SemanticMap(assoc_radius=0.5, min_observations=1)
    m.add_observation("chair", (0.0, 0.0, 0.0), 0.9)
    m.add_observation("chair", (3.0, 0.0, 0.0), 0.9)
    assert len(m.objects) == 2


def test_different_labels_never_merge():
    m = SemanticMap(assoc_radius=1.0, min_observations=1)
    m.add_observation("chair", (0.0, 0.0, 0.0), 0.9)
    m.add_observation("couch", (0.1, 0.0, 0.0), 0.9)
    assert len(m.objects) == 2


def test_single_detection_is_not_confirmed():
    m = SemanticMap(min_observations=3)
    m.add_observation("tv", (1.0, 1.0, 1.0), 0.9)
    assert m.confirmed() == []


def test_low_confidence_ignored():
    m = SemanticMap(min_confidence=0.5)
    assert m.add_observation("tv", (1.0, 1.0, 1.0), 0.3) is None


def test_query_nearest_and_farthest():
    m = SemanticMap(min_observations=1)
    m.add_observation("chair", (1.0, 0.0, 0.0), 0.9)
    m.add_observation("chair", (5.0, 0.0, 0.0), 0.9)
    assert m.query("chair", (0.0, 0.0)).x == 1.0
    assert m.query("chair", (0.0, 0.0), "farthest").x == 5.0
    assert m.query("bed", (0.0, 0.0)) is None
