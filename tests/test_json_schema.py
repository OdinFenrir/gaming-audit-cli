from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / 'src'
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from gaming_audit.models import AuditReport


class JsonSchemaTests(unittest.TestCase):
    def test_report_dict_has_only_factual_top_level_keys(self) -> None:
        report = AuditReport(
            metadata={"generated_at": "2026-04-07T22:00:00+01:00"},
            system_metrics=[],
            graphics_metrics=[],
            display_metrics=[],
            storage_metrics=[],
            settings_metrics=[],
            telemetry_metrics=[],
            software_inventory=[],
            process_inventory=[],
            service_inventory=[],
            unavailable_metrics=[],
            evidence_records=[],
        )
        payload = report.to_dict()
        self.assertEqual(
            list(payload.keys()),
            [
                "metadata",
                "system_metrics",
                "graphics_metrics",
                "display_metrics",
                "storage_metrics",
                "settings_metrics",
                "software_inventory",
                "process_inventory",
                "service_inventory",
                "telemetry_metrics",
                "unavailable_metrics",
            ],
        )
        self.assertNotIn("readiness", payload)
        self.assertNotIn("score", payload)
        self.assertNotIn("verdict", payload)


if __name__ == "__main__":
    unittest.main()
