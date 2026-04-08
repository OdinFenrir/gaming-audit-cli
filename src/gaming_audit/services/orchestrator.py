from __future__ import annotations

import json
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from typing import Callable

from ..constants import (
    AVAILABILITY_UNAVAILABLE,
    REPORT_PREFIX,
    SCOPE_DIAGNOSTICS,
    SCOPE_DISPLAYS,
    SCOPE_FULL,
    SCOPE_GRAPHICS,
    SCOPE_PROCESSES,
    SCOPE_PROCESSES_SERVICES,
    SCOPE_SERVICES,
    SCOPE_SETTINGS,
    SCOPE_STORAGE,
    SCOPE_SUMMARY,
    SCOPE_SYSTEM,
    SCOPE_TELEMETRY,
    SCOPE_TOOLS,
)
from ..models import (
    AuditReport,
    CollectedSource,
    CollectionBundle,
    DiagnosticRecord,
    EvidenceRecord,
    ReadinessRecord,
    RuntimePaths,
    SavedRunRecord,
)
from ..normalizers import (
    collect_unavailable_metrics,
    normalize_display_metrics,
    normalize_graphics_metrics,
    normalize_process_inventory,
    normalize_service_inventory,
    normalize_settings_metrics,
    normalize_software_inventory,
    normalize_storage_metrics,
    normalize_system_metrics,
    normalize_telemetry_metrics,
)
from ..reporters import write_json_report, write_text_report
from ..sources import (
    afterburner_source,
    dxdiag_source,
    network_source,
    nvidia_source,
    powercfg_source,
    processes_source,
    registry_source,
    services_source,
    software_source,
    storage_source,
    wmi_source,
)
from ..sources.command_runner import CommandRunner
from ..utils.formatting import sanitize_text
from ..utils.paths import prepare_runtime_paths
from ..utils.time_utils import filename_timestamp, iso_timestamp


Collector = Callable[[CommandRunner, Path], CollectedSource]


SOURCE_COLLECTORS: dict[str, Collector] = {
    'wmi': lambda runner, evidence_dir: wmi_source.collect(runner),
    'network': lambda runner, evidence_dir: network_source.collect(runner),
    'dxdiag': lambda runner, evidence_dir: dxdiag_source.collect(runner, evidence_dir),
    'nvidia': lambda runner, evidence_dir: nvidia_source.collect(runner),
    'storage': lambda runner, evidence_dir: storage_source.collect(runner),
    'registry': lambda runner, evidence_dir: registry_source.collect(runner),
    'powercfg': lambda runner, evidence_dir: powercfg_source.collect(runner),
    'software': lambda runner, evidence_dir: software_source.collect(runner),
    'processes': lambda runner, evidence_dir: processes_source.collect(runner),
    'services': lambda runner, evidence_dir: services_source.collect(runner),
    'afterburner': lambda runner, evidence_dir: afterburner_source.collect(),
}

SCOPE_SOURCES: dict[str, tuple[str, ...]] = {
    SCOPE_FULL: ('wmi', 'network', 'dxdiag', 'nvidia', 'storage', 'registry', 'powercfg', 'software', 'processes', 'services', 'afterburner'),
    SCOPE_SYSTEM: ('wmi', 'network'),
    SCOPE_GRAPHICS: ('wmi', 'dxdiag', 'nvidia'),
    SCOPE_DISPLAYS: ('wmi', 'dxdiag'),
    SCOPE_STORAGE: ('storage',),
    SCOPE_SETTINGS: ('registry', 'powercfg'),
    SCOPE_TOOLS: ('software',),
    SCOPE_PROCESSES: ('processes',),
    SCOPE_SERVICES: ('services',),
    SCOPE_PROCESSES_SERVICES: ('processes', 'services'),
    SCOPE_TELEMETRY: ('nvidia', 'afterburner'),
    SCOPE_DIAGNOSTICS: ('wmi', 'network', 'dxdiag', 'nvidia', 'storage', 'registry', 'powercfg', 'software', 'processes', 'services', 'afterburner'),
    SCOPE_SUMMARY: ('wmi', 'network', 'dxdiag', 'nvidia', 'registry', 'powercfg', 'software', 'afterburner'),
}


def _relative_path(project_root: Path, path: Path | None) -> str:
    if path is None:
        return ''
    try:
        return str(path.relative_to(project_root))
    except ValueError:
        return str(path)


