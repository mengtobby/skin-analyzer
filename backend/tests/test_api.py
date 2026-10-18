import time
from contextlib import ExitStack, contextmanager
from threading import Lock

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from skin_analyzer.api.app import create_app
from skin_analyzer.config import Settings
from skin_analyzer.pipeline import FrameResult
from skin_analyzer.pipeline.protocol import build_frame_header, decode_frame_message, encode_frame_message


class FakeRunner:
    def __init__(self) -> None:
        self.resets = 0
        self.started = self.stopped = False
        self.listeners = []
        self.lock = Lock()
        self.report = None
        self.version = 1
        _, jpeg = cv2.imencode(".jpg", np.zeros((10, 10, 3), np.uint8))
        self.packet = encode_frame_message(build_frame_header(
            FrameResult(None, [], None, {}), 1, 1.0, 10, 10), jpeg.tobytes())

    @property
    def is_running(self) -> bool:
        return self.started and not self.stopped

    def add_listener(self, callback):
        with self.lock:
            self.listeners.append(callback)

        def unsubscribe():
            with self.lock:
                self.listeners.remove(callback)
        return unsubscribe

    def notify(self) -> None:
        with self.lock:
            callbacks = tuple(self.listeners)
        for callback in callbacks:
            callback()

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.stopped = True
        self.notify()

    def health(self) -> dict:
        return {"status": "ok"}

    def latest_report(self) -> tuple[int, dict] | None:
        return self.report

    def latest_packet(self) -> tuple[int, bytes]:
        return self.version, self.packet

    def reset(self) -> None:
        self.resets += 1


def wait_for(condition) -> None:
    deadline = time.monotonic() + 3
    while not condition():
        assert time.monotonic() < deadline, "condition did not become true"
        time.sleep(0.001)


@contextmanager
def stream(client, headers=None):
    before = client.app.state.active_streams
    with client.websocket_connect("/ws/stream", headers=headers or {}) as socket:
        try:
            yield socket
        finally:
            socket.close()
            wait_for(lambda: client.app.state.active_streams <= before)


def ready(socket) -> bytes:
    assert socket.receive_json()["type"] == "status"
    return socket.receive_bytes()


def test_api_and_websocket() -> None:
    runner = FakeRunner()
    with TestClient(headers={"host": "localhost"}, base_url="http://localhost", app=create_app(Settings(), runner), client=("127.0.0.1", 50000)) as client:
        assert runner.started
        assert client.get("/api/health").json() == {
            "success": True, "data": {"status": "ok"}, "error": None}
        assert client.get("/api/report").json() == {"success": True, "data": None, "error": None}
        assert client.post("/api/reset").json()["data"] == {"reset": True}
        with stream(client) as socket:
            header, jpeg = decode_frame_message(ready(socket))
            assert header["type"] == "frame" and jpeg.startswith(b"\xff\xd8")
            socket.send_text("not json")
            socket.send_json({"type": "reset"})
            wait_for(lambda: runner.resets == 2)
        assert not runner.listeners
    assert runner.stopped


def test_multiple_websocket_clients() -> None:
    with TestClient(headers={"host": "localhost"}, base_url="http://localhost", app=create_app(Settings(), FakeRunner()), client=("127.0.0.1", 50000)) as client:
        with stream(client) as first:
            with stream(client) as second:
                assert ready(first) == ready(second)
        assert client.app.state.active_streams == 0


@pytest.mark.parametrize("origin", ["http://localhost:5173", "http://127.0.0.1:5173",
                                    "http://localhost:8123", "http://127.0.0.1:8123", "http://[::1]:8123",
                                    "https://trusted.example"])
def test_allowed_origins(origin) -> None:
    settings = Settings(dev=True, port=8123, extra_origins=("https://trusted.example",))
    with TestClient(headers={"host": "localhost"}, base_url="http://localhost", app=create_app(settings, FakeRunner())) as client:
        with stream(client, {"origin": origin}) as socket:
            ready(socket)
        assert client.post("/api/reset", headers={"origin": origin}).status_code == 200


@pytest.mark.parametrize("headers,host", [({"origin": "http://evil.example"}, "127.0.0.1"),
                                         ({}, "192.0.2.1"), ({}, "testclient")])
def test_untrusted_websocket(headers, host) -> None:
    with TestClient(headers={"host": "localhost"}, base_url="http://localhost", app=create_app(Settings(), FakeRunner()), client=(host, 50000)) as client:
        with pytest.raises(WebSocketDisconnect) as exc:
            with client.websocket_connect("/ws/stream", headers=headers):
                pytest.fail("untrusted connection accepted")
        assert exc.value.code == 1008
        assert client.app.state.active_streams == 0


