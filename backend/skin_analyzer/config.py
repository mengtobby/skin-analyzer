"""Validated runtime configuration."""
from __future__ import annotations

import math
import os
from dataclasses import dataclass, field
from pathlib import Path

from .user_settings import default_settings_path

BACKEND = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Settings:
    source: str = "camera:0"
    settings_file: Path = field(default_factory=default_settings_path)
    width: int = 1280
    height: int = 720
    fps: int = 30
    mirror: bool = True
    preprocess: str = "auto"
    detector: str = "auto"
    landmarker_model: Path = BACKEND / "models/face_landmarker.task"
    detector_model: Path = BACKEND / "models/skin_yolov8_seg.onnx"
    jpeg_quality: int = 75
    report_interval_s: float = 1.0
    host: str = "127.0.0.1"
    port: int = 8000
    extra_origins: tuple[str, ...] = ()
    static_dir: Path = BACKEND.parent / "frontend/dist"

    def __post_init__(self) -> None:
        if not self.source.strip() or not self.host.strip():
            raise ValueError("source and host must be nonempty")
        if any(type(v) is not int or v <= 0 for v in (self.width, self.height, self.fps)):
            raise ValueError("width, height and fps must be positive integers")
        if type(self.port) is not int or not 1 <= self.port <= 65535:
            raise ValueError("port must be between 1 and 65535")
        if self.detector not in {"auto", "classical", "onnx"}:
            raise ValueError("invalid detector")
        if self.preprocess not in {"auto", "cpu", "cuda"}:
            raise ValueError("invalid preprocessor")
        if type(self.mirror) is not bool:
            raise ValueError("mirror must be boolean")
        if type(self.jpeg_quality) is not int or not 1 <= self.jpeg_quality <= 100:
            raise ValueError("jpeg_quality must be between 1 and 100")
        if not math.isfinite(self.report_interval_s) or self.report_interval_s <= 0:
            raise ValueError("report_interval_s must be finite and positive")

    @classmethod
    def from_env(cls) -> Settings:
        values = {}
        converters = {
            "settings_file": Path, "source": str, "host": str, "detector": str, "preprocess": str,
            "port": int, "width": int, "height": int, "fps": int,
            "jpeg_quality": int, "report_interval_s": float,
            "extra_origins": lambda raw: tuple(x.strip() for x in raw.split(",") if x.strip()),
        }
        for key, convert in converters.items():
            variable = f"SKIN_{key.upper()}"
            if variable not in os.environ:
                continue
            try:
                value = convert(os.environ[variable])
                cls(**{key: value})
            except (ValueError, TypeError) as exc:
                raise ValueError(f"invalid {variable}: {exc}") from exc
            values[key] = value
        if "SKIN_MIRROR" in os.environ:
            raw = os.environ["SKIN_MIRROR"].lower()
            if raw not in {"true", "false", "1", "0", "yes", "no"}:
                raise ValueError("invalid SKIN_MIRROR")
            values["mirror"] = raw in {"true", "1", "yes"}
        return cls(**values)
