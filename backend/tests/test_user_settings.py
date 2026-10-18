"""Saved input validation and atomic writes."""
import base64
import json
import sys

from skin_analyzer import user_settings
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
    data = json.loads(store.path.read_text())
    assert data["version"] == 2
    if sys.platform == "win32":
        assert "source" not in data
        if source:
            assert source not in store.path.read_text()
    else:
        assert data == {"version": 2, "source": source}
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
    monkeypatch.setattr(user_settings.sys, "platform", "linux")
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


@pytest.mark.skipif(sys.platform != "win32", reason="Windows DPAPI")
def test_windows_password_round_trip(tmp_path):
    source = "url:http://user:unique-password@10.0.0.2/video"
    store = UserSettingsStore(tmp_path / "settings.json")
    store.save(UserSettings(source))
    assert source not in store.path.read_text()
    assert "unique-password" not in store.path.read_text()
    assert store.load() == UserSettings(source)


@pytest.mark.skipif(sys.platform != "win32", reason="Windows DPAPI")
def test_windows_legacy_migration(tmp_path):
    store = UserSettingsStore(tmp_path / "settings.json")
    source = "url:http://user:legacy-password@10.0.0.2/video"
    store.path.write_text(json.dumps({"version": 1, "source": source}))
    assert store.load() == UserSettings(source)
    assert "legacy-password" not in store.path.read_text()
    assert "source_protected" in json.loads(store.path.read_text())
    assert store.load() == UserSettings(source)


@pytest.mark.skipif(sys.platform != "win32", reason="Windows DPAPI")
def test_windows_corrupted_blob(tmp_path, caplog):
    store = UserSettingsStore(tmp_path / "settings.json")
    store.path.write_text(json.dumps({"version": 2, "source_protected":
                                     base64.b64encode(b"secret-invalid-blob").decode()}))
    assert store.load() == UserSettings()
    assert "using defaults" in caplog.text
    assert "secret" not in caplog.text


def test_non_windows_plaintext_permissions(tmp_path, monkeypatch):
    monkeypatch.setattr(user_settings.sys, "platform", "linux")
    def unexpected(data):
        raise AssertionError("DPAPI called on plaintext path")
    monkeypatch.setattr(user_settings, "_protect", unexpected)
    monkeypatch.setattr(user_settings, "_unprotect", unexpected)
    modes = []
    monkeypatch.setattr(Path, "chmod", lambda self, mode: modes.append(mode))
    store = UserSettingsStore(tmp_path / "settings.json")
    store.save(UserSettings("camera:2"))
    assert json.loads(store.path.read_text()) == {"version": 2, "source": "camera:2"}
    assert modes == [0o600]
    assert store.load() == UserSettings("camera:2")


@pytest.mark.parametrize("source", ["file:secret", "camera:-1", "url:http://user:secret@"])
def test_decrypted_source_is_validated(tmp_path, monkeypatch, caplog, source):
    monkeypatch.setattr(user_settings, "_unprotect", lambda data: json.dumps(source).encode())
    store = UserSettingsStore(tmp_path / "settings.json")
    store.path.write_text(json.dumps({"version": 2, "source_protected": "YmxvYg=="}))
    assert store.load() == UserSettings()
    assert "using defaults" in caplog.text
    assert "secret" not in caplog.text


def test_migration_failure_keeps_valid_settings(tmp_path, monkeypatch, caplog):
    monkeypatch.setattr(user_settings.sys, "platform", "win32")
    def fail(data):
        raise OSError("secret must not be logged")
    monkeypatch.setattr(user_settings, "_protect", fail)
    store = UserSettingsStore(tmp_path / "settings.json")
    store.path.write_text(json.dumps({"version": 1, "source": "camera:2"}))
    assert store.load() == UserSettings("camera:2")
    assert "Cannot migrate" in caplog.text
    assert "secret" not in caplog.text


@pytest.mark.parametrize("version", [1, 2])
def test_plaintext_migrates_to_protected_v2(tmp_path, monkeypatch, version):
    monkeypatch.setattr(user_settings.sys, "platform", "win32")
    protected_values = {}
    def protect(data):
        protected_values[b"opaque"] = data
        return b"opaque"
    monkeypatch.setattr(user_settings, "_protect", protect)
    monkeypatch.setattr(user_settings, "_unprotect", protected_values.__getitem__)
    store = UserSettingsStore(tmp_path / "settings.json")
    source = "url:http://user:secret@10.0.0.2/video"
    store.path.write_text(json.dumps({"version": version, "source": source}))
    assert store.load() == UserSettings(source)
    assert json.loads(store.path.read_text()) == {
        "version": 2, "source_protected": base64.b64encode(b"opaque").decode()}
    assert store.load() == UserSettings(source)


@pytest.mark.parametrize("protected", ["!invalid-base64!", None, 123])
def test_invalid_protected_format_uses_defaults(tmp_path, caplog, protected):
    store = UserSettingsStore(tmp_path / "settings.json")
    store.path.write_text(json.dumps({"version": 2, "source_protected": protected}))
    assert store.load() == UserSettings()
    assert "using defaults" in caplog.text


def test_protection_failure_preserves_previous_file(tmp_path, monkeypatch):
    monkeypatch.setattr(user_settings.sys, "platform", "win32")
    def fail(data):
        raise OSError("protection unavailable")
    monkeypatch.setattr(user_settings, "_protect", fail)
    store = UserSettingsStore(tmp_path / "settings.json")
    original = json.dumps({"version": 1, "source": "camera:1"})
    store.path.write_text(original)
    with pytest.raises(OSError):
        store.save(UserSettings("camera:2"))
    assert store.path.read_text() == original
    assert list(tmp_path.iterdir()) == [store.path]