def test_foreign_reset_origin() -> None:
    runner = FakeRunner()
    with TestClient(headers={"host": "localhost"}, base_url="http://localhost", app=create_app(Settings(), runner)) as client:
        response = client.post("/api/reset", headers={"origin": "http://evil.example"})
        assert response.status_code == 403
        assert response.json()["success"] is False
        assert runner.resets == 0


def test_report_delivery_and_new_frames() -> None:
    runner = FakeRunner()
    with TestClient(headers={"host": "localhost"}, base_url="http://localhost", app=create_app(Settings(), runner), client=("127.0.0.1", 50000)) as client:
        with stream(client) as socket:
            ready(socket)
            runner.report = (1, {"summary": "first"})
            runner.notify()
            assert socket.receive_json() == {"type": "report", "data": runner.report[1]}
            runner.report = (2, {"summary": "second"})
            runner.version = 2
            runner.notify()
            assert socket.receive_bytes() == runner.packet
            assert socket.receive_json()["data"] == runner.report[1]


@pytest.mark.parametrize("kind", ["binary", "array", "invalid", "unsupported", "oversized", "unicode"])
def test_invalid_messages(kind) -> None:
    with TestClient(headers={"host": "localhost"}, base_url="http://localhost", app=create_app(Settings(), FakeRunner()), client=("127.0.0.1", 50000)) as client:
        with stream(client) as socket:
            ready(socket)
            if kind in {"oversized", "unicode"}:
                socket.send_text("x" * 1025 if kind == "oversized" else "é" * 513)
                code = 1009
            else:
                for _ in range(20):
                    if kind == "binary":
                        socket.send_bytes(b"reset")
                    else:
                        socket.send_text({"array": "[]", "invalid": "!", "unsupported": '{}'}[kind])
                code = 1003
            with pytest.raises(WebSocketDisconnect) as exc:
                socket.receive_text()
            assert exc.value.code == code


def test_client_limit() -> None:
    with TestClient(headers={"host": "localhost"}, base_url="http://localhost", app=create_app(Settings(), FakeRunner()), client=("127.0.0.1", 50000)) as client:
        with ExitStack() as stack:
            for _ in range(8):
                ready(stack.enter_context(stream(client)))
            assert client.app.state.active_streams == 8
            with pytest.raises(WebSocketDisconnect) as exc:
                with client.websocket_connect("/ws/stream"):
                    pytest.fail("ninth client accepted")
            assert exc.value.code == 1013
        assert client.app.state.active_streams == 0


def test_runner_stop() -> None:
    runner = FakeRunner()
    with TestClient(headers={"host": "localhost"}, base_url="http://localhost", app=create_app(Settings(), runner), client=("127.0.0.1", 50000)) as client:
        with stream(client) as socket:
            ready(socket)
            runner.stop()
            with pytest.raises(WebSocketDisconnect) as exc:
                socket.receive_bytes()
            assert exc.value.code == 1001


@pytest.mark.parametrize("endpoint", ["/api/health", "/api/report", "/api/reset"])
def test_rest_errors_are_generic(endpoint, monkeypatch) -> None:
    runner = FakeRunner()

    def fail():
        raise RuntimeError("secret internal path")

    method = {"/api/health": "health", "/api/report": "latest_report", "/api/reset": "reset"}[endpoint]
    monkeypatch.setattr(runner, method, fail)
    with TestClient(headers={"host": "localhost"}, base_url="http://localhost", app=create_app(Settings(), runner)) as client:
        response = client.post(endpoint) if endpoint.endswith("reset") else client.get(endpoint)
        assert response.json()["success"] is False
        assert "secret" not in response.text


def test_health_error_is_generic(monkeypatch) -> None:
    runner = FakeRunner()
    monkeypatch.setattr(runner, "health", lambda: {"status": "degraded", "error": "secret path"})
    with TestClient(headers={"host": "localhost"}, base_url="http://localhost", app=create_app(Settings(), runner)) as client:
        assert client.get("/api/health").json()["data"]["error"] == "Pipeline unavailable"


@pytest.mark.parametrize("name,value", [("PORT", "bad"), ("PORT", "0"), ("WIDTH", "0"),
                                        ("HEIGHT", "bad"), ("FPS", "-1"),
                                        ("JPEG_QUALITY", "101"), ("REPORT_INTERVAL_S", "nan")])
