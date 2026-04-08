from __future__ import annotations

from pathlib import Path

from rich.console import Console

from ..constants import SCOPE_DIAGNOSTICS
from ..services.orchestrator import (
    build_diagnostics,
    build_report,
    collect_scope,
    list_evidence_artifacts,
    list_saved_runs,
    read_saved_report_content,
    resolve_latest_run_stamp,
    run_full_audit,
)
from .actions import ActionRequest, get_action, resolve_menu_selection
from .parser import InvalidCliUsage, parse_args
from .render import (
    create_console,
    render_diagnostics,
    render_error,
    render_evidence_paths,
    render_menu,
    render_numeric_choices,
    render_report,
    render_report_content,
    render_saved_runs,
)


POST_ACTION_OPTIONS = {
    1: 'Back to menu',
    2: 'Exit',
}



def _read_prompt(console: Console, prompt: str) -> str:
    console.print()
    return console.input(f'[menu.prompt]{prompt}[/]').strip()



def _prompt_number(console: Console, title: str, options: dict[int, str]) -> int:
    while True:
        console.clear()
        render_numeric_choices(console, title, options)
        selection = _read_prompt(console, 'Select a number: ')
        try:
            numeric_selection = int(selection)
        except ValueError:
            render_error(console, 'Invalid Selection', 'Please enter one of the numbered choices.')
            continue
        if numeric_selection in options:
            return numeric_selection
        render_error(console, 'Invalid Selection', 'Please enter one of the numbered choices.')



def _request_from_menu_action(action_key: str) -> ActionRequest:
    if action_key == 'recent_reports':
        return ActionRequest(action_key='reports_list', limit=8, interactive=True)
    if action_key == 'evidence_browser':
        return ActionRequest(action_key='evidence_list', interactive=True)
    if action_key == 'diagnostics':
        return ActionRequest(action_key='diagnostics', interactive=True)
    return ActionRequest(action_key=action_key, interactive=True)



def _render_request(project_root: Path, request: ActionRequest, console: Console) -> None:
    action = get_action(request.action_key)

    if request.action_key == 'full_audit':
        report = run_full_audit(project_root)
        render_report(console, report, action.sections)
        return

    if action.scope is not None:
        bundle = collect_scope(project_root, action.scope, persist_evidence=False)
        try:
            report = build_report(project_root, bundle)
            render_report(console, report, action.sections)
        finally:
            bundle.cleanup()
        return

    if request.action_key == 'reports_list':
        runs = list_saved_runs(project_root, limit=request.limit or 10)
        render_saved_runs(console, runs, 'Recent Reports')
        return

    if request.action_key in {'reports_latest', 'reports_show'}:
        run_stamp = request.run_stamp or resolve_latest_run_stamp(project_root)
        report_path, content = read_saved_report_content(project_root, run_stamp, request.format_name)
        render_report_content(console, str(report_path), request.format_name, content)
        return

    if request.action_key == 'evidence_list':
        run_stamp = request.run_stamp or resolve_latest_run_stamp(project_root)
        evidence_paths = [str(path) for path in list_evidence_artifacts(project_root, run_stamp)]
        render_evidence_paths(console, run_stamp, evidence_paths)
        return

    if request.action_key == 'diagnostics':
        bundle = collect_scope(project_root, SCOPE_DIAGNOSTICS, persist_evidence=False)
        try:
            render_diagnostics(console, build_diagnostics(bundle))
        finally:
            bundle.cleanup()
        return

    raise InvalidCliUsage(f'Unsupported action: {request.action_key}')



def run_menu(project_root: Path, console: Console | None = None) -> int:
    active_console = console or create_console()
    while True:
        active_console.clear()
        render_menu(active_console)
        selection = _read_prompt(active_console, 'Select a number: ')
        try:
            action = resolve_menu_selection(selection)
        except ValueError as error:
            render_error(active_console, 'Invalid Selection', str(error))
            continue
        if action.key == 'exit':
            return 0
        try:
            active_console.clear()
            _render_request(project_root, _request_from_menu_action(action.key), active_console)
        except Exception as error:
            render_error(active_console, 'Action Error', str(error))
        post_action = _prompt_number(active_console, 'Next', POST_ACTION_OPTIONS)
        if post_action == 2:
            return 0



def run_from_argv(project_root: Path, argv: list[str], console: Console | None = None) -> int:
    active_console = console or create_console()
    request = parse_args(argv)
    if request.action_key == 'menu' or request.interactive:
        return run_menu(project_root, active_console)
    _render_request(project_root, request, active_console)
    return 0
