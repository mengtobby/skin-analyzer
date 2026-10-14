"""Capture workers with a single replaceable frame slot."""

from __future__ import annotations

import logging
import math
import sys
import threading
import time
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Callable, Protocol
from urllib.parse import unquote, urlsplit

import cv2
import numpy as np

logger = logging.getLogger(__name__)
CaptureFactory = Callable[..., Any]
Frame = tuple[np.ndarray, float, int]


@dataclass(frozen=True)
class SourceInfo:
    spec: str
    opened: bool
    width: int
    height: int
    fps: float
    error: str | None


class FrameSource(Protocol):
    def start(self) -> None: ...
    def read(self, timeout: float = 1.0) -> Frame | None: ...
    def info(self) -> SourceInfo: ...
    def close(self) -> None: ...


class _ThreadedSource:
    def __init__(self, spec: str, width: int, height: int, fps: float,
                 mirror: bool, capture_factory: CaptureFactory | None) -> None:
        if width <= 0 or height <= 0 or not math.isfinite(fps) or fps <= 0:
            raise ValueError("Frame dimensions and fps must be positive")
        self._info = SourceInfo(spec, False, width, height, float(fps), None)
        self._mirror = mirror
        self._factory = capture_factory or cv2.VideoCapture
        self._condition = threading.Condition()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._capture: Any = None
        self._slot: Frame | None = None
        self._sequence = 0
        self._consumed = 0

    def start(self) -> None:
        with self._condition:
            if self._thread is None and not self._stop.is_set():
                self._thread = threading.Thread(target=self._run, daemon=True,
                                                name=f"capture-{self._info.spec}")
                self._thread.start()

    def read(self, timeout: float = 1.0) -> Frame | None:
        if not math.isfinite(timeout) or timeout < 0:
            raise ValueError("timeout must be finite and nonnegative")
        with self._condition:
            self._condition.wait_for(
                lambda: self._sequence > self._consumed or self._stop.is_set(), timeout)
            if self._stop.is_set() or self._sequence <= self._consumed:
                return None
            self._consumed = self._sequence
            return self._slot

    def info(self) -> SourceInfo:
        with self._condition:
            return self._info

    def close(self) -> None:
        with self._condition:
            self._stop.set()
            self._condition.notify_all()
            thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join()
        self._update(opened=False)

    def _update(self, **changes: Any) -> None:
        with self._condition:
            self._info = replace(self._info, **changes)

    def _publish(self, frame: np.ndarray) -> None:
        if (not isinstance(frame, np.ndarray) or frame.dtype != np.uint8
                or frame.ndim != 3 or frame.shape[2] != 3 or frame.size == 0):
            raise ValueError("Capture must deliver nonempty uint8 BGR frames")
        timestamp = time.time()
        owned = cv2.flip(frame, 1) if self._mirror else frame.copy()
        with self._condition:
            self._sequence += 1
            self._slot = (owned, timestamp, self._sequence)
            self._info = replace(self._info, opened=True, error=None,
                                 width=owned.shape[1], height=owned.shape[0])
            self._condition.notify_all()

    def _release(self) -> None:
        capture, self._capture = self._capture, None
        if capture is not None:
            try:
                capture.release()
            except Exception as exc:
                logger.warning("Failed to release %s: %s", self._info.spec,
                               self._error_text(exc))

    def _error_text(self, exc: Exception) -> str:
        return str(exc) or type(exc).__name__

    def _run(self) -> None:
        try:
            while not self._stop.is_set():
                try:
                    self._stream()
                except Exception as exc:
                    error = self._error_text(exc)
                    self._update(opened=False, error=error)
                    logger.warning("Capture %s failed: %s", self._info.spec, error)
                finally:
                    self._release()
                self._stop.wait(2.0)
        finally:
            self._update(opened=False)

    def _stream(self) -> None:
        raise NotImplementedError


