"""Capture tests use synthetic sources and local media only."""

import os
import threading
import time
from pathlib import Path

import cv2
import numpy as np
import pytest

from skin_analyzer.capture import (CameraSource, NetworkStreamSource,
                                   VideoFileSource, create_source)


class FakeCapture:
    def __init__(self, opened: bool = True, frames: int = 1000) -> None:
        self.opened = opened
        self.frames = frames
        self.number = 0
        self.released = False
        self.settings: dict[int, float] = {}

    def isOpened(self) -> bool:
        return self.opened

    def set(self, prop: int, value: float) -> bool:
        self.settings[prop] = value
        return True

    def read(self) -> tuple[bool, np.ndarray | None]:
        time.sleep(0.005)
        if self.number >= self.frames:
            return False, None
        frame = np.zeros((8, 12, 3), np.uint8)
        frame[:, 0] = 255
        frame[:, 1:, 0] = self.number % 255
        self.number += 1
        return True, frame

    def release(self) -> None:
        self.released = True


@pytest.mark.parametrize("spec", ["foo", "camera:abc", "camera:-1", "file:", "camera:"])
def test_invalid_spec(spec: str) -> None:
    with pytest.raises(ValueError):
        create_source(spec)


def test_parsing() -> None:
    assert isinstance(create_source("camera:0"), CameraSource)
    assert isinstance(create_source("file:x.mp4"), VideoFileSource)


def test_latest_frame_mirroring_and_close() -> None:
    capture = FakeCapture()
    source = create_source("camera:0", capture_factory=lambda *args: capture)
    source.start()
    source.start()
    try:
        first = source.read()
        assert first is not None
        assert np.all(first[0][:, -1] == 255)
        assert first[1] <= time.time()
        time.sleep(0.06)
        second = source.read()
        assert second is not None and second[2] > first[2] + 1
        third = source.read()
        assert third is not None and third[2] > second[2]
        assert source.info().opened
        assert capture.settings[cv2.CAP_PROP_FRAME_WIDTH] == 1280
    finally:
        source.close()
        source.close()
    assert capture.released
    assert source._thread is not None and not source._thread.is_alive()
    assert source.read(0) is None
    assert not source.info().opened


def test_timeout_and_failed_reads() -> None:
    source = CameraSource(capture_factory=lambda *args: FakeCapture(frames=1))
    assert source.read(0.01) is None
    source.start()
    try:
        assert source.read() is not None
        assert source.read(0.15) is None
        assert not source.info().opened
        assert "repeatedly" in (source.info().error or "")
    finally:
        source.close()


def test_failed_open_recovers() -> None:
    ready = threading.Event()
    captures: list[FakeCapture] = []

    def factory(*args: object) -> FakeCapture:
        capture = FakeCapture(opened=ready.is_set())
        captures.append(capture)
        return capture

    source = CameraSource(capture_factory=factory)
    source.start()
    try:
        assert source.read(0.1) is None
        assert not source.info().opened and source.info().error
        ready.set()
        assert source.read(3) is not None
        assert source.info().opened and source.info().error is None
    finally:
        source.close()
    assert all(capture.released for capture in captures)


def test_factory_exception_stays_in_worker() -> None:
    def factory(*args: object) -> FakeCapture:
        raise RuntimeError("test failure")

    source = CameraSource(capture_factory=factory)
    source.start()
    try:
        assert source.read(0.1) is None
        assert "test failure" in (source.info().error or "")
    finally:
        source.close()


def test_video_loops_at_native_fps(tmp_path: Path) -> None:
    path = tmp_path / "loop.avi"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 15, (32, 24))
    assert writer.isOpened()
    try:
        for value in (20, 180):
            writer.write(np.full((24, 32, 3), value, np.uint8))
    finally:
        writer.release()
    source = VideoFileSource(path, mirror=False)
    source.start()
    try:
        frames = [source.read() for _ in range(5)]
        assert all(frame is not None for frame in frames)
        assert [round(float(frame[0].mean())) for frame in frames] == [20, 180, 20, 180, 20]
        assert [frame[2] for frame in frames] == sorted({frame[2] for frame in frames})
        assert source.info().fps == pytest.approx(15)
        assert frames[-1][1] - frames[0][1] >= 0.2
    finally:
        source.close()


