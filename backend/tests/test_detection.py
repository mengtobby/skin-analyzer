from pathlib import Path

import numpy as np
import pytest

from skin_analyzer.detection import ClassicalDetector, DetectorInput, create_detector
from skin_analyzer.detection.classical import ClassicalParams
from skin_analyzer.detection.onnx_yolo import (
    decode_yolov8_seg,
    letterbox,
    parse_class_names,
    select_providers,
)
from skin_analyzer.domain import DetectionClass, FaceZone
from skin_analyzer.face import build_face_region, refine_zone_map, warp_to_canvas
from skin_analyzer.preprocessing import CpuPreprocessor
from tests.synthetic_face import canonical_landmarks, place, render_face

pytestmark = pytest.mark.unit

SCALE, ORIGIN = 200.0, (640.0, 280.0)
LANDMARKS = place(canonical_landmarks(), SCALE, 0.0, ORIGIN)


def _img_pt(u, v):
    return (ORIGIN[0] + u * SCALE, ORIGIN[1] + v * SCALE)


def _input(img):
    region = build_face_region(LANDMARKS, mirrored=True)
    pre = CpuPreprocessor().process(warp_to_canvas(img, region), wb_gains=(1, 1, 1))
    zone_map = refine_zone_map(region.zone_map, pre.lab)
    return DetectorInput(img, region, pre.bgr, pre.lab, zone_map, pre.specular_mask)


def _near(dets, pt, tol=12.0):
    return [d for d in dets if np.hypot(d.center[0] - pt[0], d.center[1] - pt[1]) < tol]


def test_detects_inflammatory_lesion_on_cheek():
    cheek = _img_pt(-0.5, 0.55)
    img = render_face(LANDMARKS, lesions=[(*cheek, 7.0)])
    dets = ClassicalDetector().detect(_input(img))
    hits = _near(dets, cheek)
    inflam = {DetectionClass.PAPULE, DetectionClass.PUSTULE, DetectionClass.RED_MARK}
    assert any(d.label in inflam for d in hits), dets
    lesion = next(d for d in hits if d.label in inflam)
    assert lesion.zone is FaceZone.LEFT_CHEEK
    assert lesion.features["peak_delta_a"] > 8
    assert 3 < lesion.features["diameter_mm"] < 9
    assert len(lesion.contour) >= 3


def test_detects_hyperpigmentation_spot():
    spot = _img_pt(0.15, -0.55)
    img = render_face(LANDMARKS, dark_spots=[(*spot, 8.0)])
    dets = ClassicalDetector().detect(_input(img))
    hits = [d for d in _near(dets, spot) if d.label is DetectionClass.HYPERPIGMENTATION]
    assert hits and hits[0].zone is FaceZone.FOREHEAD


def test_clean_face_has_no_lesions():
    img = render_face(LANDMARKS, seed=5)
    dets = ClassicalDetector().detect(_input(img))
    lesion_like = {DetectionClass.PAPULE, DetectionClass.PUSTULE,
                   DetectionClass.RED_MARK, DetectionClass.HYPERPIGMENTATION}
    assert not [d for d in dets if d.label in lesion_like]


def test_enabled_classes_filter_output():
    cheek = _img_pt(-0.5, 0.55)
    img = render_face(LANDMARKS, lesions=[(*cheek, 7.0)])
    params = ClassicalParams(enabled=frozenset({DetectionClass.HYPERPIGMENTATION}))
    dets = ClassicalDetector(params).detect(_input(img))
    assert all(d.label is DetectionClass.HYPERPIGMENTATION for d in dets)


def test_select_providers_prefers_gpu():
    assert select_providers(["CPUExecutionProvider", "DmlExecutionProvider"]) == [
        "DmlExecutionProvider", "CPUExecutionProvider"]
    assert select_providers(["CUDAExecutionProvider", "TensorrtExecutionProvider",
                             "CPUExecutionProvider"])[0] == "TensorrtExecutionProvider"
    assert select_providers([]) == ["CPUExecutionProvider"]


def test_decode_yolov8_seg_tensors():
    nc, nm, n, size = 2, 4, 6, 64
    pred = np.zeros((1, 4 + nc + nm, n), np.float32)
    pred[0, :4, 0] = (20, 20, 10, 10)  # box 0: class 1, strong
    pred[0, 4 + 1, 0] = 0.9
    pred[0, :4, 1] = (21, 20, 10, 10)  # overlapping duplicate, weaker -> NMS
    pred[0, 4 + 1, 1] = 0.6
    pred[0, :4, 2] = (50, 50, 8, 8)  # below threshold
    pred[0, 4 + 0, 2] = 0.1
    pred[0, 4 + nc, :] = 5.0  # mask coeff on proto 0
    protos = np.zeros((1, nm, 16, 16), np.float32)
    protos[0, 0] = 1.0
    out = decode_yolov8_seg(pred, protos, nc, size, conf_thr=0.35)
    assert len(out) == 1
    inst = out[0]
    assert inst.class_id == 1 and inst.score == pytest.approx(0.9)
    ys, xs = np.nonzero(inst.mask)
    assert xs.min() >= 14 and xs.max() <= 26 and ys.min() >= 14 and ys.max() <= 26


