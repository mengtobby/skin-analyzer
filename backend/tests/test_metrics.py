"""Synthetic acceptance tests for canonical skin metrics."""

from time import perf_counter

import cv2
import numpy as np
import pytest

from skin_analyzer.domain import FaceZone, SkinMetrics, ZoneMetrics, ZONE_IDS
from skin_analyzer.metrics import MetricsParams, MetricsSmoother, compute_metrics
from skin_analyzer.metrics.skin_metrics import _gaussian_blur


def canvas() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    lab = np.empty((416, 320, 3), np.float32)
    lab[:] = (65, 14, 17)
    lab[..., 0] += np.random.default_rng(7).normal(0, 0.05, lab.shape[:2]).astype(np.float32)
    zones = np.zeros(lab.shape[:2], np.uint8)
    zones[20:396, 20:140] = ZONE_IDS[FaceZone.LEFT_CHEEK]
    zones[20:396, 140:180] = ZONE_IDS[FaceZone.NOSE]
    zones[20:396, 180:300] = ZONE_IDS[FaceZone.RIGHT_CHEEK]
    return lab, zones, np.zeros(zones.shape, bool)


def test_uniform_and_inputs_unchanged() -> None:
    inputs = canvas()
    originals = tuple(a.copy() for a in inputs)
    result = compute_metrics(*inputs, 160)
    assert result is not None
    for score in (result.overall, *result.zones.values()):
        assert score.redness < 40
        assert score.texture < 10
        assert score.oiliness == 0
        assert score.pigmentation < 10
    for actual, original in zip(inputs, originals):
        np.testing.assert_array_equal(actual, original)


def test_local_redness_and_glare() -> None:
    lab, zones, glare = canvas()
    baseline = compute_metrics(lab, zones, glare, 160)
    lab[100:180, 30:130, 1] = 32
    glare[100:140, 140:180] = True
    result = compute_metrics(lab, zones, glare, 160)
    assert result is not None and baseline is not None
    assert result.zones[FaceZone.LEFT_CHEEK].redness > baseline.zones[FaceZone.LEFT_CHEEK].redness
    assert abs(result.zones[FaceZone.RIGHT_CHEEK].redness - baseline.zones[FaceZone.RIGHT_CHEEK].redness) < 2
    assert result.zones[FaceZone.NOSE].oiliness > 30
    assert result.zones[FaceZone.LEFT_CHEEK].oiliness == 0


def test_texture_and_pigmentation() -> None:
    lab, zones, glare = canvas()
    baseline = compute_metrics(lab, zones, glare, 160)
    lab[..., 0] += np.random.default_rng(3).normal(0, 2, zones.shape).astype(np.float32)
    noisy = compute_metrics(lab, zones, glare, 160)
    lab[140:240, 40:120, 0] -= 20
    patched = compute_metrics(lab, zones, glare, 160)
    assert baseline is not None and noisy is not None and patched is not None
    assert noisy.overall.texture > baseline.overall.texture + 20
    assert patched.overall.pigmentation > noisy.overall.pigmentation + 20


def test_mask_normalization_and_minimum_counts() -> None:
    lab, zones, glare = canvas()
    lab[..., 0] = 65
    lab[zones == 0, 0] = 0
    result = compute_metrics(lab, zones, glare, 160)
    assert result is not None and result.overall.pigmentation < 0.01
    zones[:] = 0
    zones[:1, :] = 1
    assert compute_metrics(lab, zones, glare, 160) is None
    zones[:2, :] = 1
    zones[10:12, :50] = 2
    result = compute_metrics(lab, zones, glare, 160)
    assert result is not None and FaceZone.NOSE not in result.zones


def test_smoother_retention_convergence_and_reset() -> None:
    smoother = MetricsSmoother(0.2)
    assert smoother.update(None) is None
    low, high = ZoneMetrics(0, 0, 0, 0), ZoneMetrics(80, 60, 40, 20)
    source = SkinMetrics(low, {FaceZone.NOSE: high})
    first = smoother.update(source)
    assert first == source and first is not source
    target = SkinMetrics(high, {})
    for _ in range(80):
        result = smoother.update(target)
    assert result is not None
    assert result.overall.redness == pytest.approx(80, abs=0.001)
    assert result.zones[FaceZone.NOSE] == high
    retained = smoother.update(None)
    assert retained == result and retained is not result
    smoother.reset()
    assert smoother.update(None) is None


@pytest.mark.parametrize("alpha", [0, -0.1, 1.1, float("nan")])
def test_invalid_smoothing_alpha(alpha: float) -> None:
    with pytest.raises(ValueError):
        MetricsSmoother(alpha)


def test_input_validation() -> None:
    lab, zones, glare = canvas()
    for bad_lab in (lab.astype(np.uint8), lab[..., :2], lab * np.nan):
        with pytest.raises(ValueError):
            compute_metrics(bad_lab, zones, glare, 160)
    with pytest.raises(ValueError):
        compute_metrics(lab, zones, glare, 0)
    zones[0, 0] = 255
    with pytest.raises(ValueError):
        compute_metrics(lab, zones, glare, 160)
    with pytest.raises(ValueError):
        MetricsParams(texture_range=(3, 1))


def test_canvas_performance() -> None:
    inputs = canvas()
    compute_metrics(*inputs, 160)
    started = perf_counter()
    for _ in range(20):
        compute_metrics(*inputs, 160)
    assert (perf_counter() - started) / 20 < 0.030


@pytest.mark.parametrize("sigma", [12.0, 20.3, 40.0])
def test_fast_gaussian_matches_opencv(sigma: float) -> None:
    light = np.random.default_rng(5).uniform(0, 100, (83, 67)).astype(np.float32)
    expected = cv2.GaussianBlur(light, (0, 0), sigma)
    np.testing.assert_allclose(_gaussian_blur(light, sigma), expected, atol=0.0001, rtol=0)
