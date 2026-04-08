from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / 'src'
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from gaming_audit.cli.actions import MENU_ACTIONS, resolve_menu_selection


class CliActionRegistryTests(unittest.TestCase):
    def test_menu_numbers_are_unique(self) -> None:
        menu_numbers = [action.menu_number for action in MENU_ACTIONS]
        self.assertEqual(len(menu_numbers), len(set(menu_numbers)))

    def test_menu_selection_resolves_processes_services(self) -> None:
        action = resolve_menu_selection('8')
        self.assertEqual(action.key, 'processes_services')

    def test_invalid_menu_selection_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            resolve_menu_selection('99')

        with self.assertRaises(ValueError):
            resolve_menu_selection('abc')


if __name__ == '__main__':
    unittest.main()
