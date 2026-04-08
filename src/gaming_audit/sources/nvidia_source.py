from __future__ import annotations

from ..constants import AVAILABILITY_AVAILABLE, AVAILABILITY_UNAVAILABLE, NVIDIA_SMI_FIELDS
from ..models import CollectedSource, EvidenceRecord
from ..utils.parsing import parse_nvidia_smi_csv
from ..utils.time_utils import iso_timestamp
from .command_runner import CommandRunner


def collect(runner: CommandRunner) -> CollectedSource:
    snapshot = CollectedSource()
    query = ",".join(NVIDIA_SMI_FIELDS)
    result = runner.run(
        ["nvidia-smi", f"--query-gpu={query}", "--format=csv,noheader"],
        timeout=20,
    )

    availability = AVAILABILITY_AVAILABLE if result.returncode == 0 and result.stdout.strip() else AVAILABILITY_UNAVAILABLE
    snapshot.evidence["nvidia_smi"] = EvidenceRecord(
        source_name="nvidia-smi",
        source_command=result.command,
        availability=availability,
        captured_at=iso_timestamp(),
        raw_output=result.stdout,
        artifact_filename="nvidia_smi.csv",
        stderr=result.stderr,
        return_code=result.returncode,
    )

    if availability == AVAILABILITY_AVAILABLE:
        snapshot.data["nvidia_smi"] = parse_nvidia_smi_csv(result.stdout, NVIDIA_SMI_FIELDS)

    return snapshot
