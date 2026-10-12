"""Skin feature detectors (classical CIELAB and learned YOLOv8-seg via ONNX Runtime)."""

from __future__ import annotations

import logging
from pathlib import Path

from ..domain import Detection, DetectionClass
from .base import Detector, DetectorInput
from .classical import ClassicalDetector, ClassicalParams

logger = logging.getLogger(__name__)

LEARNED_CLASSES = frozenset({
    DetectionClass.PAPULE, DetectionClass.PUSTULE, DetectionClass.NODULE,
    DetectionClass.COMEDONE, DetectionClass.RED_MARK,
})

__all__ = ["ClassicalDetector", "CompositeDetector", "Detector", "DetectorInput",
           "create_detector"]


class CompositeDetector:
    """Runs several detectors and concatenates their outputs."""

    def __init__(self, detectors: list[Detector]) -> None:
        self.detectors = detectors
        self.name = "+".join(d.name for d in detectors)

    def detect(self, inp: DetectorInput) -> list[Detection]:
        return [det for d in self.detectors for det in d.detect(inp)]


def create_detector(kind: str = "auto", model_path: Path | None = None) -> Detector:
    """``auto``: YOLO-seg for lesions + classical for the rest when a model exists,
    otherwise the classical detector alone. ``classical`` / ``onnx`` force one."""
    if kind not in {"auto", "classical", "onnx"}:
        raise ValueError(f"Unknown detector: {kind!r}")
    has_model = model_path is not None and model_path.is_file()
    if kind == "onnx" and not has_model:
        raise FileNotFoundError(f"ONNX model not found: {model_path}")
    if kind == "classical" or not has_model:
        if kind == "auto":
            logger.info("No learned model at %s; using classical CIELAB detector", model_path)
        return ClassicalDetector()
    try:
        from .onnx_yolo import OnnxYoloSegDetector

        learned = OnnxYoloSegDetector(model_path)  # type: ignore[arg-type]
    except Exception:
        if kind == "onnx":
            raise
        logger.exception("Failed to load ONNX model; falling back to classical detector")
        return ClassicalDetector()
    rest = frozenset(DetectionClass) - LEARNED_CLASSES
    return CompositeDetector([learned, ClassicalDetector(ClassicalParams(enabled=rest))])
