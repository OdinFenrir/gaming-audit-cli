from __future__ import annotations

from ..constants import AVAILABILITY_AVAILABLE, AVAILABILITY_UNAVAILABLE
from ..models import CollectedSource, EvidenceRecord
from ..utils.time_utils import iso_timestamp
from .command_runner import CommandRunner


def collect(runner: CommandRunner) -> CollectedSource:
    snapshot = CollectedSource()
    result = runner.run(["powercfg", "/getactivescheme"], timeout=20)

    availability = AVAILABILITY_AVAILABLE if result.returncode == 0 and result.stdout.strip() else AVAILABILITY_UNAVAILABLE
    snapshot.evidence["active_power_scheme"] = EvidenceRecord(
        source_name="powercfg",
        source_command=result.command,
        availability=availability,
        captured_at=iso_timestamp(),
        raw_output=result.stdout,
        artifact_filename="powercfg_active_scheme.txt",
        stderr=result.stderr,
        return_code=result.returncode,
    )

    if availability == AVAILABILITY_AVAILABLE:
        snapshot.data["active_power_scheme"] = result.stdout.strip()

    return snapshot
