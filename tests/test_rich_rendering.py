from __future__ import annotations

import io
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / 'src'
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from gaming_audit.models import AuditReport, DiagnosticRecord, MetricRecord, ReadinessRecord
from gaming_audit.cli.render import create_console, render_diagnostics, render_menu, render_report, render_summary



def make_metric(metric_id: str, label: str, display_value: str, raw_value, source_name: str, section: str = 'Live Telemetry') -> MetricRecord:
    return MetricRecord(
        metric_id=metric_id,
        section=section,
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
        system_metrics=[
            make_metric('windows_edition', 'Windows Edition', 'Windows 11 Home', 'Windows 11 Home', 'WMI', 'System'),
            make_metric('windows_build_number', 'Windows Build Number', '26200', '26200', 'WMI', 'System'),
            make_metric('cpu_name', 'CPU Name', 'AMD Ryzen 7 5800X3D', 'AMD Ryzen 7 5800X3D', 'WMI processor', 'System'),
            make_metric('total_physical_memory_bytes', 'Total Physical Memory', '31.91 GB', 34263000000, 'WMI', 'System'),
        ],
        graphics_metrics=[
            make_metric('nvidia_gpu_name', 'NVIDIA GPU Name', 'NVIDIA GeForce RTX 3070', 'NVIDIA GeForce RTX 3070', 'nvidia-smi', 'Graphics'),
            make_metric('nvidia_driver_version', 'GPU Driver Version', '595.97', '595.97', 'nvidia-smi', 'Graphics'),
        ],
        display_metrics=[
            make_metric('display_1_monitor_model', 'Display 1 Monitor Model', 'XB271HU', 'XB271HU', 'dxdiag', 'Displays'),
            make_metric('display_1_active_resolution', 'Display 1 Active Resolution', '2560 x 1440', '2560 x 1440', 'dxdiag', 'Displays'),
            make_metric('display_1_active_refresh_rate', 'Display 1 Active Refresh Rate', '165 Hz', 165.0, 'dxdiag', 'Displays'),
        ],
        storage_metrics=[],
        settings_metrics=[make_metric('active_power_scheme', 'Active Power Plan', 'Ultimate Performance', 'Ultimate Performance', 'powercfg', 'Gaming Settings')],
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

    def test_render_menu_includes_readiness_and_command_hints(self) -> None:
        console = self._console()
        render_menu(
            console,
            [
                ReadinessRecord('Core collectors', 'available'),
                ReadinessRecord('nvidia-smi', 'unavailable'),
                ReadinessRecord('Afterburner', 'unavailable'),
                ReadinessRecord('Saved output', 'writable'),
            ],
        )
        output = console.export_text()
        self.assertIn('Raw PC facts, compact section views', output)
        self.assertIn('Readiness', output)
        self.assertIn('Quick summary', output)
        self.assertIn('audit summary', output)
        self.assertIn('Optional collectors degrade gracefully.', output)

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

    def test_render_report_keeps_short_sections_at_fixed_width(self) -> None:
        console = self._console()
        render_report(console, make_sample_report(), ('Gaming Settings', 'Live Telemetry'))
        lines = console.export_text().splitlines()

        def visible_width(containing: str) -> int:
            matching_line = next(line for line in lines if containing in line)
            first = min(index for index, char in enumerate(matching_line) if char != ' ')
            last = max(index for index, char in enumerate(matching_line) if char != ' ')
            return last - first + 1

        self.assertEqual(visible_width('Gaming Settings'), visible_width('Live Telemetry'))

    def test_render_summary_is_plain_text_and_compact(self) -> None:
        console = self._console()
        render_summary(console, make_sample_report())
        output = console.export_text()
        self.assertIn('PC Gaming Audit Summary', output)
        self.assertIn('Primary Display', output)
        self.assertNotIn('Storage', output)

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
        self.assertIn('--query-gpu=name', output)


if __name__ == '__main__':
    unittest.main()