def _flatten_evidence_records(snapshots: dict[str, CollectedSource]) -> list[EvidenceRecord]:
    records: list[EvidenceRecord] = []
    for snapshot in snapshots.values():
        records.extend(snapshot.evidence.values())
    return records


def _materialize_evidence_artifacts(evidence_dir: Path, evidence_records: list[EvidenceRecord]) -> None:
    evidence_dir.mkdir(parents=True, exist_ok=True)
    for record in evidence_records:
        artifact_path = evidence_dir / record.artifact_filename if record.artifact_filename else None
        if artifact_path is not None:
            record.artifact_path = str(sanitize_text(str(artifact_path)))
        if artifact_path is None or artifact_path.exists():
            continue
        content = record.raw_output or record.stderr
        if not content:
            continue
        artifact_path.write_text(content, encoding='utf-8')


def _runtime_paths_for_scope(project_root: Path, run_stamp: str, persist_evidence: bool, source_keys: tuple[str, ...]) -> tuple[RuntimePaths, TemporaryDirectory[str] | None]:
    if persist_evidence:
        prepared_paths = prepare_runtime_paths(project_root, run_stamp)
        return (
            RuntimePaths(
                evidence_dir=prepared_paths['evidence_dir'],
                text_report=prepared_paths['text_report'],
                json_report=prepared_paths['json_report'],
                latest_snapshot=prepared_paths['latest_snapshot'],
            ),
            None,
        )

    if 'dxdiag' not in source_keys:
        return RuntimePaths(), None

    temporary_directory = TemporaryDirectory(prefix='gaming_audit_')
    evidence_dir = Path(temporary_directory.name) / 'evidence'
    evidence_dir.mkdir(parents=True, exist_ok=True)
    return RuntimePaths(evidence_dir=evidence_dir), temporary_directory


def _build_diagnostics(snapshots: dict[str, CollectedSource]) -> list[DiagnosticRecord]:
    diagnostics: list[DiagnosticRecord] = []
    for source_key, snapshot in snapshots.items():
        for evidence_key, record in snapshot.evidence.items():
            diagnostics.append(
                DiagnosticRecord(
                    source_key=f'{source_key}.{evidence_key}',
                    source_name=record.source_name,
                    availability=record.availability,
                    source_command=str(sanitize_text(record.source_command)),
                    captured_at=record.captured_at,
                    artifact_filename=record.artifact_filename or '',
                    artifact_path=str(sanitize_text(record.artifact_path)),
                    stderr=record.stderr,
                    return_code=record.return_code,
                )
            )
    diagnostics.sort(key=lambda item: item.source_key)
    return diagnostics


def _get_snapshot(bundle: CollectionBundle, source_key: str) -> CollectedSource:
    return bundle.snapshots.get(source_key, CollectedSource())


def _evidence_available(snapshot: CollectedSource, evidence_key: str | None = None) -> bool:
    if evidence_key is not None:
        evidence = snapshot.evidence.get(evidence_key)
        return bool(evidence and evidence.availability != AVAILABILITY_UNAVAILABLE)
    return any(item.availability != AVAILABILITY_UNAVAILABLE for item in snapshot.evidence.values())


def _output_writable(project_root: Path) -> bool:
    try:
        with NamedTemporaryFile(mode='w', dir=project_root, prefix='gaming_audit_', suffix='.tmp', delete=True, encoding='utf-8') as handle:
            handle.write('ok')
            handle.flush()
        return True
    except OSError:
        return False



def collect_scope(project_root: Path, scope: str, persist_evidence: bool = False) -> CollectionBundle:
    if scope not in SCOPE_SOURCES:
        raise ValueError(f'Unknown collection scope: {scope}')

    run_stamp = filename_timestamp()
    source_keys = SCOPE_SOURCES[scope]
    runtime_paths, temporary_directory = _runtime_paths_for_scope(project_root, run_stamp, persist_evidence, source_keys)
    runner = CommandRunner()

    bundle = CollectionBundle(
        scope=scope,
        run_stamp=run_stamp,
        runtime_paths=runtime_paths,
        temporary_directory=temporary_directory,
    )

    evidence_dir = runtime_paths.evidence_dir or project_root
    for source_key in source_keys:
        collector = SOURCE_COLLECTORS[source_key]
        bundle.snapshots[source_key] = collector(runner, evidence_dir)

    bundle.evidence_records = _flatten_evidence_records(bundle.snapshots)
    if runtime_paths.evidence_dir is not None:
        _materialize_evidence_artifacts(runtime_paths.evidence_dir, bundle.evidence_records)
    bundle.diagnostics = _build_diagnostics(bundle.snapshots)
    return bundle