def test_image_repeats_without_mutating_slot(tmp_path: Path) -> None:
    path = tmp_path / "still.png"
    image = np.zeros((8, 12, 3), np.uint8)
    image[:, 0] = 255
    assert cv2.imwrite(str(path), image)
    source = VideoFileSource(path, fps=10, mirror=False)
    source.start()
    try:
        first = source.read()
        assert first is not None
        assert source.read(0.01) is None
        first[0][:] = 50
        second = source.read()
        assert second is not None and second[2] > first[2]
        np.testing.assert_array_equal(second[0], image)
    finally:
        source.close()


def test_close_wakes_reader() -> None:
    source = CameraSource()
    result: list[object] = []
    reader = threading.Thread(target=lambda: result.append(source.read(10)))
    reader.start()
    source.close()
    reader.join(1)
    assert not reader.is_alive() and result == [None]


@pytest.mark.parametrize("timeout", [-1, float("inf"), float("nan")])
def test_invalid_timeout(timeout: float) -> None:
    with pytest.raises(ValueError):
        CameraSource().read(timeout)


@pytest.mark.parametrize("url", ["ftp://x", "http://", "file:///c", "",
                                  "http://user:secret@host/a b",
                                  "http://user:secret@[broken"])
def test_invalid_network_url(url: str) -> None:
    with pytest.raises(ValueError) as error:
        create_source(f"url:{url}")
    assert "secret" not in str(error.value)


@pytest.mark.parametrize("url", ["\x00http://host", "\x1fhttp://host", "http://host/\x7f",
                                  "http://host/\nsecret", "http://host/café"])
@pytest.mark.parametrize("use_spec", [False, True])
def test_network_url_requires_printable_ascii(url: str, use_spec: bool) -> None:
    with pytest.raises(ValueError) as error:
        create_source("url:" + url) if use_spec else NetworkStreamSource(url)
    assert str(error.value) == "Invalid network stream URL"


@pytest.mark.parametrize("userinfo", ["username", "username:pass%77ord", ""])
def test_network_all_sensitive_components_redacted(
        userinfo: str, caplog: pytest.LogCaptureFixture) -> None:
    authority = userinfo + "@" if userinfo else ""
    url = f"http://{authority}host:8080/path%74oken/longtoken?key=query%76alue#frag%6dent"
    secrets = ["pathtoken", "path%74oken", "longtoken", "queryvalue", "query%76alue",
               "fragment", "frag%6dent"]
    if userinfo:
        secrets += ["username"]
    if ":" in userinfo:
        secrets += ["pass%77ord", "password"]

    def factory(*args: object) -> FakeCapture:
        raise RuntimeError(f"Failed {url}; " + " ".join(secrets))

    source = NetworkStreamSource(url, capture_factory=factory)
    expected = "url:http://" + ("***@" if userinfo else "") + "host:8080/***?***#***"
    assert source.info().spec == expected
    assert list(map(len, source._secrets)) == sorted(map(len, source._secrets), reverse=True)
    source.start()
    try:
        deadline = time.monotonic() + 1
        while source.info().error is None and time.monotonic() < deadline:
            source.read(0.01)
        assert source.info().error is not None
        assert source._thread is not None
        assert source._thread.name == f"capture-{expected}"
        for secret in secrets:
            assert secret not in source.info().error
            assert secret not in caplog.text
    finally:
        source.close()


@pytest.mark.parametrize("suffix", ["", "/", "?", "#", "/?#"])
def test_network_redaction_preserves_root_and_hides_empty_delimiters(suffix: str) -> None:
    safe = suffix.replace("?", "?***").replace("#", "#***")
    assert NetworkStreamSource("https://host" + suffix).info().spec == "url:https://host" + safe


