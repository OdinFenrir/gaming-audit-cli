from __future__ import annotations

from ..constants import AVAILABILITY_AVAILABLE, AVAILABILITY_UNAVAILABLE
from ..models import CollectedSource, EvidenceRecord
from ..utils.time_utils import iso_timestamp
from .command_runner import CommandRunner, CommandResult


def _evidence_from_result(source_name: str, result: CommandResult, artifact_filename: str | None = None) -> EvidenceRecord:
    return EvidenceRecord(
        source_name=source_name,
        source_command=result.command,
        availability=AVAILABILITY_AVAILABLE if result.returncode == 0 and result.stdout.strip() else AVAILABILITY_UNAVAILABLE,
        captured_at=iso_timestamp(),
        raw_output=result.stdout,
        artifact_filename=artifact_filename,
        stderr=result.stderr,
        return_code=result.returncode,
    )


def collect(runner: CommandRunner) -> CollectedSource:
    snapshot = CollectedSource()

    scripts = {
        "operating_system": """
$os = Get-CimInstance Win32_OperatingSystem
[pscustomobject]@{
  caption = $os.Caption
  version = $os.Version
  build_number = $os.BuildNumber
  architecture = $os.OSArchitecture
  last_boot_up_time = $os.LastBootUpTime
} | ConvertTo-Json -Compress
""",
        "computer_system": """
$cs = Get-CimInstance Win32_ComputerSystem
[pscustomobject]@{
  manufacturer = $cs.Manufacturer
  model = $cs.Model
  total_physical_memory = $cs.TotalPhysicalMemory
} | ConvertTo-Json -Compress
""",
        "processor": """
Get-CimInstance Win32_Processor |
Select-Object -First 1 Name,Manufacturer,NumberOfCores,NumberOfLogicalProcessors,MaxClockSpeed,CurrentClockSpeed,LoadPercentage,SocketDesignation |
ConvertTo-Json -Compress
""",
        "video_controllers": """
Get-CimInstance Win32_VideoController |
Select-Object Name,Status,DriverVersion,DriverDate,VideoModeDescription,CurrentHorizontalResolution,CurrentVerticalResolution,CurrentRefreshRate,VideoProcessor,AdapterCompatibility |
ConvertTo-Json -Compress
""",
        "available_memory": """
$sample = Get-Counter '\\Memory\\Available MBytes' -MaxSamples 1
[pscustomobject]@{
  available_memory_mb = [math]::Round($sample.CounterSamples[0].CookedValue, 2)
} | ConvertTo-Json -Compress
""",
        "pagefile": """
Get-CimInstance Win32_PageFileUsage |
Select-Object Name,AllocatedBaseSize,CurrentUsage,PeakUsage |
ConvertTo-Json -Compress
""",
        "screens": """
Add-Type -AssemblyName System.Windows.Forms
[System.Windows.Forms.Screen]::AllScreens |
ForEach-Object {
  [pscustomobject]@{
    device_name = $_.DeviceName
    primary = $_.Primary
    width = $_.Bounds.Width
    height = $_.Bounds.Height
    x = $_.Bounds.X
    y = $_.Bounds.Y
  }
} | ConvertTo-Json -Compress
""",
        "audio_devices": """
Get-CimInstance Win32_SoundDevice |
Select-Object Name,Status,Manufacturer |
ConvertTo-Json -Compress
""",
    }

    for key, script in scripts.items():
        result, payload = runner.run_powershell_json(script, timeout=30)
        snapshot.evidence[key] = _evidence_from_result(f"WMI {key}", result, f"{key}.json")
        if payload is not None:
            snapshot.data[key] = payload

    return snapshot



