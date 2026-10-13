"""Landmarks -> canonical face frame, analysis canvas and anatomical zone map."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import cv2
import numpy as np

from ..domain import ZONE_BY_ID, ZONE_IDS, CanvasSpec, FaceFrame, FaceRegion, FaceZone, Point
from . import landmark_spec as spec


@dataclass(frozen=True)
class ZoneParams:
    oval_erode: float = 0.04  # canonical units
    eye_margin: float = 0.10
    brow_margin: float = 0.07
    lip_margin: float = 0.06
    nostril_margin: float = 0.05
    sidewall_inner: float = 0.06  # nasal sidewall band, inside the nose half-width
    sidewall_outer: float = 0.10  # ... and outside it (nasofacial groove)
    nasal_root_radius: float = 0.09
    forehead_gap: float = 0.04
    cheek_eye_gap: float = 0.08
    nose_side_gap: float = 0.03
    min_nose_half_width: float = 0.16
    polygon_epsilon_px: float = 2.0


def face_frame_from_landmarks(landmarks: np.ndarray) -> FaceFrame:
    """Canonical frame from the outer eye corners (left-to-right in the image)."""
    a = landmarks[spec.RIGHT_EYE_OUTER].astype(np.float64)
    b = landmarks[spec.LEFT_EYE_OUTER].astype(np.float64)
    if a[0] > b[0]:
        a, b = b, a
    d = b - a
    scale = float(np.linalg.norm(d))
    if scale < 1e-6:
        raise ValueError("Degenerate landmarks: eye corners coincide")
    axis_u = d / scale
    axis_v = np.array([-axis_u[1], axis_u[0]])
    return FaceFrame(origin=(a + b) / 2.0, axis_u=axis_u, axis_v=axis_v, scale=scale)


def image_to_canvas_affine(frame: FaceFrame, canvas: CanvasSpec) -> np.ndarray:
    k = canvas.px_per_unit / frame.scale
    rot = np.stack([frame.axis_u, frame.axis_v]) * k
    offset = np.array([canvas.u_range[0], canvas.v_range[0]]) * canvas.px_per_unit
    t = -rot @ frame.origin - offset
    return np.hstack([rot, t[:, None]]).astype(np.float64)


def _hull_mask(shape: tuple[int, int], pts: np.ndarray, grow_px: float) -> np.ndarray:
    mask = np.zeros(shape, np.uint8)
    hull = cv2.convexHull(np.round(pts).astype(np.int32))
    cv2.fillConvexPoly(mask, hull, 1)
    r = int(round(grow_px))
    if r > 0:
        cv2.polylines(mask, [hull], True, 1, thickness=2 * r + 1, lineType=cv2.LINE_8)
    elif r < 0:
        # The filled boundary already occupies one pixel; omit it from the inset.
        cv2.polylines(mask, [hull], True, 0, thickness=max(1, -2 * r - 2), lineType=cv2.LINE_8)
    return mask.astype(bool)



@lru_cache(maxsize=16)
def _canonical_grids(canvas: CanvasSpec) -> tuple[np.ndarray, np.ndarray]:
    """Reuse immutable pixel-centre coordinates for each analysis canvas."""
    w, h = canvas.size
    us = (np.arange(w) + 0.5) / canvas.px_per_unit + canvas.u_range[0]
    vs = (np.arange(h) + 0.5) / canvas.px_per_unit + canvas.v_range[0]
    u, v = np.meshgrid(us, vs)
    u.setflags(write=False)
    v.setflags(write=False)
    return u, v


def _span(lo: float, hi: float, origin: float, ppu: float, n: int) -> slice:
    """Pixel indices whose centres (i + 0.5) / ppu + origin lie in [lo, hi]."""
    first = int(np.ceil((lo - origin) * ppu - 0.5))
    last = int(np.floor((hi - origin) * ppu - 0.5))
    return slice(max(first, 0), max(min(last + 1, n), 0))


def shading_mask(
    canvas: CanvasSpec, canon: np.ndarray, params: ZoneParams = ZoneParams()
) -> np.ndarray:
    """Anatomy that frontal light always shades: nasal sidewalls, nasofacial grooves and
    the nasal root between the inner eye corners.

    Measured on real webcam frames, these mirror-symmetric shadows were the dominant
    false 'pigmented spots' after the nostrils; real pigment does not come in mirrored
    pairs at fixed anatomical positions. The canvas is axis-aligned with the canonical
    frame, so the sidewall bands are plain slices and only the small root disk needs
    per-pixel work.
    """
    w, h = canvas.size
    ppu, (u0, v0) = canvas.px_per_unit, (canvas.u_range[0], canvas.v_range[0])
    nose_u = canon[list(spec.NOSE), 0]
    nose_c = canon[spec.NOSE_TIP, 0]
    half = max(params.min_nose_half_width, (nose_u.max() - nose_u.min()) / 2)
    eye_inner = canon[[spec.LEFT_EYE_INNER, spec.RIGHT_EYE_INNER]].mean(axis=0)
    rows = _span(eye_inner[1] + 0.05, canon[list(spec.NOSE), 1].max(), v0, ppu, h)
    mask = np.zeros((h, w), bool)
    for lo, hi in ((nose_c - half - params.sidewall_outer, nose_c - half + params.sidewall_inner),
                   (nose_c + half - params.sidewall_inner, nose_c + half + params.sidewall_outer)):
        mask[rows, _span(lo, hi, u0, ppu, w)] = True
    r = params.nasal_root_radius
    box_rows = _span(eye_inner[1] - r, eye_inner[1] + r, v0, ppu, h)
    box_cols = _span(eye_inner[0] - r, eye_inner[0] + r, u0, ppu, w)
    u, v = _canonical_grids(canvas)
    du, dv = u[box_rows, box_cols] - eye_inner[0], v[box_rows, box_cols] - eye_inner[1]
    mask[box_rows, box_cols] |= du * du + dv * dv <= r * r
    return mask


def build_zone_map(
    canon: np.ndarray, canvas: CanvasSpec, mirrored: bool, params: ZoneParams = ZoneParams()
) -> np.ndarray:
    """Label every canvas pixel with a ZONE_IDS value (0 = not analysable skin)."""
    w, h = canvas.size
    ppu = canvas.px_per_unit
    pts = canvas.canonical_to_canvas(canon)
    sel = lambda idx: pts[list(idx)]  # noqa: E731
    vsel = lambda idx: canon[list(idx), 1]  # noqa: E731

    skin = _hull_mask((h, w), sel(spec.FACE_OVAL), -params.oval_erode * ppu)
    for idx, margin in (
        (spec.LEFT_EYE, params.eye_margin),
        (spec.RIGHT_EYE, params.eye_margin),
        (spec.LEFT_EYEBROW, params.brow_margin),
        (spec.RIGHT_EYEBROW, params.brow_margin),
        (spec.LIPS, params.lip_margin),
        (spec.NOSTRILS, params.nostril_margin),
    ):
        skin &= ~_hull_mask((h, w), sel(idx), margin * ppu)

    u, v = _canonical_grids(canvas)

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
        zone[mask] = ZONE_IDS[z]
    zone[~skin | shading_mask(canvas, canon, params)] = 0
    return zone


def zone_polygons(
    zone_map: np.ndarray, to_image, epsilon_px: float
) -> dict[FaceZone, tuple[Point, ...]]:
    polys: dict[FaceZone, tuple[Point, ...]] = {}
    for zid, zone in ZONE_BY_ID.items():
        if zone is FaceZone.OTHER:
            continue
        mask = (zone_map == zid).astype(np.uint8)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            continue
        largest = max(contours, key=cv2.contourArea)
        if cv2.contourArea(largest) < 50:
            continue
        approx = cv2.approxPolyDP(largest, epsilon_px, True).reshape(-1, 2)
        img_pts = to_image(approx.astype(np.float64))
        polys[zone] = tuple((float(x), float(y)) for x, y in img_pts)
    return polys


def build_face_region(
    landmarks: np.ndarray,
    canvas: CanvasSpec = CanvasSpec(),
    mirrored: bool = True,
    params: ZoneParams = ZoneParams(),
) -> FaceRegion:
    frame = face_frame_from_landmarks(landmarks)
    canon = frame.to_canonical(landmarks)
    zone_map = build_zone_map(canon, canvas, mirrored, params)

    def to_image(xy: np.ndarray) -> np.ndarray:
        return frame.to_image(canvas.canvas_to_canonical(xy))

    return FaceRegion(
        landmarks=landmarks,
        frame=frame,
        canvas=canvas,
        image_to_canvas=image_to_canvas_affine(frame, canvas),
        zone_map=zone_map,
        zone_polygons=zone_polygons(zone_map, to_image, params.polygon_epsilon_px),
    )


def warp_to_canvas(image: np.ndarray, region: FaceRegion) -> np.ndarray:
    return cv2.warpAffine(
        image,
        region.image_to_canvas,
        region.canvas.size,
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_REPLICATE,
    )
