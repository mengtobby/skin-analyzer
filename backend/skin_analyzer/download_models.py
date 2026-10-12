"""Fetch the public MediaPipe face model atomically."""
from __future__ import annotations

import logging
import os
from pathlib import Path
import tempfile
import urllib.request

from .config import BACKEND

logger = logging.getLogger(__name__)
MODEL_URL = ("https://storage.googleapis.com/mediapipe-models/face_landmarker/"
             "face_landmarker/float16/1/face_landmarker.task")


def ensure_models(models_dir: Path) -> Path:
    models_dir = Path(models_dir)
    target = models_dir / "face_landmarker.task"
    if target.is_file() and target.stat().st_size > 0:
        return target
    temporary: Path | None = None
    try:
        models_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=models_dir, suffix=".tmp", delete=False) as output:
            temporary = Path(output.name)
            with urllib.request.urlopen(MODEL_URL, timeout=60) as response:
                while chunk := response.read(1024 * 1024):
                    output.write(chunk)
            if output.tell() == 0:
                raise RuntimeError("Downloaded model is empty")
        os.replace(temporary, target)
    except Exception as exc:
        raise RuntimeError(f"Unable to download face landmarker model to {target}: {exc}") from exc
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    logger.info("Face landmarker model ready at %s", target)
    return target


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ensure_models(BACKEND / "models")
