from __future__ import annotations

from ..constants import AVAILABILITY_AVAILABLE, AVAILABILITY_UNAVAILABLE
from ..models import CollectedSource, EvidenceRecord
from ..utils.time_utils import iso_timestamp
from .command_runner import CommandRunner, CommandResult


def _build_evidence(source_name: str, result: CommandResult) -> EvidenceRecord:
    return EvidenceRecord(
        source_name=source_name,
        source_command=result.command,
        availability=AVAILABILITY_AVAILABLE if result.returncode == 0 or result.stdout.strip() else AVAILABILITY_UNAVAILABLE,
        captured_at=iso_timestamp(),
        raw_output=result.stdout,
        artifact_filename=f"{source_name.replace(' ', '_').lower()}.json",
        stderr=result.stderr,
        return_code=result.returncode,
    )


def collect(runner: CommandRunner) -> CollectedSource:
    snapshot = CollectedSource()
    adapter_script = """
Get-NetAdapter |
Where-Object { $_.Status -eq 'Up' } |
Select-Object Name,InterfaceDescription,LinkSpeed,Status |
ConvertTo-Json -Compress
"""
    ping_script = """
Test-Connection 1.1.1.1 -Count 3 |
ForEach-Object {
  [pscustomobject]@{
    Address = $_.Address.IPAddressToString
    Latency = $_.Latency
    Status = $_.Status.ToString()
  }
} |
ConvertTo-Json -Compress
"""

    adapter_result, adapter_payload = runner.run_powershell_json(adapter_script, timeout=20)
    ping_result, ping_payload = runner.run_powershell_json(ping_script, timeout=20)

    snapshot.evidence["network_adapters"] = _build_evidence("Network Adapters", adapter_result)
    snapshot.evidence["ping_sample"] = _build_evidence("Ping Sample", ping_result)

    if adapter_payload is not None:
        snapshot.data["network_adapters"] = adapter_payload
    if ping_payload is not None:
        snapshot.data["ping_sample"] = ping_payload

    return snapshot


