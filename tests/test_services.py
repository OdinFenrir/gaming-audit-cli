from __future__ import annotations

import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / 'src'
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from gaming_audit.constants import AVAILABILITY_AVAILABLE, SCOPE_DIAGNOSTICS, SCOPE_FULL, SCOPE_SYSTEM, SCOPE_TELEMETRY
from gaming_audit.models import CollectedSource, EvidenceRecord, RuntimePaths, CollectionBundle
from gaming_audit.services import build_diagnostics, build_report, collect_scope, list_saved_runs, read_saved_report_content, save_full_audit
import gaming_audit.services.orchestrator as orchestrator


class OrchestratorServiceTests(unittest.TestCase):
    def _collector_map(self, called: list[str]) -> dict[str, object]:
        def make_collector(source_key: str):
            def collector(runner, evidence_dir):
                called.append(source_key)
                return CollectedSource(
                    evidence={
                        source_key: EvidenceRecord(
                            source_name=f'{source_key} source',
                            source_command=f'collect {source_key}',
                            availability=AVAILABILITY_AVAILABLE,
                            captured_at='2026-04-07T23:00:00+01:00',
                            raw_output=f'{source_key} output',
                            artifact_filename=f'{source_key}.txt',
                            stderr='',
                            return_code=0,
                        )
                    }
                )
            return collector

        return {source_key: make_collector(source_key) for source_key in orchestrator.SOURCE_COLLECTORS.keys()}

    def test_collect_scope_uses_only_requested_system_sources(self) -> None:
        called: list[str] = []
        collector_map = self._collector_map(called)
        with TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            with patch.dict(orchestrator.SOURCE_COLLECTORS, collector_map, clear=True):
                bundle = collect_scope(project_root, SCOPE_SYSTEM, persist_evidence=False)
                self.assertEqual(set(bundle.snapshots.keys()), {'wmi', 'network'})
                self.assertEqual(called, ['wmi', 'network'])
                self.assertFalse((project_root / 'reports').exists())
                bundle.cleanup()

    def test_collect_scope_uses_only_requested_telemetry_sources(self) -> None:
        called: list[str] = []
        collector_map = self._collector_map(called)
        with TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            with patch.dict(orchestrator.SOURCE_COLLECTORS, collector_map, clear=True):
                bundle = collect_scope(project_root, SCOPE_TELEMETRY, persist_evidence=False)
                self.assertEqual(set(bundle.snapshots.keys()), {'nvidia', 'afterburner'})
                self.assertEqual(called, ['nvidia', 'afterburner'])
                self.assertFalse((project_root / 'reports').exists())
                bundle.cleanup()

    def test_full_audit_save_writes_reports_snapshot_and_evidence(self) -> None:
        called: list[str] = []
        collector_map = self._collector_map(called)
        with TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            with patch.dict(orchestrator.SOURCE_COLLECTORS, collector_map, clear=True):
                bundle = collect_scope(project_root, SCOPE_FULL, persist_evidence=True)
                report = build_report(project_root, bundle)
                save_full_audit(report, bundle)

                self.assertTrue(bundle.runtime_paths.text_report.exists())
                self.assertTrue(bundle.runtime_paths.json_report.exists())
                self.assertTrue(bundle.runtime_paths.latest_snapshot.exists())
                self.assertTrue(bundle.runtime_paths.evidence_dir.exists())
                self.assertTrue(any(bundle.runtime_paths.evidence_dir.iterdir()))

                runs = list_saved_runs(project_root, limit=1)
                self.assertEqual(len(runs), 1)
                report_path, content = read_saved_report_content(project_root, runs[0].run_stamp, 'json')
                self.assertTrue(report_path.exists())
                self.assertIn('metadata', content)
                self.assertNotIn('machine_name', content)
                bundle.cleanup()

    def test_diagnostics_include_artifact_paths_and_errors_when_materialized(self) -> None:
        called: list[str] = []
        collector_map = self._collector_map(called)
        with TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            with patch.dict(orchestrator.SOURCE_COLLECTORS, collector_map, clear=True):
                bundle = collect_scope(project_root, SCOPE_DIAGNOSTICS, persist_evidence=False)
                diagnostics = build_diagnostics(bundle)
                self.assertTrue(diagnostics)
                self.assertTrue(any(item.artifact_path for item in diagnostics))
                self.assertTrue(any(item.return_code == 0 for item in diagnostics))
                bundle.cleanup()


    def test_build_report_sanitizes_user_paths_and_guids_in_metadata(self) -> None:
        with TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir) / 'Users' / 'ldomi' / 'repo'
            project_root.mkdir(parents=True, exist_ok=True)
            bundle = CollectionBundle(
                scope=SCOPE_SYSTEM,
                run_stamp='20260408_000000',
                runtime_paths=orchestrator.RuntimePaths(
                    evidence_dir=project_root / 'evidence' / '20260408_000000',
                    text_report=project_root / 'reports' / 'txt' / 'system_audit_20260408_000000.txt',
                    json_report=project_root / 'reports' / 'json' / 'system_audit_20260408_000000.json',
                    latest_snapshot=project_root / 'snapshots' / 'latest.json',
                ),
            )
            report = build_report(project_root, bundle)
            self.assertIn('[redacted]', report.metadata['project_root'])
            self.assertIn('[redacted]', report.metadata['json_report'])
if __name__ == '__main__':
    unittest.main()