def build_report(project_root: Path, collection_bundle: CollectionBundle) -> AuditReport:
    wmi_snapshot = _get_snapshot(collection_bundle, 'wmi')
    network_snapshot = _get_snapshot(collection_bundle, 'network')
    dxdiag_snapshot = _get_snapshot(collection_bundle, 'dxdiag')
    nvidia_snapshot = _get_snapshot(collection_bundle, 'nvidia')
    storage_snapshot = _get_snapshot(collection_bundle, 'storage')
    registry_snapshot = _get_snapshot(collection_bundle, 'registry')
    powercfg_snapshot = _get_snapshot(collection_bundle, 'powercfg')
    software_snapshot = _get_snapshot(collection_bundle, 'software')
    process_snapshot = _get_snapshot(collection_bundle, 'processes')
    service_snapshot = _get_snapshot(collection_bundle, 'services')
    afterburner_snapshot = _get_snapshot(collection_bundle, 'afterburner')

    system_metrics = normalize_system_metrics(wmi_snapshot, network_snapshot)
    graphics_metrics = normalize_graphics_metrics(wmi_snapshot, dxdiag_snapshot, nvidia_snapshot)
    display_metrics = normalize_display_metrics(wmi_snapshot, dxdiag_snapshot)
    storage_metrics = normalize_storage_metrics(storage_snapshot)
    settings_metrics = normalize_settings_metrics(registry_snapshot, powercfg_snapshot)
    telemetry_metrics = normalize_telemetry_metrics(nvidia_snapshot, afterburner_snapshot)
    software_inventory = normalize_software_inventory(software_snapshot)
    process_inventory = normalize_process_inventory(process_snapshot)
    service_inventory = normalize_service_inventory(service_snapshot)
    unavailable_metrics = collect_unavailable_metrics(*collection_bundle.snapshots.values())

    metadata = {
        'generated_at': iso_timestamp(),
        'run_stamp': collection_bundle.run_stamp,
        'scope': collection_bundle.scope,
        'project_root': str(sanitize_text(str(project_root))),
        'evidence_directory': str(sanitize_text(str(collection_bundle.runtime_paths.evidence_dir or ''))),
        'text_report': str(sanitize_text(str(collection_bundle.runtime_paths.text_report or ''))),
        'json_report': str(sanitize_text(str(collection_bundle.runtime_paths.json_report or ''))),
        'latest_snapshot': str(sanitize_text(str(collection_bundle.runtime_paths.latest_snapshot or ''))),
        'evidence_directory_relative': _relative_path(project_root, collection_bundle.runtime_paths.evidence_dir),
        'text_report_relative': _relative_path(project_root, collection_bundle.runtime_paths.text_report),
        'json_report_relative': _relative_path(project_root, collection_bundle.runtime_paths.json_report),
        'latest_snapshot_relative': _relative_path(project_root, collection_bundle.runtime_paths.latest_snapshot),
    }

    return AuditReport(
        metadata=metadata,
        system_metrics=system_metrics,
        graphics_metrics=graphics_metrics,
        display_metrics=display_metrics,
        storage_metrics=storage_metrics,
        settings_metrics=settings_metrics,
        telemetry_metrics=telemetry_metrics,
        software_inventory=software_inventory,
        process_inventory=process_inventory,
        service_inventory=service_inventory,
        unavailable_metrics=unavailable_metrics,
        evidence_records=collection_bundle.evidence_records,
    )



def save_full_audit(report: AuditReport, collection_bundle: CollectionBundle) -> None:
    runtime_paths = collection_bundle.runtime_paths
    if runtime_paths.text_report is None or runtime_paths.json_report is None or runtime_paths.latest_snapshot is None:
        raise RuntimeError('Full audit runtime paths were not initialized.')
    write_text_report(report, runtime_paths.text_report)
    write_json_report(report, runtime_paths.json_report)
    write_json_report(report, runtime_paths.latest_snapshot)



def run_full_audit(project_root: Path) -> AuditReport:
    bundle = collect_scope(project_root, SCOPE_FULL, persist_evidence=True)
    try:
        report = build_report(project_root, bundle)
        save_full_audit(report, bundle)
        return report
    finally:
        bundle.cleanup()



def run_audit(project_root: Path) -> AuditReport:
    return run_full_audit(project_root)



def build_diagnostics(collection_bundle: CollectionBundle) -> list[DiagnosticRecord]:
    return list(collection_bundle.diagnostics)



