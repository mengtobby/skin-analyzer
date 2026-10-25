"""Runner cap wiring without models or physical capture devices."""
from types import SimpleNamespace

import numpy as np
import pytest

from skin_analyzer.config import Settings
from skin_analyzer.capture import CameraSource
from skin_analyzer.pipeline import runner as module


@pytest.mark.parametrize("cap", [0, 640, 1280])
def test_runner_cap_startup_switch_and_restart_factory(monkeypatch, cap):
    monkeypatch.setattr("skin_analyzer.face.landmarker.MediaPipeLandmarker", lambda *a: object())
    monkeypatch.setattr("skin_analyzer.preprocessing.create_preprocessor", lambda *a: SimpleNamespace(name="fake"))
    monkeypatch.setattr("skin_analyzer.detection.create_detector", lambda *a: SimpleNamespace(name="fake"))
    monkeypatch.setattr(module.KnowledgeBase, "load", lambda: None)
    monkeypatch.setattr(module, "FrameAnalyzer", lambda *a, **kw: SimpleNamespace(reset=lambda: None))
    # Publish synthetic input on start; retain the real source factory and publish path.
    monkeypatch.setattr(CameraSource, "start", lambda self: self._publish(np.zeros((1080, 1920, 3), np.uint8)))
    runner = module.build_default_runner(Settings(max_frame_side=cap))
    assert runner.source._max_side == cap
    runner.switch_source("camera:1")
    assert runner.source._max_side == cap
    assert runner.health()["frame_size"] == ([cap, round(1080 * cap / 1920)] if cap else [1920, 1080])
    restarted = runner._source_factory()
    assert restarted._max_side == cap
    assert restarted.info().spec == "camera:1"
