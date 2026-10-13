"""Regression and timing checks for canonical zoning."""
from time import perf_counter
import cv2
import numpy as np
import pytest
from skin_analyzer.domain import CanvasSpec, FaceZone, ZONE_IDS
from skin_analyzer.face import landmark_spec as spec
from skin_analyzer.face.geometry import ZoneParams, build_face_region, shading_mask
from tests.synthetic_face import canonical_landmarks, place

def _reference_shading_mask(
    canvas: CanvasSpec, canon: np.ndarray, params: ZoneParams = ZoneParams()
) -> np.ndarray:
    """Evaluate the anatomical criteria independently at every pixel centre."""
    w, h = canvas.size
    u, v = np.meshgrid(
        (np.arange(w) + 0.5) / canvas.px_per_unit + canvas.u_range[0],
        (np.arange(h) + 0.5) / canvas.px_per_unit + canvas.v_range[0])
    nose_u = canon[list(spec.NOSE), 0]
    centre = canon[spec.NOSE_TIP, 0]
    half = max(params.min_nose_half_width, (nose_u.max() - nose_u.min()) / 2)
    root = canon[[spec.LEFT_EYE_INNER, spec.RIGHT_EYE_INNER]].mean(axis=0)
    vertical = (v >= root[1] + 0.05) & (v <= canon[list(spec.NOSE), 1].max())
    left = (u >= centre - half - params.sidewall_outer) & (u <= centre - half + params.sidewall_inner)
    right = (u >= centre + half - params.sidewall_inner) & (u <= centre + half + params.sidewall_outer)
    disk = (u - root[0]) ** 2 + (v - root[1]) ** 2 <= params.nasal_root_radius ** 2
    return (vertical & (left | right)) | disk


def _old_hull_mask(shape: tuple[int, int], pts: np.ndarray, grow_px: float) -> np.ndarray:
    mask = np.zeros(shape, np.uint8)
    hull = cv2.convexHull(np.round(pts).astype(np.int32))
    cv2.fillConvexPoly(mask, hull, 1)
    r = int(round(grow_px))
    if r > 0:
        mask = cv2.dilate(mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1,) * 2))
    elif r < 0:
        mask = cv2.erode(mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (-2 * r + 1,) * 2))
    return mask.astype(bool)


def _old_zone_map(
    canon: np.ndarray, canvas: CanvasSpec, mirrored: bool, params: ZoneParams = ZoneParams()
) -> np.ndarray:
    """Label every canvas pixel with a ZONE_IDS value (0 = not analysable skin)."""
    w, h = canvas.size
    ppu = canvas.px_per_unit
    pts = canvas.canonical_to_canvas(canon)
    sel = lambda idx: pts[list(idx)]  # noqa: E731
    vsel = lambda idx: canon[list(idx), 1]  # noqa: E731

    skin = _old_hull_mask((h, w), sel(spec.FACE_OVAL), -params.oval_erode * ppu)
    for idx, margin in (
        (spec.LEFT_EYE, params.eye_margin),
        (spec.RIGHT_EYE, params.eye_margin),
        (spec.LEFT_EYEBROW, params.brow_margin),
        (spec.RIGHT_EYEBROW, params.brow_margin),
        (spec.LIPS, params.lip_margin),
        (spec.NOSTRILS, params.nostril_margin),
    ):
        skin &= ~_old_hull_mask((h, w), sel(idx), margin * ppu)

    us = (np.arange(w) + 0.5) / ppu + canvas.u_range[0]
    vs = (np.arange(h) + 0.5) / ppu + canvas.v_range[0]
    u, v = np.meshgrid(us, vs)

    brow_top = min(vsel(spec.LEFT_EYEBROW).min(), vsel(spec.RIGHT_EYEBROW).min())
    eye_bottom = max(vsel(spec.LEFT_EYE).max(), vsel(spec.RIGHT_EYE).max())
    eye_inner = canon[[spec.LEFT_EYE_INNER, spec.RIGHT_EYE_INNER], 1].mean()
    nose_u = canon[list(spec.NOSE), 0]
    nose_c = canon[spec.NOSE_TIP, 0]
    half = max(params.min_nose_half_width, (nose_u.max() - nose_u.min()) / 2)
    nose_lo, nose_hi = nose_c - half, nose_c + half
    nose_bottom = vsel(spec.NOSE).max()
    mouth_v = canon[[spec.MOUTH_LEFT, spec.MOUTH_RIGHT], 1].mean()
    lip_bottom = canon[spec.LOWER_LIP_BOTTOM, 1]

    zone = np.full((h, w), ZONE_IDS[FaceZone.OTHER], np.uint8)
    chin = v >= lip_bottom + 0.04
    cheek_band = (v >= eye_bottom + params.cheek_eye_gap) & (v <= mouth_v + 0.05)
    image_left = cheek_band & (u < nose_lo - params.nose_side_gap)
    image_right = cheek_band & (u > nose_hi + params.nose_side_gap)
    nose = (u >= nose_lo) & (u <= nose_hi) & (v >= eye_inner) & (v <= nose_bottom)
    forehead = v < brow_top - params.forehead_gap

    left_cheek, right_cheek = (image_left, image_right) if mirrored else (image_right, image_left)
    for mask, z in (
        (chin, FaceZone.CHIN),
        (left_cheek, FaceZone.LEFT_CHEEK),
        (right_cheek, FaceZone.RIGHT_CHEEK),
        (nose, FaceZone.NOSE),
        (forehead, FaceZone.FOREHEAD),
    ):
        zone = np.where(mask, ZONE_IDS[z], zone).astype(np.uint8)
    skin &= ~_reference_shading_mask(canvas, canon, params)
    return np.where(skin, zone, 0).astype(np.uint8)


@pytest.mark.parametrize("scale,angle", [(90, -25), (160, 0), (260, 30)])
@pytest.mark.parametrize("mirrored", [True, False])
def test_zone_map_matches_previous_algorithm(scale, angle, mirrored):
    landmarks = place(canonical_landmarks(), scale, angle, (640, 300))
    region = build_face_region(landmarks, mirrored=mirrored)
    expected = _old_zone_map(region.frame.to_canonical(landmarks), region.canvas, mirrored)
    assert (region.zone_map == expected).mean() >= 0.99


@pytest.mark.parametrize("scale,angle", [(90, -25), (160, 0), (260, 30)])
@pytest.mark.parametrize("ppu", [80, 160, 240])
def test_shading_matches_per_pixel_reference(scale, angle, ppu):
    landmarks = place(canonical_landmarks(), scale, angle, (640, 300))
    region = build_face_region(landmarks, canvas=CanvasSpec(px_per_unit=ppu))
    canon = region.frame.to_canonical(landmarks)
    np.testing.assert_array_equal(shading_mask(region.canvas, canon),
                                  _reference_shading_mask(region.canvas, canon))


def test_build_face_region_timing():
    landmarks = place(canonical_landmarks(), 200, 15, (640, 300))
    region = build_face_region(landmarks)
    canon = region.frame.to_canonical(landmarks)
    fast, reference = [], []
    for _ in range(10):
        start = perf_counter()
        build_face_region(landmarks)
        fast.append(perf_counter() - start)
        start = perf_counter()
        _old_zone_map(canon, region.canvas, True)
        reference.append(perf_counter() - start)
    assert min(fast) < min(reference) / 2