def test_invalid_environment(name, value, monkeypatch) -> None:
    monkeypatch.setenv(f"SKIN_{name}", value)
    with pytest.raises(ValueError, match=f"SKIN_{name}"):
        Settings.from_env()


def test_environment_settings(monkeypatch) -> None:
    values = {"WIDTH": "640", "HEIGHT": "480", "FPS": "24", "JPEG_QUALITY": "90",
              "REPORT_INTERVAL_S": "2.5", "EXTRA_ORIGINS": "https://one.example, https://two.example"}
    for name, value in values.items():
        monkeypatch.setenv(f"SKIN_{name}", value)
    settings = Settings.from_env()
    assert (settings.width, settings.height, settings.fps, settings.jpeg_quality) == (640, 480, 24, 90)
    assert settings.report_interval_s == 2.5
    assert settings.extra_origins == ("https://one.example", "https://two.example")


def test_real_runner_websocket(monkeypatch) -> None:
    from skin_analyzer.knowledge import KnowledgeBase
    from skin_analyzer.pipeline import PipelineRunner
    from .test_pipeline import QueuedSource, make_analyzer

    analyzer, image = make_analyzer()
    monkeypatch.setattr(analyzer, "process", lambda *_: FrameResult(None, [], None, {}))
    source = QueuedSource(image)
    runner = PipelineRunner(Settings(), source, analyzer, KnowledgeBase.load())
    with TestClient(headers={"host": "localhost"}, base_url="http://localhost", app=create_app(Settings(), runner), client=("127.0.0.1", 50000)) as client:
        with stream(client) as socket:
            assert socket.receive_json()["type"] == "status"
            source.frames.put((image, time.time(), 1))
            header, jpeg = decode_frame_message(socket.receive_bytes())
            assert header["frame_id"] == 1 and jpeg.startswith(b"\xff\xd8")
            assert socket.receive_json()["type"] == "report"
            runner.stop()
            with pytest.raises(WebSocketDisconnect) as exc:
                socket.receive_bytes()
            assert exc.value.code == 1001


def test_disconnect_with_pending_frame() -> None:
    runner = FakeRunner()
    with TestClient(headers={"host": "localhost"}, base_url="http://localhost", app=create_app(Settings(), runner), client=("127.0.0.1", 50000)) as client:
        with stream(client) as socket:
            ready(socket)
            runner.version = 2
            runner.notify()
        assert not runner.listeners


def test_cli_configuration(monkeypatch, caplog) -> None:
    from skin_analyzer import __main__ as entry

    monkeypatch.setattr("sys.argv", ["skin-analyzer", "--width", "640", "--height", "480",
                                    "--fps", "24", "--jpeg-quality", "90",
                                    "--report-interval-s", "2.5", "--extra-origins",
                                    "https://trusted.example", "--host", "0.0.0.0"])
    monkeypatch.setattr(entry, "ensure_models", lambda *_: None)
    captured = []
    monkeypatch.setattr(entry, "create_app", lambda settings: captured.append(settings))
    monkeypatch.setattr(entry.uvicorn, "run", lambda *args, **kwargs: None)
    entry.main()
    settings = captured[0]
    assert (settings.width, settings.height, settings.fps, settings.jpeg_quality) == (640, 480, 24, 90)
    assert settings.report_interval_s == 2.5
    assert settings.extra_origins == ("https://trusted.example",)
    assert "CAMERA EXPOSED" in caplog.text


def test_browser_readiness_bypasses_proxies(monkeypatch) -> None:
    from skin_analyzer import __main__ as entry
    from contextlib import nullcontext

    handlers = []

    class Opener:
        def open(self, url, timeout):
            assert url == "http://localhost:8000/api/health" and timeout == 1
            return nullcontext()

    def build_opener(handler):
        handlers.append(handler)
        return Opener()

    monkeypatch.setattr(entry.urllib.request, "build_opener", build_opener)
    monkeypatch.setattr(entry.shutil, "which", lambda *_: "msedge")
    monkeypatch.setattr(entry.subprocess, "Popen", lambda *args, **kwargs: None)
    entry._open_browser("http://localhost:8000")
    assert handlers[0].proxies == {}


