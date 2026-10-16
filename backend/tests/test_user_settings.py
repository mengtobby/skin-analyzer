"""Saved input validation and atomic writes."""
import json
from pathlib import Path

import pytest

from skin_analyzer.user_settings import UserSettings, UserSettingsStore, default_settings_path


@pytest.mark.parametrize("source", [None, "camera:1", "url:http://user:pw@10.0.0.2:8080/video"])
def test_round_trip(tmp_path, source):
    store = UserSettingsStore(tmp_path / "nested" / "settings.json")
    assert store.load() == UserSettings()
    settings = UserSettings(source)
    store.save(settings)
    assert store.load() == settings
    assert json.loads(store.path.read_text()) == {"version": 1, "source": source}
    assert list(store.path.parent.iterdir()) == [store.path]


@pytest.mark.parametrize("data", ["bad", "[]", '{"version":true}',
    '{"version":1,"source":3}', '{"version":1,"source":"file:private"}',
    '{"version":1,"source":"url:http://user:secret@"}',
    '{"version":1,"source":"camera:-1"}'])
def test_invalid_settings_are_private_defaults(tmp_path, caplog, data):
    path = tmp_path / "settings.json"
    path.write_text(data)
    assert UserSettingsStore(path).load() == UserSettings()
    assert "using defaults" in caplog.text
    assert "secret" not in caplog.text and "private" not in caplog.text


def test_replace_failure_preserves_previous_file(tmp_path, monkeypatch):
    from skin_analyzer import user_settings
    store = UserSettingsStore(tmp_path / "settings.json")
    store.save(UserSettings("camera:1"))
    def fail(source, destination):
        assert Path(source).parent == destination.parent
        assert json.loads(Path(source).read_text())["source"] == "camera:2"
        raise OSError("cannot replace")
    monkeypatch.setattr(user_settings.os, "replace", fail)
    with pytest.raises(OSError):
        store.save(UserSettings("camera:2"))
    assert store.load() == UserSettings("camera:1")
    assert list(tmp_path.iterdir()) == [store.path]


def test_default_settings_path():
    assert default_settings_path() == Path.home() / ".skin-analyzer" / "settings.json"
