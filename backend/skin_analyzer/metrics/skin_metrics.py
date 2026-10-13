"""Heuristic CIELAB skin scores on the canonical analysis canvas."""

from __future__ import annotations

from dataclasses import dataclass, fields
from types import MappingProxyType

import cv2
import numpy as np

from ..domain import FaceZone, SkinMetrics, ZoneMetrics, ZONE_IDS


@dataclass(frozen=True)
class MetricsParams:
    min_skin_pixels: int = 500
    min_zone_pixels: int = 150
    redness_range: tuple[float, float] = (8.0, 24.0)
    redness_fraction_range: tuple[float, float] = (0.0, 0.15)
    redness_delta: float = 6.0
    redness_median_weight: float = 0.6
    # Ranges calibrated on real 1280x720 webcam frames in even frontal light: per-zone
    # high-pass L* std 0.38-0.48 (cheeks/nose/chin), ~1.2 (forehead); band-pass std
    # 1.3-3.6. Normal skin therefore scores low-to-moderate, leaving headroom.
    texture_range: tuple[float, float] = (0.35, 2.0)
    oiliness_range: tuple[float, float] = (0.0, 0.06)
    pigmentation_range: tuple[float, float] = (2.0, 8.0)
    texture_sigma: float = 0.02
    pigmentation_small_sigma: float = 0.03
    pigmentation_large_sigma: float = 0.25
    erosion_pixels: int = 2

    def __post_init__(self) -> None:
        for name in ("min_skin_pixels", "min_zone_pixels", "erosion_pixels"):
            value = getattr(self, name)
            if not isinstance(value, int) or value < (0 if name == "erosion_pixels" else 1):
                raise ValueError(f"{name} must be a valid pixel count")
        for name in ("redness_range", "redness_fraction_range", "texture_range",
                     "oiliness_range", "pigmentation_range"):
            bounds = getattr(self, name)
            if len(bounds) != 2 or not np.isfinite(bounds).all() or bounds[0] >= bounds[1]:
                raise ValueError(f"{name} must contain finite increasing bounds")
        for name in ("texture_sigma", "pigmentation_small_sigma", "pigmentation_large_sigma"):
            value = getattr(self, name)
            if not np.isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be finite and positive")
        if not np.isfinite(self.redness_delta) or self.redness_delta < 0:
            raise ValueError("redness_delta must be finite and nonnegative")
        if not np.isfinite(self.redness_median_weight) or not 0 <= self.redness_median_weight <= 1:
            raise ValueError("redness_median_weight must be between zero and one")


def _validate_inputs(lab: np.ndarray, zone_map: np.ndarray,
                     specular_mask: np.ndarray, px_per_unit: float) -> None:
    if not isinstance(lab, np.ndarray) or lab.dtype != np.float32:
        raise ValueError("lab must be a float32 CIELAB array")
    if lab.ndim != 3 or lab.shape[2] != 3 or min(lab.shape[:2]) == 0:
        raise ValueError("lab must have nonempty shape HxWx3")
    if not np.isfinite(lab).all() or np.any((lab[..., 0] < 0) | (lab[..., 0] > 100)):
        raise ValueError("lab must be finite with L in [0, 100]")
    if not isinstance(zone_map, np.ndarray) or zone_map.dtype != np.uint8:
        raise ValueError("zone_map must be a uint8 array")
    if zone_map.shape != lab.shape[:2] or not np.isin(zone_map, [0, *ZONE_IDS.values()]).all():
        raise ValueError("zone_map must match lab and contain only ZONE_IDS or zero")
    if not isinstance(specular_mask, np.ndarray) or specular_mask.dtype != np.bool_:
        raise ValueError("specular_mask must be a bool array")
    if specular_mask.shape != zone_map.shape:
        raise ValueError("specular_mask must match zone_map")
    if not np.isfinite(px_per_unit) or px_per_unit <= 0:
        raise ValueError("px_per_unit must be finite and positive")


def _ramp(value: float, bounds: tuple[float, float]) -> float:
    return float(np.clip((value - bounds[0]) / (bounds[1] - bounds[0]), 0, 1) * 100)


def _masked_blur(light: np.ndarray, skin: np.ndarray, sigma: float) -> np.ndarray:
    weights = skin.astype(np.float32)
    numerator = _gaussian_blur(light * weights, sigma)
    denominator = _gaussian_blur(weights, sigma)
    return np.divide(numerator, denominator, out=np.zeros_like(light), where=denominator > 0)


