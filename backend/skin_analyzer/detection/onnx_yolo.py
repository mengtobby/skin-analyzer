"""YOLOv8-seg detector served by ONNX Runtime with hardware-aware execution providers.

Drop a model exported with ``yolo export model=best.pt format=onnx`` (see
``tools/train_yolo_seg.py``) into ``backend/models/skin_yolov8_seg.onnx``. Class names are
read from the model metadata (Ultralytics stores them) and mapped onto DetectionClass.
"""

from __future__ import annotations

import ast
import logging
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from ..domain import Detection, DetectionClass
from .base import DetectorInput

logger = logging.getLogger(__name__)

PROVIDER_PREFERENCE = (
    "TensorrtExecutionProvider",
    "CUDAExecutionProvider",
    "DmlExecutionProvider",
    "OpenVINOExecutionProvider",
    "CoreMLExecutionProvider",
    "CPUExecutionProvider",
)

CLASS_ALIASES: dict[str, DetectionClass] = {
    "papule": DetectionClass.PAPULE,
    "papules": DetectionClass.PAPULE,
    "pustule": DetectionClass.PUSTULE,
    "pustules": DetectionClass.PUSTULE,
    "nodule": DetectionClass.NODULE,
    "nodules": DetectionClass.NODULE,
    "blackhead": DetectionClass.COMEDONE,
    "blackheads": DetectionClass.COMEDONE,
    "whitehead": DetectionClass.COMEDONE,
    "whiteheads": DetectionClass.COMEDONE,
    "comedone": DetectionClass.COMEDONE,
    "dark spot": DetectionClass.HYPERPIGMENTATION,
    "dark_spot": DetectionClass.HYPERPIGMENTATION,
    "hyperpigmentation": DetectionClass.HYPERPIGMENTATION,
    "pie": DetectionClass.RED_MARK,
    "red_mark": DetectionClass.RED_MARK,
    "acne_scar": DetectionClass.TEXTURE,
    "wrinkle": DetectionClass.FINE_LINES,
    "wrinkles": DetectionClass.FINE_LINES,
}


def select_providers(available: list[str]) -> list[str]:
    chosen = [p for p in PROVIDER_PREFERENCE if p in available]
    return chosen or ["CPUExecutionProvider"]


def letterbox(img: np.ndarray, size: int) -> tuple[np.ndarray, float, tuple[int, int]]:
    h, w = img.shape[:2]
    r = size / max(h, w)
    nh, nw = int(round(h * r)), int(round(w * r))
    resized = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_LINEAR)
    out = np.full((size, size, 3), 114, np.uint8)
    top, left = (size - nh) // 2, (size - nw) // 2
    out[top : top + nh, left : left + nw] = resized
    return out, r, (left, top)


@dataclass(frozen=True)
class RawInstance:
    class_id: int
    score: float
    box_xyxy: np.ndarray  # model-input pixels
    mask: np.ndarray  # bool, model-input resolution


def decode_yolov8_seg(
    pred: np.ndarray,
    protos: np.ndarray,
    num_classes: int,
    input_size: int,
    conf_thr: float = 0.35,
    iou_thr: float = 0.5,
) -> list[RawInstance]:
    """Decode raw YOLOv8-seg tensors: pred (1, 4+nc+nm, N), protos (1, nm, mh, mw)."""
    p = pred[0].T  # (N, 4+nc+nm)
    boxes, scores_all, coeffs = p[:, :4], p[:, 4 : 4 + num_classes], p[:, 4 + num_classes :]
    cls = scores_all.argmax(axis=1)
    scores = scores_all[np.arange(len(p)), cls]
    keep = scores >= conf_thr
    if not keep.any():
        return []
    boxes, cls, scores, coeffs = boxes[keep], cls[keep], scores[keep], coeffs[keep]
    xywh = np.column_stack([boxes[:, 0] - boxes[:, 2] / 2, boxes[:, 1] - boxes[:, 3] / 2,
                            boxes[:, 2], boxes[:, 3]])
    idx = cv2.dnn.NMSBoxesBatched(xywh.tolist(), scores.tolist(), cls.tolist(), conf_thr, iou_thr)
    idx = np.asarray(idx).reshape(-1)
    nm, mh, mw = protos.shape[1:]
    proto = protos[0].reshape(nm, -1)
    out = []
    for i in idx:
        m = 1.0 / (1.0 + np.exp(-(coeffs[i] @ proto)))
        m = cv2.resize(m.reshape(mh, mw).astype(np.float32), (input_size, input_size))
        x0, y0, w, h = xywh[i]
        crop = np.zeros_like(m, dtype=bool)
        crop[max(int(y0), 0) : int(y0 + h) + 1, max(int(x0), 0) : int(x0 + w) + 1] = True
        out.append(RawInstance(int(cls[i]), float(scores[i]),
                               np.array([x0, y0, x0 + w, y0 + h]), (m > 0.5) & crop))
    return out


