"""Synthetic 478-point landmarks and a matching rendered 'face' for camera-free tests."""

from __future__ import annotations

import math

import cv2
import numpy as np

from skin_analyzer.face import landmark_spec as spec


def _ellipse(n: int, cu: float, cv: float, ru: float, rv: float) -> np.ndarray:
    t = np.linspace(0, 2 * math.pi, n, endpoint=False)
    return np.stack([cu + ru * np.cos(t), cv + rv * np.sin(t)], axis=1)


def canonical_landmarks() -> np.ndarray:
    """Plausible frontal-face landmarks in canonical units (eye-corner distance = 1)."""
    c = np.zeros((spec.NUM_LANDMARKS, 2))
    c[list(spec.FACE_OVAL)] = _ellipse(len(spec.FACE_OVAL), 0.0, 0.3, 0.85, 1.15)
    c[list(spec.RIGHT_EYE)] = _ellipse(len(spec.RIGHT_EYE), -0.32, 0.0, 0.18, 0.07)
    c[list(spec.LEFT_EYE)] = _ellipse(len(spec.LEFT_EYE), 0.32, 0.0, 0.18, 0.07)
    c[list(spec.RIGHT_EYEBROW)] = _ellipse(len(spec.RIGHT_EYEBROW), -0.32, -0.22, 0.22, 0.04)
    c[list(spec.LEFT_EYEBROW)] = _ellipse(len(spec.LEFT_EYEBROW), 0.32, -0.22, 0.22, 0.04)
    c[list(spec.LIPS)] = _ellipse(len(spec.LIPS), 0.0, 0.95, 0.28, 0.1)
    c[list(spec.NOSE)] = _ellipse(len(spec.NOSE), 0.0, 0.35, 0.17, 0.33)
    c[spec.RIGHT_EYE_OUTER] = (-0.5, 0.0)
    c[spec.LEFT_EYE_OUTER] = (0.5, 0.0)
    c[spec.RIGHT_EYE_INNER] = (-0.14, 0.0)
    c[spec.LEFT_EYE_INNER] = (0.14, 0.0)
    c[spec.NOSE_TIP] = (0.0, 0.6)
    c[spec.MOUTH_RIGHT] = (-0.28, 0.95)
    c[spec.MOUTH_LEFT] = (0.28, 0.95)
    c[spec.LOWER_LIP_BOTTOM] = (0.0, 1.05)
    c[spec.CHIN] = (0.0, 1.45)
    return c


def place(canon: np.ndarray, scale: float, angle_deg: float, origin: tuple[float, float]):
    a = math.radians(angle_deg)
    rot = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
    return canon @ rot.T * scale + np.asarray(origin)


SKIN_BGR = (150, 170, 215)


def render_face(
    landmarks: np.ndarray,
    size: tuple[int, int] = (720, 1280),
    lesions: list[tuple[float, float, float]] | None = None,
    dark_spots: list[tuple[float, float, float]] | None = None,
    seed: int = 0,
) -> np.ndarray:
    """Draw a skin-coloured face with smooth Gaussian red lesions / brown spots.

    ``lesions`` / ``dark_spots`` are (x, y, radius) in image pixels.
    """
    h, w = size
    rng = np.random.default_rng(seed)
    img = np.full((h, w, 3), (60, 70, 80), np.float32)
    hull = cv2.convexHull(np.round(landmarks[list(spec.FACE_OVAL)]).astype(np.int32))
    cv2.fillConvexPoly(img, hull, SKIN_BGR)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    for x, y, r in lesions or []:
        g = np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2 * (r / 1.5) ** 2))[..., None]
        img = img * (1 - 0.55 * g) + np.array((80, 70, 225), np.float32) * 0.55 * g
    for x, y, r in dark_spots or []:
        g = np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2 * (r / 1.5) ** 2))[..., None]
        img = img * (1 - 0.5 * g) + np.array((85, 110, 150), np.float32) * 0.5 * g
    for idx in (spec.LEFT_EYE, spec.RIGHT_EYE):
        eye = cv2.convexHull(np.round(landmarks[list(idx)]).astype(np.int32))
        cv2.fillConvexPoly(img, eye, (240, 240, 240))
    img += rng.normal(0, 1.5, img.shape).astype(np.float32)
    return np.clip(img, 0, 255).astype(np.uint8)
