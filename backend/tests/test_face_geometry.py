import numpy as np
import pytest

from skin_analyzer.domain import ZONE_IDS, FaceZone
from skin_analyzer.face import OneEuroFilter, build_face_region, face_frame_from_landmarks
from skin_analyzer.face.skin_mask import refine_zone_map
from tests.synthetic_face import canonical_landmarks, place

pytestmark = pytest.mark.unit


def _landmarks(scale=200.0, angle=0.0, origin=(640.0, 300.0)):
    return place(canonical_landmarks(), scale, angle, origin)


def test_face_frame_roundtrip_and_rotation_invariance():
    lm = _landmarks(angle=15.0)
    frame = face_frame_from_landmarks(lm)
    assert frame.scale == pytest.approx(200.0)
    canon = frame.to_canonical(lm)
    np.testing.assert_allclose(canon, canonical_landmarks(), atol=1e-9)
    np.testing.assert_allclose(frame.to_image(canon), lm, atol=1e-9)


def test_zone_map_assigns_expected_zones():
    region = build_face_region(_landmarks(), mirrored=True)
    zones = {FaceZone(z) for z in region.zone_polygons}
    assert {FaceZone.FOREHEAD, FaceZone.NOSE, FaceZone.CHIN,
            FaceZone.LEFT_CHEEK, FaceZone.RIGHT_CHEEK} <= zones
    # forehead centre: canonical (0, -0.5) -> image (640, 200)
    assert region.zone_at_image_point((640, 200)) is FaceZone.FOREHEAD
    assert region.zone_at_image_point((640, 300 + 0.35 * 200)) is FaceZone.NOSE
    assert region.zone_at_image_point((640, 300 + 1.25 * 200)) is FaceZone.CHIN
    # mirrored view: image-left cheek is the subject's left cheek
    assert region.zone_at_image_point((640 - 0.5 * 200, 300 + 0.5 * 200)) is FaceZone.LEFT_CHEEK
    assert region.zone_at_image_point((640 + 0.5 * 200, 300 + 0.5 * 200)) is FaceZone.RIGHT_CHEEK


def test_unmirrored_swaps_cheeks():
    region = build_face_region(_landmarks(), mirrored=False)
    assert region.zone_at_image_point((540, 400)) is FaceZone.RIGHT_CHEEK


def test_eyes_and_lips_are_excluded():
    region = build_face_region(_landmarks())
    eye_canvas = region.image_to_canvas_pts(np.array([[640 - 0.32 * 200, 300.0]]))[0]
    lip_canvas = region.image_to_canvas_pts(np.array([[640.0, 300 + 0.95 * 200]]))[0]
    for x, y in (eye_canvas, lip_canvas):
        assert region.zone_map[int(y), int(x)] == 0


def test_zone_map_is_scale_invariant():
    small = build_face_region(_landmarks(scale=90.0))
    big = build_face_region(_landmarks(scale=260.0))
    agree = (small.zone_map == big.zone_map).mean()
    assert agree > 0.98


def test_refine_zone_map_drops_off_colour_pixels():
    zone_map = np.full((40, 40), ZONE_IDS[FaceZone.FOREHEAD], np.uint8)
    lab = np.zeros((40, 40, 3), np.float32)
    lab[...] = (65, 15, 18)
    lab[:5] = (20, 2, 3)  # hair fringe
    refined = refine_zone_map(zone_map, lab)
    assert (refined[:5] == 0).all()
    assert (refined[5:] == ZONE_IDS[FaceZone.FOREHEAD]).all()
    assert (zone_map[:5] != 0).all()  # input untouched


def test_one_euro_reduces_jitter_but_follows_motion():
    rng = np.random.default_rng(1)
    f = OneEuroFilter()
    raw, filt = [], []
    for i in range(120):
        x = np.array([100.0 + rng.normal(0, 1.0)])
        raw.append(x[0])
        filt.append(f(x, i / 30.0, scale=100.0)[0])
    assert np.std(filt[30:]) < 0.5 * np.std(raw[30:])
    f.reset()
    for i in range(60):
        out = f(np.array([i * 10.0]), i / 30.0, scale=100.0)
    assert abs(out[0] - 590.0) < 40.0
