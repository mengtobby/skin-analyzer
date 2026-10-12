"""Camera-free end-to-end pipeline tests."""
import hashlib
import io
import queue
import threading
from pathlib import Path
import time

import numpy as np
import pytest

from skin_analyzer.capture import SourceInfo
from skin_analyzer.config import Settings
from skin_analyzer.detection import ClassicalDetector
from skin_analyzer.domain import DetectionClass, FaceZone
from skin_analyzer.knowledge import KnowledgeBase
from skin_analyzer.metrics import MetricsSmoother
from skin_analyzer.pipeline import FrameAnalyzer, PipelineRunner
from skin_analyzer.pipeline.analyzer import FrameResult
from skin_analyzer.pipeline.protocol import decode_frame_message
from skin_analyzer.preprocessing import CpuPreprocessor
from skin_analyzer.tracking import LesionTracker
from .synthetic_face import canonical_landmarks, place, render_face


class FakeLandmarker:
    def __init__(self, landmarks: np.ndarray | None) -> None:
        self.landmarks = landmarks

    def detect(self, frame: np.ndarray, timestamp_ms: int) -> np.ndarray | None:
        return self.landmarks

    def close(self) -> None:
        pass


def make_analyzer() -> tuple[FrameAnalyzer, np.ndarray]:
    landmarks = place(canonical_landmarks(), 180, 0, (320, 180))
    image = render_face(landmarks, size=(480, 640), lesions=[(410, 270, 8)])
    return FrameAnalyzer(FakeLandmarker(landmarks), CpuPreprocessor(), ClassicalDetector(),
                         LesionTracker(), MetricsSmoother()), image


class FakeSource:
    def __init__(self, image: np.ndarray) -> None:
        self.image, self.index, self.opened = image, 0, False

    def start(self) -> None:
        self.opened = True

    def close(self) -> None:
        self.opened = False

    def info(self) -> SourceInfo:
        return SourceInfo("fake", self.opened, 640, 480, 30, None)

    def read(self, timeout: float = 1.0) -> tuple[np.ndarray, float, int] | None:
        self.index += 1
        if self.index == 1:
            raise RuntimeError("transient capture failure")
        return (self.image, time.time(), self.index) if self.opened else None


def test_synthetic_analysis_and_face_loss() -> None:
    analyzer, image = make_analyzer()
    for index in range(8):
        result = analyzer.process(image, 100 + index / 30)
    assert result.metrics is not None
    assert set(result.stages_ms) == {"landmarks", "preprocess", "detect", "track", "metrics"}
    assert any(t.confirmed and t.label in {DetectionClass.PAPULE, DetectionClass.PUSTULE}
               and t.zone in {FaceZone.LEFT_CHEEK, FaceZone.RIGHT_CHEEK} for t in result.tracks)
    analyzer.landmarker.landmarks = None
    lost = analyzer.process(image, 103)
    assert lost.region is None and lost.metrics is None and not lost.tracks
    analyzer.reset()


def test_runner_recovers_and_publishes() -> None:
    analyzer, image = make_analyzer()
    runner = PipelineRunner(Settings(report_interval_s=0.05), FakeSource(image), analyzer,
                            KnowledgeBase.load())
    runner.start()
    try:
        first = runner.wait_packet(0, 5)
        assert first is not None
        second = runner.wait_packet(first[0], 5)
        assert second is not None and second[0] > first[0]
        header, jpeg = decode_frame_message(second[1])
        assert header["type"] == "frame" and jpeg.startswith(b"\xff\xd8")
        deadline = time.monotonic() + 5
        while runner.latest_report() is None and time.monotonic() < deadline:
            threading.Event().wait(0.001)
        report = runner.latest_report()
        assert report is not None
        assert set(report[1]) == {"generated_at", "face_detected", "findings", "insights",
                                  "ingredients", "products", "warnings", "disclaimer"}
        assert runner.health()["status"] == "ok"
        runner.reset()
        assert runner.latest_report() is None
    finally:
        runner.stop()


@pytest.mark.parametrize("kwargs", [{"port": 0}, {"port": 65536}, {"detector": "bad"},
                                   {"preprocess": "bad"}, {"fps": 0}])
def test_settings_validation(kwargs: dict) -> None:
    with pytest.raises(ValueError):
        Settings(**kwargs)


