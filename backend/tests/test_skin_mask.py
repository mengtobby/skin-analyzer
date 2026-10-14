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


def test_red_lesion_touching_eye_exclusion_is_kept():
    zones = np.full((40, 40), ZONE_IDS[FaceZone.LEFT_CHEEK], np.uint8)
    zones[10:20, 10:20] = 0  # eye exclusion
    lab = np.full((40, 40, 3), (65, 15, 18), np.float32)
    lab[12:18, 20:24] = (55, 42, 23)
    refined = refine_zone_map(zones, lab)
    assert refined[12:18, 20:24].all()
    assert not refined[10:20, 10:20].any()


def test_red_blob_inside_dark_hair_band_is_rejected():
    zones = np.full((40, 40), ZONE_IDS[FaceZone.LEFT_CHEEK], np.uint8)
    lab = np.full((40, 40, 3), (65, 15, 18), np.float32)
    lab[10:20] = (12, 1, 2)
    lab[12:18, 15:20] = (55, 42, 23)
    assert not refine_zone_map(zones, lab)[10:20].any()


def test_fallback_reference_and_empty_map():
    zones = np.full((10, 10), ZONE_IDS[FaceZone.FOREHEAD], np.uint8)
    lab = np.full((10, 10, 3), (65, 15, 18), np.float32)
    lab[0] = (12, 1, 2)
    refined = refine_zone_map(zones, lab)
    assert not refined[:9].any() and refined[9:].all()
    zones[:] = 0
    np.testing.assert_array_equal(refine_zone_map(zones, lab), zones)


def test_invalid_canvas():
    with pytest.raises(ValueError):
        refine_zone_map(np.ones((10, 10)), np.ones((9, 10, 3)))


@pytest.mark.parametrize("margin", [0, 3, 8])
def test_forehead_hair_margin_has_exact_depth_and_preserves_other_zones(margin):
    zones = np.full((50, 60), ZONE_IDS[FaceZone.FOREHEAD], np.uint8)
    zones[:4] = 0
    for column, zone in enumerate((FaceZone.LEFT_CHEEK, FaceZone.NOSE, FaceZone.CHIN)):
        zones[:, column * 10:(column + 1) * 10] = ZONE_IDS[zone]
    lab = np.full((*zones.shape, 3), (65, 15, 18), np.float32)
    lab[4:7, 30:] = (12, 1, 2)
    original_zones, original_lab = zones.copy(), lab.copy()
    refined = refine_zone_map(zones, lab, hair_margin_px=margin)
    assert not refined[4:7 + margin, 30:].any()
    np.testing.assert_array_equal(refined[7 + margin:, 30:], zones[7 + margin:, 30:])
    np.testing.assert_array_equal(refined[:, :30], zones[:, :30])
    expected = zones.copy()
    expected[4:7, 30:] = 0
    np.testing.assert_array_equal(refine_zone_map(zones, lab, hair_margin_px=0), expected)
    np.testing.assert_array_equal(zones, original_zones)
    np.testing.assert_array_equal(lab, original_lab)


def test_isolated_forehead_dark_spot_does_not_expand():
    zones = np.full((50, 50), ZONE_IDS[FaceZone.FOREHEAD], np.uint8)
    lab = np.full((*zones.shape, 3), (65, 15, 18), np.float32)
    lab[20:23, 20:23] = (12, 1, 2)
    expected = zones.copy()
    expected[20:23, 20:23] = 0
    np.testing.assert_array_equal(refine_zone_map(zones, lab), expected)


def test_restored_red_at_forehead_upper_boundary_does_not_trigger_margin():
    zones = np.full((40, 40), ZONE_IDS[FaceZone.FOREHEAD], np.uint8)
    zones[:5] = 0
    lab = np.full((*zones.shape, 3), (65, 15, 18), np.float32)
    lab[5:8, 15:18] = (55, 42, 23)
    np.testing.assert_array_equal(refine_zone_map(zones, lab), zones)


def test_diagonal_hair_connection_and_euclidean_margin():
    zones = np.full((40, 40), ZONE_IDS[FaceZone.FOREHEAD], np.uint8)
    lab = np.full((*zones.shape, 3), (65, 15, 18), np.float32)
    indices = np.arange(5)
    lab[indices, indices + 10] = (12, 1, 2)
    refined = refine_zone_map(zones, lab, hair_margin_px=3)
    assert refined[7, 14] == 0
    assert refined[7, 17] != 0  # diagonal distance sqrt(18) exceeds three
    assert refined[8, 14] != 0


@pytest.mark.parametrize("margin", [-1, 1.5, "8", None, True])
def test_invalid_hair_margin(margin):
    with pytest.raises(ValueError, match="Hair margin"):
        refine_zone_map(np.zeros((5, 5), np.uint8), np.zeros((5, 5, 3)), hair_margin_px=margin)


@pytest.mark.parametrize("colour", [
    (47, 15, 18), (90, 15, 18), (65, 37, 18), (65, 15, 36),
])
def test_colour_tolerance_boundaries_are_excluded(colour):
    zones = np.full((30, 30), ZONE_IDS[FaceZone.LEFT_CHEEK], np.uint8)
    lab = np.full((30, 30, 3), (65, 15, 18), np.float32)
    lab[0, 0] = colour
    refined = refine_zone_map(zones, lab)
    assert refined[0, 0] == 0 and refined[1:].all()
