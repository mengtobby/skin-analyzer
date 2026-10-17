"""Landmarker behavior with synthetic images and fake MediaPipe tasks."""
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import numpy as np
import pytest

from skin_analyzer.face.landmarker import MediaPipeLandmarker


def test_missing_model(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="download_models"):
        MediaPipeLandmarker(tmp_path / "missing.task")


@pytest.mark.parametrize("confidence", [0.5, 0.73])
def test_task_options_detection_timestamps_and_close(monkeypatch, tmp_path, confidence):
    model = tmp_path / "fake.task"
    model.touch()
    options = []
    calls = []
    closed = []
    points = [SimpleNamespace(x=0.25, y=0.75), SimpleNamespace(x=1.0, y=0.0)]
    results = iter([SimpleNamespace(face_landmarks=[points]),
                    SimpleNamespace(face_landmarks=[]), SimpleNamespace(face_landmarks=[])])

    def detect(image, timestamp):
        calls.append((image, timestamp))
        return next(results)

    task = SimpleNamespace(detect_for_video=detect, close=lambda: closed.append(True))
    vision = SimpleNamespace(
        RunningMode=SimpleNamespace(VIDEO="video"),
        FaceLandmarkerOptions=lambda **kwargs: options.append(kwargs) or kwargs,
        FaceLandmarker=SimpleNamespace(create_from_options=lambda actual: task),
    )
    mp = ModuleType("mediapipe")
    mp.ImageFormat = SimpleNamespace(SRGB="srgb")
    mp.Image = lambda **kwargs: SimpleNamespace(**kwargs)
    tasks = ModuleType("mediapipe.tasks")
    python = ModuleType("mediapipe.tasks.python")
    python.BaseOptions = lambda **kwargs: kwargs
    python.vision = vision
    for name, value in [("mediapipe", mp), ("mediapipe.tasks", tasks),
                        ("mediapipe.tasks.python", python)]:
        monkeypatch.setitem(sys.modules, name, value)
    wrapper = MediaPipeLandmarker(model, confidence)
    assert options == [dict(base_options={"model_asset_path": str(model)},
                            running_mode="video", num_faces=1,
                            min_face_detection_confidence=confidence,
                            min_face_presence_confidence=confidence,
                            min_tracking_confidence=confidence)]
    bgr = np.full((4, 8, 3), [10, 20, 30], dtype=np.uint8)
    actual = wrapper.detect(bgr, 10)
    np.testing.assert_array_equal(actual, [[2, 3], [8, 0]])
    assert actual.dtype == np.float64
    assert wrapper.detect(bgr, 10) is None
    assert wrapper.detect(bgr, 2) is None
    assert [ts for _, ts in calls] == [10, 11, 12]
    for image, _ in calls:
        assert image.image_format == "srgb"
        assert image.data.flags.c_contiguous
        np.testing.assert_array_equal(image.data, bgr[..., ::-1])
    wrapper.close()
    assert closed == [True]
