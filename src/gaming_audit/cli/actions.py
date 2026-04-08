from __future__ import annotations

from dataclasses import dataclass

from ..constants import (
    SCOPE_DISPLAYS,
    SCOPE_FULL,
    SCOPE_GRAPHICS,
    SCOPE_PROCESSES,
    SCOPE_PROCESSES_SERVICES,
    SCOPE_SERVICES,
    SCOPE_SETTINGS,
    SCOPE_STORAGE,
    SCOPE_SYSTEM,
    SCOPE_TELEMETRY,
    SCOPE_TOOLS,
)


@dataclass(frozen=True, slots=True)
class ActionDefinition:
    key: str
    menu_number: int | None
    menu_label: str
    description: str
    command_hint: str = ''
    scope: str | None = None
    sections: tuple[str, ...] = ()


@dataclass(slots=True)
class ActionRequest:
    action_key: str
    run_stamp: str = ''
    format_name: str = 'txt'
    limit: int | None = None
    interactive: bool = False


ACTION_DEFINITIONS = {
    'full_audit': ActionDefinition(
        'full_audit',
        1,
        'Full audit',
        'Save the full snapshot and evidence.',
        'audit full',
        SCOPE_FULL,
        ('Overview', 'System', 'Graphics', 'Displays', 'Storage', 'Gaming Settings', 'Performance Tools', 'Processes', 'Services', 'Live Telemetry', 'Unavailable Metrics'),
    ),
    'system': ActionDefinition(
        'system',
        2,
        'System',
        'Windows, CPU, memory, network, audio.',
        'audit section system',
        SCOPE_SYSTEM,
        ('Overview', 'System', 'Unavailable Metrics'),
    ),
    'graphics': ActionDefinition(
        'graphics',
        3,
        'Graphics',
        'GPU, driver, DirectX, WDDM, VRAM.',
        'audit section graphics',
        SCOPE_GRAPHICS,
        ('Overview', 'Graphics', 'Unavailable Metrics'),
    ),
    'displays': ActionDefinition(
        'displays',
        4,
        'Displays',
        'Screens, modes, HDR, color space.',
        'audit section displays',
        SCOPE_DISPLAYS,
        ('Overview', 'Displays', 'Unavailable Metrics'),
    ),
    'storage': ActionDefinition(
        'storage',
        5,
        'Storage',
        'Disks, health, volumes, free space.',
        'audit section storage',
        SCOPE_STORAGE,
        ('Overview', 'Storage', 'Unavailable Metrics'),
    ),
    'settings': ActionDefinition(
        'settings',
        6,
        'Gaming settings',
        'Power plan, Game DVR, Game Mode.',
        'audit section settings',
        SCOPE_SETTINGS,
        ('Overview', 'Gaming Settings', 'Unavailable Metrics'),
    ),
    'tools': ActionDefinition(
        'tools',
        7,
        'Performance tools',
        'Monitoring tools and runtimes.',
        'audit section tools',
        SCOPE_TOOLS,
        ('Overview', 'Performance Tools', 'Unavailable Metrics'),
    ),
    'processes_services': ActionDefinition(
        'processes_services',
        8,
        'Processes and services',
        'Helper processes and services.',
        'audit section proc-svc',
        SCOPE_PROCESSES_SERVICES,
        ('Overview', 'Processes', 'Services', 'Unavailable Metrics'),
    ),
    'telemetry': ActionDefinition(
        'telemetry',
        9,
        'Telemetry snapshot',
        'Current nvidia-smi and Afterburner.',
        'audit section telemetry',
        SCOPE_TELEMETRY,
        ('Overview', 'Live Telemetry', 'Unavailable Metrics'),
    ),
    'recent_reports': ActionDefinition(
        'recent_reports',
        10,
        'Recent reports',
        'Browse saved runs.',
        'reports list --limit 8',
    ),
    'evidence_browser': ActionDefinition(
        'evidence_browser',
        11,
        'Evidence browser',
        'Collector artifacts by run.',
        'evidence list --latest',
    ),
    'diagnostics': ActionDefinition(
        'diagnostics',
        12,
        'Diagnostics',
        'Commands, files, codes, errors.',
        'diagnostics',
    ),
    'exit': ActionDefinition(
        'exit',
        13,
        'Exit',
        'Close the menu.',
    ),
    'processes': ActionDefinition(
        'processes',
        None,
        'Processes',
        'Running helper processes and their paths.',
        'audit section processes',
        SCOPE_PROCESSES,
        ('Overview', 'Processes', 'Unavailable Metrics'),
    ),
    'services': ActionDefinition(
        'services',
        None,
        'Services',
        'Relevant Windows service state and start type.',
        'audit section services',
        SCOPE_SERVICES,
        ('Overview', 'Services', 'Unavailable Metrics'),
    ),
    'reports_list': ActionDefinition('reports_list', None, 'Reports list', 'Browse saved runs.', 'reports list'),
    'reports_latest': ActionDefinition('reports_latest', None, 'Latest report content', 'Open the latest saved report.', 'reports latest --format txt'),
    'reports_show': ActionDefinition('reports_show', None, 'Saved report content', 'Open a specific saved report.', 'reports show <run_stamp> --format txt'),
    'evidence_list': ActionDefinition('evidence_list', None, 'Evidence list', 'List raw evidence files for a run.', 'evidence list --latest'),
    'menu': ActionDefinition('menu', None, 'Menu', 'Open the interactive numbered menu.'),
}

MENU_ACTIONS = tuple(
    ACTION_DEFINITIONS[key]
    for key in (
        'full_audit',
        'system',
        'graphics',
        'displays',
        'storage',
        'settings',
        'tools',
        'processes_services',
        'telemetry',
        'recent_reports',
        'evidence_browser',
        'diagnostics',
        'exit',
    )
)

SECTION_ACTION_KEYS = {
    'system': 'system',
    'graphics': 'graphics',
    'displays': 'displays',
    'storage': 'storage',
    'settings': 'settings',
    'tools': 'tools',
    'processes': 'processes',
    'services': 'services',
    'telemetry': 'telemetry',
}


def resolve_menu_selection(selection: str) -> ActionDefinition:
    try:
        menu_number = int(selection)
    except ValueError as error:
        raise ValueError('Menu selection must be a number.') from error

    for action in MENU_ACTIONS:
        if action.menu_number == menu_number:
            return action
    raise ValueError(f'Unknown menu selection: {selection}')


def get_action(action_key: str) -> ActionDefinition:
    return ACTION_DEFINITIONS[action_key]
