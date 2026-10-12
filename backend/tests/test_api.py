import time

import cv2
import numpy as np
from fastapi.testclient import TestClient

from skin_analyzer.api.app import create_app
from skin_analyzer.config import Settings
from skin_analyzer.pipeline import FrameResult
from skin_analyzer.pipeline.protocol import build_frame_header, decode_frame_message, encode_frame_message


class FakeRunner:
    def __init__(self) -> None:
        self.resets = 0
        self.started = self.stopped = False
        _, jpeg = cv2.imencode(".jpg", np.zeros((10, 10, 3), np.uint8))
        self.packet = encode_frame_message(build_frame_header(
            FrameResult(None, [], None, {}), 1, time.time(), 10, 10), jpeg.tobytes())

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.stopped = True

    def health(self) -> dict:
        return {"status": "ok"}

    def latest_report(self) -> None:
        return None

    def wait_packet(self, after_version: int, timeout: float) -> tuple[int, bytes] | None:
        if after_version == 0:
            return 1, self.packet
        time.sleep(0.01)
        return None

    def reset(self) -> None:
        self.resets += 1


def test_api_and_websocket() -> None:
    runner = FakeRunner()
    with TestClient(create_app(Settings(), runner)) as client:
        assert runner.started
        assert client.get("/api/health").json() == {
            "success": True, "data": {"status": "ok"}, "error": None}
        assert client.get("/api/report").json() == {"success": True, "data": None, "error": None}
        assert client.post("/api/reset").json()["data"] == {"reset": True}
        with client.websocket_connect("/ws/stream") as socket:
            assert socket.receive_json()["type"] == "status"
            header, jpeg = decode_frame_message(socket.receive_bytes())
            assert header["type"] == "frame" and jpeg.startswith(b"\xff\xd8")
            socket.send_text("not json")
            socket.send_json({"type": "reset"})
            deadline = time.monotonic() + 2
            while runner.resets < 2 and time.monotonic() < deadline:
                time.sleep(0.01)
            assert runner.resets == 2
    assert runner.stopped


def test_multiple_websocket_clients() -> None:
    runner = FakeRunner()
    with TestClient(create_app(Settings(), runner)) as client:
        with client.websocket_connect("/ws/stream") as first:
            with client.websocket_connect("/ws/stream") as second:
                assert first.receive_json()["type"] == "status"
                assert second.receive_json()["type"] == "status"
                assert first.receive_bytes() == second.receive_bytes()
