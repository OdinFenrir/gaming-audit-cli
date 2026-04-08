from __future__ import annotations

from ..constants import APP_NAME, SECTION_ORDER
from ..models import AuditReport
from .view_data import build_section_rows


def _render_rows(rows: list[tuple[str, str]]) -> list[str]:
    if not rows:
        return []
    valued_rows = [label for label, value in rows if value]
    label_width = max((len(label) for label in valued_rows), default=0)
    rendered_rows: list[str] = []
    for label, value in rows:
        if value:
            rendered_rows.append(f'{label.ljust(label_width)} : {value}')
        else:
            rendered_rows.append(label)
    return rendered_rows


def _render_section(title: str, rows: list[tuple[str, str]]) -> list[str]:
    filtered_rows = [(label, value) for label, value in rows if label]
    if not filtered_rows:
        return []
    return ['', title, '-' * len(title), *_render_rows(filtered_rows)]


def render_console_report(report: AuditReport) -> str:
    section_rows = build_section_rows(report)
    lines = [APP_NAME, '=' * len(APP_NAME)]
    for section_name in SECTION_ORDER:
        lines.extend(_render_section(section_name, section_rows.get(section_name, [])))
    return '\n'.join(lines).rstrip() + '\n'
