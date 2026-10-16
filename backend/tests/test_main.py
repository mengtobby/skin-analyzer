"""Startup verifies the bundled model without starting a server."""
import sys
from dataclasses import replace

import pytest

from skin_analyzer import __main__ as module
from skin_analyzer.config import Settings


def test_main_verifies_existing_default_model(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings()
    calls = []
    monkeypatch.setattr(sys, "argv", ["skin-analyzer"])
    monkeypatch.setattr(Settings, "from_env", lambda: settings)
    monkeypatch.setattr(type(settings.landmarker_model), "is_file", lambda _: True)
    monkeypatch.setattr(module, "ensure_models", lambda directory: calls.append(directory))
    monkeypatch.setattr(module, "create_app", lambda actual: actual)
    monkeypatch.setattr(module.uvicorn, "run", lambda *args, **kwargs: None)
    module.main()
    assert calls == [settings.landmarker_model.parent]


def test_main_preserves_custom_model(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    settings = replace(Settings(), landmarker_model=tmp_path / "custom.task")
    monkeypatch.setattr(sys, "argv", ["skin-analyzer"])
    monkeypatch.setattr(Settings, "from_env", lambda: settings)
    monkeypatch.setattr(module, "ensure_models", lambda _: pytest.fail("custom model replaced"))
    monkeypatch.setattr(module, "create_app", lambda actual: actual)
    monkeypatch.setattr(module.uvicorn, "run", lambda *args, **kwargs: None)
    module.main()

@pytest.mark.parametrize("cli,env,expected", [(None, None, "url:http://user:secret@phone/video?token=x"),
    ("camera:1", None, "camera:1"), (None, "camera:3", "camera:3"),
    ("camera:1", "camera:3", "camera:1")])
def test_saved_input_precedence(cli, env, expected, monkeypatch, tmp_path, caplog):
    from skin_analyzer.user_settings import UserSettings, UserSettingsStore
    path = tmp_path / "settings.json"
    UserSettingsStore(path).save(UserSettings("url:http://user:secret@phone/video?token=x"))
    monkeypatch.setenv("SKIN_SETTINGS_FILE", str(path))
    monkeypatch.delenv("SKIN_SOURCE", raising=False)
    if env:
        monkeypatch.setenv("SKIN_SOURCE", env)
    monkeypatch.setattr(sys, "argv", ["skin-analyzer"] + (["--source", cli] if cli else []))
    monkeypatch.setattr(module, "ensure_models", lambda *_: None)
    captured = []
    monkeypatch.setattr(module, "create_app", lambda settings: captured.append(settings))
    monkeypatch.setattr(module.uvicorn, "run", lambda *a, **kw: None)
    caplog.set_level("INFO")
    module.main()
    assert captured[0].source == expected
    assert captured[0].settings_file == path
    assert "secret" not in caplog.text and "token" not in caplog.text
    assert ("Using saved camera input" in caplog.text) == (cli is None and env is None)
