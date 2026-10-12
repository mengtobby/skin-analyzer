"""Train a YOLOv8-seg skin-lesion model and export it for the app (optional).

The app works without this: it falls back to the classical CIELAB detector. A learned
model improves papule / pustule / comedone / nodule discrimination.

Usage (in a separate environment - ultralytics pulls in PyTorch):
    pip install ultralytics
    python tools/train_yolo_seg.py --data path/to/data.yaml --epochs 100

``data.yaml`` is a standard Ultralytics segmentation dataset (e.g. an acne dataset
exported from Roboflow in "YOLOv8" format). Class names are matched case-insensitively
against ``CLASS_ALIASES`` in backend/skin_analyzer/detection/onnx_yolo.py
(papules, pustules, nodules, blackheads, whiteheads, dark spot, ...).

The exported ONNX is copied to backend/models/skin_yolov8_seg.onnx and picked up
automatically (``--detector auto``). ONNX Runtime then runs it on TensorRT / CUDA /
DirectML / OpenVINO / CPU, whichever is available.
"""

from __future__ import annotations

import argparse
import logging
import shutil
from pathlib import Path

logger = logging.getLogger("train_yolo_seg")
TARGET = Path(__file__).resolve().parents[1] / "backend" / "models" / "skin_yolov8_seg.onnx"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--data", required=True, type=Path, help="Ultralytics data.yaml")
    parser.add_argument("--model", default="yolov8n-seg.pt", help="base checkpoint")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--device", default=None, help="e.g. 0 for CUDA, cpu")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    if not args.data.is_file():
        parser.error(f"data.yaml not found: {args.data}")
    try:
        from ultralytics import YOLO
    except ImportError as exc:
        raise SystemExit("ultralytics is not installed: pip install ultralytics") from exc

    model = YOLO(args.model)
    model.train(data=str(args.data), epochs=args.epochs, imgsz=args.imgsz, device=args.device)
    exported = Path(model.export(format="onnx", imgsz=args.imgsz, dynamic=False, simplify=True))
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(exported, TARGET)
    logger.info("Exported %s -> %s", exported, TARGET)


if __name__ == "__main__":
    main()
