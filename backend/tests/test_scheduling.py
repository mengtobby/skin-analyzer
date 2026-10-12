"""Quality gating and independent analysis cadence with synthetic capture."""
import cv2
import numpy as np
import pytest

from skin_analyzer.face import QualityParams
from skin_analyzer.pipeline import FrameAnalyzer
from skin_analyzer.pipeline.protocol import build_frame_header
from skin_analyzer.tracking import LesionTracker, TrackerParams
from .test_pipeline import make_analyzer
from .test_tracking import detection


def seeded_analyzer(monkeypatch):
    analyzer, image = make_analyzer()
    analyzer.tracker = LesionTracker(TrackerParams(min_hits=1))
    calls = []

    def detect(inputs):
        calls.append(inputs)
        return [detection(inputs.region.frame)]

    monkeypatch.setattr(analyzer.detector, "detect", detect)
    return analyzer, image, calls


def test_cadence_projects_every_frame(monkeypatch):
    analyzer, image, calls = seeded_analyzer(monkeypatch)
    results = [analyzer.process(image, i / 30) for i in range(6)]
    assert len(calls) == 3
    assert [r.analyzed for r in results] == [True, False] * 3
    assert [r.tracks[0].hits for r in results] == [1, 1, 2, 2, 3, 3]
    for first, second in zip(results[::2], results[1::2]):
        assert first.quality.ok and second.quality is first.quality
        assert second.metrics is first.metrics
        assert second.stages_ms["preprocess"] == second.stages_ms["quality"] == 0
    assert build_frame_header(results[1], 1, 0, 640, 480)["analyzed"] is False


def test_dark_frame_freezes_tracks_and_metrics(monkeypatch):
    analyzer, image, calls = seeded_analyzer(monkeypatch)
    analyzer.analysis_every = 1
    first = analyzer.process(image, 0)
    assert first.quality.ok and first.metrics is not None
    smoother_state = analyzer.smoother._last
    tracker_state = dict(analyzer.tracker._tracks)
    monkeypatch.setattr(analyzer.tracker, "update", lambda *_: pytest.fail("tracker advanced"))
    monkeypatch.setattr(analyzer.smoother, "update", lambda *_: pytest.fail("metrics advanced"))
    analyzer.landmarker.landmarks = analyzer.landmarker.landmarks + np.array([5, 3])
    dark = analyzer.process(np.zeros_like(image), 1 / 30)
    assert "too_dark" in dark.quality.issues and not dark.quality.ok
    assert dark.metrics is None and len(calls) == 1 and dark.analyzed
    assert dark.tracks == analyzer.tracker.project(dark.region.frame, 1 / 30)
    assert dark.tracks[0].bbox != first.tracks[0].bbox
    assert analyzer.tracker._tracks == tracker_state
    assert analyzer.smoother._last is smoother_state
    analyzer.analysis_every = 3
    skipped = analyzer.process(image, 2 / 30)
    assert not skipped.analyzed and skipped.metrics is None
    assert skipped.quality is dark.quality


def test_roi_and_reset(monkeypatch):
    analyzer, image, calls = seeded_analyzer(monkeypatch)
    process = analyzer.preprocessor.process
    masks = []

    def capture(bgr, wb_gains=None, roi_mask=None):
        masks.append(roi_mask.copy())
        return process(bgr, wb_gains, roi_mask)

    monkeypatch.setattr(analyzer.preprocessor, "process", capture)
    result = analyzer.process(image, 0)
    expected = cv2.dilate((result.region.zone_map > 0).astype(np.uint8),
                          np.ones((11, 11), np.uint8)).astype(bool)
    assert np.array_equal(masks[0], expected)
    analyzer.reset()
    assert analyzer.process(image, 1).analyzed and len(calls) == 2


@pytest.mark.parametrize("cadence", [0, -1, True, 1.5])
def test_invalid_cadence(cadence):
    analyzer, _ = make_analyzer()
    with pytest.raises(ValueError, match="analysis_every"):
        FrameAnalyzer(analyzer.landmarker, analyzer.preprocessor, analyzer.detector,
                      analyzer.tracker, analyzer.smoother, analysis_every=cadence)


def test_quality_params_and_no_face():
    analyzer, image = make_analyzer()
    analyzer.quality_params = QualityParams(min_face_size_px=1000)
    result = analyzer.process(image, 0)
    assert "too_far" in result.quality.issues and result.metrics is None
    analyzer.landmarker.landmarks = None
    lost = analyzer.process(image, 1)
    assert lost.quality is None and not lost.analyzed
