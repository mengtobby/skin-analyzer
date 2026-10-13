import numpy as np
import pytest

from skin_analyzer.preprocessing import create_preprocessor
from skin_analyzer.preprocessing.cpu import CpuPreprocessor, estimate_wb_gains, suppress_specular


def _tinted_scene(tint=(0.8, 1.0, 1.25), seed=0):
    """Neutral gray/white scene viewed under a coloured illuminant (BGR gains)."""
    rng = np.random.default_rng(seed)
    base = rng.uniform(60, 200, size=(120, 160, 1)).astype(np.float32)
    base[:10, :10] = 235  # white patch
    scene = np.repeat(base, 3, axis=2) * np.array(tint, dtype=np.float32)
    return np.clip(scene, 0, 255).astype(np.uint8)


@pytest.mark.unit
def test_wb_gains_neutralise_colour_cast():
    img = _tinted_scene()
    gains = estimate_wb_gains(img)
    corrected = img.astype(np.float32) * np.array(gains, dtype=np.float32)
    means = corrected[10:, 10:].reshape(-1, 3).mean(axis=0)
    assert np.ptp(means) / means.mean() < 0.05


@pytest.mark.unit
def test_wb_gains_are_clamped():
    img = np.zeros((50, 50, 3), np.uint8)
    img[..., 2] = 200  # pure red frame: unbounded correction would explode
    img[..., 1] = 5
    img[..., 0] = 5
    gains = estimate_wb_gains(img, max_gain=1.5)
    assert max(gains) / min(gains) <= 1.5 / (1 / 1.5) + 1e-6
    assert all(1 / 1.5 - 1e-6 <= g <= 1.5 + 1e-6 for g in gains)


@pytest.mark.unit
def test_specular_mask_finds_glare_and_is_suppressed():
    img = np.full((100, 100, 3), (120, 140, 190), np.uint8)  # skin-ish BGR
    img[40:50, 40:50] = (252, 252, 252)  # glare spot
    result = CpuPreprocessor().process(img, wb_gains=(1.0, 1.0, 1.0))
    assert result.specular_mask[45, 45]
    assert not result.specular_mask[10, 10]
    assert result.specular_mask.sum() >= 100
    # inpainted glare should now be close to the surrounding skin colour
    diff = np.abs(result.bgr[45, 45].astype(int) - np.array([120, 140, 190]))
    assert diff.max() < 30


@pytest.mark.unit
def test_lab_conversion_is_cielab_scaled():
    img = np.zeros((4, 4, 3), np.uint8)
    img[0, 0] = (255, 255, 255)
    img[0, 1] = (0, 0, 255)  # pure red in BGR
    result = CpuPreprocessor(suppress_specular=False).process(img, wb_gains=(1, 1, 1))
    lab = result.lab
    assert lab.dtype == np.float32
    assert lab[0, 0, 0] == pytest.approx(100, abs=0.5)
    assert abs(lab[0, 0, 1]) < 0.5 and abs(lab[0, 0, 2]) < 0.5
    # sRGB red: L*~53.2, a*~80.1, b*~67.2
    assert lab[0, 1] == pytest.approx([53.2, 80.1, 67.2], abs=1.0)
    assert lab[1, 1, 0] == pytest.approx(0, abs=0.5)


@pytest.mark.unit
def test_process_does_not_mutate_input():
    img = _tinted_scene()
    before = img.copy()
    CpuPreprocessor().process(img)
    np.testing.assert_array_equal(img, before)


@pytest.mark.unit
def test_factory_falls_back_to_cpu_when_cuda_missing():
    pre = create_preprocessor("auto")
    assert pre.name in {"cpu", "cuda"}
    with pytest.raises(ValueError):
        create_preprocessor("bogus")


@pytest.mark.unit
def test_cuda_matches_cpu_when_available():
    cuda = pytest.importorskip("skin_analyzer.preprocessing.cuda")
    if not cuda.cuda_available():
        pytest.skip("CUDA device not available")
    img = _tinted_scene(seed=3)
    gains = (1.1, 1.0, 0.9)
    cpu_res = CpuPreprocessor(suppress_specular=False).process(img, wb_gains=gains)
    gpu_res = cuda.CudaPreprocessor(suppress_specular=False).process(img, wb_gains=gains)
    np.testing.assert_allclose(gpu_res.lab, cpu_res.lab, atol=1.0)
    assert (gpu_res.specular_mask != cpu_res.specular_mask).mean() < 0.001


