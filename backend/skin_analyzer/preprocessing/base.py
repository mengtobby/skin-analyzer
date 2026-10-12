"""Preprocessing backend contract.

A backend takes a BGR uint8 image (usually the face ROI) and returns a white-balanced,
glare-suppressed image plus its CIELAB representation and a specular-highlight mask.
Backends are swappable (vectorised CPU, custom CUDA kernel, ...) behind this protocol.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np

Gains = tuple[float, float, float]  # per-channel multipliers in BGR order


@dataclass(frozen=True)
class SpecularParams:
    max_saturation: int = 70  # HSV S (0-255) above which a pixel is never glare
    abs_value: int = 235  # HSV V that is always glare when desaturated
    rel_value: int = 35  # V above local mean that counts as glare
    min_value: int = 150  # never call pixels darker than this glare
    local_window: int = 15


@dataclass(frozen=True)
class PreprocessResult:
    bgr: np.ndarray  # uint8 HxWx3, white balanced (+ glare suppressed)
    lab: np.ndarray  # float32 HxWx3, L in [0,100], a/b roughly [-128,127]
    specular_mask: np.ndarray  # bool HxW, glare pixels before suppression
    wb_gains: Gains


class Preprocessor(Protocol):
    name: str

    def estimate_gains(self, bgr: np.ndarray) -> Gains: ...

    def process(self, bgr: np.ndarray, wb_gains: Gains | None = None) -> PreprocessResult: ...
