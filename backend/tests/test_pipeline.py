"""Camera-free end-to-end pipeline tests."""
import io
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
        time.sleep(0.02)
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
    time.sleep(0.005)
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
