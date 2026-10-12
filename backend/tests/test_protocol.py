import struct

import cv2
import numpy as np
import pytest

from skin_analyzer.pipeline import FrameResult
from skin_analyzer.pipeline.protocol import build_frame_header, decode_frame_message, encode_frame_message


def test_protocol_roundtrip() -> None:
    result = FrameResult(None, [], None, dict.fromkeys(
        ("landmarks", "preprocess", "detect", "track", "metrics"), 0.0))
    header = build_frame_header(result, 1, 123.456, 20, 20, encode_ms=1.2)
    _, image = cv2.imencode(".jpg", np.zeros((20, 20, 3), np.uint8))
    packet = encode_frame_message(header, image.tobytes())
    assert decode_frame_message(packet) == (header, image.tobytes())
    assert set(header) == {"type", "frame_id", "timestamp", "width", "height", "face",
                           "tracks", "counts", "metrics", "perf", "quality", "analyzed"}
    assert header["quality"] is None and header["analyzed"] is False
    assert set(header["perf"]["stages_ms"]) == {
        "landmarks", "preprocess", "detect", "track", "metrics", "encode"}
    with pytest.raises(ValueError):
        decode_frame_message(packet[:-1])


@pytest.mark.parametrize("packet", [b"", b"123", struct.pack("<I", 100) + b"{}",
                                    struct.pack("<I", 2) + b"{}", struct.pack("<I", 1) + b"\xff"])
def test_malformed_packet(packet: bytes) -> None:
    with pytest.raises(ValueError):
        decode_frame_message(packet)


def test_quality_header_rounding_and_rejected_analysis() -> None:
    from skin_analyzer.face import QualityReport

    quality = QualityReport(False, .12345, ("too_dark", "occluded"),
                            12.345, 4.567, 180.123, -2.345, 1.234, .5)
    result = FrameResult(None, [], None, {"quality": 1.0}, quality)
    header = build_frame_header(result, 0, 0, 20, 20)
    assert header["analyzed"] is False
    assert header["quality"] == {
        "ok": False, "score": .12, "issues": ["too_dark", "occluded"],
        "brightness": 12.3, "evenness": 4.6, "face_size_px": 180.1,
        "yaw_deg": -2.3, "pitch_deg": 1.2}
    assert decode_frame_message(encode_frame_message(header, b""))[0] == header


@pytest.mark.parametrize("analyzed,timing", [(True, 0.0), (False, 5.0)])
def test_explicit_analyzed_flag(analyzed, timing):
    result = FrameResult(None, [], None, {"quality": timing}, analyzed=analyzed)
    assert build_frame_header(result, 0, 0, 20, 20)["analyzed"] is analyzed