@pytest.mark.parametrize("options", [None, "", "timeout;100", "protocol_whitelist;http",
                                     "timeout;100|protocol_whitelist;https"])
@pytest.mark.parametrize("kind", ["url", "file", "camera"])
def test_capture_protocol_allowlist(monkeypatch: pytest.MonkeyPatch,
                                   options: str | None, kind: str) -> None:
    key = "OPENCV_FFMPEG_CAPTURE_OPTIONS"
    if options is None:
        monkeypatch.delenv(key, raising=False)
    else:
        monkeypatch.setenv(key, options)
    observed: list[str | None] = []

    def factory(*args: object) -> FakeCapture:
        observed.append(os.environ.get(key))
        raise RuntimeError("stop before reading")

    spec = {"url": "url:http://host/video", "file": "file:video.mp4", "camera": "camera:0"}
    source = create_source(spec[kind], capture_factory=factory)
    with pytest.raises(RuntimeError):
        source._stream()
    allowlist = "protocol_whitelist;file,http,https,tcp,tls,rtsp,rtp,udp,crypto"
    expected = options
    if kind != "camera" and (not options or "protocol_whitelist;" not in options):
        expected = options + "|" + allowlist if options else allowlist
    assert observed and all(value == expected for value in observed)
    assert os.environ.get(key) == expected


@pytest.mark.parametrize("scheme", ["http", "HTTPS", "RTSP"])
def test_network_parsing(scheme: str) -> None:
    spec = f"url:{scheme}://10.0.0.5:8080/video"
    source = create_source(spec)
    assert isinstance(source, NetworkStreamSource)
    assert source.info().spec == f"url:{scheme}://10.0.0.5:8080/***"


def test_network_frames_and_reconnect() -> None:
    captures: list[FakeCapture] = []
    calls: list[tuple[object, ...]] = []

    def factory(*args: object) -> FakeCapture:
        calls.append(args)
        capture = FakeCapture(frames=1 if not captures else 1000)
        captures.append(capture)
        return capture

    url = "http://10.0.0.5:8080/video"
    source = NetworkStreamSource(url, fps=24, capture_factory=factory)
    source.start()
    try:
        first = source.read()
        assert first is not None
        assert np.all(first[0][:, -1] == 255)
        assert (source.info().width, source.info().height, source.info().fps) == (12, 8, 24)
        deadline = time.monotonic() + 1
        while source.info().opened and time.monotonic() < deadline:
            source.read(0.01)
        assert "repeatedly" in (source.info().error or "")
        assert captures[0].released
        assert source.read(3) is not None
        assert len(captures) == 2
        assert calls == [(url, cv2.CAP_FFMPEG)] * 2
        assert captures[0].settings == {cv2.CAP_PROP_BUFFERSIZE: 1}
    finally:
        source.close()


def test_network_credentials_redacted(caplog: pytest.LogCaptureFixture) -> None:
    url = "http://user:secret@host/video"

    def factory(*args: object) -> FakeCapture:
        raise RuntimeError(f"Failed {url}; password secret")

    source = NetworkStreamSource(url, capture_factory=factory)
    assert source.info().spec == "url:http://***@host/***"
    source.start()
    try:
        deadline = time.monotonic() + 1
        while source.info().error is None and time.monotonic() < deadline:
            source.read(0.01)
        assert source.info().error is not None
        assert "secret" not in source.info().error
        assert source._thread is not None and "secret" not in source._thread.name
    finally:
        source.close()
    assert "secret" not in caplog.text


def test_network_query_credentials_redacted(caplog: pytest.LogCaptureFixture) -> None:
    url = "http://host:8080/video?token=secret&pwd=hunter2"

    def factory(*args: object) -> FakeCapture:
        raise RuntimeError(f"Failed {url}; token=secret pwd=hunter2")

    source = NetworkStreamSource(url, capture_factory=factory)
    assert source.info().spec == "url:http://host:8080/***?***"
    source.start()
    try:
        deadline = time.monotonic() + 1
        while source.info().error is None and time.monotonic() < deadline:
            source.read(0.01)
        error = source.info().error
        assert error is not None
        assert "secret" not in error and "hunter2" not in error
        assert source._thread is not None and "secret" not in source._thread.name
    finally:
        source.close()
    assert "secret" not in caplog.text and "hunter2" not in caplog.text


