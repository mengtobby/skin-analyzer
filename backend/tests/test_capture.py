"""Capture tests use synthetic sources and local media only."""

import threading
import time
from pathlib import Path

import cv2
import numpy as np
import pytest

from skin_analyzer.capture import CameraSource, VideoFileSource, create_source


class FakeCapture:
    def __init__(self, opened: bool = True, frames: int = 1000) -> None:
        self.opened = opened
        self.frames = frames
        self.number = 0
        self.released = False
        self.settings: dict[int, float] = {}

    def isOpened(self) -> bool:
        return self.opened

    def set(self, prop: int, value: float) -> bool:
        self.settings[prop] = value
        return True

    def read(self) -> tuple[bool, np.ndarray | None]:
        time.sleep(0.005)
        if self.number >= self.frames:
            return False, None
        frame = np.zeros((8, 12, 3), np.uint8)
        frame[:, 0] = 255
        frame[:, 1:, 0] = self.number % 255
        self.number += 1
        return True, frame

    def release(self) -> None:
        self.released = True


@pytest.mark.parametrize("spec", ["foo", "camera:abc", "camera:-1", "file:", "camera:"])
def test_invalid_spec(spec: str) -> None:
    with pytest.raises(ValueError):
        create_source(spec)


def test_parsing() -> None:
    assert isinstance(create_source("camera:0"), CameraSource)
    assert isinstance(create_source("file:x.mp4"), VideoFileSource)


def test_latest_frame_mirroring_and_close() -> None:
    capture = FakeCapture()
    source = create_source("camera:0", capture_factory=lambda *args: capture)
    source.start()
    source.start()
    try:
        first = source.read()
        assert first is not None
        assert np.all(first[0][:, -1] == 255)
        assert first[1] <= time.time()
        time.sleep(0.06)
        second = source.read()
        assert second is not None and second[2] > first[2] + 1
        third = source.read()
        assert third is not None and third[2] > second[2]
        assert source.info().opened
        assert capture.settings[cv2.CAP_PROP_FRAME_WIDTH] == 1280
    finally:
        source.close()
        source.close()
    assert capture.released
    assert source._thread is not None and not source._thread.is_alive()
    assert source.read(0) is None
    assert not source.info().opened


def test_timeout_and_failed_reads() -> None:
    source = CameraSource(capture_factory=lambda *args: FakeCapture(frames=1))
    assert source.read(0.01) is None
    source.start()
    try:
        assert source.read() is not None
        assert source.read(0.15) is None
        assert not source.info().opened
        assert "repeatedly" in (source.info().error or "")
    finally:
        source.close()


def test_failed_open_recovers() -> None:
    ready = threading.Event()
    captures: list[FakeCapture] = []

    def factory(*args: object) -> FakeCapture:
        capture = FakeCapture(opened=ready.is_set())
        captures.append(capture)
        return capture

    source = CameraSource(capture_factory=factory)
    source.start()
    try:
        assert source.read(0.1) is None
        assert not source.info().opened and source.info().error
        ready.set()
        assert source.read(3) is not None
        assert source.info().opened and source.info().error is None
    finally:
        source.close()
    assert all(capture.released for capture in captures)


def test_factory_exception_stays_in_worker() -> None:
    def factory(*args: object) -> FakeCapture:
        raise RuntimeError("test failure")

    source = CameraSource(capture_factory=factory)
    source.start()
    try:
        assert source.read(0.1) is None
        assert "test failure" in (source.info().error or "")
    finally:
        source.close()


def test_video_loops_at_native_fps(tmp_path: Path) -> None:
    path = tmp_path / "loop.avi"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 15, (32, 24))
    assert writer.isOpened()
    try:
        for value in (20, 180):
            writer.write(np.full((24, 32, 3), value, np.uint8))
    finally:
        writer.release()
    source = VideoFileSource(path, mirror=False)
    source.start()
    try:
        frames = [source.read() for _ in range(5)]
        assert all(frame is not None for frame in frames)
        assert [round(float(frame[0].mean())) for frame in frames] == [20, 180, 20, 180, 20]
        assert [frame[2] for frame in frames] == sorted({frame[2] for frame in frames})
        assert source.info().fps == pytest.approx(15)
        assert frames[-1][1] - frames[0][1] >= 0.2
    finally:
        source.close()


def test_image_repeats_without_mutating_slot(tmp_path: Path) -> None:
    path = tmp_path / "still.png"
    image = np.zeros((8, 12, 3), np.uint8)
    image[:, 0] = 255
    assert cv2.imwrite(str(path), image)
    source = VideoFileSource(path, fps=10, mirror=False)
    source.start()
    try:
        first = source.read()
        assert first is not None
        assert source.read(0.01) is None
        first[0][:] = 50
        second = source.read()
        assert second is not None and second[2] > first[2]
        np.testing.assert_array_equal(second[0], image)
    finally:
        source.close()


def test_close_wakes_reader() -> None:
    source = CameraSource()
    result: list[object] = []
    reader = threading.Thread(target=lambda: result.append(source.read(10)))
    reader.start()
    source.close()
    reader.join(1)
    assert not reader.is_alive() and result == [None]


@pytest.mark.parametrize("timeout", [-1, float("inf"), float("nan")])
def test_invalid_timeout(timeout: float) -> None:
    with pytest.raises(ValueError):
        CameraSource().read(timeout)
