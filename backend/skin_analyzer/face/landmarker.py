"""MediaPipe Face Landmarker wrapper (478 landmarks, VIDEO mode with internal tracking)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Protocol

import numpy as np

logger = logging.getLogger(__name__)


class Landmarker(Protocol):
    def detect(self, bgr: np.ndarray, timestamp_ms: int) -> np.ndarray | None:
        """Return (478, 2) landmark pixel coordinates or ``None`` when no face is found."""
        ...

    def close(self) -> None: ...


class MediaPipeLandmarker:
    def __init__(self, model_path: Path, min_confidence: float = 0.5) -> None:
        if not model_path.is_file():
            raise FileNotFoundError(
                f"Face landmarker model not found at {model_path}. "
                "Run `python -m skin_analyzer.download_models`."
            )
        import mediapipe as mp
        from mediapipe.tasks.python import BaseOptions
        from mediapipe.tasks.python import vision

        self._mp = mp
        options = vision.FaceLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(model_path)),
            running_mode=vision.RunningMode.VIDEO,
            num_faces=1,
            min_face_detection_confidence=min_confidence,
            min_face_presence_confidence=min_confidence,
            min_tracking_confidence=min_confidence,
        )
        self._landmarker = vision.FaceLandmarker.create_from_options(options)
        self._last_ts = -1

    def detect(self, bgr: np.ndarray, timestamp_ms: int) -> np.ndarray | None:
        ts = max(int(timestamp_ms), self._last_ts + 1)  # MediaPipe needs strictly increasing
        self._last_ts = ts
        rgb = np.ascontiguousarray(bgr[..., ::-1])
        image = self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=rgb)
        result = self._landmarker.detect_for_video(image, ts)
        if not result.face_landmarks:
            return None
        h, w = bgr.shape[:2]
        pts = result.face_landmarks[0]
        return np.array([(p.x * w, p.y * h) for p in pts], dtype=np.float64)

    def close(self) -> None:
        self._landmarker.close()
