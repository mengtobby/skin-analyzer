"""CUDA preprocessing backend: one fused kernel for white balance, HSV and CIELAB.

Requires CuPy (``pip install cupy-cuda12x``) and an NVIDIA GPU. Glare inpainting has
no GPU equivalent here, so only the (usually tiny) glare bounding box is inpainted on
the CPU. ``create_preprocessor("auto")`` silently falls back to the CPU backend when
this module cannot run.
"""

from __future__ import annotations

import numpy as np

from .base import Gains, PreprocessResult, SpecularParams
from .cpu import estimate_wb_gains, specular_mask_from_hsv, suppress_specular

try:  # pragma: no cover - exercised only on CUDA machines
    import cupy as cp
    from cupyx.scipy import ndimage as cnd
except Exception:  # noqa: BLE001 - any import failure means "no CUDA"
    cp = None
    cnd = None

_KERNEL_SRC = r"""
__device__ __forceinline__ float srgb_to_linear(float c) {
    return c <= 0.04045f ? c / 12.92f : powf((c + 0.055f) / 1.055f, 2.4f);
}
__device__ __forceinline__ float lab_f(float t) {
    return t > 0.008856f ? cbrtf(t) : 7.787f * t + 16.0f / 116.0f;
}
extern "C" __global__
void wb_lab_hsv(const unsigned char* bgr, const float* gains, unsigned char* out_bgr,
                float* lab, float* v_out, float* s_out, int n) {
    int i = blockDim.x * blockIdx.x + threadIdx.x;
    if (i >= n) return;
    float c[3];
    for (int k = 0; k < 3; ++k) {
        float x = fminf(floorf(bgr[3 * i + k] * gains[k] + 0.5f), 255.0f);
        out_bgr[3 * i + k] = (unsigned char)x;
        c[k] = x / 255.0f;
    }
    float b = c[0], g = c[1], r = c[2];
    float mx = fmaxf(r, fmaxf(g, b));
    float mn = fminf(r, fminf(g, b));
    v_out[i] = mx * 255.0f;
    s_out[i] = mx > 0.0f ? (mx - mn) / mx * 255.0f : 0.0f;
    float R = srgb_to_linear(r), G = srgb_to_linear(g), B = srgb_to_linear(b);
    float X = (0.412453f * R + 0.357580f * G + 0.180423f * B) / 0.950456f;
    float Y = 0.212671f * R + 0.715160f * G + 0.072169f * B;
    float Z = (0.019334f * R + 0.119193f * G + 0.950227f * B) / 1.088754f;
    float fy = lab_f(Y);
    lab[3 * i + 0] = Y > 0.008856f ? 116.0f * fy - 16.0f : 903.3f * Y;
    lab[3 * i + 1] = 500.0f * (lab_f(X) - fy);
    lab[3 * i + 2] = 200.0f * (fy - lab_f(Z));
}
"""


def cuda_available() -> bool:
    if cp is None:
        return False
    try:  # pragma: no cover
        return cp.cuda.runtime.getDeviceCount() > 0
    except Exception:  # noqa: BLE001
        return False


class CudaPreprocessor:  # pragma: no cover - requires NVIDIA hardware
    name = "cuda"

    def __init__(
        self, suppress_specular: bool = True, specular: SpecularParams | None = None
    ) -> None:
        if not cuda_available():
            raise RuntimeError("CUDA backend requested but no CUDA device/CuPy found")
        self._kernel = cp.RawKernel(_KERNEL_SRC, "wb_lab_hsv")
        self._suppress = suppress_specular
        self._specular = specular or SpecularParams()

    def estimate_gains(self, bgr: np.ndarray) -> Gains:
        return estimate_wb_gains(bgr)

    def process(self, bgr: np.ndarray, wb_gains: Gains | None = None) -> PreprocessResult:
        gains = wb_gains if wb_gains is not None else self.estimate_gains(bgr)
        h, w = bgr.shape[:2]
        n = h * w
        d_in = cp.asarray(np.ascontiguousarray(bgr))
        d_gains = cp.asarray(np.asarray(gains, dtype=np.float32))
        d_bgr = cp.empty_like(d_in)
        d_lab = cp.empty((h, w, 3), dtype=cp.float32)
        d_v = cp.empty((h, w), dtype=cp.float32)
        d_s = cp.empty((h, w), dtype=cp.float32)
        threads = 256
        blocks = (n + threads - 1) // threads
        self._kernel((blocks,), (threads,), (d_in, d_gains, d_bgr, d_lab, d_v, d_s, np.int32(n)))
        win = self._specular.local_window
        d_v_local = cnd.uniform_filter(d_v, size=win, mode="reflect")
        mask = specular_mask_from_hsv(
            cp.asnumpy(cp.rint(d_v)),
            cp.asnumpy(cp.rint(d_s)),
            cp.asnumpy(d_v_local),
            self._specular,
        )
        balanced = cp.asnumpy(d_bgr)
        lab = cp.asnumpy(d_lab)
        if self._suppress and mask.any():
            balanced = suppress_specular(balanced, mask)
            # Only the glare pixels changed; recompute their LAB on the CPU.
            from .cpu import bgr_to_lab

            lab = lab.copy()
            lab[mask] = bgr_to_lab(balanced[mask].reshape(-1, 1, 3)).reshape(-1, 3)
        return PreprocessResult(bgr=balanced, lab=lab, specular_mask=mask, wb_gains=gains)
