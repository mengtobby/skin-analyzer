"""Protocol frame serialization."""
from __future__ import annotations

import json
import struct
from collections import Counter
from dataclasses import asdict
from typing import Any

from .analyzer import FrameResult


def _points(points: Any) -> list[list[float]]:
    return [[round(float(x), 1), round(float(y), 1)] for x, y in points]


def _numbers(values: Any) -> list[float]:
    return [round(float(v), 1) for v in values]


def build_frame_header(result: FrameResult, frame_id: int, timestamp: float,
                       width: int, height: int, fps: float = 0.0,
                       latency_ms: float = 0.0, encode_ms: float = 0.0) -> dict:
    region = result.region
    face_data = None
    if region is not None:
        low, high = region.landmarks.min(axis=0), region.landmarks.max(axis=0)
        face_data = {"bbox": _numbers((*low, *(high - low))), "zones": [
            {"zone": zone.value, "polygon": _points(polygon)}
            for zone, polygon in region.zone_polygons.items()]}
    tracks = [{"id": t.track_id, "label": t.label.value,
               "confidence": round(float(t.confidence), 3), "zone": t.zone.value,
               "bbox": _numbers(t.bbox), "contour": _points(t.contour),
               "size_mm": round(float(t.size_mm), 1), "age": t.age}
              for t in result.tracks if t.confirmed]
    metrics = None
    if result.metrics is not None:
        def scores(value: Any) -> dict:
            return {k: round(float(v), 1) for k, v in asdict(value).items()}
        metrics = {"overall": scores(result.metrics.overall), "zones": {
            zone.value: scores(value) for zone, value in result.metrics.zones.items()}}
    return {"type": "frame", "frame_id": int(frame_id), "timestamp": round(timestamp, 3),
            "width": width, "height": height, "face": face_data, "tracks": tracks,
            "counts": dict(Counter(t["label"] for t in tracks)), "metrics": metrics,
            "perf": {"fps": round(fps, 1), "latency_ms": round(latency_ms, 1),
                     "stages_ms": {k: round(v, 1) for k, v in
                                   {**result.stages_ms, "encode": encode_ms}.items()}}}


def encode_frame_message(header: dict, jpeg: bytes) -> bytes:
    try:
        encoded = json.dumps(header, ensure_ascii=False, allow_nan=False,
                             separators=(",", ":")).encode("utf-8")
        return struct.pack("<I", len(encoded)) + encoded + bytes(jpeg)
    except (TypeError, ValueError, OverflowError, struct.error) as exc:
        raise ValueError("invalid frame message") from exc


def decode_frame_message(data: bytes) -> tuple[dict, bytes]:
    if len(data) < 4:
        raise ValueError("missing frame header length")
    length = struct.unpack("<I", data[:4])[0]
    if length == 0 or length > len(data) - 4:
        raise ValueError("truncated frame header")
    try:
        header = json.loads(data[4:4 + length].decode("utf-8"),
                            parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
    except (UnicodeDecodeError, ValueError) as exc:
        raise ValueError("invalid frame JSON") from exc
    if not isinstance(header, dict) or header.get("type") != "frame":
        raise ValueError("expected frame header")
    jpeg = bytes(data[4 + length:])
    if jpeg and (not jpeg.startswith(b"\xff\xd8") or not jpeg.endswith(b"\xff\xd9")):
        raise ValueError("invalid or truncated JPEG")
    return header, jpeg
