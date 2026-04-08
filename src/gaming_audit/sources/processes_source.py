from __future__ import annotations

from ..constants import AVAILABILITY_AVAILABLE, AVAILABILITY_UNAVAILABLE, RELEVANT_PROCESS_NAMES
from ..models import CollectedSource, EvidenceRecord
from ..utils.time_utils import iso_timestamp
from .command_runner import CommandRunner


def collect(runner: CommandRunner) -> CollectedSource:
    snapshot = CollectedSource()
    executable_names = ",".join(f"'{name}.exe'" for name in RELEVANT_PROCESS_NAMES)
    script = f"""
Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
Where-Object {{ $_.Name -in @({executable_names}) }} |
Select-Object Name,ProcessId,ExecutablePath |
ConvertTo-Json -Compress
"""
    result, payload = runner.run_powershell_json(script, timeout=20)
    availability = AVAILABILITY_AVAILABLE if result.returncode == 0 or result.stdout.strip() else AVAILABILITY_UNAVAILABLE
    snapshot.evidence["processes"] = EvidenceRecord(
        source_name="Processes",
        source_command=result.command,
        availability=availability,
        captured_at=iso_timestamp(),
        raw_output=result.stdout,
        artifact_filename="processes.json",
        stderr=result.stderr,
        return_code=result.returncode,
    )
    if payload is not None:
        snapshot.data["processes"] = payload
    return snapshot

