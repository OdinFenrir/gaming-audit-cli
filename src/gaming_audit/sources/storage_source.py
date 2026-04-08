from __future__ import annotations

from ..constants import AVAILABILITY_AVAILABLE, AVAILABILITY_UNAVAILABLE
from ..models import CollectedSource, EvidenceRecord
from ..utils.time_utils import iso_timestamp
from .command_runner import CommandRunner, CommandResult


def _build_evidence(source_name: str, result: CommandResult) -> EvidenceRecord:
    return EvidenceRecord(
        source_name=source_name,
        source_command=result.command,
        availability=AVAILABILITY_AVAILABLE if result.returncode == 0 and result.stdout.strip() else AVAILABILITY_UNAVAILABLE,
        captured_at=iso_timestamp(),
        raw_output=result.stdout,
        artifact_filename=f"{source_name.replace(' ', '_').lower()}.json",
        stderr=result.stderr,
        return_code=result.returncode,
    )


def collect(runner: CommandRunner) -> CollectedSource:
    snapshot = CollectedSource()

    disk_script = """
Get-PhysicalDisk |
Select-Object FriendlyName,Model,MediaType,HealthStatus,Size,BusType,FirmwareVersion |
ConvertTo-Json -Compress
"""
    volume_script = """
Get-Volume |
Where-Object { $_.DriveLetter } |
Select-Object DriveLetter,FileSystemLabel,FileSystem,SizeRemaining,Size,HealthStatus,DriveType |
ConvertTo-Json -Compress
"""

    disk_result, disk_payload = runner.run_powershell_json(disk_script, timeout=30)
    volume_result, volume_payload = runner.run_powershell_json(volume_script, timeout=30)

    snapshot.evidence["physical_disks"] = _build_evidence("Physical Disks", disk_result)
    snapshot.evidence["volumes"] = _build_evidence("Volumes", volume_result)

    if disk_payload is not None:
        snapshot.data["physical_disks"] = disk_payload
    if volume_payload is not None:
        snapshot.data["volumes"] = volume_payload

    return snapshot

