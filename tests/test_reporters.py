from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / 'src'
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from gaming_audit.models import AuditReport, MetricRecord
from gaming_audit.reporters.console_reporter import render_console_report


def make_metric(metric_id: str, label: str, display_value: str, raw_value, source_name: str) -> MetricRecord:
    return MetricRecord(
        metric_id=metric_id,
        section="Live Telemetry",
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
        system_metrics=[make_metric("cpu_name", "CPU Name", "AMD Ryzen 7 5800X3D", "AMD Ryzen 7 5800X3D", "WMI processor")],
        graphics_metrics=[make_metric("nvidia_gpu_name", "NVIDIA GPU Name", "NVIDIA GeForce RTX 3070", "NVIDIA GeForce RTX 3070", "nvidia-smi")],
        display_metrics=[
            make_metric("display_1_monitor_model", "Display 1 Monitor Model", "XB271HU", "XB271HU", "dxdiag"),
            make_metric("display_1_active_resolution", "Display 1 Active Resolution", "2560 x 1440", "2560 x 1440", "dxdiag"),
            make_metric("display_1_active_refresh_rate", "Display 1 Active Refresh Rate", "165 Hz", 165.0, "dxdiag"),
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
        self.assertNotIn("PASS", output)
        self.assertNotIn("WARN", output)
        self.assertNotIn("FAIL", output)
        self.assertNotIn("score", output.lower())
        self.assertNotIn("final verdict", output.lower())


if __name__ == "__main__":
    unittest.main()

