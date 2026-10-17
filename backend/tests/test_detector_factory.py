"""Detector selection never loads a real learned model."""
from types import SimpleNamespace

import pytest

from skin_analyzer import detection
from skin_analyzer.detection import onnx_yolo
from skin_analyzer.domain import DetectionClass


@pytest.mark.parametrize("kind", ["classical", "auto"])
@pytest.mark.parametrize("path_kind", ["none", "missing", "directory"])
def test_without_model(kind, path_kind, tmp_path):
    path = {"none": None, "missing": tmp_path / "missing.onnx", "directory": tmp_path}[path_kind]
    assert isinstance(detection.create_detector(kind, path), detection.ClassicalDetector)


@pytest.mark.parametrize("path_kind", ["none", "missing"])
def test_forced_missing_model(path_kind, tmp_path):
    with pytest.raises(FileNotFoundError, match="ONNX model not found"):
        detection.create_detector("onnx", None if path_kind == "none" else tmp_path / "missing")


def test_invalid_name():
    with pytest.raises(ValueError, match="Unknown detector"):
        detection.create_detector("invalid")


@pytest.mark.parametrize("kind", ["auto", "onnx"])
def test_model_combines_complementary_detectors(kind, monkeypatch, tmp_path):
    model = tmp_path / "fake.onnx"
    model.touch()
    learned_output, classical_output = object(), object()
    learned = SimpleNamespace(name="learned", detect=lambda inp: [learned_output])
    calls = []
    monkeypatch.setattr(onnx_yolo, "OnnxYoloSegDetector", lambda path: calls.append(path) or learned)
    result = detection.create_detector(kind, model)
    assert calls == [model]
    assert isinstance(result, detection.CompositeDetector)
    assert result.detectors[0] is learned
    classical = result.detectors[1]
    assert classical.p.enabled == frozenset(DetectionClass) - detection.LEARNED_CLASSES
    monkeypatch.setattr(classical, "detect", lambda inp: [classical_output])
    assert result.name == f"learned+{classical.name}"
    assert result.detect(object()) == [learned_output, classical_output]


@pytest.mark.parametrize("kind", ["auto", "onnx"])
def test_model_load_failure(kind, monkeypatch, tmp_path, caplog):
    model = tmp_path / "fake.onnx"
    model.touch()

    def fail(path):
        raise RuntimeError("fake model failure")

    monkeypatch.setattr(onnx_yolo, "OnnxYoloSegDetector", fail)
    if kind == "onnx":
        with pytest.raises(RuntimeError, match="fake model failure"):
            detection.create_detector(kind, model)
    else:
        assert isinstance(detection.create_detector(kind, model), detection.ClassicalDetector)
        assert "falling back" in caplog.text

