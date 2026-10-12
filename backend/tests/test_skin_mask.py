import numpy as np
import pytest

from skin_analyzer.domain import ZONE_IDS, FaceZone
from skin_analyzer.face import refine_zone_map

pytestmark = pytest.mark.unit


def test_cheek_reference_removes_forehead_hair_and_keeps_red_lesion():
    zones = np.full((60, 60), ZONE_IDS[FaceZone.FOREHEAD], np.uint8)
    zones[40:, :30] = ZONE_IDS[FaceZone.LEFT_CHEEK]
    zones[40:, 30:] = ZONE_IDS[FaceZone.RIGHT_CHEEK]
    lab = np.full((60, 60, 3), (65, 15, 18), np.float32)
    lab[:40] = (12, 1, 2)  # hair dominates the whole-face median
    lab[45:50, 10:15, 1] += 12
    original_zones, original_lab = zones.copy(), lab.copy()
    refined = refine_zone_map(zones, lab)
    assert not refined[:40].any()
    np.testing.assert_array_equal(refined[40:], zones[40:])
    np.testing.assert_array_equal(zones, original_zones)
    np.testing.assert_array_equal(lab, original_lab)


def test_low_chroma_rejected_even_at_skin_brightness():
    zones = np.full((30, 30), ZONE_IDS[FaceZone.LEFT_CHEEK], np.uint8)
    lab = np.full((30, 30, 3), (65, 15, 18), np.float32)
    lab[:3] = (65, 1, 2)
    assert not refine_zone_map(zones, lab)[:3].any()


def test_enclosed_red_lesion_kept_but_boundary_red_and_dark_holes_rejected():
    zones = np.full((40, 40), ZONE_IDS[FaceZone.LEFT_CHEEK], np.uint8)
    lab = np.full((40, 40, 3), (65, 15, 18), np.float32)
    lab[15:20, 15:20] = (55, 42, 23)
    lab[:5, :5] = (55, 42, 23)
    lab[25:30, 25:30] = (12, 1, 2)
    refined = refine_zone_map(zones, lab)
    assert refined[15:20, 15:20].all()
    assert not refined[:5, :5].any()
    assert not refined[25:30, 25:30].any()


def test_achromatic_balanced_skin_is_not_fragmented_by_chroma_noise():
    zones = np.full((30, 30), ZONE_IDS[FaceZone.LEFT_CHEEK], np.uint8)
    lab = np.full((30, 30, 3), (65, 0.18, 0.12), np.float32)
    lab[::2, ::2, 1:] = 0
    lab[:3] = (12, 0, 0)
    refined = refine_zone_map(zones, lab)
    assert refined[3:].all() and not refined[:3].any()


def test_fallback_reference_and_empty_map():
    zones = np.full((10, 10), ZONE_IDS[FaceZone.FOREHEAD], np.uint8)
    lab = np.full((10, 10, 3), (65, 15, 18), np.float32)
    lab[0] = (12, 1, 2)
    refined = refine_zone_map(zones, lab)
    assert not refined[0].any() and refined[1:].all()
    zones[:] = 0
    np.testing.assert_array_equal(refine_zone_map(zones, lab), zones)


def test_invalid_canvas():
    with pytest.raises(ValueError):
        refine_zone_map(np.ones((10, 10)), np.ones((9, 10, 3)))


@pytest.mark.parametrize("colour", [
    (47, 15, 18), (90, 15, 18), (65, 37, 18), (65, 15, 36),
])
def test_colour_tolerance_boundaries_are_excluded(colour):
    zones = np.full((30, 30), ZONE_IDS[FaceZone.LEFT_CHEEK], np.uint8)
    lab = np.full((30, 30, 3), (65, 15, 18), np.float32)
    lab[0, 0] = colour
    refined = refine_zone_map(zones, lab)
    assert refined[0, 0] == 0 and refined[1:].all()
