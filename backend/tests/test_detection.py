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
    params = ClassicalParams(dark_k=4.0, dark_floor=7.0, pigment_diam_units=(0.03, 0.20))
    dets = ClassicalDetector(params).detect(dc_replace(inp, canvas_lab=lab))
    spot = inp.region.canvas_to_image(np.array([[cx, cy]]))[0]
    hits = [d for d in _near(dets, spot) if d.label is DetectionClass.HYPERPIGMENTATION]
    assert hits, dets
