from dataclasses import replace

import numpy as np
import pytest

from skin_analyzer.domain import ZONE_IDS, FaceZone
from skin_analyzer.face import QualityParams, assess_quality, build_face_region
from skin_analyzer.face.landmark_spec import NOSE_TIP
from tests.synthetic_face import canonical_landmarks, place

pytestmark = pytest.mark.unit


def _capture(scale=120.0, nose=(0.0, 0.54), brightness=65.0):
    landmarks = canonical_landmarks()
    landmarks[NOSE_TIP] = nose
    region = build_face_region(place(landmarks, scale, 0, (300, 200)))
    lab = np.full((*region.zone_map.shape, 3), (brightness, 15, 18), np.float32)
    return region, lab, region.zone_map.copy()


def test_good_capture_and_no_mutation():
    region, lab, zones = _capture()
    original = [a.copy() for a in (region.landmarks, region.zone_map, lab, zones)]
    report = assess_quality(region, lab, zones)
    assert report.ok and report.issues == () and report.score == 1.0
    assert report.brightness == 65 and report.face_size_px == 120
    assert report.yaw_deg == pytest.approx(0) and report.pitch_deg == pytest.approx(0)
    for actual, expected in zip((region.landmarks, region.zone_map, lab, zones), original):
        np.testing.assert_array_equal(actual, expected)


@pytest.mark.parametrize("kwargs,issue", [
    ({"brightness": 27}, "too_dark"), ({"brightness": 90}, "too_bright"),
    ({"scale": 60}, "too_far"), ({"nose": (0.25, 0.54)}, "turned_away"),
    ({"nose": (0, 1.1)}, "tilted"),
])
def test_capture_issues(kwargs, issue):
    report = assess_quality(*_capture(**kwargs))
    assert issue in report.issues and not report.ok
    assert 0 <= report.score < 1


@pytest.mark.parametrize("pair", [
    (FaceZone.LEFT_CHEEK, FaceZone.RIGHT_CHEEK), (FaceZone.FOREHEAD, FaceZone.CHIN),
])
def test_uneven_light(pair):
    region, lab, zones = _capture()
    lab[zones == ZONE_IDS[pair[0]], 0] = 55
    lab[zones == ZONE_IDS[pair[1]], 0] = 75
    report = assess_quality(region, lab, zones)
    assert report.evenness == 20 and "uneven_light" in report.issues


def test_coverage_and_empty_skin():
    region, lab, zones = _capture()
    indices = np.flatnonzero(zones)
    zones.flat[indices[:int(len(indices) * 0.5)]] = 0
    report = assess_quality(region, lab, zones)
    assert "occluded" in report.issues and report.skin_coverage == pytest.approx(0.5, abs=0.001)
    report = assess_quality(region, lab, np.zeros_like(zones))
    assert report.issues == ("too_dark", "occluded") and report.score == 0


def test_small_zones_do_not_influence_evenness():
    region, lab, zones = _capture()
    zones[:] = 0
    zones.flat[:149] = ZONE_IDS[FaceZone.LEFT_CHEEK]
    zones.flat[149:298] = ZONE_IDS[FaceZone.RIGHT_CHEEK]
    region = replace(region, zone_map=zones.copy())
    lab.reshape(-1, 3)[:149, 0] = 40
    assert assess_quality(region, lab, zones).evenness == 0


def test_custom_threshold_and_invalid_inputs():
    capture = _capture(brightness=30)
    assert assess_quality(*capture, QualityParams(min_brightness=25)).ok
    with pytest.raises(ValueError):
        QualityParams(min_skin_coverage=2)
    region, lab, zones = capture
    with pytest.raises(ValueError):
        assess_quality(region, lab[:-1], zones)
    lab[0, 0, 0] = np.nan
    with pytest.raises(ValueError):
        assess_quality(region, lab, zones)