@pytest.mark.parametrize("host", ["localhost", "127.0.0.1:8000", "[::1]", "[::1]:8000"])
def test_trusted_hosts(host) -> None:
    with TestClient(headers={"host": "localhost"}, app=create_app(Settings(), FakeRunner()),
                    base_url="http://localhost", client=("127.0.0.1", 50000)) as client:
        assert client.get("/api/report", headers={"host": host}).status_code == 200
        with stream(client, {"host": host}) as socket:
            ready(socket)


@pytest.mark.parametrize("host", ["evil.example", "evil.example:8000", "localhost@evil.example",
                                   "localhost/evil", "localhost:bad", "localhost:65536"])
def test_untrusted_hosts(host, tmp_path) -> None:
    (tmp_path / "index.html").write_text("trusted frontend")
    runner = FakeRunner()
    settings = Settings(static_dir=tmp_path)
    with TestClient(headers={"host": "localhost"}, app=create_app(settings, runner), base_url="http://localhost") as client:
        for path in ("/api/report", "/api/health", "/"):
            response = client.get(path, headers={"host": host})
            assert response.status_code == 400
            assert response.json() == {
                "success": False, "data": None, "error": "Host not allowed"}
        assert client.post("/api/reset", headers={"host": host}).status_code == 400
        assert runner.resets == 0
        with pytest.raises(WebSocketDisconnect) as exc:
            with client.websocket_connect("/ws/stream", headers={"host": host,
                                           "origin": "http://localhost:8000"}):
                pytest.fail("untrusted host accepted")
        assert exc.value.code == 1008


@pytest.mark.parametrize("host,origin", [("192.168.1.5", "http://192.168.1.5:8000"),
                                        ("::1", "http://[::1]:8000"),
                                        ("MyPC", "http://mypc:8000")])
def test_served_origins(host, origin) -> None:
    with TestClient(headers={"host": "localhost"}, app=create_app(Settings(host=host), FakeRunner()), base_url=origin) as client:
        assert client.post("/api/reset", headers={"origin": origin}).status_code == 200
        with stream(client, {"origin": origin, "host": origin.split("//", 1)[1]}) as socket:
            ready(socket)


@pytest.mark.parametrize("bind_host", ["0.0.0.0", "::"])
def test_wildcard_bind_trusts_explicit_origin_hosts(bind_host, caplog) -> None:
    settings = Settings(host=bind_host, extra_origins=("https://trusted.example:8443",))
    with TestClient(headers={"host": "localhost"}, app=create_app(settings, FakeRunner()), base_url="http://localhost") as client:
        assert client.get("/api/report", headers={"host": "trusted.example"}).status_code == 200
        with stream(client, {"host": "trusted.example:8443",
                             "origin": "https://trusted.example:8443"}) as socket:
            ready(socket)
        assert "hosts from --extra-origins" in caplog.text
        assert client.get("/api/report", headers={"host": bind_host}).status_code == 400
        assert client.get("/api/report", headers={"host": "192.168.1.5"}).status_code == 400


def test_runner_close_on_shutdown() -> None:
    class ClosingRunner(FakeRunner):
        closed = False

        def close(self) -> None:
            self.closed = True
            self.stop()

    runner = ClosingRunner()
    with TestClient(headers={"host": "localhost"}, app=create_app(Settings(), runner), base_url="http://localhost"):
        assert runner.started and not runner.closed
    assert runner.closed and runner.stopped

class SettingsRunner(FakeRunner):
    def __init__(self):
        super().__init__()
        from skin_analyzer.capture import create_source
        self.source = create_source("camera:2", width=640, height=480)
        self.specs = []

    def switch_source(self, spec):
        from skin_analyzer.capture import create_source
        self.specs.append(spec)
        self.source = create_source(spec)


def test_settings_switch_and_redaction(tmp_path):
    from skin_analyzer.user_settings import UserSettingsStore
    runner = SettingsRunner()
    path = tmp_path / "settings.json"
    with TestClient(create_app(Settings(settings_file=path), runner), base_url="http://localhost") as client:
        assert client.get("/api/settings").json()["data"]["source"] == {
            "kind": "camera", "spec": "camera:2", "camera_index": 2}
        url = "http://user:secret@phone.example/video?token=private"
        response = client.post("/api/settings/source", json={"kind": "url", "url": url})
        assert response.status_code == 200 and response.json()["data"]["saved"]
        assert "secret" not in response.text and "private" not in response.text
        assert runner.specs == ["url:" + url]
        assert UserSettingsStore(path).load().source == "url:" + url


