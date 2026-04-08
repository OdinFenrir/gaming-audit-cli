from __future__ import annotations

import json
from pathlib import Path

from rich import box
from rich.align import Align
from rich.console import Console, Group
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

from ..constants import APP_NAME
from ..models import AuditReport, DiagnosticRecord, SavedRunRecord
from ..reporters.view_data import build_section_rows
from ..utils.formatting import format_bytes
from .actions import MENU_ACTIONS


CLI_THEME = Theme(
    {
        'app.title': 'bold white',
        'app.subtitle': 'bright_cyan',
        'panel.border': 'bright_cyan',
        'panel.muted': 'grey74',
        'label': 'bold white',
        'value': 'grey93',
        'subheading': 'bold cyan',
        'menu.number': 'bold black on bright_cyan',
        'menu.title': 'bold white',
        'menu.description': 'grey89',
        'menu.command': 'bright_black',
        'menu.prompt': 'bold bright_white',
        'section.header': 'bold white',
        'status.available': 'bold green3',
        'status.unavailable': 'bold red',
        'status.running': 'bold green3',
        'status.stopped': 'bold yellow3',
        'path': 'bright_black',
    }
)

SECTION_STYLES = {
    'Overview': 'bright_cyan',
    'System': 'green3',
    'Graphics': 'medium_purple',
    'Displays': 'deep_sky_blue1',
    'Storage': 'gold3',
    'Gaming Settings': 'turquoise2',
    'Performance Tools': 'spring_green3',
    'Processes': 'orchid',
    'Services': 'steel_blue1',
    'Live Telemetry': 'bright_cyan',
    'Unavailable Metrics': 'red',
}


def create_console(**kwargs) -> Console:
    return Console(theme=CLI_THEME, highlight=False, **kwargs)


def _content_width(console: Console, preferred: int, minimum: int = 56) -> int:
    available = max(minimum, console.width - 8)
    return max(minimum, min(preferred, available))


def _center(renderable) -> Align:
    return Align.center(renderable)


def _banner(console: Console, title: str, subtitle: str, footer: str = '') -> Panel:
    width = _content_width(console, 82, 60)
    body = Group(
        Text(title, style='app.title', justify='center'),
        Text(subtitle, style='app.subtitle', justify='center'),
    )
    return Panel(
        body,
        box=box.ROUNDED,
        border_style='panel.border',
        padding=(0, 1),
        subtitle=footer,
        subtitle_align='right',
        expand=False,
        width=width,
    )


def _footer_panel(console: Console, message: str) -> Panel:
    return Panel(
        Text(message, style='menu.command', justify='center'),
        box=box.ROUNDED,
        border_style='panel.border',
        padding=(0, 1),
        expand=False,
        width=_content_width(console, 82, 60),
    )


def _style_inline_value(value: str) -> Text:
    text = Text(value, style='value')
    replacements = [
        ('Installed=Yes', 'status.available'),
        ('Installed=No', 'panel.muted'),
        ('Running=Yes', 'status.running'),
        ('Running=No', 'panel.muted'),
        ('Status=Running', 'status.running'),
        ('Status=Stopped', 'status.stopped'),
        ('available', 'status.available'),
        ('unavailable', 'status.unavailable'),
    ]
    for token, style_name in replacements:
        start = 0
        while True:
            index = value.find(token, start)
            if index == -1:
                break
            text.stylize(style_name, index, index + len(token))
            start = index + len(token)
    return text


def _menu_table(console: Console, title: str, subtitle: str, actions: list) -> Group:
    table = Table(
        box=box.SIMPLE_HEAVY,
        border_style='panel.border',
        expand=False,
        padding=(0, 1),
        row_styles=['', 'dim'],
        width=_content_width(console, 96, 64),
    )
    table.add_column('#', style='menu.number', justify='center', width=4, no_wrap=True)
    table.add_column('Action', style='menu.title', width=22, no_wrap=False)
    table.add_column('Summary', style='menu.description', min_width=20, ratio=1, no_wrap=False)
    table.add_column('CLI', style='menu.command', width=28, overflow='fold', no_wrap=False)
    for action in actions:
        command_hint = action.command_hint or 'interactive only'
        table.add_row(str(action.menu_number), action.menu_label, action.description, command_hint)
    return Group(
        Text(title, style='section.header', justify='center'),
        Text(subtitle, style='panel.muted', justify='center'),
        _center(table),
    )


