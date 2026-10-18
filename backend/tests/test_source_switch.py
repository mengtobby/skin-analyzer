"""Deterministic runtime source switching tests."""
import threading
import time
from types import SimpleNamespace

import numpy as np
import pytest

from skin_analyzer.capture import SourceInfo
from skin_analyzer.config import Settings
from skin_analyzer.pipeline import PipelineRunner, SourceBusyError, SourceSwitchError


class Source:
    def __init__(self, spec="camera:0", ready=True):
        self.spec, self.ready = spec, ready
        self.closed = threading.Event()
        self.entered = threading.Event()
        self.deliver = threading.Event()
        self.opened = False

    def start(self):
        self.opened = True

    def read(self, timeout=1.0):
        self.entered.set()
        if self.ready:
            self.ready = False
            return np.zeros((2, 3, 3), np.uint8), time.time(), 1
        self.deliver.wait(timeout)
        return None

    def close(self):
        self.opened = False
        self.closed.set()
        self.deliver.set()

    def info(self):
        return SourceInfo(self.spec, self.opened, 3, 2, 30, None)


def runner_for(source):
    resets = []
    analyzer = SimpleNamespace(reset=lambda: resets.append(True))
    runner = PipelineRunner(Settings(), Source(), analyzer, None)
    runner._create_source = lambda spec: source
    return runner, resets


def test_switch_resets_and_closes_old():
    source = Source("camera:1")
    runner, resets = runner_for(source)
    old = runner.source
    runner._packet, runner._report = b"old", {"findings": [1]}
    notifications = []
    runner.add_listener(lambda: notifications.append(True))
    runner.switch_source("camera:1")
    assert runner.source is source and runner.source_spec() == "camera:1"
    assert resets == [True] and notifications == [True]
    cleared = runner.latest_report()
    assert runner.latest_packet() is None and cleared is not None and cleared[1] is None
    assert old.closed.wait(1)


def test_timeout_leaves_previous_input_and_redacts():
    source = Source("url:http://user:***@host/video?***", ready=False)
    runner, resets = runner_for(source)
    old = runner.source
    old.start()
    start = time.monotonic()
    with pytest.raises(SourceSwitchError) as error:
        runner.switch_source("url:http://user:password@host/video?token=secret", .03)
    assert time.monotonic() - start < 1
    assert "password" not in str(error.value) and "secret" not in str(error.value)
    assert "previous input is still active" in str(error.value)
    assert source.closed.wait(1)
    assert runner.source is old and old.opened and not resets


def test_same_spec_and_invalid_and_unconfigured():
    runner, resets = runner_for(Source())
    runner._create_source = lambda spec: pytest.fail("must not create")
    runner.switch_source("camera:0")
    assert not resets
    def invalid(spec):
        raise ValueError("invalid")
    runner._create_source = invalid
    with pytest.raises(ValueError, match="invalid"):
        runner.switch_source("bad")
    runner._create_source = None
    with pytest.raises(RuntimeError):
        runner.switch_source("camera:1")
    runner._closed = True
    with pytest.raises(RuntimeError):
        runner.switch_source("camera:0")


def test_concurrent_switch_is_busy():
    source = Source(ready=False)
    runner, _ = runner_for(source)
    errors = []
    def switch():
        try:
            runner.switch_source("camera:1", .1)
        except SourceSwitchError as error:
            errors.append(error)
    worker = threading.Thread(target=switch)
    worker.start()
    try:
        assert source.entered.wait(1)
        with pytest.raises(SourceBusyError):
            runner.switch_source("camera:2")
    finally:
        worker.join(2)
    assert len(errors) == 1


def test_restart_keeps_switched_spec():
    source = Source("camera:1")
    runner, _ = runner_for(source)
    created = []
    def create(spec):
        created.append(spec)
        return Source(spec, ready=False)
    runner.switch_source("camera:1")
    runner._create_source = create
    runner._source_factory = lambda: runner._create_source(runner.source_spec())
    runner.start()
    runner.stop()
    runner.start()
    try:
        assert created == ["camera:1"]
        assert runner.source.spec == "camera:1"
    finally:
        runner.stop()


def test_inflight_old_frame_is_discarded():
    new = Source("camera:1")
    runner, _ = runner_for(new)
    old = runner.source
    processed = []
    runner._process = lambda *frame: processed.append(frame)
    def old_read(timeout=1.0):
        old.entered.set()
        assert old.closed.wait(2)
        return np.zeros((2, 3, 3), np.uint8), time.time(), 9
    old.read = old_read
    original_read = new.read
    def new_read(timeout=1.0):
        if not new.ready:
            runner._stop.set()
            return None
        return original_read(timeout)
    new.read = new_read
    worker = threading.Thread(target=runner._run_frames)
    worker.start()
    try:
        assert old.entered.wait(1)
        runner.switch_source("camera:1")
        worker.join(2)
        assert not worker.is_alive()
        assert processed == []
    finally:
        old.closed.set()
        runner._stop.set()
        worker.join(2)


def test_blocking_old_close_does_not_delay_switch():
    runner, _ = runner_for(Source("camera:1"))
    entered, release = threading.Event(), threading.Event()
    def close():
        entered.set()
        release.wait(2)
    runner.source.close = close
    try:
        runner.switch_source("camera:1")
        assert entered.wait(1)
        assert not release.is_set()
    finally:
        release.set()
