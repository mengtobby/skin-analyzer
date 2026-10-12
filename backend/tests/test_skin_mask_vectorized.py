"""Vectorised red-lesion restoration must match the per-component reference exactly."""
from time import perf_counter

import cv2
import numpy as np
import pytest

from skin_analyzer.face.skin_mask import _enclosed_red_skin


def _reference(accepted: np.ndarray, candidates: np.ndarray, skin: np.ndarray) -> np.ndarray:
    """Original per-component loop (kept as the specification)."""
    count, labels, stats, _ = cv2.connectedComponentsWithStats(
        candidates.astype(np.uint8), connectivity=8
    )
    labels = np.pad(labels, 1)
    accepted = np.pad(accepted, 1)
    skin = np.pad(skin, 1, constant_values=True)
    restored = np.zeros(count, bool)
    kernel = np.ones((3, 3), np.uint8)
    for label in range(1, count):
        x, y, width, height, _ = stats[label]
        region = np.s_[y:y + height + 2, x:x + width + 2]
        component = labels[region] == label
        ring = cv2.dilate(component.astype(np.uint8), kernel).astype(bool) & ~component
        border = ring & skin[region]
        total = np.count_nonzero(border)
        restored[label] = total > 0 and np.count_nonzero(border & accepted[region]) >= 0.6 * total
    return restored[labels[1:-1, 1:-1]]


def _scene(seed: int, red_fraction: float, shape=(416, 320)):
    rng = np.random.default_rng(seed)
    skin = np.ones(shape, bool)
    skin[150:190, 60:120] = False  # eye-like exclusion hole (neutral)
    skin[:, :8] = False
    candidates = (rng.random(shape) < red_fraction) & skin
    candidates |= cv2.dilate((rng.random(shape) < red_fraction / 20).astype(np.uint8),
                             np.ones((5, 5), np.uint8)).astype(bool) & skin
    accepted = skin & ~candidates & (rng.random(shape) > 0.3)
    return accepted, candidates, skin


@pytest.mark.parametrize("seed,fraction", [(0, 0.0), (1, 0.005), (2, 0.02), (3, 0.05), (4, 0.10)])
def test_matches_reference(seed, fraction):
    accepted, candidates, skin = _scene(seed, fraction)
    np.testing.assert_array_equal(
        _enclosed_red_skin(accepted, candidates, skin), _reference(accepted, candidates, skin))


def test_edge_touching_components_count_canvas_border_as_rejected():
    skin = np.ones((20, 20), bool)
    candidates = np.zeros_like(skin)
    candidates[0:3, 5:8] = True  # touches the top canvas edge
    accepted = skin & ~candidates
    np.testing.assert_array_equal(
        _enclosed_red_skin(accepted, candidates, skin), _reference(accepted, candidates, skin))


def test_heavy_speckle_is_fast():
    accepted, candidates, skin = _scene(4, 0.10)
    _enclosed_red_skin(accepted, candidates, skin)
    timings = []
    for _ in range(5):
        start = perf_counter()
        _enclosed_red_skin(accepted, candidates, skin)
        timings.append(perf_counter() - start)
    assert min(timings) < 0.015  # reference loop: ~120 ms on this input
