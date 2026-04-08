from __future__ import annotations

from ..constants import AVAILABILITY_AVAILABLE, AVAILABILITY_UNAVAILABLE, RELEVANT_SERVICE_PATTERNS
from ..models import CollectedSource, EvidenceRecord
from ..utils.time_utils import iso_timestamp
from .command_runner import CommandRunner


def collect(runner: CommandRunner) -> CollectedSource:
    snapshot = CollectedSource()
    pattern = "|".join(RELEVANT_SERVICE_PATTERNS)
    script = f"""
Get-Service -ErrorAction SilentlyContinue |
Where-Object {{ $_.Name -match '{pattern}' -or $_.DisplayName -match '{pattern}' }} |
ForEach-Object {{
  [pscustomobject]@{{
    Name = $_.Name
    DisplayName = $_.DisplayName
    Status = $_.Status.ToString()
    StartType = $_.StartType.ToString()
  }}
}} |
ConvertTo-Json -Compress
"""
    result, payload = runner.run_powershell_json(script, timeout=20)
    availability = AVAILABILITY_AVAILABLE if result.returncode == 0 or result.stdout.strip() else AVAILABILITY_UNAVAILABLE
    snapshot.evidence["services"] = EvidenceRecord(
        source_name="Services",
        source_command=result.command,
        availability=availability,
        captured_at=iso_timestamp(),
        raw_output=result.stdout,
        artifact_filename="services.json",
        stderr=result.stderr,
        return_code=result.returncode,
    )
    if payload is not None:
        snapshot.data["services"] = payload
    return snapshot

