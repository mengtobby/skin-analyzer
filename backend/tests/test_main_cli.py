"""CLI and browser startup use fakes exclusively."""
import sys
from dataclasses import replace
from types import SimpleNamespace

import pytest

from skin_analyzer import __main__ as cli
from skin_analyzer.config import Settings
from skin_analyzer.user_settings import UserSettings, UserSettingsStore


@pytest.mark.parametrize("host,expected_host", [("0.0.0.0", "127.0.0.1"),
                                                ("::", "127.0.0.1"),
                                                ("127.0.0.1", "127.0.0.1")])
def test_main_overrides_and_open(monkeypatch, tmp_path, caplog, host, expected_host):
    settings = replace(Settings(), settings_file=tmp_path / "settings.json")
    monkeypatch.setattr(Settings, "from_env", lambda: settings)
    monkeypatch.setattr(sys, "argv", ["skin-analyzer", "--source", "image:synthetic.png",
        "--host", host, "--port", "8765", "--detector", "classical", "--preprocess", "cpu",
        "--width", "640", "--height", "480", "--fps", "15", "--jpeg-quality", "80",
        "--report-interval-s", "2.5", "--extra-origins", " https://a.test, ,https://b.test, ",
        "--no-mirror", "--open"])
    models, built, runs, threads = [], [], [], []
    app = object()
    monkeypatch.setattr(cli, "ensure_models", lambda path: models.append(path))

    def build(actual):
        built.append(actual)
        return app

    def thread(**kwargs):
        threads.append(kwargs)
        return SimpleNamespace(start=lambda: threads.append("started"))

    monkeypatch.setattr(cli, "create_app", build)
    monkeypatch.setattr(cli.threading, "Thread", thread)
    monkeypatch.setattr(cli.uvicorn, "run", lambda *args, **kwargs: runs.append((args, kwargs)))
    cli.main()
    assert built == [replace(settings, source="image:synthetic.png", host=host, port=8765,
        detector="classical", preprocess="cpu", width=640, height=480, fps=15,
        jpeg_quality=80, report_interval_s=2.5, extra_origins=("https://a.test", "https://b.test"),
        mirror=False)]
    assert runs == [((app,), {"host": host, "port": 8765})]
    assert models == [settings.landmarker_model.parent]
    assert threads == [{"target": cli._open_browser,
                        "args": (f"http://{expected_host}:8765",), "daemon": True}, "started"]
    assert ("CAMERA EXPOSED" in caplog.text) == (host != "127.0.0.1")


@pytest.mark.parametrize("args", [["--port", "bad"], ["--detector", "bad"], ["--unknown"]])
def test_invalid_arguments_exit_before_startup(monkeypatch, args):
    monkeypatch.setattr(sys, "argv", ["skin-analyzer", *args])
    monkeypatch.setattr(cli, "ensure_models", lambda *_: pytest.fail("model access"))
    monkeypatch.setattr(cli.uvicorn, "run", lambda *a, **kw: pytest.fail("server startup"))
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 2


