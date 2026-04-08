from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / 'src'
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from gaming_audit.cli.parser import InvalidCliUsage, parse_args


class CliParserTests(unittest.TestCase):
    def test_no_args_defaults_to_menu(self) -> None:
        request = parse_args([])
        self.assertEqual(request.action_key, 'menu')
        self.assertTrue(request.interactive)

    def test_audit_full_maps_to_full_audit_action(self) -> None:
        request = parse_args(['audit', 'full'])
        self.assertEqual(request.action_key, 'full_audit')

    def test_audit_summary_maps_to_summary_action(self) -> None:
        request = parse_args(['audit', 'summary'])
        self.assertEqual(request.action_key, 'summary')

    def test_audit_section_telemetry_maps_to_telemetry_action(self) -> None:
        request = parse_args(['audit', 'section', 'telemetry'])
        self.assertEqual(request.action_key, 'telemetry')

    def test_reports_latest_json_preserves_requested_format(self) -> None:
        request = parse_args(['reports', 'latest', '--format', 'json'])
        self.assertEqual(request.action_key, 'reports_latest')
        self.assertEqual(request.format_name, 'json')

    def test_invalid_section_raises_invalid_cli_usage(self) -> None:
        with self.assertRaises(InvalidCliUsage):
            parse_args(['audit', 'section', 'invalid'])


if __name__ == '__main__':
    unittest.main()
