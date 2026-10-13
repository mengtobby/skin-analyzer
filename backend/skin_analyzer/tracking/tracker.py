"""Greedy lesion association and lifecycle management in the canonical face frame."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, replace
import logging
import math
from typing import Sequence

import numpy as np

from ..domain import Detection, DetectionClass, FaceFrame, FaceZone, Point, Track
from . import kalman

logger = logging.getLogger(__name__)
_INFLAMMATORY = frozenset({DetectionClass.PAPULE, DetectionClass.PUSTULE,
                          DetectionClass.RED_MARK, DetectionClass.NODULE})


@dataclass(frozen=True)
class TrackerParams:
    gate_units: float = 0.05
    min_hits: int = 3
    confirm_window: int = 6
    max_misses: int = 12
    face_lost_timeout_s: float = 1.5
    process_noise: float = 1e-4
    measurement_noise: float = 4e-4
    confidence_alpha: float = 0.3

    def __post_init__(self) -> None:
        values = (self.gate_units, self.face_lost_timeout_s, self.process_noise,
                  self.measurement_noise, self.confidence_alpha)
        if not all(math.isfinite(x) for x in values):
            raise ValueError("Tracker parameters must be finite")
        if min(self.gate_units, self.face_lost_timeout_s, self.process_noise) < 0:
            raise ValueError("Gates, timeout and process noise must be nonnegative")
        if self.measurement_noise <= 0 or not 0 < self.confidence_alpha <= 1:
            raise ValueError("Invalid measurement noise or confidence alpha")
        if any(type(x) is not int for x in (self.min_hits, self.confirm_window, self.max_misses)):
            raise ValueError("Lifecycle parameters must be integers")
        if self.min_hits < 1 or self.confirm_window < self.min_hits or self.max_misses < 0:
            raise ValueError("Invalid lifecycle parameters")


@dataclass(frozen=True)
class _Tracked:
    track_id: int
    state: kalman.KalmanState
    labels: tuple[DetectionClass, ...]
    confidence: float
    contour: tuple[Point, ...]
    zone: FaceZone
    radius: float
    age: int = 1
    hits: int = 1
    misses: int = 0
    confirmed: bool = False

    @property
    def label(self) -> DetectionClass:
        return Counter(self.labels).most_common(1)[0][0]


def _validate_frame(frame: FaceFrame) -> None:
    if not math.isfinite(frame.scale) or frame.scale <= 0:
        raise ValueError("Face scale must be positive and finite")
    vectors = [np.asarray(x) for x in (frame.origin, frame.axis_u, frame.axis_v)]
    if any(x.shape != (2,) or not np.isfinite(x).all() for x in vectors):
        raise ValueError("Face vectors must be finite two-dimensional vectors")
    axes = np.stack(vectors[1:])
    if not np.allclose(axes @ axes.T, np.eye(2), atol=1e-5):
        raise ValueError("Face axes must be orthonormal")


def _measurement(detection: Detection, frame: FaceFrame) -> tuple[Point, tuple[Point, ...], float]:
    if not isinstance(detection.label, DetectionClass) or not isinstance(detection.zone, FaceZone):
        raise ValueError("Detection label and zone must be domain enums")
    values = (*detection.bbox, detection.confidence, detection.area_px)
    if len(detection.bbox) != 4 or not np.isfinite(values).all():
        raise ValueError("Detection values must be finite")
    if min(detection.bbox[2:]) < 0 or detection.area_px < 0 or not 0 <= detection.confidence <= 1:
        raise ValueError("Invalid detection dimensions, area or confidence")
    points = np.asarray(detection.contour, dtype=float)
    if points.ndim != 2 or points.shape[1] != 2 or not len(points) or not np.isfinite(points).all():
        raise ValueError("Detection contour must contain finite points")
    center = tuple(float(x) for x in frame.to_canonical(np.asarray(detection.center))[0])
    contour = tuple((float(x), float(y)) for x, y in frame.to_canonical(points))
    return center, contour, math.sqrt(detection.area_px / math.pi) / frame.scale


class LesionTracker:
    def __init__(self, params: TrackerParams | None = None) -> None:
        self.params = params if params is not None else TrackerParams()
        self.reset()

    def reset(self) -> None:
        self._next_id = 1
        self.clear()

    def clear(self) -> None:
        """Discard tracks and lifecycle state while preserving the next track id."""
        self._tracks: dict[int, _Tracked] = {}
        self._last_face: float | None = None
        self._lost_since: float | None = None

    def update(self, detections: Sequence[Detection], frame: FaceFrame | None,
               timestamp: float) -> list[Track]:
        if not math.isfinite(timestamp):
            raise ValueError("Timestamp must be finite")
        if frame is None:
            if self._lost_since is None:
                self._lost_since = self._last_face if self._last_face is not None else timestamp
            self._expire_lost(timestamp)
            return []
        _validate_frame(frame)
        measurements = [_measurement(d, frame) for d in detections]
        self._expire_lost(timestamp)
        self._lost_since = None
        self._last_face = timestamp
        predicted = {i: replace(t, state=kalman.predict(t.state, timestamp, self.params.process_noise),
                                age=t.age + 1) for i, t in self._tracks.items()}
        matches = self._associate(predicted, detections, measurements)
        self._tracks = self._advance(predicted, matches, detections, measurements)
        for index, detection in enumerate(detections):
            if index not in matches.values():
                self._spawn(detection, measurements[index], timestamp)
        return [self._output(t, frame) for _, t in sorted(self._tracks.items()) if t.confirmed]

    def _expire_lost(self, timestamp: float) -> None:
        if self._lost_since is not None and timestamp - self._lost_since > self.params.face_lost_timeout_s:
            if self._tracks:
                logger.debug("Clearing lesion tracks after face loss")
            self._tracks.clear()

    def project(self, frame: FaceFrame, timestamp: float) -> list[Track]:
        """Reproject confirmed filtered tracks without advancing temporal state."""
        if not math.isfinite(timestamp):
            raise ValueError("Timestamp must be finite")
        _validate_frame(frame)
        return [self._output(t, frame) for _, t in sorted(self._tracks.items()) if t.confirmed]

    def _associate(self, tracks: dict[int, _Tracked], detections: Sequence[Detection],
                   measurements: list[tuple[Point, tuple[Point, ...], float]]) -> dict[int, int]:
        candidates: list[tuple[float, int, int]] = []
        for track_id, track in tracks.items():
            for index, detection in enumerate(detections):
                compatible = track.label == detection.label or (
                    track.label in _INFLAMMATORY and detection.label in _INFLAMMATORY)
                distance = math.dist(track.state.mean[:2], measurements[index][0])
                if compatible and distance <= max(self.params.gate_units, 0.6 * track.radius):
                    candidates.append((distance, track_id, index))
        matches: dict[int, int] = {}
        used: set[int] = set()
        for _, track_id, index in sorted(candidates):
            if track_id not in matches and index not in used:
                matches[track_id] = index
                used.add(index)
        return matches

    def _advance(self, tracks: dict[int, _Tracked], matches: dict[int, int],
                 detections: Sequence[Detection],
                 measurements: list[tuple[Point, tuple[Point, ...], float]]) -> dict[int, _Tracked]:
        result: dict[int, _Tracked] = {}
        for track_id, track in tracks.items():
            if track_id in matches:
                index = matches[track_id]
                center, contour, radius = measurements[index]
                detection = detections[index]
                alpha = self.params.confidence_alpha
                track = replace(track, state=kalman.update(track.state, center, self.params.measurement_noise),
                                labels=(*track.labels, detection.label)[-15:],
                                confidence=(1 - alpha) * track.confidence + alpha * detection.confidence,
                                contour=contour, radius=radius, zone=detection.zone,
                                hits=track.hits + 1, misses=0)
                if track.hits >= self.params.min_hits and track.age <= self.params.confirm_window:
                    track = replace(track, confirmed=True)
            else:
                track = replace(track, misses=track.misses + 1)
            expired = (track.confirmed and track.misses > self.params.max_misses) or (
                not track.confirmed and track.age >= self.params.confirm_window)
            if not expired:
                result[track_id] = track
        return result

    def _spawn(self, detection: Detection, measurement: tuple[Point, tuple[Point, ...], float],
               timestamp: float) -> None:
        center, contour, radius = measurement
        self._tracks[self._next_id] = _Tracked(
            self._next_id, kalman.initialize(center, timestamp, self.params.measurement_noise),
            (detection.label,), detection.confidence, contour, detection.zone, radius,
            confirmed=self.params.min_hits == 1)
        self._next_id += 1

    def _output(self, track: _Tracked, frame: FaceFrame) -> Track:
        contour = np.asarray(track.contour)
        center = (contour.min(axis=0) + contour.max(axis=0)) / 2
        contour = contour + np.asarray(track.state.mean[:2]) - center
        points = frame.to_image(contour)
        minimum, maximum = points.min(axis=0), points.max(axis=0)
        bbox = (*minimum, *(maximum - minimum))
        return Track(track.track_id, track.label, track.confidence, tuple(float(x) for x in bbox),
                     tuple((float(x), float(y)) for x, y in points), track.zone,
                     track.state.mean[:2], 180 * track.radius, track.age, track.hits,
                     track.misses, track.confirmed)
