"""Cleared findings are versioned and broadcast without opening a camera."""
from types import SimpleNamespace
from threading import Event

import pytest
from fastapi.testclient import TestClient

from skin_analyzer.api.app import create_app
from skin_analyzer.config import Settings
from skin_analyzer.knowledge import KnowledgeBase
from skin_analyzer.pipeline import FrameResult, PipelineRunner
from .test_api import FakeRunner, ready, stream, wait_for
from .test_source_switch import Source


@pytest.mark.parametrize("action", ["reset", "switch"])
def test_clear_versions_report_and_notifies_outside_locks(action: str) -> None:
    runner = PipelineRunner(Settings(), Source(), SimpleNamespace(reset=lambda: None),
                            KnowledgeBase.load())
    assert runner.latest_report() is None
    runner._publish_report(FrameResult(None, [], None, {}))
    published = runner.latest_report()
    assert published is not None and published[1] is not None
    observations = []

    def notified() -> None:
        analysis_free = runner._analysis_lock.acquire(blocking=False)
        if analysis_free:
            runner._analysis_lock.release()
        observations.append((analysis_free, runner._condition._is_owned(), runner.latest_report()))

    runner.add_listener(notified)
    if action == "reset":
        runner.reset()
    else:
        runner._create_source = lambda spec: Source(spec)
        runner.switch_source("camera:1")
    cleared = (published[0] + 1, None)
    assert runner.latest_report() == cleared
    assert observations == [(True, False, cleared)]


class ClearableRunner(FakeRunner):
    def __init__(self) -> None:
        super().__init__()
        self.report_read = Event()

    def latest_report(self) -> tuple[int, dict | None] | None:
        report = self.report
        self.report_read.set()
        return report

    def reset(self) -> None:
        self.resets += 1
        version = self.report[0] if self.report is not None else 0
        self.report = (version + 1, None)
        self.notify()


def test_reset_broadcasts_null_to_all_sessions_and_rest() -> None:
    runner = ClearableRunner()
    app = create_app(Settings(), runner)
    with TestClient(app, base_url="http://localhost", headers={"host": "localhost"},
                    client=("127.0.0.1", 50000)) as client:
        with stream(client) as first, stream(client) as second:
            ready(first)
            ready(second)
            runner.report = (1, {"findings": [{"title": "previous person"}]})
            runner.notify()
            for socket in (first, second):
                assert socket.receive_json() == {"type": "report", "data": runner.report[1]}
            assert client.post("/api/reset").status_code == 200
            for socket in (first, second):
                assert socket.receive_json() == {"type": "report", "data": None}
            assert client.get("/api/report").json() == {
                "success": True, "data": None, "error": None}
            runner.report_read.clear()
            assert client.post("/api/reset").status_code == 200
            wait_for(runner.report_read.is_set)
            runner.report = (runner.report[0] + 1, {"findings": []})
            runner.notify()
            for socket in (first, second):
                assert socket.receive_json() == {"type": "report", "data": {"findings": []}}


@pytest.mark.parametrize("clear_when", ["never", "before_connect", "after_connect"])
def test_fresh_session_has_no_spurious_null_report(clear_when: str) -> None:
    runner = ClearableRunner()
    if clear_when == "before_connect":
        runner.report = (1, {"findings": []})
        runner.reset()
    app = create_app(Settings(), runner)
    with TestClient(app, base_url="http://localhost", headers={"host": "localhost"},
                    client=("127.0.0.1", 50000)) as client:
        with stream(client) as socket:
            ready(socket)
            wait_for(runner.report_read.is_set)
            if clear_when == "after_connect":
                runner.report_read.clear()
                assert client.post("/api/reset").status_code == 200
                wait_for(runner.report_read.is_set)
            version = runner.report[0] if runner.report is not None else 0
            runner.report = (version + 1, {"findings": []})
            runner.notify()
            # Any spurious initial null would arrive before this first report.
            assert socket.receive_json() == {"type": "report", "data": {"findings": []}}
