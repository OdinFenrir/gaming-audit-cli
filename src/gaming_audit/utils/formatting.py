from __future__ import annotations

import re
from typing import Any

_USER_PATH_PATTERN = re.compile(r'(?i)\b([A-Z]:\\Users\\)([^\\\s]+)')
_GUID_PATTERN = re.compile(r'(?i)\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b')


def format_yes_no(value: bool | None) -> str:
    if value is None:
        return "Unknown"
    return "Yes" if value else "No"


def format_number(value: float | int) -> str:
    if isinstance(value, int):
        return str(value)
    return f"{value:.2f}".rstrip("0").rstrip(".")


def format_bytes(value: int | float | None) -> str:
    if value is None:
        return "Unavailable"
    size = float(value)
    units = ["B", "KB", "MB", "GB", "TB"]
    for unit in units:
        if abs(size) < 1024.0 or unit == units[-1]:
            return f"{format_number(size)} {unit}"
        size /= 1024.0
    return f"{format_number(size)} TB"


def format_mebibytes(value: int | float | None) -> str:
    if value is None:
        return "Unavailable"
    return f"{format_number(value)} MB"


def format_gibibytes_from_bytes(value: int | float | None) -> str:
    if value is None:
        return "Unavailable"
    return f"{format_number(float(value) / (1024 ** 3))} GB"


def sanitize_text(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    masked = _USER_PATH_PATTERN.sub(r'\1[redacted]', value)
    masked = _GUID_PATTERN.sub('[redacted-guid]', masked)
    return masked


def format_display_value(value: Any, unit: str = "", unavailable_label: str = "Unavailable") -> str:
    if value is None:
        return unavailable_label
    if isinstance(value, bool):
        return format_yes_no(value)
    if isinstance(value, (int, float)):
        rendered = format_number(value)
        return f"{rendered} {unit}".strip()
    if isinstance(value, list):
        return ", ".join(str(sanitize_text(item)) for item in value)
    text = str(sanitize_text(value)).strip()
    if not text:
        return unavailable_label
    return f"{text} {unit}".strip()

