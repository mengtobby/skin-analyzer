"""Canonical tracking behavior and immutable Kalman regression tests."""

import math

import numpy as np
import pytest

from skin_analyzer.domain import Detection, DetectionClass, FaceFrame, FaceZone
from skin_analyzer.tracking import LesionTracker, TrackerParams
from skin_analyzer.tracking import kalman


def frame(index: int = 0) -> FaceFrame:
    angle = index * 0.04
    return FaceFrame(np.array([300.0 + index * 3, 200.0 - index]),
                     np.array([math.cos(angle), math.sin(angle)]),
                     np.array([-math.sin(angle), math.cos(angle)]), 100.0 + index * 2)


def detection(face: FaceFrame, center: tuple[float, float] = (0.2, 0.5),
              label: DetectionClass = DetectionClass.PAPULE,
              confidence: float = 0.8) -> Detection:
    points = face.to_image(np.asarray(center) + np.array([[-.01, -.01], [.01, -.01],
                                                        [.01, .01], [-.01, .01]]))
    lo, hi = points.min(axis=0), points.max(axis=0)
    return Detection(label, tuple(float(x) for x in (*lo, *(hi - lo))), confidence,
                     tuple((float(x), float(y)) for x, y in points),
                     math.pi * (0.01 * face.scale) ** 2, FaceZone.CHIN)


def test_head_motion_and_reprojection() -> None:
    tracker = LesionTracker()
    for index in range(30):
        face = frame(index)
        observed = detection(face)
        tracks = tracker.update([observed], face, index / 30)
        if index >= 2:
            assert len(tracks) == 1 and tracks[0].track_id == 1
            assert np.allclose(tracks[0].canonical_center, (.2, .5))
            assert np.allclose(tracks[0].contour, observed.contour)
            assert tracks[0].size_mm == pytest.approx(1.8)


def test_transient_and_confirmation_window() -> None:
    tracker = LesionTracker()
    assert tracker.update([detection(frame())], frame(), 0) == []
    for index in range(1, 8):
        assert tracker.update([], frame(), index / 30) == []
    assert tracker.update([detection(frame())], frame(), 1) == []
    tracker.update([detection(frame())], frame(), 1.1)
    assert tracker.update([detection(frame())], frame(), 1.2)[0].track_id == 2


def test_jitter_is_suppressed() -> None:
    rng = np.random.default_rng(13)
    jitter = rng.normal(0, .01, (300, 2))
    tracker = LesionTracker()
    centers = []
    for index, offset in enumerate(jitter):
        tracks = tracker.update([detection(frame(), tuple(np.array([.2, .5]) + offset))],
                                frame(), index / 30)
        if index >= 30:
            assert len(tracks) == 1
            centers.append(tracks[0].canonical_center)
    assert np.all(np.std(centers, axis=0) < .5 * np.std(jitter[30:], axis=0))


def test_misses_and_latest_contour() -> None:
    tracker = LesionTracker(TrackerParams(min_hits=1))
    original = detection(frame())
    tracker.update([original], frame(), 0)
    for index in range(1, 13):
        tracks = tracker.update([], frame(index), index / 30)
        assert tracks[0].misses == index
        assert np.allclose(tracks[0].contour, detection(frame(index)).contour)
    assert tracker.update([], frame(), 13 / 30) == []


def test_face_loss_timeout_and_reset() -> None:
    tracker = LesionTracker(TrackerParams(min_hits=1))
    tracker.update([detection(frame())], frame(), 0)
    assert tracker.update([], None, .5) == []
    track = tracker.update([detection(frame())], frame(), 1)[0]
    assert track.track_id == 1 and track.misses == 0 and track.age == 2
    tracker.update([], None, 1.1)
    track = tracker.update([detection(frame())], frame(), 2.6)[0]
    assert track.track_id == 2
    tracker.update([], None, 3)
    tracker.update([], None, 5)
    assert tracker.update([detection(frame())], frame(), 5.1)[0].track_id == 3
    tracker.reset()
    assert tracker.update([detection(frame())], frame(), 6)[0].track_id == 1


def test_label_compatibility_majority_and_confidence() -> None:
    tracker = LesionTracker(TrackerParams(min_hits=1))
    for index in range(20):
        label = DetectionClass.PAPULE if index % 2 == 0 else DetectionClass.PUSTULE
        tracks = tracker.update([detection(frame(), label=label),
                                 detection(frame(), (.21, .5), DetectionClass.HYPERPIGMENTATION)],
                                frame(), index / 30)
        assert [t.track_id for t in tracks] == [1, 2]
        assert tracks[1].label == DetectionClass.HYPERPIGMENTATION
    assert tracks[0].label == DetectionClass.PUSTULE
    tracks = tracker.update([detection(frame(), confidence=.2)], frame(), 1)
    assert tracks[0].confidence == pytest.approx(.62)


def test_inputs_and_kalman_states_are_immutable() -> None:
    face = frame()
    observed = detection(face)
    old_contour, old_origin = observed.contour, face.origin.copy()
    tracker = LesionTracker(TrackerParams(min_hits=1))
    tracker.update([observed], face, 0)
    tracker.update([observed], face, .1)
    assert observed.contour == old_contour
    assert np.array_equal(face.origin, old_origin)
    state = kalman.initialize((.2, .5), 0, .0004)
    predicted = kalman.predict(state, 1, .0001)
    updated = kalman.update(predicted, (.21, .49), .0004)
    assert state.mean == (.2, .5, 0, 0)
    assert updated != predicted
    assert kalman.predict(state, 100, .0001).covariance == predicted.covariance
    assert kalman.predict(state, -1, .0001).covariance == kalman.predict(state, 0, .0001).covariance


@pytest.mark.parametrize("kwargs", [{"min_hits": 0}, {"confirm_window": 2},
                                    {"measurement_noise": 0}, {"confidence_alpha": 2},
                                    {"gate_units": float("nan")}, {"max_misses": -1}])
def test_invalid_params(kwargs: dict[str, float]) -> None:
    with pytest.raises(ValueError):
        TrackerParams(**kwargs)


def test_invalid_boundaries_do_not_change_tracks() -> None:
    tracker = LesionTracker(TrackerParams(min_hits=1))
    tracker.update([detection(frame())], frame(), 0)
    with pytest.raises(ValueError):
        tracker.update([], frame(), float("nan"))
    with pytest.raises(ValueError):
        tracker.update([detection(frame(), confidence=2)], frame(), 1)
    invalid = FaceFrame(frame().origin, frame().axis_u, frame().axis_v, 0)
    with pytest.raises(ValueError):
        tracker.update([], invalid, 1)
    assert tracker.update([detection(frame())], frame(), .1)[0].hits == 2