def test_settings_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SKIN_PORT", "8080")
    monkeypatch.setenv("SKIN_MIRROR", "false")
    assert Settings.from_env().port == 8080
    assert Settings.from_env().mirror is False


def test_report_versions_ignore_generation_time() -> None:
    analyzer, image = make_analyzer()
    analyzer.landmarker.landmarks = None
    runner = PipelineRunner(Settings(report_interval_s=0.001), FakeSource(image),
                            analyzer, KnowledgeBase.load())
    runner._process(image, time.time(), 1)
    first = runner.latest_report()
    assert first is not None
    runner._last_report = 0.0
    runner._process(image, time.time(), 2)
    assert runner.latest_report() == first
    first[1]["warnings"].append("external mutation")
    assert "external mutation" not in runner.latest_report()[1]["warnings"]


def test_model_download_atomic_and_cached(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from skin_analyzer import download_models

    calls = []

    def response(url: str, timeout: float) -> io.BytesIO:
        calls.append(url)
        return io.BytesIO(b"model data")

    monkeypatch.setattr(download_models, "EXPECTED_SHA256", hashlib.sha256(b"model data").hexdigest())
    monkeypatch.setattr(download_models.urllib.request, "urlopen", response)
    target = download_models.ensure_models(tmp_path)
    assert target.read_bytes() == b"model data"
    assert list(tmp_path.iterdir()) == [target]
    assert download_models.ensure_models(tmp_path) == target
    assert len(calls) == 1


def test_failed_download_cleans_partial_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from skin_analyzer import download_models

    def fail(url: str, timeout: float) -> None:
        raise OSError("offline")

    monkeypatch.setattr(download_models.urllib.request, "urlopen", fail)
    with pytest.raises(RuntimeError, match="Unable to download"):
        download_models.ensure_models(tmp_path)
    assert not list(tmp_path.iterdir())


class QueuedSource(FakeSource):
    def __init__(self, image: np.ndarray) -> None:
        super().__init__(image)
        self.frames = queue.Queue()

    def read(self, timeout: float = 1.0):
        try:
            return self.frames.get(timeout=timeout)
        except queue.Empty:
            return None

    def close(self) -> None:
        super().close()
        self.frames.put(None)


def empty_runner(monkeypatch):
    analyzer, image = make_analyzer()
    monkeypatch.setattr(analyzer, "process", lambda *_: FrameResult(None, [], None, {}))
    runner = PipelineRunner(Settings(report_interval_s=10), QueuedSource(image),
                            analyzer, KnowledgeBase.load(), landmarker_name="fake")
    return runner, image


def test_analysis_failure_publishes_and_throttles(monkeypatch, caplog):
    from skin_analyzer.pipeline import runner as module
    runner, image = empty_runner(monkeypatch)
    clock = [100.0]
    monkeypatch.setattr(module.time, "monotonic", lambda: clock[0])

    def fail(*_):
        raise ValueError("private path")
    monkeypatch.setattr(runner.analyzer, "process", fail)
    for index in range(3):
        runner._process(image, time.time(), index)
    header, jpeg = decode_frame_message(runner.latest_packet()[1])
    assert header["face"] is None and header["tracks"] == []
    assert jpeg.startswith(b"\xff\xd8")
    assert runner.health()["error"] == "analysis failed: ValueError"
    records = [r for r in caplog.records if r.getMessage().startswith("analysis failed")]
    assert len(records) == 1 and records[0].exc_info
    clock[0] += 5
    runner._process(image, time.time(), 4)
    assert "2 suppressed" in caplog.records[-1].getMessage()


@pytest.mark.parametrize("stage", ["generate_report", "report_to_dict"])
def test_report_failure_persists_and_is_interval_limited(monkeypatch, stage):
    from skin_analyzer.pipeline import runner as module
    runner, image = empty_runner(monkeypatch)
    original = getattr(module, stage)
    calls = []

    def fail(*args, **kwargs):
        calls.append(1)
        raise RuntimeError("secret")
    monkeypatch.setattr(module, stage, fail)
    runner._process(image, time.time(), 1)
    runner._process(image, time.time(), 2)
    assert calls == [1]
    assert runner.health()["error"] == "report failed: RuntimeError"
    monkeypatch.setattr(module, stage, original)
    runner._last_report = 0
    runner._process(image, time.time(), 3)
    assert runner.health()["error"] is None


@pytest.mark.parametrize("raises", [False, True])
def test_encoding_failure_drops_frame(monkeypatch, raises):
    from skin_analyzer.pipeline import runner as module
    runner, image = empty_runner(monkeypatch)

    def fail(*_):
        if raises:
            raise ValueError("secret")
        return False, None
    monkeypatch.setattr(module.cv2, "imencode", fail)
    runner._process(image, time.time(), 1)
    assert runner.latest_packet() is None
    assert runner.health()["error"].startswith("encoding failed:")


def test_listeners_restart_and_stop(monkeypatch):
    runner, image = empty_runner(monkeypatch)
    notifications = queue.Queue()

    def broken():
        raise ValueError("listener")
    runner.add_listener(broken)
    unsubscribe = runner.add_listener(lambda: notifications.put(threading.current_thread()))
    runner.start()
    runner.source.frames.put((image, time.time(), 1))
    assert notifications.get(timeout=5) is runner._thread
    assert notifications.get(timeout=5) is runner._thread
    assert runner.is_running
    assert runner.health()["landmarker"] == "fake"
    version = runner.latest_packet()[0]
    runner.stop()
    assert notifications.get(timeout=5) is threading.current_thread()
    assert notifications.empty()
    assert not runner.is_running
    assert runner.wait_packet(version, 0.1) is None
    unsubscribe()
    unsubscribe()
    runner.start()
    try:
        runner.source.frames.put((image, time.time(), 2))
        assert runner.wait_packet(version, 5) is not None
        assert notifications.empty()
    finally:
        runner.stop()


def test_restart_recreates_default_source(monkeypatch):
    runner, image = empty_runner(monkeypatch)
    sources = []

    def source_factory():
        source = QueuedSource(image)
        sources.append(source)
        return source
    runner._source_factory = source_factory
    runner.start()
    runner.stop()
    runner.start()
    try:
        assert runner.source is sources[0]
        runner.source.frames.put((image, time.time(), 1))
        assert runner.wait_packet(0, 5) is not None
    finally:
        runner.stop()


def test_stop_bounds_hung_read(monkeypatch, caplog):
    runner, _ = empty_runner(monkeypatch)
    entered, release = threading.Event(), threading.Event()

    def hang(timeout):
        entered.set()
        release.wait(10)
        return None
    monkeypatch.setattr(runner.source, "read", hang)
    notifications = []
    runner.add_listener(lambda: notifications.append(runner.is_running))
    runner.start()
    assert entered.wait(5)
    start = time.monotonic()
    try:
        runner.stop()
        assert time.monotonic() - start < 3.5
        assert notifications == [False]
        assert "shutdown timed out" in caplog.text
        with pytest.raises(RuntimeError, match="has not stopped"):
            runner.start()
    finally:
        release.set()
        runner._thread.join(5)
    assert notifications == [False]


def test_wait_packet_wakes_on_stop(monkeypatch):
    runner, _ = empty_runner(monkeypatch)
    waiting, finished = threading.Event(), threading.Event()
    results = []
    original_wait = runner._condition.wait

    def wait(timeout=None):
        waiting.set()
        return original_wait(timeout)

    monkeypatch.setattr(runner._condition, "wait", wait)

    def receive():
        results.append(runner.wait_packet(0, 10))
        finished.set()

    thread = threading.Thread(target=receive, daemon=True)
    thread.start()
    assert waiting.wait(5)
    start = time.monotonic()
    runner.stop()
    assert finished.wait(0.5)
    assert time.monotonic() - start < 0.5
    thread.join(1)
    assert results == [None]


@pytest.mark.parametrize("fails", [False, True])
def test_close_releases_resources_once(monkeypatch, caplog, fails):
    runner, _ = empty_runner(monkeypatch)
    calls = []

    def close_landmarker():
        calls.append("landmarker")
        if fails:
            raise RuntimeError("close failed")

    monkeypatch.setattr(runner.analyzer.landmarker, "close", close_landmarker)
    monkeypatch.setattr(runner.source, "close", lambda: calls.append("source"))
    runner.close()
    runner.close()
    assert calls == ["source", "landmarker"]
    if fails:
        assert "Landmarker close failed" in caplog.text
    with pytest.raises(RuntimeError, match="closed"):
        runner.start()