def test_letterbox_and_class_names():
    img = np.zeros((100, 200, 3), np.uint8)
    out, r, (left, top) = letterbox(img, 64)
    assert out.shape == (64, 64, 3) and r == pytest.approx(0.32) and left == 0 and top == 16
    assert parse_class_names({"names": "{0: 'papules', 1: 'pustules'}"}) == {
        0: "papules", 1: "pustules"}
    assert parse_class_names({"names": "not python"}) == {}


def test_create_detector_falls_back_without_model(tmp_path: Path):
    det = create_detector("auto", tmp_path / "missing.onnx")
    assert det.name == "classical-cielab"
    with pytest.raises(FileNotFoundError):
        create_detector("onnx", tmp_path / "missing.onnx")
    with pytest.raises(ValueError):
        create_detector("magic")


def test_hysteresis_keeps_soft_edged_spot_at_true_extent():
    from skin_analyzer.detection.classical import hysteresis

    strong = np.zeros((20, 20), bool)
    weak = np.zeros((20, 20), bool)
    weak[5:12, 5:12] = True  # true extent of a soft-edged spot
    strong[8, 8] = True  # only its core passes the strict threshold
    weak[15:18, 15:18] = True  # weak-only noise blob without a seed
    kept = hysteresis(strong, weak)
    assert kept[5:12, 5:12].all()
    assert not kept[15:18, 15:18].any()
    assert kept.sum() == 49


def test_detects_soft_low_contrast_pigment_spot():
    from dataclasses import replace as dc_replace

    inp = _input(render_face(LANDMARKS, seed=7))
    cx, cy = inp.region.image_to_canvas_pts(np.array([_img_pt(-0.45, 0.5)]))[0]
    yy, xx = np.mgrid[0:inp.canvas_lab.shape[0], 0:inp.canvas_lab.shape[1]]
    sigma = 2.5 * (160 / 90) / 1.5  # 2.5 mm radius soft-edged spot on the canvas
    g = np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * sigma**2)).astype(np.float32)
    lab = inp.canvas_lab.copy()
    lab[..., 0] -= 9.0 * g
    lab[..., 2] += 2.7 * g
    params = ClassicalParams()
    dets = ClassicalDetector(params).detect(dc_replace(inp, canvas_lab=lab))
    spot = inp.region.canvas_to_image(np.array([[cx, cy]]))[0]
    hits = [d for d in _near(dets, spot) if d.label is DetectionClass.HYPERPIGMENTATION]
    assert hits, dets


def _spot_context(strength):
    from skin_analyzer.detection.classical import _Ctx

    inp = _input(render_face(LANDMARKS, seed=7))
    zeros = np.zeros_like(strength)
    return _Ctx(inp, inp.region.canvas.px_per_unit, inp.zone_map > 0,
                -strength, strength, zeros, 1.0, 1.0)


def test_bridged_red_lesions_use_each_peaks_half_maximum():
    inp = _input(render_face(LANDMARKS, seed=7))
    shape = inp.canvas_lab.shape[:2]
    cx, cy = inp.region.image_to_canvas_pts(np.array([_img_pt(-0.45, 0.5)]))[0].astype(int)
    strength = np.zeros(shape, np.float32)
    strength[cy - 2:cy + 3, cx - 12:cx + 13] = 3.0
    strength[cy - 3:cy + 4, cx - 12:cx - 5] = 11.0
    strength[cy - 1:cy + 2, cx - 10:cx - 7] = 24.0
    strength[cy - 3:cy + 4, cx + 6:cx + 13] = 6.0
    strength[cy - 1:cy + 2, cx + 8:cx + 11] = 10.0
    dets = ClassicalDetector()._inflammatory(_spot_context(strength))
    assert len(dets) == 2
    by_peak = sorted(dets, key=lambda d: d.features["peak_delta_a"])
    assert by_peak[0].features["peak_delta_a"] == pytest.approx(10.0)
    assert by_peak[1].features["peak_delta_a"] == pytest.approx(24.0)
    assert by_peak[0].area_px > by_peak[1].area_px


