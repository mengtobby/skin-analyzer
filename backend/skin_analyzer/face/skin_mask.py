"""Adaptive skin refinement: drop hair with a forehead margin, beard, glasses and shadows."""

from __future__ import annotations

import cv2
import numpy as np

from ..domain import ZONE_IDS, FaceZone


_NEIGHBOUR_SHIFTS = tuple(
    (dy, dx) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if (dy, dx) != (0, 0)
)


_KERNEL_3X3 = np.ones((3, 3), np.uint8)
_NO_LABEL = np.float32(2**24)  # above any label; float32 stays exact below 2**24


def _multi_ring_pairs(padded: np.ndarray, pixels: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """(component, pixel) pairs for ring pixels touching several components."""
    lookup = np.pad(padded, 1)
    width = lookup.shape[1]
    ys, xs = np.divmod(pixels, padded.shape[1])
    centre = (ys + 1) * width + (xs + 1)
    flat = lookup.ravel()
    neighbours = np.stack(
        [np.take(flat, centre + dy * width + dx) for dy, dx in _NEIGHBOUR_SHIFTS], axis=1
    )
    neighbours.sort(axis=1)
    first = np.ones(neighbours.shape, bool)  # count each component once per pixel
    first[:, 1:] = neighbours[:, 1:] != neighbours[:, :-1]
    rows, cols = np.nonzero(first & (neighbours > 0))
    return neighbours[rows, cols], pixels[rows]


def _ring_pairs(padded: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Every (component label, flat ring-pixel index) adjacency, each pair once.

    Max-dilation and min-erosion of the label image give each pixel's largest and
    smallest neighbouring label; where they agree the pixel touches exactly one
    component (the common case) and needs no per-pixel work.
    """
    as_float = padded.astype(np.float32)
    largest = cv2.dilate(as_float, _KERNEL_3X3).ravel()
    smallest = cv2.erode(np.where(padded > 0, as_float, _NO_LABEL), _KERNEL_3X3).ravel()
    ring = (padded.ravel() == 0) & (largest > 0)
    single = np.flatnonzero(ring & (largest == smallest))
    multi = np.flatnonzero(ring & (largest != smallest))
    multi_components, multi_pixels = _multi_ring_pairs(padded, multi)
    components = np.concatenate([largest[single].astype(np.int64), multi_components])
    return components, np.concatenate([single, multi_pixels])


def _enclosed_red_skin(
    accepted: np.ndarray, candidates: np.ndarray, skin: np.ndarray
) -> np.ndarray:
    """Restore components with at least 60% accepted skin on their non-neutral ring.

    Fully vectorised, so the cost does not grow with the number of red components
    (noisy or flushed skin can have thousands).
    """
    count, labels = cv2.connectedComponents(candidates.astype(np.uint8), connectivity=8)
    if count <= 1:
        return np.zeros(candidates.shape, bool)
    # Pad by one: outside the canvas counts as rejected skin (never neutral, never
    # accepted); only actual zone-zero pixels (oval and feature exclusions) are neutral.
    padded = np.pad(labels, 1)
    skin_p = np.pad(skin, 1, constant_values=True)
    accepted_p = np.pad(accepted, 1, constant_values=False)
    component, pixel = _ring_pairs(padded)
    in_skin = np.take(skin_p.ravel(), pixel)
    good = in_skin & np.take(accepted_p.ravel(), pixel)
    total = np.bincount(component, weights=in_skin, minlength=count)
    accepted_count = np.bincount(component, weights=good, minlength=count)
    restored = (total > 0) & (accepted_count >= 0.6 * total)
    restored[0] = False
    return restored[labels]


def _hair_margin(forehead: np.ndarray, hair: np.ndarray, radius: int) -> np.ndarray:
    """Euclidean margin around hair components touching the forehead's top edge.

    ``hair`` holds only dark or low-chroma rejections, so shine, b* shifts and red
    patches at the hairline never widen the excluded band.
    """
    rejected = forehead & hair
    if not rejected.any():
        return np.zeros(forehead.shape, bool)
    _, labels = cv2.connectedComponents(rejected.astype(np.uint8), connectivity=8)
    above = np.zeros_like(forehead)
    above[1:] = forehead[:-1]
    boundary_labels = np.unique(labels[forehead & ~above])
    fringe = np.isin(labels, boundary_labels[boundary_labels != 0])
    if not fringe.any():
        return np.zeros(forehead.shape, bool)
    distance = cv2.distanceTransform((~fringe).astype(np.uint8), cv2.DIST_L2, cv2.DIST_MASK_PRECISE)
    return forehead & (distance <= radius)


def refine_zone_map(
    zone_map: np.ndarray,
    lab: np.ndarray,
    max_dark: float = 18.0,
    max_bright: float = 25.0,
    max_da: float = 22.0,
    max_db: float = 18.0,
    *,
    hair_margin_px: int = 8,
) -> np.ndarray:
    """Zero out zone pixels whose colour is far from this face's own median skin colour.

    Use the pooled cheeks when they contain at least 300 pixels, otherwise all
    zone pixels. This adapts to skin tone without letting a large hair fringe
    dominate the reference. Low-chroma pixels are rejected relative to that skin.
    Red components mostly bordered by accepted skin are retained as possible lesions.
    Dark or low-chroma (hair) rejections touching the forehead's upper boundary
    get a surrounding margin.
    """
    if isinstance(hair_margin_px, bool) or not isinstance(hair_margin_px, int) or hair_margin_px < 0:
        raise ValueError("Hair margin must be a non-negative integer")
    if zone_map.ndim != 2 or lab.shape != (*zone_map.shape, 3):
        raise ValueError("Lab canvas must match the two-dimensional zone map")
    if not np.isfinite(lab).all():
        raise ValueError("Lab canvas must contain finite values")
    if not all(np.isfinite(v) and v > 0 for v in (max_dark, max_bright, max_da, max_db)):
        raise ValueError("Colour tolerances must be finite and positive")
    skin = zone_map > 0
    if not skin.any():
        return zone_map.copy()
    cheeks = np.isin(zone_map, [ZONE_IDS[FaceZone.LEFT_CHEEK], ZONE_IDS[FaceZone.RIGHT_CHEEK]])
    ref = np.median(lab[cheeks if cheeks.sum() >= 300 else skin], axis=0)
    d = lab - ref
    # White balancing can make the skin reference effectively achromatic. In
    # that case a relative chroma cutoff separates numerical noise, not hair.
    ref_chroma = np.hypot(ref[1], ref[2])
    dark = d[..., 0] <= -max_dark
    low_chroma = (ref_chroma >= 1.0) & (np.hypot(lab[..., 1], lab[..., 2]) < 0.35 * ref_chroma)
    colour_ok = ~dark & (d[..., 0] < max_bright) & (np.abs(d[..., 2]) < max_db) & ~low_chroma
    ok = skin & colour_ok & (np.abs(d[..., 1]) < max_da)
    red = skin & colour_ok & (d[..., 1] >= max_da)
    if red.any():
        ok |= _enclosed_red_skin(ok, red, skin)
    if hair_margin_px > 0:
        hair = skin & ~ok & (dark | low_chroma)
        ok &= ~_hair_margin(zone_map == ZONE_IDS[FaceZone.FOREHEAD], hair, hair_margin_px)
    return np.where(ok, zone_map, 0).astype(zone_map.dtype)