@pytest.mark.parametrize("body", [{"kind": "file", "path": "x"}, {"kind": "camera", "index": True},
    {"kind": "camera", "index": 10}, {"kind": "camera", "index": -1},
    {"kind": "url", "url": "file:secret"}, {"kind": "url", "url": "http://a/ secret"},
    {"kind": "url", "url": "http://a:" + "9" * 8}, {"kind": "url", "url": "x" * 2049},
    {"kind": "camera", "index": 0, "extra": 1}, [], None])
def test_settings_invalid(body, tmp_path):
    runner = SettingsRunner()
    with TestClient(create_app(Settings(settings_file=tmp_path / "s"), runner), base_url="http://localhost") as client:
        response = client.post("/api/settings/source", json=body)
        assert response.status_code == 422
        assert response.json()["data"] is None and not runner.specs
        assert "secret" not in response.text


def test_camera_probe_cache(monkeypatch, tmp_path):
    from skin_analyzer.api import app as api
    from skin_analyzer.capture import CameraInfo
    calls = []
    now = [100.0]
    monkeypatch.setattr(api.time, "monotonic", lambda: now[0])
    monkeypatch.setattr(api, "probe_cameras", lambda **kw: calls.append(kw) or [CameraInfo(0, 320, 240)])
    with TestClient(create_app(Settings(settings_file=tmp_path / "s"), SettingsRunner()), base_url="http://localhost") as client:
        cameras = client.get("/api/settings/cameras").json()["data"]["cameras"]
        assert cameras == [{"index": 0, "width": 320, "height": 240, "active": False},
                           {"index": 2, "width": 640, "height": 480, "active": True}]
        client.get("/api/settings/cameras")
        assert calls == [{"skip": {2}}]
        now[0] += 10
        client.get("/api/settings/cameras")
        assert len(calls) == 2


@pytest.mark.parametrize("error,status,message", [("busy", 409, "Another input change is in progress"),
    ("switch", 502, "Could not open camera"), ("invalid", 422, "That stream address is not valid"),
    ("closed", 503, "Switching inputs is not available right now")])
def test_settings_switch_errors(error, status, message, monkeypatch, tmp_path):
    from skin_analyzer.pipeline import SourceBusyError, SourceSwitchError
    runner = SettingsRunner()
    exception = {"busy": SourceBusyError, "switch": SourceSwitchError, "invalid": ValueError,
                 "closed": RuntimeError}[error]
    def fail(spec):
        raise exception("Could not open camera")
    monkeypatch.setattr(runner, "switch_source", fail)
    with TestClient(create_app(Settings(settings_file=tmp_path / "s"), runner), base_url="http://localhost") as client:
        response = client.post("/api/settings/source", json={"kind": "camera", "index": 0})
        assert response.status_code == status and response.json()["error"] == message
        assert response.json()["success"] is False and response.json()["data"] is None


def test_settings_origin_and_save_failure(monkeypatch, tmp_path):
    from skin_analyzer.user_settings import UserSettingsStore
    runner = SettingsRunner()
    def fail(*args):
        raise OSError("secret")
    monkeypatch.setattr(UserSettingsStore, "save", fail)
    with TestClient(create_app(Settings(settings_file=tmp_path / "s"), runner), base_url="http://localhost") as client:
        assert client.post("/api/settings/source", headers={"origin": "http://evil.example"},
                           json={"kind": "camera", "index": 0}).status_code == 403
        assert not runner.specs
        response = client.post("/api/settings/source", json={"kind": "camera", "index": 0})
        assert response.json()["data"]["saved"] is False

@pytest.mark.parametrize("site", [None, "same-origin", "same-site", "none", "cross-site"])
def test_fetch_site_policy(site):
    runner = FakeRunner()
    headers = {} if site is None else {"sec-fetch-site": site}
    with TestClient(headers={"host": "localhost"}, app=create_app(Settings(), runner), base_url="http://localhost",
                    client=("127.0.0.1", 50000)) as client:
        for method, path in [("GET", "/api/report"), ("POST", "/api/reset")]:
            response = client.request(method, path, headers=headers)
            assert response.status_code == (403 if site == "cross-site" else 200)
            if site == "cross-site":
                assert response.json() == {"success": False, "data": None,
                                           "error": "Cross-site request blocked"}
        assert runner.resets == (0 if site == "cross-site" else 1)
        if site == "cross-site":
            with pytest.raises(WebSocketDisconnect) as exc:
                with client.websocket_connect("/ws/stream", headers=headers):
                    pytest.fail("cross-site socket accepted")
            assert exc.value.code == 1008
        else:
            with stream(client, headers) as socket:
                ready(socket)


