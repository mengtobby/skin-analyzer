"""JSON-ready protocol serialization."""
from dataclasses import asdict
from enum import Enum
from typing import Any

from .models import Report


def _json_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_value(item) for item in value]
    return value


def report_to_dict(report: Report) -> dict:
    return _json_value(asdict(report))
