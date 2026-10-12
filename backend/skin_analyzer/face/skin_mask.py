"""Adaptive skin refinement: drop hair, beard, glasses frames and deep shadow pixels."""

from __future__ import annotations

import numpy as np


def refine_zone_map(
    zone_map: np.ndarray,
    lab: np.ndarray,
    max_dark: float = 28.0,
    max_bright: float = 30.0,
    max_da: float = 28.0,
    max_db: float = 22.0,
) -> np.ndarray:
    """Zero out zone pixels whose colour is far from this face's own median skin colour.

    The reference is taken per frame from the face itself, so it adapts to any skin
    tone and lighting rather than relying on a fixed (and biased) skin-colour gamut.
    """
    skin = zone_map > 0
    if skin.sum() < 200:
        return zone_map
    ref = np.median(lab[skin], axis=0)
    d = lab - ref
    ok = (
        (d[..., 0] > -max_dark)
        & (d[..., 0] < max_bright)
        & (np.abs(d[..., 1]) < max_da)
        & (np.abs(d[..., 2]) < max_db)
    )
    return np.where(ok, zone_map, 0).astype(zone_map.dtype)
