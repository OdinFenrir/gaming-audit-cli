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

    scripts = {
        "game_config_store": """
$item = Get-ItemProperty 'HKCU:\\System\\GameConfigStore' -ErrorAction SilentlyContinue
[pscustomobject]@{
  game_dvr_enabled = $item.GameDVR_Enabled
  game_dvr_fse_behavior_mode = $item.GameDVR_FSEBehaviorMode
  game_dvr_honor_user_fse_behavior_mode = $item.GameDVR_HonorUserFSEBehaviorMode
} | ConvertTo-Json -Compress
""",
        "game_bar": """
$item = Get-ItemProperty 'HKCU:\\Software\\Microsoft\\GameBar' -ErrorAction SilentlyContinue
[pscustomobject]@{
  auto_game_mode_enabled = $item.AutoGameModeEnabled
  show_startup_panel = $item.ShowStartupPanel
  use_nexus_for_game_bar_enabled = $item.UseNexusForGameBarEnabled
} | ConvertTo-Json -Compress
""",
    }

    for key, script in scripts.items():
        result, payload = runner.run_powershell_json(script, timeout=20)
        snapshot.evidence[key] = _build_evidence(key.replace("_", " ").title(), result)
        if payload is not None:
            snapshot.data[key] = payload

    return snapshot
