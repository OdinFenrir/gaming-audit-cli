from __future__ import annotations

import re
from pathlib import Path

from ..constants import AVAILABILITY_AVAILABLE, AVAILABILITY_UNAVAILABLE
from ..models import CollectedSource, EvidenceRecord
from ..utils.parsing import parse_dxdiag_text
from ..utils.time_utils import iso_timestamp
from .command_runner import CommandRunner


_MACHINE_NAME_PATTERN = re.compile(r'(?im)^(\s*Machine name:\s*).+$')
_MACHINE_ID_PATTERN = re.compile(r'(?im)^(\s*Machine Id:\s*).+$')


def _sanitize_dxdiag_output(raw_output: str) -> str:
    sanitized = _MACHINE_NAME_PATTERN.sub(r'\1[redacted]', raw_output)
    return _MACHINE_ID_PATTERN.sub(r'\1[redacted]', sanitized)


def collect(runner: CommandRunner, evidence_dir: Path) -> CollectedSource:
    snapshot = CollectedSource()
    output_path = evidence_dir / "dxdiag.txt"
    result = runner.run(["dxdiag", "/whql:off", "/t", str(output_path)], timeout=60)

    raw_output = ""
    if output_path.exists():
        raw_output = _sanitize_dxdiag_output(output_path.read_text(encoding="utf-8", errors="replace"))
        output_path.write_text(raw_output, encoding="utf-8")

    availability = AVAILABILITY_AVAILABLE if result.returncode == 0 and raw_output else AVAILABILITY_UNAVAILABLE
    snapshot.evidence["dxdiag"] = EvidenceRecord(
        source_name="dxdiag",
        source_command=result.command,
        availability=availability,
        captured_at=iso_timestamp(),
        raw_output=raw_output,
        artifact_filename=output_path.name,
        stderr=result.stderr,
        return_code=result.returncode,
    )

    if raw_output:
        snapshot.data["dxdiag"] = parse_dxdiag_text(raw_output)

    return snapshot