def _gaussian_blur(image: np.ndarray, sigma: float) -> np.ndarray:
    """Gaussian blur; large sigmas run on a downsampled image (a low-pass loses nothing there).

    Keeps the sigma=40 px pigmentation baseline at well under a millisecond instead of an
    exact full-resolution convolution.
    """
    factor = int(min(8, sigma // 4))
    if factor < 2:
        return cv2.GaussianBlur(image, (0, 0), sigma)
    h, w = image.shape[:2]
    sw, sh = max(1, w // factor), max(1, h // factor)
    small = cv2.resize(image, (sw, sh), interpolation=cv2.INTER_AREA)
    blurred = cv2.GaussianBlur(small, (0, 0), sigmaX=sigma * sw / w, sigmaY=sigma * sh / h)
    return cv2.resize(blurred, (w, h), interpolation=cv2.INTER_LINEAR)


def _score(mask: np.ndarray, a: np.ndarray, face_median: float,
           high_pass: np.ndarray, band_pass: np.ndarray, glare: np.ndarray,
           params: MetricsParams) -> ZoneMetrics:
    values = a[mask]
    weight = params.redness_median_weight
    redness = weight * _ramp(float(np.median(values)), params.redness_range)
    redness += (1 - weight) * _ramp(float(np.mean(values > face_median + params.redness_delta)),
                                   params.redness_fraction_range)
    radius = params.erosion_pixels
    kernel = np.ones((2 * radius + 1, 2 * radius + 1), np.uint8)
    interior = cv2.erode(mask.astype(np.uint8), kernel, borderType=cv2.BORDER_CONSTANT,
                         borderValue=0).astype(bool)
    texture_std = float(np.std(high_pass[interior])) if interior.any() else 0.0
    return ZoneMetrics(
        redness=redness,
        texture=_ramp(texture_std, params.texture_range),
        oiliness=_ramp(float(np.mean(glare[mask])), params.oiliness_range),
        pigmentation=_ramp(float(np.std(band_pass[mask])), params.pigmentation_range),
    )


def compute_metrics(lab: np.ndarray, zone_map: np.ndarray, specular_mask: np.ndarray,
                    px_per_unit: float, params: MetricsParams | None = None) -> SkinMetrics | None:
    """Compute shared blurs once, then score the face and sufficiently populated zones."""
    _validate_inputs(lab, zone_map, specular_mask, px_per_unit)
    params = params if params is not None else MetricsParams()
    if not isinstance(params, MetricsParams):
        raise ValueError("params must be MetricsParams or None")
    skin = zone_map > 0
    if np.count_nonzero(skin) < params.min_skin_pixels:
        return None
    light, a = lab[..., 0], lab[..., 1]
    high_pass = light - cv2.GaussianBlur(light, (0, 0), params.texture_sigma * px_per_unit)
    band_pass = (_masked_blur(light, skin, params.pigmentation_small_sigma * px_per_unit)
                 - _masked_blur(light, skin, params.pigmentation_large_sigma * px_per_unit))
    median = float(np.median(a[skin]))
    overall = _score(skin, a, median, high_pass, band_pass, specular_mask, params)
    zones = {}
    for zone, zone_id in ZONE_IDS.items():
        mask = zone_map == zone_id
        if np.count_nonzero(mask) >= params.min_zone_pixels:
            zones[zone] = _score(mask, a, median, high_pass, band_pass, specular_mask, params)
    return SkinMetrics(overall, MappingProxyType(zones))


def _blend(previous: ZoneMetrics, current: ZoneMetrics, alpha: float) -> ZoneMetrics:
    return ZoneMetrics(**{
        field.name: (1 - alpha) * getattr(previous, field.name) + alpha * getattr(current, field.name)
        for field in fields(ZoneMetrics)
    })


class MetricsSmoother:
    """Fieldwise EMA retaining the most recent estimate for temporarily missing zones."""

    def __init__(self, alpha: float = 0.15) -> None:
        if not np.isfinite(alpha) or not 0 < alpha <= 1:
            raise ValueError("alpha must be finite and in (0, 1]")
        self._alpha = float(alpha)
        self._last: SkinMetrics | None = None

    def update(self, metrics: SkinMetrics | None) -> SkinMetrics | None:
        if metrics is None:
            return self._copy_last()
        if not isinstance(metrics, SkinMetrics):
            raise ValueError("metrics must be SkinMetrics or None")
        for score in (metrics.overall, *metrics.zones.values()):
            if not isinstance(score, ZoneMetrics) or any(
                not np.isfinite(getattr(score, f.name)) or not 0 <= getattr(score, f.name) <= 100
                for f in fields(ZoneMetrics)
            ):
                raise ValueError("metrics scores must be finite and in [0, 100]")
        if any(not isinstance(zone, FaceZone) for zone in metrics.zones):
            raise ValueError("metrics zones must be FaceZone keys")
        previous = self._last
        overall = metrics.overall if previous is None else _blend(previous.overall, metrics.overall, self._alpha)
        zones = {} if previous is None else dict(previous.zones)
        for zone, score in metrics.zones.items():
            zones[zone] = _blend(zones[zone], score, self._alpha) if zone in zones else score
        self._last = SkinMetrics(overall, MappingProxyType(zones))
        return self._copy_last()

    def _copy_last(self) -> SkinMetrics | None:
        if self._last is None:
            return None
        return SkinMetrics(_blend(self._last.overall, self._last.overall, 1.0), MappingProxyType({
            zone: _blend(score, score, 1.0) for zone, score in self._last.zones.items()
        }))

    def reset(self) -> None:
        self._last = None