def parse_class_names(meta: dict[str, str]) -> dict[int, str]:
    raw = meta.get("names")
    if not raw:
        return {}
    try:
        names = ast.literal_eval(raw)
    except (ValueError, SyntaxError):
        return {}
    return {int(k): str(v) for k, v in names.items()} if isinstance(names, dict) else {}


class OnnxYoloSegDetector:  # pragma: no cover - needs a trained model file
    name = "onnx-yolov8-seg"

    def __init__(self, model_path: Path, conf_thr: float = 0.35, roi_pad: float = 0.15) -> None:
        import onnxruntime as ort

        self.providers = select_providers(ort.get_available_providers())
        self.session = ort.InferenceSession(str(model_path), providers=self.providers)
        self.active_provider = self.session.get_providers()[0]
        inp = self.session.get_inputs()[0]
        self.input_name = inp.name
        self.input_size = int(inp.shape[-1]) if isinstance(inp.shape[-1], int) else 640
        meta = self.session.get_modelmeta().custom_metadata_map
        self.class_names = parse_class_names(meta)
        self.conf_thr = conf_thr
        self.roi_pad = roi_pad
        logger.info("YOLO-seg loaded on %s with classes %s", self.active_provider, self.class_names)

    def _roi(self, inp: DetectorInput) -> tuple[int, int, int, int]:
        lm = inp.region.landmarks
        h, w = inp.frame_bgr.shape[:2]
        x0, y0 = lm.min(axis=0)
        x1, y1 = lm.max(axis=0)
        px, py = (x1 - x0) * self.roi_pad, (y1 - y0) * self.roi_pad
        return (int(max(0, x0 - px)), int(max(0, y0 - py)),
                int(min(w, x1 + px)), int(min(h, y1 + py)))

    def detect(self, inp: DetectorInput) -> list[Detection]:
        x0, y0, x1, y1 = self._roi(inp)
        crop = inp.frame_bgr[y0:y1, x0:x1]
        if crop.size == 0:
            return []
        boxed, r, (left, top) = letterbox(crop, self.input_size)
        blob = boxed[..., ::-1].transpose(2, 0, 1)[None].astype(np.float32) / 255.0
        pred, protos = self.session.run(None, {self.input_name: blob})[:2]
        nc = pred.shape[1] - 4 - protos.shape[1]
        dets = []
        for inst in decode_yolov8_seg(pred, protos, nc, self.input_size, self.conf_thr):
            label = CLASS_ALIASES.get(self.class_names.get(inst.class_id, "").lower())
            if label is None:
                continue
            contours, _ = cv2.findContours(inst.mask.astype(np.uint8), cv2.RETR_EXTERNAL,
                                           cv2.CHAIN_APPROX_SIMPLE)
            if not contours:
                continue
            c = max(contours, key=cv2.contourArea).reshape(-1, 2).astype(np.float64)
            pts = (c - (left, top)) / r + (x0, y0)
            bx0, by0 = pts.min(axis=0)
            bx1, by1 = pts.max(axis=0)
            center = ((bx0 + bx1) / 2, (by0 + by1) / 2)
            dets.append(Detection(
                label=label,
                bbox=(float(bx0), float(by0), float(bx1 - bx0), float(by1 - by0)),
                confidence=inst.score,
                contour=tuple((float(x), float(y)) for x, y in pts),
                area_px=float(inst.mask.sum() / (r * r)),
                zone=inp.region.zone_at_image_point(center),
                features={"model_score": inst.score},
            ))
        return dets
