from __future__ import annotations

import re

from ..models import AuditReport, MetricRecord

_POWER_PLAN_NAME_PATTERN = re.compile(r'\(([^)]+)\)')


def _first_metric(metrics: list[MetricRecord], *metric_ids: str) -> MetricRecord | None:
    for metric_id in metric_ids:
        for metric in metrics:
            if metric.metric_id == metric_id and metric.display_value:
                return metric
    return None



def _line(label: str, value: str) -> str:
    return f'{label.ljust(15)} : {value}'



def _clean_power_plan(value: str) -> str:
    match = _POWER_PLAN_NAME_PATTERN.search(value)
    if match:
        return match.group(1).strip()
    return value.strip()



def render_summary_text(report: AuditReport) -> str:
    lines = ['PC Gaming Audit Summary']

    os_metrics = {
        metric.metric_id: metric.display_value
        for metric in report.system_metrics
        if metric.display_value
    }
    os_parts = [
        os_metrics.get('windows_edition', ''),
        f"Version {os_metrics['windows_version']}" if os_metrics.get('windows_version') else '',
        f"Build {os_metrics['windows_build_number']}" if os_metrics.get('windows_build_number') else '',
    ]
    os_value = ' | '.join(part for part in os_parts if part)
    if os_value:
        lines.append(_line('OS', os_value))

    cpu_metric = _first_metric(report.system_metrics, 'cpu_name')
    if cpu_metric:
        lines.append(_line('CPU', cpu_metric.display_value))

    gpu_metric = _first_metric(report.graphics_metrics, 'nvidia_gpu_name', 'video_controller_1_name')
    driver_metric = _first_metric(report.graphics_metrics, 'nvidia_driver_version', 'video_controller_1_driver_version')
    if gpu_metric:
        gpu_value = gpu_metric.display_value
        if driver_metric:
            gpu_value = f'{gpu_value} | Driver {driver_metric.display_value}'
        lines.append(_line('GPU', gpu_value))

    display_parts = [
        metric.display_value
        for metric in (
            _first_metric(report.display_metrics, 'display_1_monitor_model', 'display_1_monitor_name'),
            _first_metric(report.display_metrics, 'display_1_active_resolution'),
            _first_metric(report.display_metrics, 'display_1_active_refresh_rate'),
        )
        if metric is not None and metric.display_value
    ]
    if display_parts:
        lines.append(_line('Primary Display', ' | '.join(display_parts)))

    ram_metric = _first_metric(report.system_metrics, 'total_physical_memory_bytes')
    if ram_metric:
        lines.append(_line('RAM', ram_metric.display_value))

    power_metric = _first_metric(report.settings_metrics, 'active_power_scheme')
    if power_metric:
        lines.append(_line('Power Plan', _clean_power_plan(power_metric.display_value)))

    game_mode_metric = _first_metric(report.settings_metrics, 'auto_game_mode_enabled')
    if game_mode_metric:
        lines.append(_line('Game Mode', game_mode_metric.display_value))

    game_dvr_metric = _first_metric(report.settings_metrics, 'game_dvr_enabled')
    if game_dvr_metric:
        lines.append(_line('Game DVR', game_dvr_metric.display_value))

    telemetry_sources = sorted({metric.source_name for metric in report.telemetry_metrics if metric.source_name})
    if telemetry_sources:
        lines.append(_line('Telemetry', ', '.join(telemetry_sources)))

    gpu_temp_metric = _first_metric(report.telemetry_metrics, 'nvidia_temperature_gpu')
    if gpu_temp_metric:
        lines.append(_line('GPU Temp', gpu_temp_metric.display_value))

    gpu_usage_metric = _first_metric(report.telemetry_metrics, 'nvidia_utilization_gpu')
    if gpu_usage_metric:
        lines.append(_line('GPU Usage', gpu_usage_metric.display_value))

    limited_sources: list[str] = []
    unavailable_labels = {metric.label for metric in report.unavailable_metrics}
    if 'nvidia-smi' not in telemetry_sources or 'nvidia-smi' in unavailable_labels:
        limited_sources.append('nvidia-smi')
    if 'MSI Afterburner Shared Memory' not in telemetry_sources or 'MSI Afterburner Shared Memory' in unavailable_labels:
        limited_sources.append('Afterburner')

    if limited_sources:
        lines.append(_line('Notes', f"Optional telemetry may be limited ({', '.join(limited_sources)})."))

    return '\n'.join(lines) + '\n'