class CameraSource(_ThreadedSource):
    def __init__(self, index: int = 0, width: int = 1280, height: int = 720,
                 fps: int = 30, mirror: bool = True,
                 capture_factory: CaptureFactory | None = None) -> None:
        if not isinstance(index, int) or index < 0:
            raise ValueError("Camera index must be a nonnegative integer")
        super().__init__(f"camera:{index}", width, height, fps, mirror, capture_factory)
        self._index = index

    def _open(self) -> np.ndarray:
        backends = ([cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]
                    if sys.platform == "win32" else [cv2.CAP_ANY])
        errors: list[str] = []
        for backend in backends:
            try:
                self._capture = self._factory(self._index, backend)
                if not self._capture.isOpened():
                    raise RuntimeError("Camera did not open")
                info = self.info()
                for prop, value in ((cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG")),
                                    (cv2.CAP_PROP_FRAME_WIDTH, info.width),
                                    (cv2.CAP_PROP_FRAME_HEIGHT, info.height),
                                    (cv2.CAP_PROP_FPS, info.fps)):
                    self._capture.set(prop, value)
                ok, frame = self._capture.read()
                if not ok or frame is None:
                    raise RuntimeError("Camera failed its initial frame read")
                return frame
            except Exception as exc:
                errors.append(f"backend {backend}: {exc}")
                self._release()
        raise RuntimeError("; ".join(errors))

    def _stream(self) -> None:
        self._publish(self._open())
        failures = 0
        while not self._stop.is_set():
            ok, frame = self._capture.read()
            if not ok or frame is None:
                failures += 1
                self._update(error="Camera frame read failed")
                if failures >= 3:
                    raise RuntimeError("Camera frame reads failed repeatedly")
                self._stop.wait(0.02)
                continue
            failures = 0
            self._publish(frame)


class NetworkStreamSource(_ThreadedSource):
    def __init__(self, url: str, width: int = 1280, height: int = 720,
                 fps: int = 30, mirror: bool = True,
                 capture_factory: CaptureFactory | None = None) -> None:
        try:
            parsed = urlsplit(url)
            if (parsed.scheme.lower() not in {"http", "https", "rtsp"}
                    or not parsed.hostname or any(char.isspace() for char in url)):
                raise ValueError
            password = parsed.password
        except (ValueError, TypeError, AttributeError):
            raise ValueError("Invalid network stream URL") from None
        self._url = url
        self._password = password
        safe_url = url
        if password is not None:
            userinfo, host = parsed.netloc.rsplit("@", 1)
            safe_netloc = userinfo.split(":", 1)[0] + ":***@" + host
            safe_url = url.replace(parsed.netloc, safe_netloc, 1)
        self._safe_url = safe_url
        super().__init__(f"url:{safe_url}", width, height, fps, mirror, capture_factory)

    def _error_text(self, exc: Exception) -> str:
        error = super()._error_text(exc).replace(self._url, self._safe_url)
        if self._password:
            for password in (self._password, unquote(self._password)):
                if password:
                    error = error.replace(password, "***")
        return error

    def _stream(self) -> None:
        self._capture = self._factory(self._url, cv2.CAP_FFMPEG)
        if not self._capture.isOpened():
            raise RuntimeError("Network stream did not open")
        try:
            self._capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        except Exception as exc:
            logger.debug("Cannot set stream buffer size: %s", self._error_text(exc))
        ok, frame = self._capture.read()
        if not ok or frame is None:
            raise RuntimeError("Network stream failed its initial frame read")
        self._publish(frame)
        failures = 0
        while not self._stop.is_set():
            ok, frame = self._capture.read()
            if not ok or frame is None:
                failures += 1
                self._update(error="Network stream frame read failed")
                if failures >= 3:
                    raise RuntimeError("Network stream frame reads failed repeatedly")
                self._stop.wait(0.02)
                continue
            failures = 0
            self._publish(frame)


class VideoFileSource(_ThreadedSource):
    def __init__(self, path: str | Path, fps: int = 30, mirror: bool = True,
                 capture_factory: CaptureFactory | None = None) -> None:
        if not str(path).strip():
            raise ValueError("File path must not be empty")
        self._path = str(path)
        super().__init__(f"file:{path}", 1280, 720, fps, mirror, capture_factory)

    def _stream(self) -> None:
        image = Path(self._path).suffix.lower() in {".png", ".jpg", ".jpeg"}
        if image:
            frame = cv2.imread(self._path, cv2.IMREAD_COLOR)
            if frame is None:
                raise RuntimeError(f"Cannot read image: {self._path}")
            native_fps = self.info().fps
        else:
            self._capture = self._factory(self._path)
            if not self._capture.isOpened():
                raise RuntimeError(f"Cannot open video: {self._path}")
            native_fps = float(self._capture.get(cv2.CAP_PROP_FPS))
            if not math.isfinite(native_fps) or native_fps <= 0:
                native_fps = 30.0
        self._update(fps=native_fps)
        deadline = time.monotonic()
        while not self._stop.is_set():
            if not image:
                frame = self._read_video()
            self._publish(frame)
            deadline = max(deadline + 1.0 / native_fps, time.monotonic())
            self._stop.wait(max(0.0, deadline - time.monotonic()))

    def _read_video(self) -> np.ndarray:
        ok, frame = self._capture.read()
        if not ok or frame is None:
            self._capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ok, frame = self._capture.read()
        if not ok or frame is None:
            raise RuntimeError(f"Cannot read video frames: {self._path}")
        return frame


def create_source(spec: str, width: int = 1280, height: int = 720,
                  fps: int = 30, mirror: bool = True,
                  capture_factory: CaptureFactory | None = None) -> FrameSource:
    if not isinstance(spec, str):
        raise ValueError("Source specification must be a string")
    kind, separator, value = spec.partition(":")
    if separator and kind == "url":
        return NetworkStreamSource(value, width, height, fps, mirror, capture_factory)
    if separator and kind == "camera" and value.isascii() and value.isdecimal():
        return CameraSource(int(value), width, height, fps, mirror, capture_factory)
    if separator and kind == "file" and value.strip():
        return VideoFileSource(value, fps, mirror, capture_factory)
    raise ValueError(f"Invalid source specification: {spec!r}")
