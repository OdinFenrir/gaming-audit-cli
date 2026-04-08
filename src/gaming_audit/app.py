from __future__ import annotations

import sys
from pathlib import Path



def main(project_root: Path, argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')

    try:
        import rich  # noqa: F401
    except ModuleNotFoundError:
        print('Rich is required for the audit CLI. Install it with: python -m pip install rich', file=sys.stderr)
        return 1

    from .cli import InvalidCliUsage, create_console, render_error, run_from_argv

    arguments = sys.argv[1:] if argv is None else argv
    try:
        return run_from_argv(project_root, arguments)
    except InvalidCliUsage as error:
        console = create_console()
        render_error(console, 'Invalid CLI Usage', str(error))
        return 2
    except Exception as error:
        console = create_console()
        render_error(console, 'Audit CLI Error', str(error))
        return 1
