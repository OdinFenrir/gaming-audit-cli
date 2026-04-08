from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / 'src'
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from gaming_audit.models import AuditReport, MetricRecord, ReadinessRecord
from gaming_audit.reporters.console_reporter import render_console_report
from gaming_audit.reporters.summary_reporter import render_summary_text


def make_metric(metric_id: str, label: str, display_value: str, raw_value, source_name: str, section: str = 'Live Telemetry') -> MetricRecord:
    return MetricRecord(
        metric_id=metric_id,
        section=section,
        label=label,
        raw_value=raw_value,
        display_value=display_value,
        unit="",
        availability="available",
        source_name=source_name,
        source_command="source command",
        captured_at="2026-04-07T22:00:00+01:00",
    )


def make_sample_report() -> AuditReport:
    telemetry_metrics = [
        make_metric("nvidia_temperature_gpu", "GPU Temperature", "50", "50", "nvidia-smi"),
        make_metric("nvidia_utilization_gpu", "GPU Utilization", "2 %", "2", "nvidia-smi"),
        make_metric("afterburner_gpu_temp", "GPU temperature", "49 C", 49.0, "MSI Afterburner Shared Memory"),
        make_metric("afterburner_cpu_temp", "CPU temperature", "59.5 C", 59.5, "MSI Afterburner Shared Memory"),
        make_metric("afterburner_cpu1_temp", "CPU1 temperature", "58 C", 58.0, "MSI Afterburner Shared Memory"),
        make_metric("afterburner_cpu2_temp", "CPU2 temperature", "61 C", 61.0, "MSI Afterburner Shared Memory"),
        make_metric("afterburner_commit_charge", "Commit charge", "12729 MB", 12729.0, "MSI Afterburner Shared Memory"),
        make_metric("afterburner_temp_limit", "Temp limit", "0", 0.0, "MSI Afterburner Shared Memory"),
    ]
    return AuditReport(
        metadata={
            "generated_at": "2026-04-07T22:00:00+01:00",
            "text_report_relative": r"reports\txt\system_audit_20260407_220000.txt",
            "json_report_relative": r"reports\json\system_audit_20260407_220000.json",
            "latest_snapshot_relative": r"snapshots\latest.json",
            "evidence_directory_relative": r"evidence\20260407_220000",
        },
        system_metrics=[
            make_metric("windows_edition", "Windows Edition", "Windows 11 Home", "Windows 11 Home", "WMI", "System"),
            make_metric("windows_version", "Windows Version", "24H2", "24H2", "WMI", "System"),
            make_metric("windows_build_number", "Windows Build Number", "26200", "26200", "WMI", "System"),
            make_metric("cpu_name", "CPU Name", "AMD Ryzen 7 5800X3D", "AMD Ryzen 7 5800X3D", "WMI processor", "System"),
            make_metric("total_physical_memory_bytes", "Total Physical Memory", "31.91 GB", 34263000000, "WMI", "System"),
        ],
        graphics_metrics=[
            make_metric("nvidia_gpu_name", "NVIDIA GPU Name", "NVIDIA GeForce RTX 3070", "NVIDIA GeForce RTX 3070", "nvidia-smi", "Graphics"),
            make_metric("nvidia_driver_version", "GPU Driver Version", "595.97", "595.97", "nvidia-smi", "Graphics"),
        ],
        display_metrics=[
            make_metric("display_1_monitor_model", "Display 1 Monitor Model", "XB271HU", "XB271HU", "dxdiag", "Displays"),
            make_metric("display_1_active_resolution", "Display 1 Active Resolution", "2560 x 1440", "2560 x 1440", "dxdiag", "Displays"),
            make_metric("display_1_active_refresh_rate", "Display 1 Active Refresh Rate", "165 Hz", 165.0, "dxdiag", "Displays"),
        ],
        storage_metrics=[],
        settings_metrics=[
            make_metric("active_power_scheme", "Active Power Plan", "Ultimate Performance", "Ultimate Performance", "powercfg", "Gaming Settings"),
            make_metric("auto_game_mode_enabled", "Auto Game Mode Enabled", "Yes", True, "registry", "Gaming Settings"),
            make_metric("game_dvr_enabled", "Game DVR Enabled", "No", False, "registry", "Gaming Settings"),
        ],
        telemetry_metrics=telemetry_metrics,
        software_inventory=[],
        process_inventory=[],
        service_inventory=[],
        unavailable_metrics=[],
        evidence_records=[],
    )


class ReporterTests(unittest.TestCase):
    def test_console_report_contains_sections_and_compact_telemetry(self) -> None:
        output = render_console_report(make_sample_report())
        self.assertIn("Overview", output)
        self.assertIn("Primary Display", output)
        self.assertIn("GPU Snapshot [nvidia-smi]", output)
        self.assertIn("GPU Snapshot [MSI Afterburner]", output)
        self.assertIn("CPU Per-Core Summary [MSI Afterburner]", output)
        self.assertIn("CPU Temperature Range", output)
        self.assertNotIn("CPU1 temperature", output)
        self.assertNotIn("CPU2 temperature", output)
        self.assertIn("Additional Raw Telemetry [JSON]", output)

    def test_summary_report_is_compact_and_high_signal(self) -> None:
        output = render_summary_text(make_sample_report())
        self.assertIn('PC Gaming Audit Summary', output)
        self.assertIn('OS', output)
        self.assertIn('CPU', output)
        self.assertIn('GPU', output)
        self.assertIn('Primary Display', output)
        self.assertIn('Power Plan', output)
        self.assertIn('Telemetry', output)
        self.assertIn('GPU Temp', output)
        self.assertIn('GPU Usage', output)
        self.assertNotIn('Storage', output)
        self.assertNotIn('Processes', output)
        self.assertNotIn('Services', output)
        self.assertLessEqual(len([line for line in output.splitlines() if line.strip()]), 12)


if __name__ == "__main__":
    unittest.main()
