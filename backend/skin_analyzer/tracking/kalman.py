"""Immutable constant-velocity Kalman states in canonical coordinates."""

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np


@dataclass(frozen=True)
class KalmanState:
    mean: tuple[float, float, float, float]
    covariance: tuple[tuple[float, ...], ...]
    timestamp: float


def _state(mean: np.ndarray, covariance: np.ndarray, timestamp: float) -> KalmanState:
    return KalmanState(tuple(float(x) for x in mean),
                       tuple(tuple(float(x) for x in row) for row in covariance), timestamp)


def initialize(center: tuple[float, float], timestamp: float,
               measurement_noise: float) -> KalmanState:
    return _state(np.array([*center, 0.0, 0.0]),
                  np.diag([measurement_noise, measurement_noise, 1e-4, 1e-4]), timestamp)


def predict(state: KalmanState, timestamp: float, process_noise: float) -> KalmanState:
    if not math.isfinite(timestamp) or not math.isfinite(process_noise) or process_noise < 0:
        raise ValueError("Timestamp must be finite and process noise nonnegative")
    dt = float(np.clip(timestamp - state.timestamp, 1 / 120, 0.5))
    transition = np.eye(4)
    transition[0, 2] = transition[1, 3] = dt
    acceleration = np.array([[dt * dt / 2, 0], [0, dt * dt / 2], [dt, 0], [0, dt]])
    covariance = transition @ np.asarray(state.covariance) @ transition.T
    covariance += process_noise * acceleration @ acceleration.T
    return _state(transition @ np.asarray(state.mean), covariance, timestamp)


def update(state: KalmanState, center: tuple[float, float],
           measurement_noise: float) -> KalmanState:
    if not np.isfinite(center).all() or not math.isfinite(measurement_noise) or measurement_noise <= 0:
        raise ValueError("Center must be finite and measurement noise positive")
    covariance = np.asarray(state.covariance)
    observation = np.eye(2, 4)
    noise = np.eye(2) * measurement_noise
    gain = np.linalg.solve(covariance[:2, :2] + noise, covariance[:2, :]).T
    mean = np.asarray(state.mean) + gain @ (np.asarray(center) - np.asarray(state.mean[:2]))
    residual = np.eye(4) - gain @ observation
    covariance = residual @ covariance @ residual.T + gain @ noise @ gain.T
    return _state(mean, covariance, state.timestamp)
