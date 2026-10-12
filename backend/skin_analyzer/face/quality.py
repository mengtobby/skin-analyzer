"""Capture suitability using skin colour and approximate landmark-based pose."""

from __future__ import annotations

from dataclasses import dataclass, fields

import numpy as np

from ..domain import ZONE_IDS, FaceRegion, FaceZone
from .landmark_spec import NOSE_TIP


@dataclass(frozen=True)
class QualityParams:
    min_brightness: float = 35.0
    max_brightness: float = 88.0
    max_evenness: float = 14.0
    min_face_size_px: float = 80.0
    max_yaw_deg: float = 25.0
    max_pitch_deg: float = 22.0
    min_skin_coverage: float = 0.6
    min_zone_pixels: int = 150
    nose_yaw_scale: float = 0.45
    frontal_nose_v: float = 0.60
    nose_pitch_scale: float = 0.9

    def __post_init__(self) -> None:
        if not all(np.isfinite(getattr(self, f.name)) and getattr(self, f.name) > 0
                   for f in fields(self)):
            raise ValueError("Quality parameters must be finite and positive")
        if self.min_brightness >= self.max_brightness or self.min_skin_coverage > 1:
            raise ValueError("Invalid brightness range or coverage threshold")
        if int(self.min_zone_pixels) != self.min_zone_pixels:
            raise ValueError("Minimum zone pixels must be an integer")


@dataclass(frozen=True)
class QualityReport:
    ok: bool
    score: float
    issues: tuple[str, ...]
    brightness: float
    evenness: float
    face_size_px: float
    yaw_deg: float
    pitch_deg: float
    skin_coverage: float


def _evenness(lab: np.ndarray, zones: np.ndarray, minimum: int) -> float:
    differences = [0.0]
    for first, second in ((FaceZone.LEFT_CHEEK, FaceZone.RIGHT_CHEEK),
                          (FaceZone.FOREHEAD, FaceZone.CHIN)):
        a, b = zones == ZONE_IDS[first], zones == ZONE_IDS[second]
        if a.sum() >= minimum and b.sum() >= minimum:
            differences.append(abs(float(np.median(lab[a, 0]) - np.median(lab[b, 0]))))
    return max(differences)


def assess_quality(
    region: FaceRegion, canvas_lab: np.ndarray, zone_map: np.ndarray,
    params: QualityParams | None = None,
) -> QualityReport:
    """Assess refined skin; region.zone_map supplies the unrefined coverage denominator.

    Yaw from nose u and pitch from nose v are heuristic approximations, not a
    calibrated 3D head-pose estimate. Empty skin fails darkness and coverage.
    Soft margins are clipped measurement/threshold ratios (inverse for maxima).
    """
    p = params or QualityParams()
    if zone_map.ndim != 2 or canvas_lab.shape != (*zone_map.shape, 3):
        raise ValueError("Lab canvas must match the two-dimensional zone map")
    if region.zone_map.shape != zone_map.shape or not np.isfinite(canvas_lab).all():
        raise ValueError("Invalid region shape or nonfinite Lab canvas")
    if not np.isfinite(region.frame.scale) or region.frame.scale <= 0:
        raise ValueError("Face scale must be finite and positive")
    nose = region.frame.to_canonical(region.landmarks)[NOSE_TIP]
    if not np.isfinite(nose).all():
        raise ValueError("Nose landmark must be finite")
    skin = (zone_map > 0) & (region.zone_map > 0)
    zones = np.where(skin, zone_map, 0)
    brightness = float(np.median(canvas_lab[skin, 0])) if skin.any() else 0.0
    evenness = _evenness(canvas_lab, zones, p.min_zone_pixels)
    coverage = float(skin.sum() / max(1, np.count_nonzero(region.zone_map)))
    yaw = float(np.degrees(np.arcsin(np.clip(nose[0] / p.nose_yaw_scale, -1, 1))))
    pitch = float(np.degrees(np.arctan((nose[1] - p.frontal_nose_v) / p.nose_pitch_scale)))
    checks = (
        ("too_dark", brightness, p.min_brightness, True),
        ("too_bright", brightness, p.max_brightness, False),
        ("uneven_light", evenness, p.max_evenness, False),
        ("too_far", float(region.frame.scale), p.min_face_size_px, True),
        ("turned_away", abs(yaw), p.max_yaw_deg, False),
        ("tilted", abs(pitch), p.max_pitch_deg, False),
        ("occluded", coverage, p.min_skin_coverage, True),
    )
    issues = tuple(code for code, value, limit, lower in checks
                   if (value < limit if lower else value > limit))
    margins = [np.clip(value / limit if lower else limit / max(value, limit), 0, 1)
               for _, value, limit, lower in checks]
    return QualityReport(not issues, float(np.prod(margins)), issues, brightness,
                         evenness, float(region.frame.scale), yaw, pitch, coverage)
