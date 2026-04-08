# PC Gaming System Audit

This project collects raw Windows gaming-related system facts and presents them through a Rich CLI, a TXT report, a JSON report, and per-run evidence artifacts.

It is read-only. It does not change drivers, settings, or hardware values.

By default, saved reports and evidence are sanitized to omit machine-specific identifiers that are not needed for gaming analysis, including machine name, MAC address, disk serial numbers, and CPU processor ID.

## Main Usage

From the project root:

```powershell
python run_audit.py
```

That opens the numbered Rich menu.

Direct commands are also available:

```powershell
python run_audit.py audit full
python run_audit.py audit section telemetry
python run_audit.py reports list --limit 5
python run_audit.py reports latest --format txt
python run_audit.py reports show 20260407_225212 --format json
python run_audit.py evidence list --latest
python run_audit.py diagnostics
```

## Installed Entry Points

After an editable install:

```powershell
python -m pip install -e .
python -m gaming_audit audit full
gaming-audit reports list --limit 5
```

`python -m gaming_audit` and `gaming-audit` use the current working directory as the audit project root.

If `gaming-audit` is not recognized on Windows, add your Python user Scripts directory to `PATH`, or run the installed launcher directly:

```powershell
& "$env:APPDATA\Python\Python314\Scripts\gaming-audit.exe" reports list --limit 5
```

## What It Collects

- Windows version and machine details
- CPU, RAM, and pagefile facts
- GPU, driver, DirectX, and WDDM facts
- connected displays and active display modes
- storage device and volume facts
- Game DVR, Game Mode, and power plan facts
- performance-tool inventory and process state
- service state for relevant gaming/performance services
- live telemetry from `nvidia-smi`
- optional MSI Afterburner shared-memory telemetry when available
- saved report history and per-run evidence artifacts
- explicit source diagnostics with command, return code, error text, and artifact path

## Output Locations

Full audits save to:

- `reports\txt\system_audit_<timestamp>.txt`
- `reports\json\system_audit_<timestamp>.json`
- `snapshots\latest.json`
- `evidence\<timestamp>\`

Section views and diagnostics are read-only terminal views and do not create saved runs.

## Repository Hygiene

The source code is safe to version normally, but the generated runtime output is machine-specific and should stay out of Git:

- `reports/`
- `snapshots/`
- `evidence/`
- `src/gaming_readiness_audit.egg-info/`
- `__pycache__/`

Those folders can contain:

- machine name
- installed software inventory
- service and process names
- display models and resolutions
- disk models, serial numbers, and volume labels
- network adapter names, MAC addresses, and ping samples
- saved raw command output from `dxdiag`, `nvidia-smi`, registry queries, and WMI-backed collectors

If you publish this project, commit the source tree and tests, but do not commit generated reports or evidence artifacts from your own PC.

## Sharing Safely

Before pushing to GitHub or sharing a zip of the repo, check that you are not including:

- `reports/json/system_audit_*.json`
- `reports/txt/system_audit_*.txt`
- `snapshots/latest.json`
- anything under `evidence/*`

These files are useful locally, but they expose detailed hardware and software facts about your machine.

Recommended local workflow:

```powershell
git status --ignored
```

Then confirm only source files, tests, and documentation are staged.

## Tests

```powershell
python -m unittest discover -s tests -v
python -m compileall src tests
```

