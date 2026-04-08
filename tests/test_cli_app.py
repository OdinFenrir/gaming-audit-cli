from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

from rich.console import Console

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / 'src'
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from gaming_audit.cli.actions import ActionRequest
from gaming_audit.cli.app import _render_request, run_menu
from tests.test_rich_rendering import make_sample_report


class CliAppTests(unittest.TestCase):
    def test_render_request_uses_viewer_for_interactive_full_audit(self) -> None:
        console = mock.Mock(spec=Console)
        report = make_sample_report()
        request = ActionRequest(action_key='full_audit', interactive=True)

        with (
            mock.patch('gaming_audit.cli.app.run_full_audit', return_value=report) as run_full_audit,
            mock.patch('gaming_audit.cli.app._run_full_audit_viewer') as run_viewer,
            mock.patch('gaming_audit.cli.app.render_report') as render_report,
        ):
            handled_in_viewer = _render_request(PROJECT_ROOT, request, console)

        self.assertTrue(handled_in_viewer)
        run_full_audit.assert_called_once_with(PROJECT_ROOT)
        run_viewer.assert_called_once()
        render_report.assert_not_called()

    def test_render_request_renders_full_report_for_noninteractive_full_audit(self) -> None:
        console = mock.Mock(spec=Console)
        report = make_sample_report()
        request = ActionRequest(action_key='full_audit', interactive=False)

        with (
            mock.patch('gaming_audit.cli.app.run_full_audit', return_value=report) as run_full_audit,
            mock.patch('gaming_audit.cli.app._run_full_audit_viewer') as run_viewer,
            mock.patch('gaming_audit.cli.app.render_report') as render_report,
        ):
            handled_in_viewer = _render_request(PROJECT_ROOT, request, console)

        self.assertFalse(handled_in_viewer)
        run_full_audit.assert_called_once_with(PROJECT_ROOT)
        run_viewer.assert_not_called()
        render_report.assert_called_once()

    def test_run_menu_skips_post_action_prompt_after_full_audit_viewer(self) -> None:
        console = mock.Mock(spec=Console)

        with (
            mock.patch('gaming_audit.cli.app.build_readiness', return_value=[]),
            mock.patch('gaming_audit.cli.app.render_menu'),
            mock.patch('gaming_audit.cli.app._read_prompt', side_effect=['2', '14']),
            mock.patch('gaming_audit.cli.app._render_request', side_effect=[True]) as render_request,
            mock.patch('gaming_audit.cli.app._prompt_number') as prompt_number,
        ):
            result = run_menu(PROJECT_ROOT, console)

        self.assertEqual(result, 0)
        render_request.assert_called_once()
        prompt_number.assert_not_called()


if __name__ == '__main__':
    unittest.main()
