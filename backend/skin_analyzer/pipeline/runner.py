"""Threaded pipeline and latest-value publication."""
from __future__ import annotations

import copy
import logging
import math
import threading
import time

import cv2
import numpy as np

from ..config import Settings
from ..capture import FrameSource, create_source
from ..knowledge import KnowledgeBase, generate_report, report_to_dict
from .analyzer import FrameAnalyzer
from .protocol import build_frame_header, encode_frame_message

logger = logging.getLogger(__name__)


class PipelineRunner:
    def __init__(self, settings: Settings, source: FrameSource, analyzer: FrameAnalyzer,
                 kb: KnowledgeBase, onnx_providers: tuple[str, ...] = (),
                 detector_name: str = "", preprocessor_name: str = "") -> None:
        self.settings, self.source, self.analyzer, self.kb = settings, source, analyzer, kb
        self.onnx_providers = tuple(onnx_providers)
        self.detector_name, self.preprocessor_name = detector_name, preprocessor_name
        self._condition = threading.Condition()
        self._analysis_lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._packet: bytes | None = None
        self._version = self._report_version = 0
        self._report: dict | None = None
        self._error: str | None = None
        self._last_frame = 0.0
        self._fps = 0.0
        self._last_report = 0.0

    def start(self) -> None:
        with self._condition:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop.clear()
            self.source.start()
            self._thread = threading.Thread(target=self._run, daemon=True, name="skin-pipeline")
            self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        with self._condition:
            self._condition.notify_all()
        self.source.close()
        if self._thread is not None:
            self._thread.join()
        close = getattr(self.analyzer.landmarker, "close", None)
        if close is not None:
            close()

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                frame = self.source.read(timeout=0.5)
                if frame is None:
                    continue
                with self._analysis_lock:
                    self._process(*frame)
            except Exception as exc:
                logger.exception("Pipeline frame failed")
                with self._condition:
                    self._error = str(exc)
                self._stop.wait(0.01)

    def _process(self, frame: np.ndarray, timestamp: float, frame_id: int) -> None:
        result = self.analyzer.process(frame, timestamp)
        start = time.perf_counter()
        ok, encoded = cv2.imencode(".jpg", frame,
                                  [cv2.IMWRITE_JPEG_QUALITY, self.settings.jpeg_quality])
        encode_ms = (time.perf_counter() - start) * 1000
        now = time.monotonic()
        if self._last_frame:
            instant = 1 / max(now - self._last_frame, 1e-6)
            self._fps = instant if not self._fps else 0.1 * instant + 0.9 * self._fps
        header = build_frame_header(result, frame_id, timestamp, frame.shape[1], frame.shape[0],
                                    self._fps, max(0, (time.time() - timestamp) * 1000), encode_ms)
        packet = encode_frame_message(header, encoded.tobytes() if ok else b"")
        with self._condition:
            self._last_frame = now
            self._error = None if ok else "JPEG encoding failed"
            self._packet = packet
            self._version += 1
            self._condition.notify_all()
        if now - self._last_report >= self.settings.report_interval_s:
            report = report_to_dict(generate_report(result.tracks, result.metrics, self.kb,
                                                    now=time.time(), face_detected=result.region is not None))
            with self._condition:
                old = {k: v for k, v in (self._report or {}).items() if k != "generated_at"}
                new = {k: v for k, v in report.items() if k != "generated_at"}
                if old != new:
                    self._report, self._report_version = report, self._report_version + 1
            self._last_report = now

    def wait_packet(self, after_version: int, timeout: float) -> tuple[int, bytes] | None:
        if type(after_version) is not int or after_version < 0 or not math.isfinite(timeout) or timeout < 0:
            raise ValueError("version and timeout must be nonnegative")
        with self._condition:
            self._condition.wait_for(lambda: self._version > after_version or self._stop.is_set(), timeout)
            if self._version > after_version and self._packet is not None:
                return self._version, self._packet
            return None

    def latest_report(self) -> tuple[int, dict] | None:
        with self._condition:
            return None if self._report is None else (self._report_version, copy.deepcopy(self._report))

    def health(self) -> dict:
        info = self.source.info()
        with self._condition:
            delivering = self._last_frame and time.monotonic() - self._last_frame < 2.0
            return {"status": "ok" if info.opened and delivering else "degraded",
                    "source": info.spec, "camera_open": info.opened,
                    "frame_size": [info.width, info.height], "detector": self.detector_name,
                    "preprocessor": self.preprocessor_name, "onnx_providers": list(self.onnx_providers),
                    "landmarker": "mediapipe-face-landmarker", "error": self._error or info.error}

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
    return PipelineRunner(settings, source, analyzer, kb, providers, detector.name, preprocessor.name)