def test_foreign_camera_origin_does_not_probe(monkeypatch):
    from skin_analyzer.api import app as api
    monkeypatch.setattr(api, "probe_cameras", lambda **kw: pytest.fail("camera probe"))
    with TestClient(headers={"host": "localhost"}, app=create_app(Settings(), SettingsRunner()), base_url="http://localhost") as client:
        assert client.get("/api/settings/cameras", headers={"origin": "https://evil.test"}).status_code == 403
        assert client.get("/api/settings/cameras", headers={"sec-fetch-site": "cross-site"}).status_code == 403


def test_security_headers_on_api_static_and_rejections(tmp_path):
    (tmp_path / "index.html").write_text("<html>dashboard</html>", encoding="utf-8")
    with TestClient(headers={"host": "localhost"}, app=create_app(Settings(static_dir=tmp_path), FakeRunner()), base_url="http://localhost") as client:
        for path, headers in [("/", {}), ("/api/report", {}), ("/missing", {}),
                              ("/api/report", {"host": "evil.test"}),
                              ("/api/report", {"sec-fetch-site": "cross-site"})]:
            response = client.get(path, headers=headers)
            assert response.headers["x-frame-options"] == "DENY"
            assert response.headers["x-content-type-options"] == "nosniff"
            assert response.headers["referrer-policy"] == "no-referrer"
            assert response.headers["content-security-policy"] == (
                "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: blob:; connect-src 'self' ws: wss:; object-src 'none'; "
                "base-uri 'self'; frame-ancestors 'none'; form-action 'self'")


@pytest.mark.parametrize("dev", [False, True])
@pytest.mark.parametrize("origin", ["http://localhost:5173", "http://127.0.0.1:5173"])
def test_vite_origin_requires_dev(dev, origin):
    with TestClient(headers={"host": "localhost"}, app=create_app(Settings(dev=dev), FakeRunner()), base_url="http://localhost") as client:
        assert client.post("/api/reset", headers={"origin": origin}).status_code == (200 if dev else 403)
        if dev:
            with stream(client, {"origin": origin}) as socket:
                ready(socket)
        else:
            with pytest.raises(WebSocketDisconnect) as exc:
                with client.websocket_connect("/ws/stream", headers={"origin": origin}):
                    pytest.fail("Vite trusted outside development")
            assert exc.value.code == 1008


@pytest.mark.parametrize("mode", ["length", "stream", "declared", "understated"])
def test_source_body_limit(mode):
    runner = SettingsRunner()
    with TestClient(headers={"host": "localhost"}, app=create_app(Settings(), runner), base_url="http://localhost") as client:
        if mode == "declared":
            response = client.post("/api/settings/source", content=b"{}", headers={"content-length": "4097"})
        elif mode == "length":
            response = client.post("/api/settings/source", content=b" " * 4097)
        else:
            headers = {"content-length": "2"} if mode == "understated" else {}
            response = client.post("/api/settings/source", content=iter([b" " * 2048, b" " * 2049]), headers=headers)
        assert response.status_code == 413
        assert response.json()["success"] is False and not runner.specs


@pytest.mark.parametrize("body", [b"[" * 1500 + b"]" * 1500, b"{", b"\xff"])
def test_source_malformed_json_is_friendly(body):
    runner = SettingsRunner()
    with TestClient(headers={"host": "localhost"}, app=create_app(Settings(), runner), base_url="http://localhost") as client:
        response = client.post("/api/settings/source", content=body)
        assert response.status_code == 422
        assert response.json()["error"] == "Choose a camera from 0 to 9 or a valid HTTP, HTTPS or RTSP stream address"
        assert not runner.specs


def test_security_headers_on_unhandled_errors(monkeypatch, tmp_path):
    from skin_analyzer.api import app as api

    runner = FakeRunner()
    def fail(_runner):
        raise RuntimeError("private error")
    monkeypatch.setattr(api, "_source_view", fail)
    (tmp_path / "index.html").write_text("<html>dashboard</html>", encoding="utf-8")
    with TestClient(headers={"host": "localhost"},
                    app=create_app(Settings(static_dir=tmp_path), runner),
                    base_url="http://localhost", raise_server_exceptions=False) as client:
        # A route with no local error handler exercises the outer server-error response.
        response = client.get("/api/settings")
        assert response.status_code == 500
        assert response.headers["x-frame-options"] == "DENY"
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["referrer-policy"] == "no-referrer"
        assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
        assert "private error" not in response.text
