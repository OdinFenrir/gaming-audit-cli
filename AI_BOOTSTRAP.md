# AI Bootstrap: Full Diagnosis

Use this file when an AI agent needs to run the complete gaming system diagnosis for this project without guessing the workflow.

## Goal

Run the full audit, generate the saved outputs, and know where to read the results afterward.

## Preconditions

- Run from the repository root.
- Windows is the target environment.
- The tool is read-only. It collects facts and writes reports and evidence artifacts.
- Output is written relative to the current working directory.

## Preferred Command

For a full diagnosis from source:

```powershell
python run_audit.py audit full
```

For a full diagnosis from the built executable:

```powershell
.\dist\gaming-audit.exe audit full
```

## What This Does

The full diagnosis:

- collects all supported system sections
- writes a saved text report
- writes a saved JSON report
- updates the latest snapshot
- writes per-run evidence artifacts

## Generated Output Locations

After a successful full diagnosis, inspect:

- `reports\txt\system_audit_<run_stamp>.txt`
- `reports\json\system_audit_<run_stamp>.json`
- `snapshots\latest.json`
- `evidence\<run_stamp>\`

## Recommended Read Order

If an AI needs the best summary first:

1. Read the newest file in `reports\txt\`
2. If more detail is needed, read the matching file in `reports\json\`
3. If raw collector output is needed, inspect files under `evidence\<run_stamp>\`

## Optional Interactive Path

If using the interactive menu instead of a direct command:

1. Run:

```powershell
python run_audit.py
```

2. Select `2` for `Full audit`
3. Use the section viewer to inspect one section at a time

Direct command mode is preferred for automation and AI workflows.

## Fast Verification

After running the full diagnosis, verify that:

- a new TXT report exists in `reports\txt\`
- a new JSON report exists in `reports\json\`
- a matching evidence folder exists in `evidence\`

## Compact Alternative

If a full saved diagnosis is not needed and only a quick summary is required:

```powershell
python run_audit.py audit summary
```

## Notes For AI Agents

- Prefer `audit full` for complete machine context.
- Prefer the TXT report for fast reading.
- Use the JSON report when exact structured values are needed.
- Use evidence files only when investigating raw collector behavior or missing fields.
- Do not assume optional collectors exist. Missing collectors are reported as unavailable, not as fatal errors.
