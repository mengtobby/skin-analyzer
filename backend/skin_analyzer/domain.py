"""Core domain types shared across the vision pipeline, API and knowledge layers."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping

import numpy as np

Point = tuple[float, float]
BBox = tuple[float, float, float, float]  # x, y, w, h in image pixels


class FaceZone(str, Enum):
    FOREHEAD = "forehead"
    NOSE = "nose"
    LEFT_CHEEK = "left_cheek"
    RIGHT_CHEEK = "right_cheek"
    CHIN = "chin"
    OTHER = "other"


# Integer ids used inside zone label maps (0 = not skin / excluded).
ZONE_IDS: Mapping[FaceZone, int] = {
    FaceZone.FOREHEAD: 1,
    FaceZone.NOSE: 2,
    FaceZone.LEFT_CHEEK: 3,
    FaceZone.RIGHT_CHEEK: 4,
    FaceZone.CHIN: 5,
    FaceZone.OTHER: 6,
}
ZONE_BY_ID: Mapping[int, FaceZone] = {v: k for k, v in ZONE_IDS.items()}


class DetectionClass(str, Enum):
    PAPULE = "papule"
    PUSTULE = "pustule"
    RED_MARK = "red_mark"  # flat post-inflammatory erythema
    DIFFUSE_REDNESS = "diffuse_redness"
    HYPERPIGMENTATION = "hyperpigmentation"
    TEXTURE = "texture_irregularity"
    FINE_LINES = "fine_lines"
    COMEDONE = "comedone"  # learned-model only (blackheads / whiteheads)
    NODULE = "nodule"  # learned-model only


@dataclass(frozen=True)
class Detection:
    """A single skin feature found in one frame (image pixel coordinates)."""

    label: DetectionClass
    bbox: BBox
    confidence: float
    contour: tuple[Point, ...]
    area_px: float
    zone: FaceZone = FaceZone.OTHER
    features: Mapping[str, float] = field(default_factory=dict)

    @property
    def center(self) -> Point:
        x, y, w, h = self.bbox
        return (x + w / 2.0, y + h / 2.0)


@dataclass(frozen=True)
class Track:
    """A temporally stable skin feature (output of the tracker, image px for display)."""

    track_id: int
    label: DetectionClass  # majority vote over the track's history
    confidence: float  # smoothed
    bbox: BBox
    contour: tuple[Point, ...]
    zone: FaceZone
    canonical_center: Point  # (u, v) in the canonical face frame
    size_mm: float
    age: int  # frames since the track was created
    hits: int  # frames with a matched detection
    misses: int  # consecutive frames without a match
    confirmed: bool


@dataclass(frozen=True)
class ZoneMetrics:
    """Heuristic 0-100 scores (higher = more of that property). Not clinically calibrated."""

    redness: float
    texture: float
    oiliness: float
    pigmentation: float


@dataclass(frozen=True)
class SkinMetrics:
    overall: ZoneMetrics
    zones: Mapping[FaceZone, ZoneMetrics]


@dataclass(frozen=True)
class FaceFrame:
    """Similarity transform between image pixels and a canonical face frame.

    Canonical frame: origin at the midpoint between the outer eye corners, +u along
    the eye line (towards image-right eye), +v downwards, unit = inter-ocular distance.
    Lesions are (nearly) static in this frame, which makes tracking robust to head motion.
    """

    origin: np.ndarray  # (2,) image px
    axis_u: np.ndarray  # (2,) unit vector
    axis_v: np.ndarray  # (2,) unit vector
    scale: float  # inter-ocular distance in px

    def to_canonical(self, pts: np.ndarray) -> np.ndarray:
        d = np.asarray(pts, dtype=np.float64).reshape(-1, 2) - self.origin
        return np.stack([d @ self.axis_u, d @ self.axis_v], axis=1) / self.scale

    def to_image(self, pts: np.ndarray) -> np.ndarray:
        c = np.asarray(pts, dtype=np.float64).reshape(-1, 2) * self.scale
        return self.origin + c[:, :1] * self.axis_u + c[:, 1:2] * self.axis_v


@dataclass(frozen=True)
class CanvasSpec:
    """Fixed-size, roll-corrected analysis canvas laid over the canonical face frame."""

    u_range: tuple[float, float] = (-1.0, 1.0)
    v_range: tuple[float, float] = (-1.0, 1.6)
    px_per_unit: float = 160.0

    @property
    def size(self) -> tuple[int, int]:  # (width, height)
        w = round((self.u_range[1] - self.u_range[0]) * self.px_per_unit)
        h = round((self.v_range[1] - self.v_range[0]) * self.px_per_unit)
        return (int(w), int(h))

    def canonical_to_canvas(self, uv: np.ndarray) -> np.ndarray:
        uv = np.asarray(uv, dtype=np.float64).reshape(-1, 2)
        offset = np.array([self.u_range[0], self.v_range[0]])
        return (uv - offset) * self.px_per_unit

    def canvas_to_canonical(self, xy: np.ndarray) -> np.ndarray:
        xy = np.asarray(xy, dtype=np.float64).reshape(-1, 2)
        offset = np.array([self.u_range[0], self.v_range[0]])
        return xy / self.px_per_unit + offset


@dataclass(frozen=True)
class FaceRegion:
    """Everything downstream stages need to know about the face in one frame."""

    landmarks: np.ndarray  # (N, 2) image px
    frame: FaceFrame
    canvas: CanvasSpec
    image_to_canvas: np.ndarray  # (2, 3) affine for cv2.warpAffine
    zone_map: np.ndarray  # (H, W) uint8 ZONE_IDS on the canvas, 0 = excluded
    zone_polygons: Mapping[FaceZone, tuple[Point, ...]]  # image px, for display

    @property
    def skin_mask(self) -> np.ndarray:
        return self.zone_map > 0

    def canvas_to_image(self, xy: np.ndarray) -> np.ndarray:
        return self.frame.to_image(self.canvas.canvas_to_canonical(xy))

    def image_to_canvas_pts(self, xy: np.ndarray) -> np.ndarray:
        return self.canvas.canonical_to_canvas(self.frame.to_canonical(xy))

    def zone_at_image_point(self, xy: Point) -> FaceZone:
        cx, cy = self.image_to_canvas_pts(np.array(xy))[0]
        h, w = self.zone_map.shape
        ix, iy = int(round(cx)), int(round(cy))
        if not (0 <= ix < w and 0 <= iy < h):
            return FaceZone.OTHER
        return ZONE_BY_ID.get(int(self.zone_map[iy, ix]), FaceZone.OTHER)
