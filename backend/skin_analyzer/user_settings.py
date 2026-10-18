"""Atomic persistence of the user's preferred camera input."""
from __future__ import annotations

import base64
import ctypes
import json
import logging
import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .capture import create_source

logger = logging.getLogger(__name__)


class _DataBlob(ctypes.Structure):
    _fields_ = [("size", ctypes.c_uint32), ("data", ctypes.POINTER(ctypes.c_ubyte))]


def _crypt(data: bytes, *, decrypt: bool) -> bytes:
    if sys.platform != "win32":
        raise OSError("Windows settings protection is unavailable")
    from ctypes import wintypes

    crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    buffer = ctypes.create_string_buffer(data)
    entropy_buffer = ctypes.create_string_buffer(b"skin-analyzer/settings/v2")
    source = _DataBlob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
    entropy = _DataBlob(len(entropy_buffer.raw) - 1,
                        ctypes.cast(entropy_buffer, ctypes.POINTER(ctypes.c_ubyte)))
    output = _DataBlob()
    operation = crypt32.CryptUnprotectData if decrypt else crypt32.CryptProtectData
    operation.argtypes = [ctypes.POINTER(_DataBlob), ctypes.c_void_p,
                          ctypes.POINTER(_DataBlob), ctypes.c_void_p, ctypes.c_void_p,
                          wintypes.DWORD, ctypes.POINTER(_DataBlob)]
    operation.restype = wintypes.BOOL
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    kernel32.LocalFree.restype = ctypes.c_void_p
    try:
        if not operation(ctypes.byref(source), None, ctypes.byref(entropy), None,
                         None, 1, ctypes.byref(output)):  # CRYPTPROTECT_UI_FORBIDDEN
            action = "decrypt" if decrypt else "encrypt"
            raise OSError(f"Cannot {action} settings (Windows error {ctypes.get_last_error()})")
        return ctypes.string_at(output.data, output.size)
    finally:
        if output.data:
            kernel32.LocalFree(ctypes.cast(output.data, ctypes.c_void_p))


def _protect(data: bytes) -> bytes:
    return _crypt(data, decrypt=False)


def _unprotect(data: bytes) -> bytes:
    return _crypt(data, decrypt=True)


@dataclass(frozen=True)
class UserSettings:
    source: str | None = None


def _validate_source(source: object) -> str | None:
    if source is None:
        return None
    if not isinstance(source, str) or not source.startswith(("camera:", "url:")):
        raise ValueError("Unsupported saved input")
    create_source(source)
    return source


class UserSettingsStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> UserSettings:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if (not isinstance(data, dict) or type(data.get("version")) is not int
                    or data["version"] not in (1, 2)):
                raise ValueError("Invalid settings format")
            if data["version"] == 2 and "source_protected" in data:
                protected = base64.b64decode(data["source_protected"], validate=True)
                source = json.loads(_unprotect(protected).decode("utf-8"))
            else:
                source = data.get("source")
            settings = UserSettings(_validate_source(source))
            if sys.platform == "win32" and "source_protected" not in data:
                try:
                    self.save(settings)
                except (OSError, ValueError, TypeError):
                    logger.warning("Cannot migrate saved user settings")
            return settings
        except FileNotFoundError:
            return UserSettings()
        except (OSError, ValueError, TypeError, UnicodeError):
            logger.warning("Cannot load saved user settings; using defaults")
            return UserSettings()

    def save(self, settings: UserSettings) -> None:
        source = _validate_source(settings.source)
        data: dict[str, object] = {"version": 2}
        if sys.platform == "win32":
            data["source_protected"] = base64.b64encode(
                _protect(json.dumps(source).encode("utf-8"))).decode("ascii")
        else:
            data["source"] = source
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary: str | None = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8",
                                             dir=self.path.parent, delete=False) as handle:
                temporary = handle.name
                json.dump(data, handle)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
            if sys.platform != "win32":
                self.path.chmod(0o600)
        finally:
            if temporary is not None:
                Path(temporary).unlink(missing_ok=True)


def default_settings_path() -> Path:
    return Path.home() / ".skin-analyzer" / "settings.json"
