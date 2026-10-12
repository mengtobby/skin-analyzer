"""Image preprocessing backends (white balance, glare suppression, CIELAB)."""

from __future__ import annotations

import logging

from .base import Gains, PreprocessResult, Preprocessor, SpecularParams
from .cpu import CpuPreprocessor

logger = logging.getLogger(__name__)

__all__ = [
    "CpuPreprocessor",
    "Gains",
    "PreprocessResult",
    "Preprocessor",
    "SpecularParams",
    "create_preprocessor",
]


def create_preprocessor(backend: str = "auto") -> Preprocessor:
    """Build a preprocessing backend: ``auto`` prefers CUDA and falls back to CPU."""
    if backend not in {"auto", "cpu", "cuda"}:
        raise ValueError(f"Unknown preprocessing backend: {backend!r}")
    if backend in {"auto", "cuda"}:
        from .cuda import CudaPreprocessor, cuda_available

        if cuda_available():
            return CudaPreprocessor()
        if backend == "cuda":
            raise RuntimeError("CUDA preprocessing requested but CUDA is unavailable")
        logger.info("CUDA not available; using CPU preprocessing backend")
    return CpuPreprocessor()
