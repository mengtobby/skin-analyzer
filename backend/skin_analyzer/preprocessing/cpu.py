"""Vectorised CPU preprocessing backend (NumPy + OpenCV SIMD kernels)."""

from __future__ import annotations

import cv2
import numpy as np

from .base import Gains, PreprocessResult, SpecularParams

_CLIP_LEVEL = 250


def estimate_wb_gains(
    bgr: np.ndarray, percentile: float = 97.0, max_gain: float = 1.5
) -> Gains:
    """Robust white-patch estimate of illuminant-correcting gains (green-normalised).

    Under the dichromatic reflection model the brightest non-clipped reflections carry
    the illuminant colour, so a high percentile per channel estimates it. Gains are
    clamped so a strongly coloured scene (e.g. a face filling the frame) is never
    "corrected" into grey.
    """
    pixels = bgr.reshape(-1, 3)
    unclipped = pixels[(pixels < _CLIP_LEVEL).all(axis=1)]
    if len(unclipped) < 64:
        return (1.0, 1.0, 1.0)
    p = np.percentile(unclipped, percentile, axis=0).astype(np.float64)
    p = np.maximum(p, 1.0)
    gains = np.clip(p[1] / p, 1.0 / max_gain, max_gain)
    return (float(gains[0]), float(gains[1]), float(gains[2]))


def apply_gains(bgr: np.ndarray, gains: Gains) -> np.ndarray:
    scaled = bgr.astype(np.float32) * np.asarray(gains, dtype=np.float32)
    return np.clip(scaled + 0.5, 0, 255).astype(np.uint8)


def specular_mask_from_hsv(
    v: np.ndarray, s: np.ndarray, v_local: np.ndarray, params: SpecularParams
) -> np.ndarray:
    v = v.astype(np.float32)
    bright = (v >= params.abs_value) | (
        (v - v_local >= params.rel_value) & (v >= params.min_value)
    )
    return bright & (s <= params.max_saturation)


def bgr_to_lab(bgr: np.ndarray) -> np.ndarray:
    """sRGB (gamma-encoded) uint8 BGR -> CIELAB float32 (D65)."""
    return cv2.cvtColor(bgr.astype(np.float32) / 255.0, cv2.COLOR_BGR2Lab)


def suppress_specular(bgr: np.ndarray, mask: np.ndarray) -> np.ndarray:
    if not mask.any():
        return bgr
    grown = cv2.dilate(mask.astype(np.uint8), np.ones((3, 3), np.uint8))
    return cv2.inpaint(bgr, grown, 3, cv2.INPAINT_TELEA)


class CpuPreprocessor:
    name = "cpu"

    def __init__(
        self,
        suppress_specular: bool = True,
        specular: SpecularParams | None = None,
    ) -> None:
        self._suppress = suppress_specular
        self._specular = specular or SpecularParams()

    def estimate_gains(self, bgr: np.ndarray) -> Gains:
        return estimate_wb_gains(bgr)

    def process(self, bgr: np.ndarray, wb_gains: Gains | None = None) -> PreprocessResult:
        gains = wb_gains if wb_gains is not None else self.estimate_gains(bgr)
        balanced = apply_gains(bgr, gains)
        hsv = cv2.cvtColor(balanced, cv2.COLOR_BGR2HSV)
        v = hsv[..., 2]
        win = self._specular.local_window
        v_local = cv2.blur(v.astype(np.float32), (win, win))
        mask = specular_mask_from_hsv(v, hsv[..., 1], v_local, self._specular)
        cleaned = suppress_specular(balanced, mask) if self._suppress else balanced
        return PreprocessResult(
            bgr=cleaned, lab=bgr_to_lab(cleaned), specular_mask=mask, wb_gains=gains
        )
