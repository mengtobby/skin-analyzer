"""One-Euro filter (Casiez et al., CHI 2012) vectorised over landmark arrays.

Low cutoff when the face is still (kills jitter), higher cutoff when it moves fast
(kills lag). Positions are normalised by face scale so tuning is resolution-independent.
"""

from __future__ import annotations

import math

import numpy as np


def _alpha(cutoff: np.ndarray | float, dt: float) -> np.ndarray | float:
    tau = 1.0 / (2.0 * math.pi * cutoff)
    return 1.0 / (1.0 + tau / dt)


class OneEuroFilter:
    def __init__(self, min_cutoff: float = 1.2, beta: float = 4.0, d_cutoff: float = 1.0) -> None:
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff
        self._x: np.ndarray | None = None
        self._dx: np.ndarray | None = None
        self._t: float | None = None

    def reset(self) -> None:
        self._x = self._dx = self._t = None

    def __call__(self, x: np.ndarray, t: float, scale: float = 1.0) -> np.ndarray:
        """Filter ``x`` (any shape) observed at time ``t`` seconds; returns a new array."""
        x = np.asarray(x, dtype=np.float64)
        if self._x is None or self._t is None or t <= self._t or self._x.shape != x.shape:
            self._x, self._dx, self._t = x.copy(), np.zeros_like(x), t
            return x.copy()
        dt = t - self._t
        dx = (x - self._x) / dt
        dx_hat = self._dx + _alpha(self.d_cutoff, dt) * (dx - self._dx)
        speed = np.abs(dx_hat) / max(scale, 1e-6)
        a = _alpha(self.min_cutoff + self.beta * speed, dt)
        x_hat = self._x + a * (x - self._x)
        self._x, self._dx, self._t = x_hat, dx_hat, t
        return x_hat.copy()
