from __future__ import annotations

import json
import re
from typing import Any


_KEY_VALUE_LINE = re.compile(r"^\s*([^:]+):\s*(.*)$")


def ensure_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def load_json_text(text: str) -> Any:
    if not text.strip():
        return None
    return json.loads(text)


def parse_nvidia_smi_csv(text: str, fields: list[str]) -> dict[str, str]:
    line = text.strip().splitlines()[0]
    parts = [part.strip() for part in line.split(",")]
    values = {}
    for field_name, part in zip(fields, parts, strict=False):
        values[field_name] = part
    return values


def parse_dxdiag_text(text: str) -> dict[str, Any]:
    result: dict[str, Any] = {"system": {}, "displays": []}
    in_system_section = False
    in_display_section = False
    current_display: dict[str, str] | None = None

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if stripped == "System Information":
            in_system_section = True
            in_display_section = False
            current_display = None
            continue
        if stripped == "Display Devices":
            in_system_section = False
            in_display_section = True
            current_display = None
            continue
        if stripped and set(stripped) == {"-"}:
            continue

        match = _KEY_VALUE_LINE.match(line)
        if not match:
            continue

        key = match.group(1).strip()
        value = match.group(2).strip()
        normalized_key = re.sub(r"\s+", "_", key.lower())

        if in_system_section:
            result["system"][normalized_key] = value
            continue

        if in_display_section:
            if normalized_key == "card_name":
                current_display = {}
                result["displays"].append(current_display)
            if current_display is None:
                current_display = {}
                result["displays"].append(current_display)
            current_display[normalized_key] = value

    return result