def test_diffuse_red_area_with_tiny_peak_is_not_a_spot():
    inp = _input(render_face(LANDMARKS, seed=7))
    yy, xx = np.indices(inp.canvas_lab.shape[:2])
    cx, cy = inp.region.image_to_canvas_pts(np.array([_img_pt(-0.45, 0.5)]))[0]
    strength = np.zeros(xx.shape, np.float32)
    strength[(xx - cx) ** 2 + (yy - cy) ** 2 < (0.2 * inp.region.canvas.px_per_unit) ** 2] = 5.9
    strength[(xx - cx) ** 2 + (yy - cy) ** 2 < 3 ** 2] = 12.0
    assert ClassicalDetector()._inflammatory(_spot_context(strength)) == []


@pytest.mark.parametrize("dark", [False, True])
def test_morphology_split_fragment_requires_its_own_seed(dark):
    inp = _input(render_face(LANDMARKS, seed=7))
    cx, cy = inp.region.image_to_canvas_pts(np.array([_img_pt(-0.45, 0.5)]))[0].astype(int)
    strength = np.zeros(inp.canvas_lab.shape[:2], np.float32)
    strength[cy - 3:cy + 4, cx - 14:cx - 7] = 10.0
    strength[cy, cx - 7:cx + 7] = 4.0  # opening removes this narrow bridge
    strength[cy - 4:cy + 5, cx + 7:cx + 16] = 4.0
    ctx = _spot_context(strength)
    detector = ClassicalDetector()
    if dark:
        from dataclasses import replace

        ctx = replace(ctx, da=np.zeros_like(strength))
        dets = detector._pigmentation(ctx)
        assert all(-d.features["delta_l"] > detector.p.dark_floor for d in dets)
    else:
        dets = detector._inflammatory(ctx)
        assert all(d.features["peak_delta_a"] > detector.p.red_floor for d in dets)
    assert len(dets) == 1


def test_half_max_components_measure_weaker_piece_at_its_own_peak():
    strength = np.zeros((20, 40), np.float32)
    strength[8:11, 5:31] = 3.0
    strength[6:13, 5:12] = 11.0
    strength[8:11, 7:10] = 24.0
    strength[6:13, 24:31] = 6.0
    strength[8:11, 26:29] = 10.0
    pieces = list(ClassicalDetector()._half_max_components(
        strength > 2.5, strength, 2.5, 5.0, (0.02, 0.10), 160.0
    ))
    assert len(pieces) == 2
    assert sorted(int(comp.sum()) for comp, _, _, _ in pieces) == [9, 49]
    for comp, sl, _, diameter in pieces:
        peak = strength[sl][comp].max()
        assert peak > 5.0
        assert (strength[sl][comp] >= peak / 2).all()
        assert diameter == pytest.approx(2 * np.sqrt(comp.sum() / np.pi) / 160)


@pytest.mark.parametrize("four_connected_owners", [False, True])
def test_diagonal_core_chains_keep_each_peaks_full_half_maximum(monkeypatch, four_connected_owners):
    import cv2

    transform = cv2.distanceTransformWithLabels

    def distance_with_four_connected_components(src, distance_type, mask_size, *, labelType):
        distance, owners = transform(src, distance_type, mask_size, labelType=cv2.DIST_LABEL_PIXEL)
        if labelType == cv2.DIST_LABEL_CCOMP:
            _, parts = cv2.connectedComponents((src == 0).astype(np.uint8), connectivity=4)
            lookup = np.zeros(int(owners.max()) + 1, dtype=parts.dtype)
            lookup[owners[src == 0]] = parts[src == 0]
            owners = lookup[owners]
        return distance, owners

    if four_connected_owners:
        # Exercise ownership when OpenCV's component connectivity differs from our cores.
        monkeypatch.setattr(cv2, "distanceTransformWithLabels", distance_with_four_connected_components)
    strength = np.zeros((20, 40), np.float32)
    strength[8:11, 5:31] = 3.0  # weak bridge joins two separately seeded cores
    strength[5:8, 5:8] = 14.0
    strength[8:11, 8:11] = 14.0  # touches the first block only diagonally
    strength[6, 6] = 24.0
    strength[8:11, 24:27] = 6.0
    strength[11:14, 27:30] = 6.0  # second core also has a diagonal-only link
    strength[9, 25] = 10.0
    pieces = list(ClassicalDetector()._half_max_components(
        strength > 2.5, strength, 2.5, 5.0, (0.02, 0.10), 160.0
    ))
    assert len(pieces) == 2
    for comp, sl, _, diameter in pieces:
        values = strength[sl]
        peak = float(values[comp].max())
        expected = (values >= 12.0) if peak > 20 else ((values >= 5.0) & (values < 12.0))
        np.testing.assert_array_equal(comp, expected)
        assert comp.sum() == 18
        assert peak == pytest.approx(24.0 if peak > 20 else 10.0)
        assert diameter == pytest.approx(2 * np.sqrt(18 / np.pi) / 160)
