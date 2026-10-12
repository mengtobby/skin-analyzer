"""Detector contract and the per-frame input bundle every detector receives."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import cv2
import numpy as np

from ..domain import ZONE_BY_ID, BBox, Detection, DetectionClass, FaceRegion, FaceZone, Point

MM_PER_UNIT = 90.0  # mean adult outer-canthal width; converts canonical units to ~mm


@dataclass(frozen=True)
class DetectorInput:
    frame_bgr: np.ndarray  # full camera frame (for learned detectors)
    region: FaceRegion
    canvas_bgr: np.ndarray  # white-balanced, glare-suppressed canvas
    canvas_lab: np.ndarray  # float32 CIELAB canvas
    zone_map: np.ndarray  # refined canvas zone map (0 = not skin)
    specular_mask: np.ndarray  # canvas bool


class Detector(Protocol):
    name: str

    def detect(self, inp: DetectorInput) -> list[Detection]: ...


def component_to_detection(
    comp_mask: np.ndarray,
    offset: tuple[int, int],
    label: DetectionClass,
    confidence: float,
    zone_map_crop: np.ndarray,
    region: FaceRegion,
    features: dict[str, float],
) -> Detection | None:
    """Convert a canvas-space component mask (cropped at ``offset``) to an image Detection."""
    contours, _ = cv2.findContours(
        comp_mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    if not contours:
        return None
    contour = max(contours, key=len)
    approx = cv2.approxPolyDP(contour, 1.0, True).reshape(-1, 2).astype(np.float64)
    if len(approx) < 3:
        approx = contour.reshape(-1, 2).astype(np.float64)
    approx += np.asarray(offset, dtype=np.float64)
    img_pts = region.canvas_to_image(approx)
    x0, y0 = img_pts.min(axis=0)
    x1, y1 = img_pts.max(axis=0)
    bbox: BBox = (float(x0), float(y0), float(max(x1 - x0, 1.0)), float(max(y1 - y0, 1.0)))
    zone_ids = zone_map_crop[comp_mask & (zone_map_crop > 0)]
    zone = FaceZone.OTHER
    if zone_ids.size:
        zone = ZONE_BY_ID.get(int(np.bincount(zone_ids).argmax()), FaceZone.OTHER)
    scale = (region.frame.scale / region.canvas.px_per_unit) ** 2
    contour_pts: tuple[Point, ...] = tuple((float(x), float(y)) for x, y in img_pts)
    return Detection(
        label=label,
        bbox=bbox,
        confidence=float(np.clip(confidence, 0.0, 1.0)),
        contour=contour_pts,
        area_px=float(comp_mask.sum() * scale),
        zone=zone,
        features=features,
    )
