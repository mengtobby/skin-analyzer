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
