"""Fetch the public MediaPipe face model atomically."""
from __future__ import annotations

import logging
import hashlib
import os
from pathlib import Path
import tempfile
import urllib.request

from .config import BACKEND

logger = logging.getLogger(__name__)
MODEL_URL = ("https://storage.googleapis.com/mediapipe-models/face_landmarker/"
             "face_landmarker/float16/1/face_landmarker.task")
EXPECTED_SHA256 = "64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff"
MAX_MODEL_BYTES = 20 * 1024 * 1024


def _valid_model(path: Path) -> bool:
    if path.stat().st_size > MAX_MODEL_BYTES:
        return False
    with path.open("rb") as model:
        return hashlib.file_digest(model, "sha256").hexdigest() == EXPECTED_SHA256


def ensure_models(models_dir: Path) -> Path:
    models_dir = Path(models_dir)
    target = models_dir / "face_landmarker.task"
    if target.is_file():
        if _valid_model(target):
            return target
        logger.warning("Existing face landmarker model failed SHA-256 verification: %s", target)
    temporary: Path | None = None
    try:
        models_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=models_dir, suffix=".tmp", delete=False) as output:
            temporary = Path(output.name)
            # Constant https URL; the payload is size-capped and SHA-256 verified below.
            with urllib.request.urlopen(MODEL_URL, timeout=60) as response:  # nosec B310
                while chunk := response.read(1024 * 1024):
                    if output.tell() + len(chunk) > MAX_MODEL_BYTES:
                        raise RuntimeError("Downloaded model exceeds 20 MB size limit")
                    output.write(chunk)
            if output.tell() == 0:
                raise RuntimeError("Downloaded model is empty")
        if not _valid_model(temporary):
            raise RuntimeError("Downloaded model SHA-256 mismatch")
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