@pytest.mark.parametrize("mode", ["path", "environment", "default", "launch_error", "timeout"])
def test_browser_launch(monkeypatch, tmp_path, mode, caplog):
    health, pauses, launches, browsers = [], [], [], []
    attempts = 0

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def open_health(url, timeout):
        nonlocal attempts
        attempts += 1
        health.append((url, timeout))
        if mode == "timeout" or attempts == 1:
            raise OSError("not ready")
        return Response()

    monkeypatch.setattr(cli.urllib.request, "build_opener", lambda handler: SimpleNamespace(open=open_health))
    monkeypatch.setattr(cli.time, "sleep", lambda seconds: pauses.append(seconds))
    monkeypatch.setattr(cli.shutil, "which", lambda name: "fake-edge" if mode in {"path", "launch_error"} else None)
    for variable in ("ProgramFiles(x86)", "ProgramFiles", "LOCALAPPDATA"):
        monkeypatch.setenv(variable, str(tmp_path / variable))
    candidate = tmp_path / "ProgramFiles" / "Microsoft/Edge/Application/msedge.exe"
    if mode == "environment":  # a real file instead of patching Path.is_file process-wide
        candidate.parent.mkdir(parents=True)
        candidate.touch()

    def launch(args, **kwargs):
        launches.append((args, kwargs))
        if mode == "launch_error":
            raise OSError("launch failed")

    monkeypatch.setattr(cli.subprocess, "Popen", launch)
    monkeypatch.setattr(cli.webbrowser, "open", lambda url: browsers.append(url))
    url = "http://127.0.0.1:8765"
    cli._open_browser(url)
    assert health == [(url + "/api/health", 1)] * (120 if mode == "timeout" else 2)
    assert pauses == [0.5] * (120 if mode == "timeout" else 1)
    if mode == "timeout":
        assert not launches and not browsers
        assert "Server did not become ready" in caplog.text
    elif mode == "default":
        assert not launches
        assert browsers == [url]
    else:
        edge = str(candidate) if mode == "environment" else "fake-edge"
        assert launches == [([edge, f"--app={url}"],
                            {"creationflags": getattr(cli.subprocess, "CREATE_NO_WINDOW", 0)})]
        assert browsers == ([url] if mode == "launch_error" else [])
        if mode == "launch_error":
            assert "Could not launch Edge" in caplog.text


def _run_without_server(monkeypatch, settings, argv):
    built = []
    monkeypatch.setattr(Settings, "from_env", lambda: settings)
    monkeypatch.setattr(sys, "argv", ["skin-analyzer", *argv])
    monkeypatch.setattr(cli, "ensure_models", lambda path: None)
    monkeypatch.setattr(cli, "create_app", lambda actual: built.append(actual) or object())
    monkeypatch.setattr(cli.uvicorn, "run", lambda *args, **kwargs: None)
    cli.main()
    return built[0]


@pytest.mark.parametrize("argv,env_source,expected", [
    ([], None, "camera:2"),                               # saved choice restored on launch
    (["--source", "camera:1"], None, "camera:1"),         # explicit flag wins
    ([], "camera:3", "camera:3"),                         # SKIN_SOURCE wins
])
def test_saved_camera_input_used_only_without_explicit_source(monkeypatch, tmp_path, argv, env_source, expected):
    settings_file = tmp_path / "settings.json"
    UserSettingsStore(settings_file).save(UserSettings(source="camera:2"))
    base = replace(Settings(), settings_file=settings_file, source=env_source or Settings().source)
    if env_source:
        monkeypatch.setenv("SKIN_SOURCE", env_source)
    else:
        monkeypatch.delenv("SKIN_SOURCE", raising=False)
    assert _run_without_server(monkeypatch, base, argv).source == expected


def test_missing_saved_input_keeps_default(monkeypatch, tmp_path):
    monkeypatch.delenv("SKIN_SOURCE", raising=False)
    base = replace(Settings(), settings_file=tmp_path / "absent.json")
    assert _run_without_server(monkeypatch, base, []).source == Settings().source

@pytest.mark.parametrize("raw,expected", [("true", True), ("1", True), ("yes", True),
    ("false", False), ("0", False), ("no", False), ("TRUE", True)])
def test_dev_environment(monkeypatch, raw, expected):
    monkeypatch.setenv("SKIN_DEV", raw)
    assert Settings.from_env().dev is expected


def test_dev_default_and_invalid_environment(monkeypatch):
    monkeypatch.delenv("SKIN_DEV", raising=False)
    assert Settings.from_env().dev is False
    monkeypatch.setenv("SKIN_DEV", "maybe")
    with pytest.raises(ValueError, match="invalid SKIN_DEV"):
        Settings.from_env()
    with pytest.raises(ValueError, match="dev must be boolean"):
        Settings(dev=1)


@pytest.mark.parametrize("environment,argv,expected", [(False, [], False),
    (False, ["--dev"], True), (True, [], True)])
def test_dev_cli(monkeypatch, tmp_path, environment, argv, expected):
    settings = replace(Settings(), dev=environment, settings_file=tmp_path / "absent.json")
    assert _run_without_server(monkeypatch, settings, argv).dev is expected
