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
                           "tracks", "counts", "metrics", "perf"}
    assert set(header["perf"]["stages_ms"]) == {
        "landmarks", "preprocess", "detect", "track", "metrics", "encode"}
    with pytest.raises(ValueError):
        decode_frame_message(packet[:-1])


@pytest.mark.parametrize("packet", [b"", b"123", struct.pack("<I", 100) + b"{}",
                                    struct.pack("<I", 2) + b"{}", struct.pack("<I", 1) + b"\xff"])
def test_malformed_packet(packet: bytes) -> None:
    with pytest.raises(ValueError):
        decode_frame_message(packet)
