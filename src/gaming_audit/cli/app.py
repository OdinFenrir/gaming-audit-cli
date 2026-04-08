from __future__ import annotations

from pathlib import Path

from rich.console import Console

from ..constants import SCOPE_DIAGNOSTICS, SCOPE_SUMMARY
from ..services.orchestrator import (
    build_diagnostics,
    build_readiness,
    build_report,
    collect_scope,
    list_evidence_artifacts,
    list_saved_runs,
    read_saved_report_content,
    resolve_latest_run_stamp,
    run_full_audit,
)
from ..utils.formatting import sanitize_text
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
    render_summary,
)


POST_ACTION_OPTIONS = {
    1: 'Back to menu',
    2: 'Exit',
}

FULL_AUDIT_NAV_BACK_TO_LIST = 1
FULL_AUDIT_NAV_BACK_TO_MENU = 2
FULL_AUDIT_NAV_PREVIOUS = 3
FULL_AUDIT_NAV_NEXT = 4



def _read_prompt(console: Console, prompt: str) -> str:
    console.print()
    return console.input(f'[menu.prompt]{prompt}[/]').strip()



def _prompt_number(console: Console, title: str, options: dict[int, str]) -> int:
    while True:
        console.print()
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


def _full_audit_section_options(sections: tuple[str, ...]) -> dict[int, str]:
    options = {index: section for index, section in enumerate(sections, start=1)}
    options[0] = 'Back to main menu'
    return options


def _full_audit_navigation_options(section_index: int, section_count: int) -> dict[int, str]:
    options = {
        FULL_AUDIT_NAV_BACK_TO_LIST: 'Section list',
        FULL_AUDIT_NAV_BACK_TO_MENU: 'Back to main menu',
    }
    if section_index > 0:
        options[FULL_AUDIT_NAV_PREVIOUS] = 'Previous section'
    if section_index < section_count - 1:
        options[FULL_AUDIT_NAV_NEXT] = 'Next section'
    return options


def _run_full_audit_viewer(console: Console, report, sections: tuple[str, ...]) -> None:
    while True:
        console.clear()
        selected_section = _prompt_number(console, 'Full Audit Sections', _full_audit_section_options(sections))
        if selected_section == 0:
            return

        section_index = selected_section - 1
        while True:
            console.clear()
            render_report(console, report, (sections[section_index],))
            navigation_options = _full_audit_navigation_options(section_index, len(sections))
            selection = _prompt_number(console, f'Full Audit Viewer ({section_index + 1}/{len(sections)})', navigation_options)
            if selection == FULL_AUDIT_NAV_BACK_TO_LIST:
                break
            if selection == FULL_AUDIT_NAV_BACK_TO_MENU:
                return
            if selection == FULL_AUDIT_NAV_PREVIOUS:
                section_index -= 1
                continue
            if selection == FULL_AUDIT_NAV_NEXT:
                section_index += 1



def _render_request(project_root: Path, request: ActionRequest, console: Console) -> bool:
    action = get_action(request.action_key)

    if request.action_key == 'summary':
        bundle = collect_scope(project_root, SCOPE_SUMMARY, persist_evidence=False)
        try:
            report = build_report(project_root, bundle)
            render_summary(console, report)
        finally:
            bundle.cleanup()
        return False

    if request.action_key == 'full_audit':
        report = run_full_audit(project_root)
        if request.interactive:
            _run_full_audit_viewer(console, report, action.sections)
            return True
        render_report(console, report, action.sections)
        return False

    if action.scope is not None:
        bundle = collect_scope(project_root, action.scope, persist_evidence=False)
        try:
            report = build_report(project_root, bundle)
            render_report(console, report, action.sections)
        finally:
            bundle.cleanup()
        return False

    if request.action_key == 'reports_list':
        runs = list_saved_runs(project_root, limit=request.limit or 10)
        render_saved_runs(console, runs, 'Recent Reports')
        return False

    if request.action_key in {'reports_latest', 'reports_show'}:
        run_stamp = request.run_stamp or resolve_latest_run_stamp(project_root)
        report_path, content = read_saved_report_content(project_root, run_stamp, request.format_name)
        render_report_content(console, str(report_path), request.format_name, content)
        return False

    if request.action_key == 'evidence_list':
        run_stamp = request.run_stamp or resolve_latest_run_stamp(project_root)
        evidence_paths = [str(path) for path in list_evidence_artifacts(project_root, run_stamp)]
        render_evidence_paths(console, run_stamp, evidence_paths)
        return False

    if request.action_key == 'diagnostics':
        bundle = collect_scope(project_root, SCOPE_DIAGNOSTICS, persist_evidence=False)
        try:
            render_diagnostics(console, build_diagnostics(bundle))
        finally:
            bundle.cleanup()
        return False

    raise InvalidCliUsage(f'Unsupported action: {request.action_key}')



def run_menu(project_root: Path, console: Console | None = None) -> int:
    active_console = console or create_console()
    readiness = build_readiness(project_root)
    while True:
        active_console.clear()
        render_menu(active_console, readiness)
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
            handled_in_viewer = _render_request(project_root, _request_from_menu_action(action.key), active_console)
        except Exception as error:
            render_error(active_console, 'Action Error', str(error))
            handled_in_viewer = False
        if handled_in_viewer:
            continue
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
