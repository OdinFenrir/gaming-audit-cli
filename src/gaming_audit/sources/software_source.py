from __future__ import annotations

from ..constants import AVAILABILITY_AVAILABLE, AVAILABILITY_UNAVAILABLE, SOFTWARE_APPX_PACKAGES, SOFTWARE_REGISTRY_PATTERNS
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

    registry_pattern = "|".join(SOFTWARE_REGISTRY_PATTERNS.values())
    registry_script = fr"""
$paths = @(
  'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*',
  'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*',
  'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*'
)
Get-ItemProperty $paths -ErrorAction SilentlyContinue |
Where-Object {{ $_.DisplayName -match '{registry_pattern}' }} |
Select-Object DisplayName,DisplayVersion,InstallLocation |
ConvertTo-Json -Compress
"""

    appx_names = ",".join(f"'{package_name}'" for package_name in SOFTWARE_APPX_PACKAGES.values())
    appx_script = f"""
Get-AppxPackage -ErrorAction SilentlyContinue |
Where-Object {{ $_.Name -in @({appx_names}) }} |
Select-Object Name,Version,InstallLocation |
ConvertTo-Json -Compress
"""

    file_probe_script = r"""
$items = @(
  [pscustomobject]@{ Name = 'NVIDIA App'; Path = 'C:\Program Files\NVIDIA Corporation\NVIDIA App\CEF\NVIDIA App.exe' },
  [pscustomobject]@{ Name = 'MSI Afterburner'; Path = 'C:\Program Files (x86)\MSI Afterburner\MSIAfterburner.exe' },
  [pscustomobject]@{ Name = 'RivaTuner Statistics Server'; Path = 'C:\Program Files (x86)\RivaTuner Statistics Server\RTSS.exe' },
  [pscustomobject]@{ Name = 'HWiNFO'; Path = 'C:\Program Files\HWiNFO64\HWiNFO64.EXE' }
)
$items |
ForEach-Object {
  $exists = Test-Path $_.Path
  $version = $null
  if ($exists) {
    $versionInfo = (Get-Item $_.Path).VersionInfo
    $version = $versionInfo.ProductVersion
    if (-not $version) {
      $version = $versionInfo.FileVersion
    }
  }
  [pscustomobject]@{
    Name = $_.Name
    Exists = $exists
    Path = $_.Path
    Version = $version
  }
} |
ConvertTo-Json -Compress
"""

    registry_result, registry_payload = runner.run_powershell_json(registry_script, timeout=40)
    appx_result, appx_payload = runner.run_powershell_json(appx_script, timeout=40)
    file_result, file_payload = runner.run_powershell_json(file_probe_script, timeout=20)

    snapshot.evidence["registry_software"] = _build_evidence("Registry Software", registry_result)
    snapshot.evidence["appx_software"] = _build_evidence("Appx Software", appx_result)
    snapshot.evidence["tool_files"] = _build_evidence("Tool Files", file_result)

    if registry_payload is not None:
        snapshot.data["registry_software"] = registry_payload
    if appx_payload is not None:
        snapshot.data["appx_software"] = appx_payload
    if file_payload is not None:
        snapshot.data["tool_files"] = file_payload

    return snapshot