def build_readiness(project_root: Path) -> list[ReadinessRecord]:
    runner = CommandRunner()
    wmi_snapshot = wmi_source.collect(runner)
    nvidia_snapshot = nvidia_source.collect(runner)
    afterburner_snapshot = afterburner_source.collect()

    readiness = [
        ReadinessRecord('Core collectors', 'available' if _evidence_available(wmi_snapshot, 'operating_system') else 'unavailable'),
        ReadinessRecord('nvidia-smi', 'available' if _evidence_available(nvidia_snapshot, 'nvidia_smi') else 'unavailable'),
        ReadinessRecord('Afterburner', 'available' if _evidence_available(afterburner_snapshot, 'afterburner_shared_memory') else 'unavailable'),
        ReadinessRecord('Saved output', 'writable' if _output_writable(project_root) else 'unwritable'),
    ]
    return readiness



def list_saved_runs(project_root: Path, limit: int | None = None) -> list[SavedRunRecord]:
    json_dir = project_root / 'reports' / 'json'
    if not json_dir.exists():
        return []

    runs: list[SavedRunRecord] = []
    for report_path in sorted(json_dir.glob(f'{REPORT_PREFIX}_*.json'), reverse=True):
        payload = json.loads(report_path.read_text(encoding='utf-8'))
        metadata = payload.get('metadata', {})
        run_stamp = str(metadata.get('run_stamp', '')) or report_path.stem.removeprefix(f'{REPORT_PREFIX}_')
        runs.append(
            SavedRunRecord(
                run_stamp=run_stamp,
                generated_at=str(metadata.get('generated_at', '')),
                text_report_path=str(sanitize_text(str(metadata.get('text_report', project_root / 'reports' / 'txt' / f'{REPORT_PREFIX}_{run_stamp}.txt')))),
                json_report_path=str(sanitize_text(str(metadata.get('json_report', report_path)))),
                evidence_directory=str(sanitize_text(str(metadata.get('evidence_directory', project_root / 'evidence' / run_stamp)))),
                section_counts={
                    'system': len(payload.get('system_metrics', [])),
                    'graphics': len(payload.get('graphics_metrics', [])),
                    'displays': len(payload.get('display_metrics', [])),
                    'storage': len(payload.get('storage_metrics', [])),
                    'settings': len(payload.get('settings_metrics', [])),
                    'telemetry': len(payload.get('telemetry_metrics', [])),
                },
            )
        )

    if limit is not None:
        return runs[:limit]
    return runs



def resolve_latest_run_stamp(project_root: Path) -> str:
    runs = list_saved_runs(project_root, limit=1)
    if not runs:
        raise FileNotFoundError('No saved audit runs were found.')
    return runs[0].run_stamp



def _saved_json_path(project_root: Path, run_stamp: str) -> Path:
    return project_root / 'reports' / 'json' / f'{REPORT_PREFIX}_{run_stamp}.json'



def _saved_text_path(project_root: Path, run_stamp: str) -> Path:
    return project_root / 'reports' / 'txt' / f'{REPORT_PREFIX}_{run_stamp}.txt'



def load_saved_report(project_root: Path, run_stamp: str) -> AuditReport:
    report_path = _saved_json_path(project_root, run_stamp)
    if not report_path.exists():
        raise FileNotFoundError(f'Saved JSON report was not found for run {run_stamp}.')
    payload = json.loads(report_path.read_text(encoding='utf-8'))
    return AuditReport.from_dict(payload)



def read_saved_report_content(project_root: Path, run_stamp: str, format_name: str) -> tuple[Path, str]:
    if format_name == 'json':
        report_path = _saved_json_path(project_root, run_stamp)
    elif format_name == 'txt':
        report_path = _saved_text_path(project_root, run_stamp)
    else:
        raise ValueError(f'Unsupported report format: {format_name}')

    if not report_path.exists():
        raise FileNotFoundError(f'Saved {format_name.upper()} report was not found for run {run_stamp}.')
    return report_path, report_path.read_text(encoding='utf-8')



def list_evidence_artifacts(project_root: Path, run_stamp: str) -> list[Path]:
    evidence_dir = project_root / 'evidence' / run_stamp
    if not evidence_dir.exists():
        raise FileNotFoundError(f'Evidence directory was not found for run {run_stamp}.')
    return sorted((path for path in evidence_dir.iterdir() if path.is_file()), key=lambda path: path.name.lower())