def _bright_background_scene():
    image = np.full((416, 320, 3), 255, np.uint8)
    roi = np.zeros(image.shape[:2], bool)
    roi[80:330, 70:250] = True
    image[roi] = (120, 140, 190)
    image[170:176, 150:156] = 252
    return image, roi


@pytest.mark.parametrize("suppress", [True, False])
def test_roi_excludes_background_glare(suppress):
    image, roi = _bright_background_scene()
    before = image.copy()
    result = CpuPreprocessor(suppress_specular=suppress).process(
        image, wb_gains=(1, 1, 1), roi_mask=roi
    )
    assert result.specular_mask[172, 152]
    assert not result.specular_mask[~roi].any()
    np.testing.assert_array_equal(result.bgr[~roi], image[~roi])
    np.testing.assert_array_equal(image, before)


def test_roi_clips_inpainting_dilation():
    image = np.full((40, 40, 3), (120, 140, 190), np.uint8)
    roi = np.zeros((40, 40), bool)
    roi[10:30, 10:30] = True
    image[10:13, 10:13] = 252
    result = CpuPreprocessor().process(image, wb_gains=(1, 1, 1), roi_mask=roi)
    np.testing.assert_array_equal(result.bgr[~roi], image[~roi])


@pytest.mark.parametrize("roi", [np.zeros((4, 4), bool), np.zeros((8, 8), np.uint8)])
def test_invalid_roi_is_rejected(roi):
    with pytest.raises(ValueError, match="roi_mask"):
        CpuPreprocessor().process(np.zeros((8, 8, 3), np.uint8), roi_mask=roi)


def test_empty_roi_reports_no_glare():
    image = np.full((40, 40, 3), 255, np.uint8)
    result = CpuPreprocessor().process(
        image, wb_gains=(1, 1, 1), roi_mask=np.zeros((40, 40), bool)
    )
    assert not result.specular_mask.any()
    np.testing.assert_array_equal(result.bgr, image)


def test_suppress_specular_with_glare_outside_roi_returns_input():
    image = np.full((40, 40, 3), (120, 140, 190), np.uint8)
    image[2:5, 2:5] = 252
    mask = np.zeros((40, 40), bool)
    mask[2:5, 2:5] = True
    roi = np.zeros((40, 40), bool)
    roi[10:30, 10:30] = True
    before = image.copy()
    result = suppress_specular(image, mask, roi)
    assert result is image
    np.testing.assert_array_equal(image, before)


@pytest.mark.parametrize("seed", [0, 3, 9])
def test_subsampled_wb_matches_full_resolution(seed):
    rng = np.random.default_rng(seed)
    neutral = rng.uniform(60, 235, (416, 320, 1))
    image = np.clip(neutral * np.array([0.8, 1.0, 1.15]), 0, 255).astype(np.uint8)
    pixels = image.reshape(-1, 3)
    pixels = pixels[(pixels < 250).all(axis=1)]
    full = np.percentile(pixels, 97, axis=0)
    expected = np.clip(full[1] / np.maximum(full, 1), 1 / 1.5, 1.5)
    np.testing.assert_allclose(estimate_wb_gains(image), expected, rtol=0.01)


def test_roi_preprocessing_timing():
    from time import perf_counter

    image, roi = _bright_background_scene()
    preprocessor = CpuPreprocessor()

    def best_of(run, repeats: int = 7) -> float:
        run()
        timings = []
        for _ in range(repeats):
            start = perf_counter()
            run()
            timings.append(perf_counter() - start)
        return min(timings)

    with_roi = best_of(lambda: preprocessor.process(image, roi_mask=roi))
    without_roi = best_of(lambda: preprocessor.process(image))
    # Relative bound (independent of machine load): restricting glare inpainting to the
    # face must avoid the costly background inpaint (~11x measured).
    assert with_roi * 4 < without_roi
