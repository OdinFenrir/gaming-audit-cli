from __future__ import annotations

import argparse

from .actions import ActionRequest, SECTION_ACTION_KEYS


class InvalidCliUsage(ValueError):
    pass


class ArgumentParserWithCode(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise InvalidCliUsage(message)



def build_parser() -> argparse.ArgumentParser:
    parser = ArgumentParserWithCode(prog='gaming-audit', add_help=True)
    subparsers = parser.add_subparsers(dest='command')

    subparsers.add_parser('menu')

    audit_parser = subparsers.add_parser('audit')
    audit_subparsers = audit_parser.add_subparsers(dest='audit_command', required=True)
    audit_subparsers.add_parser('full')
    audit_subparsers.add_parser('summary')
    section_parser = audit_subparsers.add_parser('section')
    section_parser.add_argument('section', choices=sorted(SECTION_ACTION_KEYS.keys()))

    reports_parser = subparsers.add_parser('reports')
    reports_subparsers = reports_parser.add_subparsers(dest='reports_command', required=True)
    reports_list_parser = reports_subparsers.add_parser('list')
    reports_list_parser.add_argument('--limit', type=int, default=10)
    reports_latest_parser = reports_subparsers.add_parser('latest')
    reports_latest_parser.add_argument('--format', dest='format_name', choices=('txt', 'json'), default='txt')
    reports_show_parser = reports_subparsers.add_parser('show')
    reports_show_parser.add_argument('run_stamp')
    reports_show_parser.add_argument('--format', dest='format_name', choices=('txt', 'json'), default='txt')

    evidence_parser = subparsers.add_parser('evidence')
    evidence_subparsers = evidence_parser.add_subparsers(dest='evidence_command', required=True)
    evidence_list_parser = evidence_subparsers.add_parser('list')
    evidence_group = evidence_list_parser.add_mutually_exclusive_group()
    evidence_group.add_argument('--run-stamp', dest='run_stamp')
    evidence_group.add_argument('--latest', action='store_true')

    subparsers.add_parser('diagnostics')
    return parser



def parse_args(argv: list[str]) -> ActionRequest:
    parser = build_parser()
    namespace = parser.parse_args(argv)

    if not namespace.command:
        return ActionRequest(action_key='menu', interactive=True)
    if namespace.command == 'menu':
        return ActionRequest(action_key='menu', interactive=True)
    if namespace.command == 'audit':
        if namespace.audit_command == 'full':
            return ActionRequest(action_key='full_audit')
        if namespace.audit_command == 'summary':
            return ActionRequest(action_key='summary')
        return ActionRequest(action_key=SECTION_ACTION_KEYS[namespace.section])
    if namespace.command == 'reports':
        if namespace.reports_command == 'list':
            return ActionRequest(action_key='reports_list', limit=namespace.limit)
        if namespace.reports_command == 'latest':
            return ActionRequest(action_key='reports_latest', format_name=namespace.format_name)
        return ActionRequest(action_key='reports_show', run_stamp=namespace.run_stamp, format_name=namespace.format_name)
    if namespace.command == 'evidence':
        return ActionRequest(
            action_key='evidence_list',
            run_stamp='' if namespace.latest else (namespace.run_stamp or ''),
        )
    if namespace.command == 'diagnostics':
        return ActionRequest(action_key='diagnostics')
    raise InvalidCliUsage('Unsupported command.')
