from __future__ import annotations

from pathlib import Path

from ..models import AuditReport
from .console_reporter import render_console_report


def write_text_report(report: AuditReport, output_path: Path) -> None:
    output_path.write_text(render_console_report(report), encoding="utf-8")
