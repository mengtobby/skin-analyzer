"""Single-frame analysis with temporal state."""
from dataclasses import dataclass
import math
from time import perf_counter

import cv2
import numpy as np

from .. import face
from ..domain import CanvasSpec, FaceRegion, SkinMetrics, Track
from ..face.landmarker import Landmarker
from ..detection import Detector, DetectorInput
from ..preprocessing import Preprocessor
from ..tracking import LesionTracker
from ..metrics import MetricsSmoother, compute_metrics


@dataclass(frozen=True)
class FrameResult:
    region: FaceRegion | None
    tracks: list[Track]
    metrics: SkinMetrics | None
    stages_ms: dict[str, float]
    quality: face.QualityReport | None = None

    analyzed: bool = False


class FrameAnalyzer:
    def __init__(self, landmarker: Landmarker, preprocessor: Preprocessor,
                 detector: Detector, tracker: LesionTracker, smoother: MetricsSmoother,
                 canvas: CanvasSpec = CanvasSpec(), mirrored: bool = True,
                 analysis_every: int = 2, quality_params: face.QualityParams | None = None) -> None:
        if type(analysis_every) is not int or analysis_every < 1:
            raise ValueError("analysis_every must be a positive integer")
        self.landmarker, self.preprocessor, self.detector = landmarker, preprocessor, detector
        self.tracker, self.smoother = tracker, smoother
        self.canvas, self.mirrored = canvas, mirrored
        self.analysis_every, self.quality_params = analysis_every, quality_params
        self._filter = face.OneEuroFilter()
        self._gains: np.ndarray | None = None
        self._frame_index = 0
        self._quality: face.QualityReport | None = None
        self._metrics: SkinMetrics | None = None
        self._last_ok_timestamp: float | None = None
        self._last_good: tuple[list[Track], SkinMetrics | None] | None = None
        self._face_lost_since: float | None = None
        self._last_face_seen: float | None = None

    def reset(self) -> None:
        self.tracker.reset()
        self.smoother.reset()
        self._filter.reset()
        self._gains = None
        self._frame_index = 0
        self._quality = None
        self._metrics = None
        self._last_ok_timestamp = None
        self._last_good = None
        self._face_lost_since = None
        self._last_face_seen = None

    def _invalidate_analysis(self) -> None:
        """Discard temporal state that could belong to a previous face."""
        self.tracker.clear()
        self._quality = None
        self._gains = None
        self._filter.reset()
        self._last_good = None
        self._last_ok_timestamp = None
        self._metrics = None
        self.smoother.reset()

    def _note_face_lost(self, timestamp: float) -> None:
        """Forget the last good analysis once the face has been gone past the timeout.

        A returning face may belong to someone else, so stale findings must not be
        republished for it; brief landmark dropouts keep the state.
        """
        if self._face_lost_since is None:
            self._face_lost_since = timestamp
        elif timestamp - self._face_lost_since > self.tracker.params.face_lost_timeout_s:
            self._invalidate_analysis()

    def last_good(self) -> tuple[list[Track], SkinMetrics | None] | None:
        """Return the latest accepted analysis with an independent track list."""
        if self._last_good is None:
            return None
        tracks, metrics = self._last_good
        return list(tracks), metrics

    def process(self, frame_bgr: np.ndarray, timestamp: float) -> FrameResult:
        if (frame_bgr.dtype != np.uint8 or frame_bgr.ndim != 3
                or frame_bgr.shape[2] != 3 or not frame_bgr.size or not math.isfinite(timestamp)):
            raise ValueError("expected a nonempty uint8 BGR frame and finite timestamp")
        analyze = self._frame_index % self.analysis_every == 0
        self._frame_index += 1
        stages = dict.fromkeys(("landmarks", "preprocess", "quality", "detect", "track", "metrics"), 0.0)
        start = perf_counter()
        landmarks = self.landmarker.detect(frame_bgr, int(timestamp * 1000))
        if landmarks is None:
            self._note_face_lost(timestamp)
            self._filter.reset()
            self._gains = None
            self._quality = None
            self._metrics = None
            stages["landmarks"] = (perf_counter() - start) * 1000
            start = perf_counter()
            tracks = self.tracker.update([], None, timestamp)
            stages["track"] = (perf_counter() - start) * 1000
            self.smoother.update(None)
            return FrameResult(None, tracks, None, stages)
        landmarks = np.asarray(landmarks)
        if landmarks.ndim != 2 or landmarks.shape[1] != 2 or landmarks.shape[0] < 468 or not np.isfinite(landmarks).all():
            raise ValueError("expected finite face landmarks with shape (N, 2), N >= 468")
        if (self._last_face_seen is not None and
                timestamp - self._last_face_seen > self.tracker.params.face_lost_timeout_s):
            self._invalidate_analysis()
        self._last_face_seen = timestamp
        self._face_lost_since = None
        scale = face.face_frame_from_landmarks(landmarks).scale
        region = face.build_face_region(self._filter(landmarks, timestamp, scale),
                                        self.canvas, self.mirrored)
        stages["landmarks"] = (perf_counter() - start) * 1000
        if not analyze:
            return self._project(region, timestamp, stages)
        return self._analyze(frame_bgr, region, timestamp, stages)

    def _project(self, region: FaceRegion, timestamp: float,
                 stages: dict[str, float]) -> FrameResult:
        start = perf_counter()
        rejected = self._quality is not None and not self._quality.ok
        hidden = rejected and (self._freeze_expired(timestamp) or
                               "turned_away" in self._quality.issues)
        tracks = [] if hidden else self.tracker.project(region.frame, timestamp)
        stages["track"] = (perf_counter() - start) * 1000
        metrics = self._metrics if self._quality is not None and self._quality.ok else None
        return FrameResult(region, tracks, metrics, stages, self._quality)

    def _freeze_expired(self, timestamp: float) -> bool:
        return (self._last_ok_timestamp is None or
                timestamp - self._last_ok_timestamp > self.tracker.params.face_lost_timeout_s)

    def _analyze(self, frame_bgr: np.ndarray, region: FaceRegion, timestamp: float,
                 stages: dict[str, float]) -> FrameResult:
        start = perf_counter()
        canvas = face.warp_to_canvas(frame_bgr, region)
        gains = np.asarray(self.preprocessor.estimate_gains(canvas))
        self._gains = gains if self._gains is None else 0.1 * gains + 0.9 * self._gains
        roi = cv2.dilate((region.zone_map > 0).astype(np.uint8),
                         np.ones((11, 11), np.uint8)).astype(bool)
        pre = self.preprocessor.process(canvas, tuple(float(v) for v in self._gains), roi_mask=roi)
        zones = face.refine_zone_map(region.zone_map, pre.lab)
        stages["preprocess"] = (perf_counter() - start) * 1000
        start = perf_counter()
        self._quality = face.assess_quality(region, pre.lab, zones, self.quality_params)
        stages["quality"] = (perf_counter() - start) * 1000
        if not self._quality.ok:
            if self._freeze_expired(timestamp):
                self.tracker.update([], region.frame, timestamp)
            return self._project(region, timestamp, stages)
        start = perf_counter()
        dets = self.detector.detect(DetectorInput(frame_bgr, region, pre.bgr, pre.lab,
                                                zones, pre.specular_mask))
        stages["detect"] = (perf_counter() - start) * 1000
        start = perf_counter()
        tracks = self.tracker.update(dets, region.frame, timestamp)
        stages["track"] = (perf_counter() - start) * 1000
        start = perf_counter()
        metrics = self.smoother.update(compute_metrics(pre.lab, zones, pre.specular_mask,
                                                       self.canvas.px_per_unit))
        stages["metrics"] = (perf_counter() - start) * 1000
        self._metrics = metrics
        self._last_ok_timestamp = timestamp
        self._last_good = (list(tracks), metrics)
        return FrameResult(region, tracks, metrics, stages, self._quality, analyzed=True)