def render_error(console: Console, title: str, message: str) -> None:
    panel = Panel(Text(message, style='value'), title=title, border_style='red', box=box.HEAVY, padding=(0, 1), expand=False, width=_content_width(console, 76, 52))
    console.print(_center(panel))


def render_message(console: Console, title: str, message: str) -> None:
    panel = Panel(Text(message, style='value'), title=title, border_style='panel.border', box=box.ROUNDED, padding=(0, 1), expand=False, width=_content_width(console, 76, 52))
    console.print(_center(panel))


def render_numeric_choices(console: Console, title: str, options: dict[int, str]) -> None:
    width = _content_width(console, 52, 34)
    table = Table(
        title=title,
        title_style='section.header',
        box=box.SIMPLE_HEAVY,
        border_style='panel.border',
        expand=False,
        padding=(0, 1),
        row_styles=['', 'dim'],
        width=width,
    )
    table.add_column('#', style='menu.number', justify='center', width=4, no_wrap=True)
    table.add_column('Action', style='menu.title', min_width=18)
    for number, label in options.items():
        table.add_row(str(number), label)
    console.print(_center(table))


def render_menu(console: Console) -> None:
    console.print(
        _center(
            _banner(
                console,
                APP_NAME,
                'Raw PC facts, compact section views, saved history, and diagnostics.',
                'Choose a number',
            )
        )
    )

    audit_actions = [action for action in MENU_ACTIONS if action.menu_number and action.menu_number <= 9]
    utility_actions = [action for action in MENU_ACTIONS if action.menu_number and action.menu_number >= 10]

    console.print(_menu_table(console, 'Audit Views', 'Live sections for the current machine.', audit_actions))
    console.print()
    console.print(_menu_table(console, 'Reports And Tools', 'Saved runs, evidence, and diagnostics.', utility_actions))
    console.print()
    console.print(_center(_footer_panel(console, 'Type a number and press Enter. Direct commands still work.')))


def _report_header(console: Console, report: AuditReport, sections: tuple[str, ...]) -> Panel:
    generated_at = str(report.metadata.get('generated_at', ''))
    subtitle = generated_at
    section_text = ', '.join(sections)
    body = Group(
        Text(APP_NAME, style='app.title', justify='center'),
        Text('Read-only snapshot of raw system facts. No grading. No scoring.', style='app.subtitle', justify='center'),
        Text(f'Sections: {section_text}', style='panel.muted', justify='center'),
    )
    return Panel(body, box=box.ROUNDED, border_style='panel.border', padding=(0, 1), subtitle=subtitle, subtitle_align='right', expand=False, width=_content_width(console, 88, 62))


def _render_section_table(console: Console, title: str, rows: list[tuple[str, str]]) -> None:
    if not rows:
        return

    grid = Table(
        show_header=False,
        box=None,
        expand=True,
        pad_edge=False,
        collapse_padding=True,
        padding=(0, 1),
    )
    grid.add_column('Label', style='label', ratio=1, min_width=22, no_wrap=False)
    grid.add_column('Value', style='value', ratio=2, min_width=28, no_wrap=False)

    for label, value in rows:
        if value:
            grid.add_row(Text(label, style='label'), _style_inline_value(value))
        else:
            grid.add_row(Text(''), Align.left(Text(label, style='subheading')))

    panel = Panel(
        grid,
        title=Text(title, style='section.header'),
        title_align='left',
        border_style=SECTION_STYLES.get(title, 'panel.border'),
        box=box.ROUNDED,
        padding=(0, 1),
        expand=False,
        width=_content_width(console, 90, 62),
    )
    console.print(_center(panel))


def render_report(console: Console, report: AuditReport, sections: tuple[str, ...]) -> None:
    section_rows = build_section_rows(report)
    console.print(_center(_report_header(console, report, sections)))
    for section_name in sections:
        rows = section_rows.get(section_name, [])
        if rows:
            _render_section_table(console, section_name, rows)


