from __future__ import annotations

from pathlib import Path


def prepare_runtime_paths(project_root: Path, run_stamp: str) -> dict[str, Path]:
    evidence_dir = project_root / "evidence" / run_stamp
    txt_dir = project_root / "reports" / "txt"
    json_dir = project_root / "reports" / "json"
    snapshots_dir = project_root / "snapshots"

    for directory in (evidence_dir, txt_dir, json_dir, snapshots_dir):
        directory.mkdir(parents=True, exist_ok=True)

    return {
        "evidence_dir": evidence_dir,
        "text_report": txt_dir / f"system_audit_{run_stamp}.txt",
        "json_report": json_dir / f"system_audit_{run_stamp}.json",
        "latest_snapshot": snapshots_dir / "latest.json",
    }
