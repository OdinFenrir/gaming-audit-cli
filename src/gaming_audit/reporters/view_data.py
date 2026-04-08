from __future__ import annotations

from typing import Iterable

from ..models import AuditReport, MetricRecord, ProcessRecord, ServiceRecord, SoftwareRecord
from ..utils.formatting import format_display_value, format_yes_no


NVIDIA_TELEMETRY_ORDER = [
    'nvidia_temperature_gpu',
    'nvidia_utilization_gpu',
    'nvidia_utilization_memory',
    'nvidia_power_draw',
    'nvidia_clocks_current_graphics',
    'nvidia_fan_speed',
]

AFTERBURNER_GPU_LABELS = [
    'GPU temperature',
    'GPU usage',
    'FB usage',
    'VID usage',
    'BUS usage',
    'Memory usage',
    'Core clock',
    'Memory clock',
    'Power',
    'Fan speed',
    'Fan tachometer',
]

AFTERBURNER_CPU_LABELS = [
    'CPU temperature',
    'CPU usage',
    'CPU clock',
    'CPU power',
    'RAM usage',
    'Commit charge',
]

AFTERBURNER_PER_CORE_GROUPS = [
    ('temperature', 'CPU Temperature Range', 'C'),
    ('usage', 'CPU Usage Range', '%'),
    ('clock', 'CPU Clock Range', 'MHz'),
    ('power', 'CPU Power Range', 'W'),
]


def _metric_rows(metrics: list[MetricRecord]) -> list[tuple[str, str]]:
    return [(metric.label, metric.display_value) for metric in metrics]


def _software_rows(items: list[SoftwareRecord]) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for item in items:
        details = [f'Installed={format_yes_no(item.installed)}']
        if item.version:
            details.append(f'Version={item.version}')
        if item.install_path:
            details.append(f'Path={item.install_path}')
        if item.source_name:
            details.append(f'Source={item.source_name}')
        rows.append((item.name, ' | '.join(details)))
    return rows


def _process_rows(items: list[ProcessRecord]) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for item in items:
        details = [f'Running={format_yes_no(item.running)}']
        if item.pid is not None:
            details.append(f'PID={item.pid}')
        if item.path:
            details.append(f'Path={item.path}')
        rows.append((item.name, ' | '.join(details)))
    return rows


def _service_rows(items: list[ServiceRecord]) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for item in items:
        details = [f'Status={item.status}']
        if item.start_type:
            details.append(f'StartType={item.start_type}')
        rows.append((item.name, ' | '.join(details)))
    return rows


def _first_metric_by_id(metrics: Iterable[MetricRecord], metric_id: str) -> MetricRecord | None:
    for metric in metrics:
        if metric.metric_id == metric_id:
            return metric
    return None


def _overview_rows(report: AuditReport) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for label, value in (('Generated At', str(report.metadata.get('generated_at', ''))),):
        if value:
            rows.append((label, value))

    cpu_metric = _first_metric_by_id(report.system_metrics, 'cpu_name')
    gpu_metric = _first_metric_by_id(report.graphics_metrics, 'nvidia_gpu_name') or _first_metric_by_id(report.graphics_metrics, 'video_controller_1_name')
    monitor_metric = _first_metric_by_id(report.display_metrics, 'display_1_monitor_model')
    resolution_metric = _first_metric_by_id(report.display_metrics, 'display_1_active_resolution')
    refresh_metric = _first_metric_by_id(report.display_metrics, 'display_1_active_refresh_rate')

    if cpu_metric:
        rows.append(('CPU', cpu_metric.display_value))
    if gpu_metric:
        rows.append(('GPU', gpu_metric.display_value))
    if monitor_metric or resolution_metric or refresh_metric:
        display_parts = [
            metric.display_value
            for metric in (monitor_metric, resolution_metric, refresh_metric)
            if metric and metric.display_value
        ]
        if display_parts:
            rows.append(('Primary Display', ' | '.join(display_parts)))

    telemetry_sources = sorted({metric.source_name for metric in report.telemetry_metrics if metric.source_name})
    if telemetry_sources:
        rows.append(('Telemetry Sources', ', '.join(telemetry_sources)))

    for label, key in (
        ('Text Report', 'text_report_relative'),
        ('JSON Report', 'json_report_relative'),
        ('Latest Snapshot', 'latest_snapshot_relative'),
        ('Evidence Folder', 'evidence_directory_relative'),
    ):
        value = str(report.metadata.get(key, ''))
        if value:
            rows.append((label, value))
    return rows


