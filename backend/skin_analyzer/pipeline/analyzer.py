"""Single-frame analysis with temporal state."""
from dataclasses import dataclass
import math
from time import perf_counter

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


class FrameAnalyzer:
    def __init__(self, landmarker: Landmarker, preprocessor: Preprocessor,
                 detector: Detector, tracker: LesionTracker, smoother: MetricsSmoother,
                 canvas: CanvasSpec = CanvasSpec(), mirrored: bool = True) -> None:
        self.landmarker, self.preprocessor, self.detector = landmarker, preprocessor, detector
        self.tracker, self.smoother = tracker, smoother
        self.canvas, self.mirrored = canvas, mirrored
        self._filter = face.OneEuroFilter()
        self._gains: np.ndarray | None = None

    def reset(self) -> None:
        self.tracker.reset()
        self.smoother.reset()
        self._filter.reset()
        self._gains = None

    def process(self, frame_bgr: np.ndarray, timestamp: float) -> FrameResult:
        if (frame_bgr.dtype != np.uint8 or frame_bgr.ndim != 3
                or frame_bgr.shape[2] != 3 or not frame_bgr.size or not math.isfinite(timestamp)):
            raise ValueError("expected a nonempty uint8 BGR frame and finite timestamp")
        stages = dict.fromkeys(("landmarks", "preprocess", "detect", "track", "metrics"), 0.0)
        start = perf_counter()
        landmarks = self.landmarker.detect(frame_bgr, int(timestamp * 1000))
        if landmarks is None:
            self._filter.reset()
            self._gains = None
            stages["landmarks"] = (perf_counter() - start) * 1000
            start = perf_counter()
            tracks = self.tracker.update([], None, timestamp)
            stages["track"] = (perf_counter() - start) * 1000
            self.smoother.update(None)
            return FrameResult(None, tracks, None, stages)
        landmarks = np.asarray(landmarks)
        if landmarks.ndim != 2 or landmarks.shape[1] != 2 or landmarks.shape[0] < 468 or not np.isfinite(landmarks).all():
            raise ValueError("expected finite face landmarks with shape (N, 2), N >= 468")
        scale = face.face_frame_from_landmarks(landmarks).scale
        region = face.build_face_region(self._filter(landmarks, timestamp, scale),
                                        self.canvas, self.mirrored)
        stages["landmarks"] = (perf_counter() - start) * 1000
        start = perf_counter()
        canvas = face.warp_to_canvas(frame_bgr, region)
        gains = np.asarray(self.preprocessor.estimate_gains(canvas))
        self._gains = gains if self._gains is None else 0.1 * gains + 0.9 * self._gains
        pre = self.preprocessor.process(canvas, tuple(float(v) for v in self._gains))
        zones = face.refine_zone_map(region.zone_map, pre.lab)
        stages["preprocess"] = (perf_counter() - start) * 1000
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
        return FrameResult(region, tracks, metrics, stages)