def render_saved_runs(console: Console, runs: list[SavedRunRecord], title: str) -> None:
    if not runs:
        render_message(console, title, 'No saved audit runs were found.')
        return

    console.print(_center(_banner(console, title, 'Saved full-audit runs sorted newest first.', 'Use reports show <run_stamp> to open one directly')))
    table = Table(
        box=box.SIMPLE_HEAVY,
        border_style='panel.border',
        header_style='bold bright_white',
        expand=False,
        padding=(0, 1),
        row_styles=['', 'dim'],
        width=_content_width(console, 104, 74),
    )
    table.add_column('Run Stamp', style='menu.title', width=17, no_wrap=True)
    table.add_column('Generated At', style='value', width=25)
    table.add_column('TXT Report', style='path', ratio=1, overflow='fold')
    table.add_column('JSON Report', style='path', ratio=1, overflow='fold')
    table.add_column('Evidence', style='path', ratio=1, overflow='fold')
    for run in runs:
        table.add_row(
            run.run_stamp,
            run.generated_at,
            run.text_report_path,
            run.json_report_path,
            run.evidence_directory,
        )
    console.print(_center(table))


def render_report_content(console: Console, path: str, format_name: str, content: str) -> None:
    console.print(_center(_banner(console, f'Saved {format_name.upper()} Report', path, 'Loaded from disk')))
    if format_name == 'json':
        try:
            content = json.dumps(json.loads(content), indent=2)
        except json.JSONDecodeError:
            pass
        console.print(_center(Panel(Syntax(content, 'json', word_wrap=True, line_numbers=True), border_style='panel.border', box=box.ROUNDED, padding=(0, 1), expand=False, width=_content_width(console, 96, 68))))
        return
    console.print(_center(Panel(Text(content, style='value'), border_style='panel.border', box=box.ROUNDED, padding=(0, 1), expand=False, width=_content_width(console, 88, 62))))


def render_evidence_paths(console: Console, run_stamp: str, evidence_paths: list[str]) -> None:
    if not evidence_paths:
        render_message(console, 'Evidence Browser', f'No evidence artifacts were found for run {run_stamp}.')
        return

    console.print(_center(_banner(console, 'Evidence Browser', f'Raw artifacts for run {run_stamp}', 'Absolute paths are shown below')))
    table = Table(
        box=box.SIMPLE_HEAVY,
        border_style='panel.border',
        header_style='bold bright_white',
        expand=False,
        padding=(0, 1),
        row_styles=['', 'dim'],
        width=_content_width(console, 96, 70),
    )
    table.add_column('File', style='menu.title', min_width=20)
    table.add_column('Size', style='value', width=12, justify='right')
    table.add_column('Absolute Path', style='path', ratio=2, overflow='fold')
    for raw_path in evidence_paths:
        path = Path(raw_path)
        size_value = format_bytes(path.stat().st_size) if path.exists() else 'Unavailable'
        table.add_row(path.name, size_value, str(path))
    console.print(_center(table))


def render_diagnostics(console: Console, diagnostics: list[DiagnosticRecord]) -> None:
    if not diagnostics:
        render_message(console, 'Diagnostics', 'No diagnostics were available for this run.')
        return

    console.print(_center(_banner(console, 'Diagnostics', 'Every source is shown, including unavailable ones.', 'Collectors and stderr are visible below')))
    table = Table(
        box=box.SIMPLE_HEAVY,
        border_style='panel.border',
        header_style='bold bright_white',
        expand=False,
        padding=(0, 1),
        row_styles=['', 'dim'],
        width=_content_width(console, 106, 76),
    )
    table.add_column('Source Key', style='menu.title', min_width=18)
    table.add_column('Availability', width=13, no_wrap=True)
    table.add_column('Code', width=6, justify='right')
    table.add_column('Artifact', style='path', ratio=1, overflow='fold')
    table.add_column('Command', style='value', ratio=2, overflow='fold')
    table.add_column('Error', style='value', ratio=1, overflow='fold')
    for item in diagnostics:
        artifact_value = item.artifact_path or item.artifact_filename or ''
        availability_value = Text(item.availability)
        availability_style = 'status.available' if item.availability == 'available' else 'status.unavailable'
        availability_value.stylize(availability_style)
        table.add_row(
            item.source_key,
            availability_value,
            '' if item.return_code is None else str(item.return_code),
            artifact_value,
            item.source_command,
            item.stderr,
        )
    console.print(_center(table))

