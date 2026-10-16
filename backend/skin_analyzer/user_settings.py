"""Atomic persistence of the user's preferred camera input."""
from __future__ import annotations

import json
import logging
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .capture import create_source

logger = logging.getLogger(__name__)


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
                    or data["version"] != 1):
                raise ValueError("Invalid settings format")
            return UserSettings(_validate_source(data.get("source")))
        except FileNotFoundError:
            return UserSettings()
        except (OSError, ValueError, TypeError, UnicodeError):
            logger.warning("Cannot load saved user settings; using defaults")
            return UserSettings()

    def save(self, settings: UserSettings) -> None:
        source = _validate_source(settings.source)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary: str | None = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8",
                                             dir=self.path.parent, delete=False) as handle:
                temporary = handle.name
                json.dump({"version": 1, "source": source}, handle)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
        finally:
            if temporary is not None:
                Path(temporary).unlink(missing_ok=True)


def default_settings_path() -> Path:
    return Path.home() / ".skin-analyzer" / "settings.json"
