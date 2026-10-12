"""Adaptive skin refinement: drop hair, beard, glasses frames and deep shadow pixels."""

from __future__ import annotations

import cv2
import numpy as np

from ..domain import ZONE_IDS, FaceZone


def _enclosed_red_skin(accepted: np.ndarray, candidates: np.ndarray) -> np.ndarray:
    """Retain red lesion centres only when surrounded by accepted skin.

    Flood the complement from every canvas edge using padding. Any remaining
    hole is enclosed skin; non-red exclusions are barriers to restoration.
    """
    exterior = np.pad((~accepted).astype(np.uint8), 1, constant_values=1)
    cv2.floodFill(exterior, None, (0, 0), 2, flags=8)
    holes = exterior[1:-1, 1:-1] == 1
    count, labels = cv2.connectedComponents(holes.astype(np.uint8), connectivity=8)
    invalid = np.bincount(labels[holes & ~candidates], minlength=count) > 0
    invalid[0] = True
    return holes & ~invalid[labels]


def refine_zone_map(
    zone_map: np.ndarray,
    lab: np.ndarray,
    max_dark: float = 18.0,
    max_bright: float = 25.0,
    max_da: float = 22.0,
    max_db: float = 18.0,
) -> np.ndarray:
    """Zero out zone pixels whose colour is far from this face's own median skin colour.

    Use the pooled cheeks when they contain at least 300 pixels, otherwise all
    zone pixels. This adapts to skin tone without letting a large hair fringe
    dominate the reference. Low-chroma pixels are rejected relative to that skin.
    Red-only holes enclosed by accepted skin are retained as possible lesions.
    """
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
    colour_ok = (
        (d[..., 0] > -max_dark)
        & (d[..., 0] < max_bright)
        & (np.abs(d[..., 2]) < max_db)
        & ((ref_chroma < 1.0) | (np.hypot(lab[..., 1], lab[..., 2]) >= 0.35 * ref_chroma))
    )
    ok = skin & colour_ok & (np.abs(d[..., 1]) < max_da)
    red = skin & colour_ok & (d[..., 1] >= max_da)
    if red.any():
        ok |= _enclosed_red_skin(ok, red)
    return np.where(ok, zone_map, 0).astype(zone_map.dtype)
