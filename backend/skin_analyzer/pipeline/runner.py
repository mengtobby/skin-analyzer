"""Threaded pipeline and latest-value publication."""
from __future__ import annotations

import copy
from collections.abc import Callable
import logging
import math
import threading
import time

import cv2
import numpy as np

from ..config import Settings
from ..capture import FrameSource, create_source
from ..knowledge import KnowledgeBase, generate_report, report_to_dict
from .analyzer import FrameAnalyzer, FrameResult
from .protocol import build_frame_header, encode_frame_message

logger = logging.getLogger(__name__)
DELIVERY_WINDOW_S = 2.0
LOG_INTERVAL_S = 5.0


class PipelineRunner:
    def __init__(self, settings: Settings, source: FrameSource, analyzer: FrameAnalyzer,
                 kb: KnowledgeBase, onnx_providers: tuple[str, ...] = (),
                 detector_name: str = "", preprocessor_name: str = "",
                 landmarker_name: str = "mediapipe-face-landmarker") -> None:
        self.settings, self.source, self.analyzer, self.kb = settings, source, analyzer, kb
        self.onnx_providers = tuple(onnx_providers)
        self.detector_name, self.preprocessor_name = detector_name, preprocessor_name
        self._condition = threading.Condition()
        self._analysis_lock = threading.Lock()
        self._stop = threading.Event()
        self._stop_notified = False
        self._closed = False
        self._thread: threading.Thread | None = None
        self._packet: bytes | None = None
        self._version = self._report_version = 0
        self._report: dict | None = None
        self.landmarker_name = landmarker_name
        self._frame_error: tuple[float, str] | None = None
        self._report_error: tuple[float, str] | None = None
        self._listeners: dict[object, Callable[[], None]] = {}
        self._log_counts: dict[tuple[str, type], tuple[float, int]] = {}
        self._close_thread: threading.Thread | None = None
        self._source_factory: Callable[[], FrameSource] | None = None
        self._last_frame = 0.0
        self._fps = 0.0
        self._last_report = 0.0

    def start(self) -> None:
        with self._condition:
            if self._closed:
                raise RuntimeError("Pipeline runner is closed")
            if self._thread is not None and self._thread.is_alive():
                if self._stop.is_set():
                    raise RuntimeError("Previous pipeline worker has not stopped")
                return
            if self._close_thread and self._close_thread.is_alive():
                raise RuntimeError("Previous source close has not finished")
            if self._thread is not None and self._source_factory is not None:
                self.source = self._source_factory()
            self._stop = threading.Event()
            self._stop_notified = False
            self._close_thread = None
            self._last_frame = self._last_report = self._fps = 0.0
            self.source.start()
            self._thread = threading.Thread(target=self._run, daemon=True, name="skin-pipeline")
            self._thread.start()

    def stop(self) -> None:
        self._notify_stop()
        deadline = time.monotonic() + 3.0
        with self._condition:
            if self._close_thread is None:
                self._close_thread = threading.Thread(target=self._close_source, daemon=True)
                self._close_thread.start()
        for thread in (self._thread, self._close_thread):
            if thread is not None and thread is not threading.current_thread():
                thread.join(max(0.0, deadline - time.monotonic()))
                if thread.is_alive():
                    logger.warning("Pipeline shutdown timed out: %s", thread.name)

    def _notify_stop(self) -> None:
        with self._condition:
            self._stop.set()
            self._condition.notify_all()
            if self._stop_notified:
                return
            self._stop_notified = True
        self._notify_listeners()

    def close(self) -> None:
        with self._condition:
            if self._closed:
                return
            self._closed = True
        self.stop()
        worker = self._thread
        if worker is not None and worker.is_alive():
            # stop() timed out: the worker may still be inside landmarker.detect(); closing the
            # native graph under it could crash. Leave it to process exit instead.
            logger.warning("Pipeline worker still running after stop(); skipping landmarker close")
            return
        try:
            close = getattr(self.analyzer.landmarker, "close", None)
            if callable(close):
                close()
        except Exception as exc:
            self._log_failure("Landmarker close failed", exc)

    def _close_source(self) -> None:
        try:
            self.source.close()
        except Exception as exc:
            self._log_failure("Source close failed", exc)

    @property
    def is_running(self) -> bool:
        with self._condition:
            return bool(self._thread and self._thread.is_alive() and not self._stop.is_set())

    def add_listener(self, callback: Callable[[], None]) -> Callable[[], None]:
        if not callable(callback):
            raise TypeError("listener must be callable")
        token = object()
        with self._condition:
            self._listeners[token] = callback

        def unsubscribe() -> None:
            with self._condition:
                self._listeners.pop(token, None)
        return unsubscribe

    def _notify_listeners(self) -> None:
        with self._condition:
            callbacks = tuple(self._listeners.values())
        for callback in callbacks:
            try:
                callback()
            except Exception as exc:
                self._log_failure("Listener failed", exc)

    def _log_failure(self, message: str, exc: Exception) -> None:
        key = (message, type(exc))
        now = time.monotonic()
        with self._condition:
            previous, suppressed = self._log_counts.get(key, (-math.inf, 0))
            if now - previous < LOG_INTERVAL_S:
                self._log_counts[key] = (previous, suppressed + 1)
                return
            self._log_counts[key] = (now, 0)
        logger.error("%s (%d suppressed)", message, suppressed,
                     exc_info=(type(exc), exc, exc.__traceback__))

    def _set_error(self, category: str, exc: Exception) -> None:
        error = (time.monotonic(), f"{category} failed: {type(exc).__name__}")
        with self._condition:
            if category == "report":
                self._report_error = error
            else:
                self._frame_error = error
        self._log_failure(f"{category} failed", exc)

    def _run(self) -> None:
        try:
            self._run_frames()
        finally:
            self._notify_stop()

    def _run_frames(self) -> None:
        while not self._stop.is_set():
            try:
                frame = self.source.read(timeout=0.5)
                if frame is None or self._stop.is_set():
                    continue
                with self._analysis_lock:
                    self._process(*frame)
            except Exception as exc:
                self._set_error("frame", exc)
                self._stop.wait(0.01)

    def _process(self, frame: np.ndarray, timestamp: float, frame_id: int) -> None:
        try:
            result = self.analyzer.process(frame, timestamp)
        except Exception as exc:
            self._set_error("analysis", exc)
            result = FrameResult(None, [], None, {})
        else:
            with self._condition:
                self._frame_error = None
        encoded_frame = self._encode(frame)
        if encoded_frame is None:
            return
        jpeg, encode_ms = encoded_frame
        now = time.monotonic()
        if self._last_frame:
            instant = 1 / max(now - self._last_frame, 1e-6)
            self._fps = instant if not self._fps else 0.1 * instant + 0.9 * self._fps
        header = build_frame_header(result, frame_id, timestamp, frame.shape[1], frame.shape[0],
                                    self._fps, max(0, (time.time() - timestamp) * 1000), encode_ms)
        packet = encode_frame_message(header, jpeg)
        with self._condition:
            self._last_frame = now
            self._packet = packet
            self._version += 1
            self._condition.notify_all()
        self._notify_listeners()
        if now - self._last_report >= self.settings.report_interval_s:
            self._last_report = now
            self._publish_report(result)

    def _encode(self, frame: np.ndarray) -> tuple[bytes, float] | None:
        start = time.perf_counter()
        try:
            ok, encoded = cv2.imencode(".jpg", frame,
                                      [cv2.IMWRITE_JPEG_QUALITY, self.settings.jpeg_quality])
            if not ok:
                raise RuntimeError("JPEG encoding returned no image")
        except Exception as exc:
            self._set_error("encoding", exc)
            return None
        encode_ms = (time.perf_counter() - start) * 1000
        return encoded.tobytes(), encode_ms

    def _publish_report(self, result: FrameResult) -> None:
        try:
            tracks, metrics = result.tracks, result.metrics
            face_detected = result.region is not None
            if result.quality is not None and not result.quality.ok:
                accepted = self.analyzer.last_good()
                if accepted is None:
                    return
                tracks, metrics = accepted
                face_detected = True
            report = report_to_dict(generate_report(tracks, metrics, self.kb,
                                                    now=time.time(), face_detected=face_detected))
        except Exception as exc:
            self._set_error("report", exc)
            return
        with self._condition:
            self._report_error = None
            old = {k: v for k, v in (self._report or {}).items() if k != "generated_at"}
            new = {k: v for k, v in report.items() if k != "generated_at"}
            changed = old != new
            if changed:
                self._report, self._report_version = report, self._report_version + 1
        if changed:
            self._notify_listeners()

    def latest_packet(self) -> tuple[int, bytes] | None:
        with self._condition:
            return None if self._packet is None else (self._version, self._packet)

    def wait_packet(self, after_version: int, timeout: float) -> tuple[int, bytes] | None:
        if type(after_version) is not int or after_version < 0 or not math.isfinite(timeout) or timeout < 0:
            raise ValueError("version and timeout must be nonnegative")
        with self._condition:
            self._condition.wait_for(
                lambda: self._version > after_version or self._stop.is_set(), timeout)
            if not self._stop.is_set() and self._version > after_version and self._packet is not None:
                return self._version, self._packet
            return None

    def latest_report(self) -> tuple[int, dict] | None:
        with self._condition:
            return None if self._report is None else (self._report_version, copy.deepcopy(self._report))

    def health(self) -> dict:
        info = self.source.info()
        with self._condition:
            delivering = self._last_frame and time.monotonic() - self._last_frame < DELIVERY_WINDOW_S
            errors = [e for e in (self._frame_error, self._report_error) if e is not None]
            error = max(errors, key=lambda e: e[0])[1] if errors else (
                "capture failed" if info.error else None)
            return {"status": "ok" if info.opened and delivering else "degraded",
                    "source": info.spec, "camera_open": info.opened,
                    "frame_size": [info.width, info.height], "detector": self.detector_name,
                    "preprocessor": self.preprocessor_name, "onnx_providers": list(self.onnx_providers),
                    "landmarker": self.landmarker_name, "error": error}

    def reset(self) -> None:
        with self._analysis_lock:
            self.analyzer.reset()
            with self._condition:
                self._packet = None
                self._report = None
                self._last_report = 0.0


def build_default_runner(settings: Settings) -> PipelineRunner:
    from ..face.landmarker import MediaPipeLandmarker
    from ..preprocessing import create_preprocessor
    from ..detection import create_detector
    from ..tracking import LesionTracker
    from ..metrics import MetricsSmoother

    try:
        import onnxruntime
        providers = tuple(onnxruntime.get_available_providers())
    except ImportError:
        providers = ()
    preprocessor = create_preprocessor(settings.preprocess)
    detector = create_detector(settings.detector, settings.detector_model)
    kb = KnowledgeBase.load()
    landmarker = MediaPipeLandmarker(settings.landmarker_model)
    analyzer = FrameAnalyzer(landmarker, preprocessor, detector, LesionTracker(),
                             MetricsSmoother(), mirrored=settings.mirror)
    source = create_source(settings.source, settings.width, settings.height,
                           settings.fps, settings.mirror)
    runner = PipelineRunner(settings, source, analyzer, kb, providers, detector.name, preprocessor.name)
    runner._source_factory = lambda: create_source(
        settings.source, settings.width, settings.height, settings.fps, settings.mirror)
    return runner
