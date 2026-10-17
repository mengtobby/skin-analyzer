"""Regenerate the camera-free guided-flow fixtures from the repository root."""

from __future__ import annotations

import json
import math
from dataclasses import asdict
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "backend" / "tests"))

import cv2

from synthetic_face import canonical_landmarks, place, render_face
from skin_analyzer.domain import DetectionClass, FaceZone, SkinMetrics, Track, ZoneMetrics
from skin_analyzer.knowledge import KnowledgeBase, generate_report, report_to_dict

NOW = 1791900000.0


def main() -> None:
    directory = Path(__file__).resolve().parent
    landmarks = place(canonical_landmarks(), 220, 0, (640, 300))
    spots = [
        (DetectionClass.PAPULE, FaceZone.LEFT_CHEEK, 548, 440, 9),
        (DetectionClass.PUSTULE, FaceZone.CHIN, 668, 575, 8),
        (DetectionClass.RED_MARK, FaceZone.RIGHT_CHEEK, 742, 452, 10),
        (DetectionClass.HYPERPIGMENTATION, FaceZone.FOREHEAD, 700, 205, 9),
    ]
    image = render_face(
        landmarks, size=(720, 1280),
        lesions=[(x, y, r) for _, _, x, y, r in spots[:3]],
        dark_spots=[(700, 205, 9)], seed=0,
    )
    tracks = []
    for track_id, (label, zone, x, y, radius) in enumerate(spots, start=1):
        contour = tuple(
            (round(x + radius * math.cos(i * math.tau / 12), 4),
             round(y + radius * math.sin(i * math.tau / 12), 4))
            for i in range(12)
        )
        tracks.append(Track(
            track_id=track_id, label=label, confidence=0.95,
            bbox=(x - radius, y - radius, radius * 2, radius * 2),
            contour=contour, zone=zone,
            canonical_center=((x - 640) / 220, (y - 300) / 220),
            size_mm=round(radius * 2 * 63 / 220, 2),
            age=30, hits=30, misses=0, confirmed=True,
        ))
    metrics = SkinMetrics(overall=ZoneMetrics(46, 28, 12, 34), zones={})
    minimum, maximum = landmarks.min(axis=0), landmarks.max(axis=0)
    header = {
        "type": "frame", "frame_id": 1, "timestamp": NOW,
        "width": 1280, "height": 720, "analyzed": True,
        "face": {
            "bbox": [*minimum.tolist(), *(maximum - minimum).tolist()],
            "zones": [{"zone": "forehead", "polygon": [
                [535, 150], [745, 150], [760, 245], [520, 245],
            ]}],
        },
        "tracks": [{
            "id": t.track_id, "label": t.label.value, "confidence": t.confidence,
            "zone": t.zone.value, "bbox": t.bbox, "contour": t.contour,
            "size_mm": t.size_mm, "age": t.age,
        } for t in tracks],
        "counts": {label.value: 1 for label, *_ in spots},
        "metrics": asdict(metrics),
        "quality": {
            "ok": True, "score": 0.92, "issues": [], "brightness": 170,
            "evenness": 0.95, "face_size_px": float(maximum[0] - minimum[0]),
            "yaw_deg": 0, "pitch_deg": 0,
        },
        "perf": {"fps": 10, "latency_ms": 12, "stages_ms": {"analysis": 10}},
    }
    report = report_to_dict(generate_report(tracks, metrics, KnowledgeBase.load(), now=NOW))
    encoded, jpeg = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 85])
    if not encoded:
        raise RuntimeError("Could not encode the synthetic face")
    (directory / "stream-face.jpg").write_bytes(jpeg.tobytes())
    for name, data in (("stream-header.json", header), ("stream-report.json", report)):
        (directory / name).write_text(
            json.dumps(data, indent=2, allow_nan=False) + "\n", encoding="utf-8",
        )


if __name__ == "__main__":
    main()
