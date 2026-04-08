from __future__ import annotations

import io
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / 'src'
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from gaming_audit.models import AuditReport, DiagnosticRecord, MetricRecord
from gaming_audit.cli.render import create_console, render_diagnostics, render_menu, render_report



def make_metric(metric_id: str, label: str, display_value: str, raw_value, source_name: str) -> MetricRecord:
    return MetricRecord(
        metric_id=metric_id,
        section='Live Telemetry',
        label=label,
        raw_value=raw_value,
        display_value=display_value,
        unit='',
        availability='available',
        source_name=source_name,
        source_command='source command',
        captured_at='2026-04-07T22:00:00+01:00',
    )



def make_sample_report() -> AuditReport:
    telemetry_metrics = [
        make_metric('nvidia_temperature_gpu', 'GPU Temperature', '50', '50', 'nvidia-smi'),
        make_metric('nvidia_utilization_gpu', 'GPU Utilization', '2 %', '2', 'nvidia-smi'),
        make_metric('afterburner_gpu_temp', 'GPU temperature', '49 C', 49.0, 'MSI Afterburner Shared Memory'),
        make_metric('afterburner_cpu_temp', 'CPU temperature', '59.5 C', 59.5, 'MSI Afterburner Shared Memory'),
        make_metric('afterburner_cpu1_temp', 'CPU1 temperature', '58 C', 58.0, 'MSI Afterburner Shared Memory'),
        make_metric('afterburner_cpu2_temp', 'CPU2 temperature', '61 C', 61.0, 'MSI Afterburner Shared Memory'),
        make_metric('afterburner_commit_charge', 'Commit charge', '12729 MB', 12729.0, 'MSI Afterburner Shared Memory'),
        make_metric('afterburner_temp_limit', 'Temp limit', '0', 0.0, 'MSI Afterburner Shared Memory'),
    ]
    return AuditReport(
        metadata={
            'generated_at': '2026-04-07T22:00:00+01:00',
            'json_report_relative': r'reports\json\system_audit_20260407_220000.json',
        },
        system_metrics=[make_metric('cpu_name', 'CPU Name', 'AMD Ryzen 7 5800X3D', 'AMD Ryzen 7 5800X3D', 'WMI processor')],
        graphics_metrics=[make_metric('nvidia_gpu_name', 'NVIDIA GPU Name', 'NVIDIA GeForce RTX 3070', 'NVIDIA GeForce RTX 3070', 'nvidia-smi')],
        display_metrics=[
            make_metric('display_1_monitor_model', 'Display 1 Monitor Model', 'XB271HU', 'XB271HU', 'dxdiag'),
            make_metric('display_1_active_resolution', 'Display 1 Active Resolution', '2560 x 1440', '2560 x 1440', 'dxdiag'),
            make_metric('display_1_active_refresh_rate', 'Display 1 Active Refresh Rate', '165 Hz', 165.0, 'dxdiag'),
        ],
        storage_metrics=[],
        settings_metrics=[],
        telemetry_metrics=telemetry_metrics,
        software_inventory=[],
        process_inventory=[],
        service_inventory=[],
        unavailable_metrics=[],
        evidence_records=[],
    )


class RichRenderingTests(unittest.TestCase):
    def _console(self):
        return create_console(record=True, width=180, file=io.StringIO(), force_terminal=False, color_system=None)

    def test_render_menu_includes_compact_tables_and_command_hints(self) -> None:
        console = self._console()
        render_menu(console)
        output = console.export_text()
        self.assertIn('Raw PC facts, compact section views', output)
        self.assertIn('Audit Views', output)
        self.assertIn('Reports And Tools', output)
        self.assertIn('Telemetry snapshot', output)
        self.assertIn('Current nvidia-smi and', output)
        self.assertIn('Afterburner.', output)
        self.assertIn('audit section telemetry', output)
        self.assertIn('Type a number and press Enter.', output)

    def test_render_report_groups_compact_telemetry_without_verdict_language(self) -> None:
        console = self._console()
        render_report(console, make_sample_report(), ('Overview', 'Live Telemetry'))
        output = console.export_text()
        self.assertIn('Read-only snapshot of raw system facts.', output)
        self.assertIn('GPU Snapshot [nvidia-smi]', output)
        self.assertIn('GPU Snapshot [MSI Afterburner]', output)
        self.assertIn('CPU Per-Core Summary [MSI Afterburner]', output)
        self.assertNotIn('CPU1 temperature', output)
        self.assertNotIn('CPU2 temperature', output)
        self.assertNotIn('PASS', output)
        self.assertNotIn('WARN', output)
        self.assertNotIn('FAIL', output)
        self.assertNotIn('score', output.lower())
        self.assertNotIn('verdict', output.lower())

    def test_render_diagnostics_includes_source_details(self) -> None:
        console = self._console()
        render_diagnostics(
            console,
            [
                DiagnosticRecord(
                    source_key='nvidia.nvidia_smi',
                    source_name='nvidia-smi',
                    availability='available',
                    source_command='nvidia-smi --query-gpu=name',
                    captured_at='2026-04-07T22:00:00+01:00',
                    artifact_filename='nvidia_smi.csv',
                    artifact_path=r'C:\Reports\nvidia_smi.csv',
                    stderr='',
                    return_code=0,
                )
            ],
        )
        output = console.export_text()
        self.assertIn('Every source is shown', output)
        self.assertIn('nvidia.nvidia_smi', output)
        self.assertIn('nvidia-smi', output)
        self.assertIn('--query-gpu=name', output)
        self.assertIn(r'C:\Reports\n', output)
        self.assertIn('vidia_smi.cs', output)


if __name__ == '__main__':
    unittest.main()