def _range_summary(metrics: list[MetricRecord], unit: str) -> str:
    if not metrics:
        return ''
    numeric_values = [float(metric.raw_value) for metric in metrics if isinstance(metric.raw_value, (int, float))]
    if not numeric_values:
        return ''
    minimum = min(numeric_values)
    maximum = max(numeric_values)
    count = len(numeric_values)
    return f'{count} samples | Min={format_display_value(minimum, unit)} | Max={format_display_value(maximum, unit)}'


def _telemetry_rows(metrics: list[MetricRecord], json_report_path: str) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    shown_metric_ids: set[str] = set()

    nvidia_metrics = [metric for metric in metrics if metric.source_name == 'nvidia-smi']
    if nvidia_metrics:
        rows.append(('GPU Snapshot [nvidia-smi]', ''))
        for metric_id in NVIDIA_TELEMETRY_ORDER:
            metric = _first_metric_by_id(nvidia_metrics, metric_id)
            if not metric:
                continue
            rows.append((f'  {metric.label}', metric.display_value))
            shown_metric_ids.add(metric.metric_id)

    afterburner_metrics = [metric for metric in metrics if metric.source_name == 'MSI Afterburner Shared Memory']
    if afterburner_metrics:
        metric_by_label = {metric.label.lower(): metric for metric in afterburner_metrics}

        rows.append(('GPU Snapshot [MSI Afterburner]', ''))
        for label in AFTERBURNER_GPU_LABELS:
            metric = metric_by_label.get(label.lower())
            if not metric:
                continue
            rows.append((f'  {metric.label}', metric.display_value))
            shown_metric_ids.add(metric.metric_id)

        rows.append(('CPU Snapshot [MSI Afterburner]', ''))
        for label in AFTERBURNER_CPU_LABELS:
            metric = metric_by_label.get(label.lower())
            if not metric:
                continue
            rows.append((f'  {metric.label}', metric.display_value))
            shown_metric_ids.add(metric.metric_id)

        rows.append(('CPU Per-Core Summary [MSI Afterburner]', ''))
        for suffix, summary_label, unit in AFTERBURNER_PER_CORE_GROUPS:
            matching_metrics = [
                metric
                for metric in afterburner_metrics
                if metric.label.startswith('CPU')
                and metric.label[3:metric.label.find(' ')].isdigit()
                and metric.label.lower().endswith(suffix)
            ]
            if not matching_metrics:
                continue
            rows.append((f'  {summary_label}', _range_summary(matching_metrics, unit)))
            shown_metric_ids.update(metric.metric_id for metric in matching_metrics)

    remaining_metric_count = len({metric.metric_id for metric in metrics}) - len(shown_metric_ids)
    if remaining_metric_count > 0:
        label = 'Additional Raw Telemetry [JSON]'
        if json_report_path:
            rows.append((label, f'{remaining_metric_count} more metrics saved in {json_report_path}'))
        else:
            rows.append((label, f'{remaining_metric_count} more metrics available in the in-memory report.'))

    return rows


def build_section_rows(report: AuditReport) -> dict[str, list[tuple[str, str]]]:
    return {
        'Overview': _overview_rows(report),
        'System': _metric_rows(report.system_metrics),
        'Graphics': _metric_rows(report.graphics_metrics),
        'Displays': _metric_rows(report.display_metrics),
        'Storage': _metric_rows(report.storage_metrics),
        'Gaming Settings': _metric_rows(report.settings_metrics),
        'Performance Tools': _software_rows(report.software_inventory),
        'Processes': _process_rows(report.process_inventory),
        'Services': _service_rows(report.service_inventory),
        'Live Telemetry': _telemetry_rows(report.telemetry_metrics, str(report.metadata.get('json_report_relative', ''))),
        'Unavailable Metrics': _metric_rows(report.unavailable_metrics),
    }