@pytest.mark.parametrize("opened,frames", [(False, 1000), (True, 0)])
def test_network_requires_open_and_initial_frame(opened: bool, frames: int) -> None:
    capture = FakeCapture(opened=opened, frames=frames)
    source = NetworkStreamSource("http://host/video", capture_factory=lambda *args: capture)
    source.start()
    try:
        deadline = time.monotonic() + 1
        while source.info().error is None and time.monotonic() < deadline:
            source.read(0.01)
        assert source.info().error
        assert not source.info().opened
        assert source.read(0) is None
    finally:
        source.close()
    assert capture.released


def test_network_buffer_setting_is_best_effort() -> None:
    class UnsupportedBufferCapture(FakeCapture):
        def set(self, prop: int, value: float) -> bool:
            raise RuntimeError("unsupported property")

    source = NetworkStreamSource("http://host/video", mirror=False,
                                 capture_factory=lambda *args: UnsupportedBufferCapture())
    source.start()
    try:
        frame = source.read()
        assert frame is not None
        assert np.all(frame[0][:, 0] == 255)
    finally:
        source.close()


def test_network_counts_consecutive_failures() -> None:
    capture = FakeCapture()
    frame = np.zeros((8, 12, 3), np.uint8)
    results = iter([(True, frame), (False, None), (False, None),
                    (True, frame), (False, None), (False, None), (False, None)])
    reads: list[bool] = []

    def read() -> tuple[bool, np.ndarray | None]:
        result = next(results)
        reads.append(result[0])
        return result

    capture.read = read
    source = NetworkStreamSource("http://host/video", capture_factory=lambda *args: capture)
    try:
        with pytest.raises(RuntimeError, match="repeatedly"):
            source._stream()
        assert reads == [True, False, False, True, False, False, False]
        assert source._sequence == 2
    finally:
        source._release()


def test_network_release_errors_redacted(caplog: pytest.LogCaptureFixture) -> None:
    url = "rtsp://user:secret@host/video"

    class FailedReleaseCapture(FakeCapture):
        def release(self) -> None:
            raise RuntimeError(f"Cannot release {url}: secret")

    source = NetworkStreamSource(url)
    source._capture = FailedReleaseCapture()
    source._release()
    assert "Cannot release" in caplog.text
    assert "secret" not in caplog.text


def test_camera_probe_skips_releases_and_ignores_failures(monkeypatch):
    from skin_analyzer.capture import CameraInfo, probe_cameras
    from skin_analyzer.capture import sources
    monkeypatch.setattr(sources.sys, "platform", "win32")
    captures = []
    calls = []
    class ProbeCapture(FakeCapture):
        def read(self):
            if not self.opened:
                raise RuntimeError("bad index")
            return True, np.zeros((9, 14, 3), np.uint8)
    def factory(index, backend):
        calls.append((index, backend))
        capture = ProbeCapture(opened=index == 2 and backend == cv2.CAP_MSMF)
        captures.append(capture)
        return capture
    assert probe_cameras([0, 1, 2], skip=[0], capture_factory=factory) == [CameraInfo(2, 14, 9)]
    assert all(capture.released for capture in captures)
    assert calls == [(1, b) for b in [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]] + [
        (2, cv2.CAP_DSHOW), (2, cv2.CAP_MSMF)]


def test_camera_probe_read_exception_releases_and_continues():
    from skin_analyzer.capture import probe_cameras
    captures = []
    class BrokenCapture(FakeCapture):
        def read(self):
            raise RuntimeError("read failed")
    def factory(index, backend):
        if index == 0:
            raise RuntimeError("constructor failed")
        capture = BrokenCapture()
        captures.append(capture)
        return capture
    assert probe_cameras([0, 1], capture_factory=factory) == []
    assert captures and all(capture.released for capture in captures)
