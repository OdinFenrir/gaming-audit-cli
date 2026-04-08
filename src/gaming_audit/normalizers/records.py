from __future__ import annotations

import math
import re
from typing import Any

from ..constants import (
    AVAILABILITY_AVAILABLE,
    AVAILABILITY_UNAVAILABLE,
    SECTION_DISPLAYS,
    SECTION_GRAPHICS,
    SECTION_SETTINGS,
    SECTION_STORAGE,
    SECTION_SYSTEM,
    SECTION_TELEMETRY,
    SOFTWARE_APPX_PACKAGES,
    SOFTWARE_REGISTRY_PATTERNS,
    RELEVANT_PROCESS_NAMES,
)
from ..models import CollectedSource, MetricRecord, ProcessRecord, ServiceRecord, SoftwareRecord
from ..utils.formatting import format_display_value, format_gibibytes_from_bytes, format_mebibytes, format_yes_no, sanitize_text
from ..utils.parsing import ensure_list
from ..utils.time_utils import iso_timestamp

_CURRENT_MODE_PATTERN = re.compile(r"(?P<width>\d+)\s*x\s*(?P<height>\d+).+?\((?P<refresh>[\d.]+)Hz\)", re.IGNORECASE)


def _evidence(snapshot: CollectedSource, key: str | None = None):
    if key and key in snapshot.evidence:
        return snapshot.evidence[key]
    if snapshot.evidence:
        return next(iter(snapshot.evidence.values()))
    return None


def _metric(
    section: str,
    metric_id: str,
    label: str,
    raw_value: Any,
    display_value: str,
    snapshot: CollectedSource,
    evidence_key: str | None = None,
) -> MetricRecord:
    evidence = _evidence(snapshot, evidence_key)
    availability = AVAILABILITY_AVAILABLE
    if raw_value is None or (isinstance(raw_value, str) and not raw_value.strip()):
        availability = AVAILABILITY_UNAVAILABLE
    if evidence is not None and evidence.availability == AVAILABILITY_UNAVAILABLE:
        availability = AVAILABILITY_UNAVAILABLE
    return MetricRecord(
        metric_id=metric_id,
        section=section,
        label=label,
        raw_value=sanitize_text(raw_value),
        display_value=sanitize_text(display_value),
        unit="",
        availability=availability,
        source_name=evidence.source_name if evidence else "",
        source_command=sanitize_text(evidence.source_command) if evidence else "",
        captured_at=evidence.captured_at if evidence else iso_timestamp(),
    )


def _append_metric(
    metrics: list[MetricRecord],
    section: str,
    metric_id: str,
    label: str,
    raw_value: Any,
    snapshot: CollectedSource,
    evidence_key: str | None = None,
    display_value: str | None = None,
) -> None:
    if raw_value is None:
        return
    if isinstance(raw_value, str) and not raw_value.strip():
        return
    rendered = display_value if display_value is not None else format_display_value(raw_value)
    metrics.append(_metric(section, metric_id, label, raw_value, rendered, snapshot, evidence_key))


def _find_case_insensitive(mapping: dict[str, Any], key: str) -> Any:
    normalized = key.lower()
    for candidate_key, value in mapping.items():
        if candidate_key.lower() == normalized:
            return value
    return None


def _parse_current_mode(mode_text: str | None) -> tuple[int | None, int | None, float | None]:
    if not mode_text:
        return None, None, None
    match = _CURRENT_MODE_PATTERN.search(mode_text)
    if not match:
        return None, None, None
    return int(match.group("width")), int(match.group("height")), float(match.group("refresh"))


def normalize_system_metrics(wmi_snapshot: CollectedSource, network_snapshot: CollectedSource) -> list[MetricRecord]:
    metrics: list[MetricRecord] = []

    operating_system = wmi_snapshot.data.get("operating_system", {})
    computer_system = wmi_snapshot.data.get("computer_system", {})
    processor = wmi_snapshot.data.get("processor", {})
    available_memory = wmi_snapshot.data.get("available_memory", {})

    _append_metric(metrics, SECTION_SYSTEM, "windows_edition", "Windows Edition", operating_system.get("caption"), wmi_snapshot, "operating_system")
    _append_metric(metrics, SECTION_SYSTEM, "windows_version", "Windows Version", operating_system.get("version"), wmi_snapshot, "operating_system")
    _append_metric(metrics, SECTION_SYSTEM, "windows_build_number", "Windows Build Number", operating_system.get("build_number"), wmi_snapshot, "operating_system")
    _append_metric(metrics, SECTION_SYSTEM, "windows_architecture", "Windows Architecture", operating_system.get("architecture"), wmi_snapshot, "operating_system")
    _append_metric(metrics, SECTION_SYSTEM, "last_boot_up_time", "Last Boot Time", operating_system.get("last_boot_up_time"), wmi_snapshot, "operating_system")

    _append_metric(metrics, SECTION_SYSTEM, "system_manufacturer", "System Manufacturer", computer_system.get("manufacturer"), wmi_snapshot, "computer_system")
    _append_metric(metrics, SECTION_SYSTEM, "system_model", "System Model", computer_system.get("model"), wmi_snapshot, "computer_system")
    total_memory = computer_system.get("total_physical_memory")
    _append_metric(
        metrics,
        SECTION_SYSTEM,
        "total_physical_memory_bytes",
        "Total Physical Memory",
        total_memory,
        wmi_snapshot,
        "computer_system",
        format_gibibytes_from_bytes(total_memory),
    )

    _append_metric(metrics, SECTION_SYSTEM, "cpu_name", "CPU Name", processor.get("Name"), wmi_snapshot, "processor")
    _append_metric(metrics, SECTION_SYSTEM, "cpu_manufacturer", "CPU Manufacturer", processor.get("Manufacturer"), wmi_snapshot, "processor")
    _append_metric(metrics, SECTION_SYSTEM, "cpu_physical_cores", "CPU Physical Core Count", processor.get("NumberOfCores"), wmi_snapshot, "processor")
    _append_metric(metrics, SECTION_SYSTEM, "cpu_logical_processors", "CPU Logical Processor Count", processor.get("NumberOfLogicalProcessors"), wmi_snapshot, "processor")
    _append_metric(metrics, SECTION_SYSTEM, "cpu_max_clock_mhz", "CPU Max Clock", processor.get("MaxClockSpeed"), wmi_snapshot, "processor", format_display_value(processor.get("MaxClockSpeed"), "MHz"))
    _append_metric(metrics, SECTION_SYSTEM, "cpu_current_clock_mhz", "CPU Current Clock", processor.get("CurrentClockSpeed"), wmi_snapshot, "processor", format_display_value(processor.get("CurrentClockSpeed"), "MHz"))
    _append_metric(metrics, SECTION_SYSTEM, "cpu_load_percent", "CPU Load", processor.get("LoadPercentage"), wmi_snapshot, "processor", format_display_value(processor.get("LoadPercentage"), "%"))
    _append_metric(metrics, SECTION_SYSTEM, "cpu_socket_designation", "CPU Socket", processor.get("SocketDesignation"), wmi_snapshot, "processor")

    available_memory_mb = available_memory.get("available_memory_mb")
    _append_metric(metrics, SECTION_SYSTEM, "available_memory_mb", "Available Memory", available_memory_mb, wmi_snapshot, "available_memory", format_mebibytes(available_memory_mb))
    for index, pagefile in enumerate(ensure_list(wmi_snapshot.data.get("pagefile")), start=1):
        prefix = f"pagefile_{index}"
        pagefile_name = pagefile.get("Name")
        _append_metric(metrics, SECTION_SYSTEM, f"{prefix}_name", f"Pagefile {index} Path", pagefile_name, wmi_snapshot, "pagefile")
        allocated_size = pagefile.get("AllocatedBaseSize")
        current_usage = pagefile.get("CurrentUsage")
        peak_usage = pagefile.get("PeakUsage")
        _append_metric(metrics, SECTION_SYSTEM, f"{prefix}_allocated_mb", f"Pagefile {index} Allocated Size", allocated_size, wmi_snapshot, "pagefile", format_mebibytes(allocated_size))
        _append_metric(metrics, SECTION_SYSTEM, f"{prefix}_current_usage_mb", f"Pagefile {index} Current Usage", current_usage, wmi_snapshot, "pagefile", format_mebibytes(current_usage))
        _append_metric(metrics, SECTION_SYSTEM, f"{prefix}_peak_usage_mb", f"Pagefile {index} Peak Usage", peak_usage, wmi_snapshot, "pagefile", format_mebibytes(peak_usage))

    for index, adapter in enumerate(ensure_list(network_snapshot.data.get("network_adapters")), start=1):
        prefix = f"network_adapter_{index}"
        _append_metric(metrics, SECTION_SYSTEM, f"{prefix}_name", f"Network Adapter {index} Name", adapter.get("Name"), network_snapshot, "network_adapters")
        _append_metric(metrics, SECTION_SYSTEM, f"{prefix}_description", f"Network Adapter {index} Description", adapter.get("InterfaceDescription"), network_snapshot, "network_adapters")
        _append_metric(metrics, SECTION_SYSTEM, f"{prefix}_link_speed", f"Network Adapter {index} Link Speed", adapter.get("LinkSpeed"), network_snapshot, "network_adapters")
        _append_metric(metrics, SECTION_SYSTEM, f"{prefix}_status", f"Network Adapter {index} Status", adapter.get("Status"), network_snapshot, "network_adapters")

    for index, sample in enumerate(ensure_list(network_snapshot.data.get("ping_sample")), start=1):
        prefix = f"ping_sample_{index}"
        _append_metric(metrics, SECTION_SYSTEM, f"{prefix}_address", f"Ping Sample {index} Address", sample.get("Address"), network_snapshot, "ping_sample")
        latency = sample.get("Latency")
        _append_metric(metrics, SECTION_SYSTEM, f"{prefix}_latency_ms", f"Ping Sample {index} Latency", latency, network_snapshot, "ping_sample", format_display_value(latency, "ms"))
        _append_metric(metrics, SECTION_SYSTEM, f"{prefix}_status", f"Ping Sample {index} Status", sample.get("Status"), network_snapshot, "ping_sample")

    for index, audio_device in enumerate(ensure_list(wmi_snapshot.data.get("audio_devices")), start=1):
        prefix = f"audio_device_{index}"
        _append_metric(metrics, SECTION_SYSTEM, f"{prefix}_name", f"Audio Device {index} Name", audio_device.get("Name"), wmi_snapshot, "audio_devices")
        _append_metric(metrics, SECTION_SYSTEM, f"{prefix}_status", f"Audio Device {index} Status", audio_device.get("Status"), wmi_snapshot, "audio_devices")
        _append_metric(metrics, SECTION_SYSTEM, f"{prefix}_manufacturer", f"Audio Device {index} Manufacturer", audio_device.get("Manufacturer"), wmi_snapshot, "audio_devices")

    return metrics


def normalize_graphics_metrics(
    wmi_snapshot: CollectedSource,
    dxdiag_snapshot: CollectedSource,
    nvidia_snapshot: CollectedSource,
) -> list[MetricRecord]:
    metrics: list[MetricRecord] = []

    dxdiag_system = dxdiag_snapshot.data.get("dxdiag", {}).get("system", {})
    _append_metric(metrics, SECTION_GRAPHICS, "directx_version", "DirectX Version", dxdiag_system.get("directx_version"), dxdiag_snapshot, "dxdiag")
    _append_metric(metrics, SECTION_GRAPHICS, "dxdiag_version", "DxDiag Version", dxdiag_system.get("dxdiag_version"), dxdiag_snapshot, "dxdiag")

    for index, controller in enumerate(ensure_list(wmi_snapshot.data.get("video_controllers")), start=1):
        prefix = f"video_controller_{index}"
        _append_metric(metrics, SECTION_GRAPHICS, f"{prefix}_name", f"Video Controller {index} Name", controller.get("Name"), wmi_snapshot, "video_controllers")
        _append_metric(metrics, SECTION_GRAPHICS, f"{prefix}_status", f"Video Controller {index} Status", controller.get("Status"), wmi_snapshot, "video_controllers")
        _append_metric(metrics, SECTION_GRAPHICS, f"{prefix}_driver_version", f"Video Controller {index} Driver Version", controller.get("DriverVersion"), wmi_snapshot, "video_controllers")
        _append_metric(metrics, SECTION_GRAPHICS, f"{prefix}_driver_date", f"Video Controller {index} Driver Date", controller.get("DriverDate"), wmi_snapshot, "video_controllers")
        _append_metric(metrics, SECTION_GRAPHICS, f"{prefix}_video_processor", f"Video Controller {index} Video Processor", controller.get("VideoProcessor"), wmi_snapshot, "video_controllers")
        _append_metric(metrics, SECTION_GRAPHICS, f"{prefix}_adapter_compatibility", f"Video Controller {index} Adapter Compatibility", controller.get("AdapterCompatibility"), wmi_snapshot, "video_controllers")
        _append_metric(metrics, SECTION_GRAPHICS, f"{prefix}_video_mode", f"Video Controller {index} Video Mode", controller.get("VideoModeDescription"), wmi_snapshot, "video_controllers")
        _append_metric(metrics, SECTION_GRAPHICS, f"{prefix}_current_horizontal_resolution", f"Video Controller {index} Current Horizontal Resolution", controller.get("CurrentHorizontalResolution"), wmi_snapshot, "video_controllers", format_display_value(controller.get("CurrentHorizontalResolution"), "px"))
        _append_metric(metrics, SECTION_GRAPHICS, f"{prefix}_current_vertical_resolution", f"Video Controller {index} Current Vertical Resolution", controller.get("CurrentVerticalResolution"), wmi_snapshot, "video_controllers", format_display_value(controller.get("CurrentVerticalResolution"), "px"))
        _append_metric(metrics, SECTION_GRAPHICS, f"{prefix}_current_refresh_rate", f"Video Controller {index} Current Refresh Rate", controller.get("CurrentRefreshRate"), wmi_snapshot, "video_controllers", format_display_value(controller.get("CurrentRefreshRate"), "Hz"))

    for index, display in enumerate(ensure_list(dxdiag_snapshot.data.get("dxdiag", {}).get("displays")), start=1):
        prefix = f"graphics_adapter_{index}"
        _append_metric(metrics, SECTION_GRAPHICS, f"{prefix}_card_name", f"Graphics Adapter {index} Card Name", display.get("card_name"), dxdiag_snapshot, "dxdiag")
        _append_metric(metrics, SECTION_GRAPHICS, f"{prefix}_manufacturer", f"Graphics Adapter {index} Manufacturer", display.get("manufacturer"), dxdiag_snapshot, "dxdiag")
        _append_metric(metrics, SECTION_GRAPHICS, f"{prefix}_chip_type", f"Graphics Adapter {index} Chip Type", display.get("chip_type"), dxdiag_snapshot, "dxdiag")
        _append_metric(metrics, SECTION_GRAPHICS, f"{prefix}_display_memory", f"Graphics Adapter {index} Display Memory", display.get("display_memory"), dxdiag_snapshot, "dxdiag")
        _append_metric(metrics, SECTION_GRAPHICS, f"{prefix}_dedicated_memory", f"Graphics Adapter {index} Dedicated Memory", display.get("dedicated_memory"), dxdiag_snapshot, "dxdiag")
        _append_metric(metrics, SECTION_GRAPHICS, f"{prefix}_shared_memory", f"Graphics Adapter {index} Shared Memory", display.get("shared_memory"), dxdiag_snapshot, "dxdiag")
        _append_metric(metrics, SECTION_GRAPHICS, f"{prefix}_driver_version", f"Graphics Adapter {index} Driver Version", display.get("driver_version"), dxdiag_snapshot, "dxdiag")
        _append_metric(metrics, SECTION_GRAPHICS, f"{prefix}_driver_model", f"Graphics Adapter {index} Driver Model", display.get("driver_model"), dxdiag_snapshot, "dxdiag")

    nvidia_data = nvidia_snapshot.data.get("nvidia_smi", {})
    _append_metric(metrics, SECTION_GRAPHICS, "nvidia_gpu_name", "NVIDIA GPU Name", nvidia_data.get("name"), nvidia_snapshot, "nvidia_smi")
    _append_metric(metrics, SECTION_GRAPHICS, "nvidia_driver_version", "GPU Driver Version", nvidia_data.get("driver_version"), nvidia_snapshot, "nvidia_smi")

    return metrics


def normalize_display_metrics(wmi_snapshot: CollectedSource, dxdiag_snapshot: CollectedSource) -> list[MetricRecord]:
    metrics: list[MetricRecord] = []

    for index, screen in enumerate(ensure_list(wmi_snapshot.data.get("screens")), start=1):
        prefix = f"screen_{index}"
        _append_metric(metrics, SECTION_DISPLAYS, f"{prefix}_device_name", f"Screen {index} Device Name", screen.get("device_name"), wmi_snapshot, "screens")
        _append_metric(metrics, SECTION_DISPLAYS, f"{prefix}_primary", f"Screen {index} Primary Display", screen.get("primary"), wmi_snapshot, "screens", format_yes_no(screen.get("primary")))
        _append_metric(metrics, SECTION_DISPLAYS, f"{prefix}_width", f"Screen {index} Width", screen.get("width"), wmi_snapshot, "screens", format_display_value(screen.get("width"), "px"))
        _append_metric(metrics, SECTION_DISPLAYS, f"{prefix}_height", f"Screen {index} Height", screen.get("height"), wmi_snapshot, "screens", format_display_value(screen.get("height"), "px"))
        position = f"{screen.get('x')}, {screen.get('y')}" if screen.get("x") is not None and screen.get("y") is not None else None
        _append_metric(metrics, SECTION_DISPLAYS, f"{prefix}_position", f"Screen {index} Position", position, wmi_snapshot, "screens")

    for index, display in enumerate(ensure_list(dxdiag_snapshot.data.get("dxdiag", {}).get("displays")), start=1):
        prefix = f"display_{index}"
        _append_metric(metrics, SECTION_DISPLAYS, f"{prefix}_monitor_name", f"Display {index} Monitor Name", display.get("monitor_name"), dxdiag_snapshot, "dxdiag")
        _append_metric(metrics, SECTION_DISPLAYS, f"{prefix}_monitor_model", f"Display {index} Monitor Model", display.get("monitor_model"), dxdiag_snapshot, "dxdiag")
        _append_metric(metrics, SECTION_DISPLAYS, f"{prefix}_current_mode", f"Display {index} Current Mode", display.get("current_mode"), dxdiag_snapshot, "dxdiag")
        _append_metric(metrics, SECTION_DISPLAYS, f"{prefix}_hdr_support", f"Display {index} HDR Support", display.get("hdr_support"), dxdiag_snapshot, "dxdiag")
        _append_metric(metrics, SECTION_DISPLAYS, f"{prefix}_display_color_space", f"Display {index} Color Space", display.get("display_color_space"), dxdiag_snapshot, "dxdiag")
        _append_metric(metrics, SECTION_DISPLAYS, f"{prefix}_output_type", f"Display {index} Output Type", display.get("output_type"), dxdiag_snapshot, "dxdiag")

        width, height, refresh = _parse_current_mode(display.get("current_mode"))
        _append_metric(metrics, SECTION_DISPLAYS, f"{prefix}_active_resolution", f"Display {index} Active Resolution", f"{width} x {height}" if width and height else None, dxdiag_snapshot, "dxdiag")
        _append_metric(metrics, SECTION_DISPLAYS, f"{prefix}_active_refresh_rate", f"Display {index} Active Refresh Rate", refresh, dxdiag_snapshot, "dxdiag", format_display_value(refresh, "Hz"))

    return metrics


def normalize_storage_metrics(storage_snapshot: CollectedSource) -> list[MetricRecord]:
    metrics: list[MetricRecord] = []

    for index, disk in enumerate(ensure_list(storage_snapshot.data.get("physical_disks")), start=1):
        prefix = f"physical_disk_{index}"
        _append_metric(metrics, SECTION_STORAGE, f"{prefix}_friendly_name", f"Physical Disk {index} Friendly Name", disk.get("FriendlyName"), storage_snapshot, "physical_disks")
        _append_metric(metrics, SECTION_STORAGE, f"{prefix}_model", f"Physical Disk {index} Model", disk.get("Model"), storage_snapshot, "physical_disks")
        _append_metric(metrics, SECTION_STORAGE, f"{prefix}_media_type", f"Physical Disk {index} Media Type", disk.get("MediaType"), storage_snapshot, "physical_disks")
        _append_metric(metrics, SECTION_STORAGE, f"{prefix}_health_status", f"Physical Disk {index} Health Status", disk.get("HealthStatus"), storage_snapshot, "physical_disks")
        size_bytes = disk.get("Size")
        _append_metric(metrics, SECTION_STORAGE, f"{prefix}_size", f"Physical Disk {index} Size", size_bytes, storage_snapshot, "physical_disks", format_gibibytes_from_bytes(size_bytes))
        _append_metric(metrics, SECTION_STORAGE, f"{prefix}_bus_type", f"Physical Disk {index} Bus Type", disk.get("BusType"), storage_snapshot, "physical_disks")
        _append_metric(metrics, SECTION_STORAGE, f"{prefix}_firmware_version", f"Physical Disk {index} Firmware Version", disk.get("FirmwareVersion"), storage_snapshot, "physical_disks")

    for volume in ensure_list(storage_snapshot.data.get("volumes")):
        drive_letter = volume.get("DriveLetter")
        prefix = f"volume_{str(drive_letter).lower()}"
        _append_metric(metrics, SECTION_STORAGE, f"{prefix}_label", f"Volume {drive_letter} Label", volume.get("FileSystemLabel"), storage_snapshot, "volumes")
        _append_metric(metrics, SECTION_STORAGE, f"{prefix}_filesystem", f"Volume {drive_letter} File System", volume.get("FileSystem"), storage_snapshot, "volumes")
        size_bytes = volume.get("Size")
        free_bytes = volume.get("SizeRemaining")
        _append_metric(metrics, SECTION_STORAGE, f"{prefix}_total_size", f"Volume {drive_letter} Total Size", size_bytes, storage_snapshot, "volumes", format_gibibytes_from_bytes(size_bytes))
        _append_metric(metrics, SECTION_STORAGE, f"{prefix}_free_space", f"Volume {drive_letter} Free Space", free_bytes, storage_snapshot, "volumes", format_gibibytes_from_bytes(free_bytes))
        _append_metric(metrics, SECTION_STORAGE, f"{prefix}_health_status", f"Volume {drive_letter} Health Status", volume.get("HealthStatus"), storage_snapshot, "volumes")
        _append_metric(metrics, SECTION_STORAGE, f"{prefix}_drive_type", f"Volume {drive_letter} Drive Type", volume.get("DriveType"), storage_snapshot, "volumes")

    return metrics


def normalize_settings_metrics(registry_snapshot: CollectedSource, powercfg_snapshot: CollectedSource) -> list[MetricRecord]:
    metrics: list[MetricRecord] = []

    power_scheme = sanitize_text(powercfg_snapshot.data.get("active_power_scheme"))
    _append_metric(metrics, SECTION_SETTINGS, "active_power_scheme", "Active Power Plan", power_scheme, powercfg_snapshot, "active_power_scheme")

    game_config_store = registry_snapshot.data.get("game_config_store", {})
    _append_metric(metrics, SECTION_SETTINGS, "game_dvr_enabled", "Game DVR Enabled", game_config_store.get("game_dvr_enabled"), registry_snapshot, "game_config_store", format_yes_no(bool(game_config_store.get("game_dvr_enabled"))) if game_config_store.get("game_dvr_enabled") is not None else None)
    _append_metric(metrics, SECTION_SETTINGS, "game_dvr_fse_behavior_mode", "Game DVR FSE Behavior Mode", game_config_store.get("game_dvr_fse_behavior_mode"), registry_snapshot, "game_config_store")
    _append_metric(metrics, SECTION_SETTINGS, "game_dvr_honor_user_fse_behavior_mode", "Game DVR Honor User FSE Behavior Mode", game_config_store.get("game_dvr_honor_user_fse_behavior_mode"), registry_snapshot, "game_config_store")

    game_bar = registry_snapshot.data.get("game_bar", {})
    _append_metric(metrics, SECTION_SETTINGS, "auto_game_mode_enabled", "Auto Game Mode Enabled", game_bar.get("auto_game_mode_enabled"), registry_snapshot, "game_bar", format_yes_no(bool(game_bar.get("auto_game_mode_enabled"))) if game_bar.get("auto_game_mode_enabled") is not None else None)
    _append_metric(metrics, SECTION_SETTINGS, "show_startup_panel", "Show Startup Panel", game_bar.get("show_startup_panel"), registry_snapshot, "game_bar", format_yes_no(bool(game_bar.get("show_startup_panel"))) if game_bar.get("show_startup_panel") is not None else None)
    _append_metric(metrics, SECTION_SETTINGS, "use_nexus_for_game_bar_enabled", "Use Nexus For Game Bar Enabled", game_bar.get("use_nexus_for_game_bar_enabled"), registry_snapshot, "game_bar", format_yes_no(bool(game_bar.get("use_nexus_for_game_bar_enabled"))) if game_bar.get("use_nexus_for_game_bar_enabled") is not None else None)

    return metrics


def _sanitize_unit(unit: str | None) -> str:
    if not unit:
        return ""
    cleaned = str(unit).replace("°", "").replace("�", "").strip()
    if cleaned.lower() == "c":
        return "C"
    return cleaned


def _is_real_afterburner_value(value: Any) -> bool:
    if value is None:
        return False
    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        return False
    if not math.isfinite(numeric_value):
        return False
    if abs(numeric_value) >= 3.0e38:
        return False
    return True


def normalize_telemetry_metrics(nvidia_snapshot: CollectedSource, afterburner_snapshot: CollectedSource) -> list[MetricRecord]:
    metrics: list[MetricRecord] = []

    nvidia_data = nvidia_snapshot.data.get("nvidia_smi", {})
    nvidia_labels = {
        "temperature.gpu": "GPU Temperature",
        "utilization.gpu": "GPU Utilization",
        "utilization.memory": "GPU Memory Utilization",
        "power.draw": "GPU Power Draw",
        "clocks.current.graphics": "GPU Graphics Clock",
        "fan.speed": "GPU Fan Speed",
    }
    for field_name, label in nvidia_labels.items():
        value = nvidia_data.get(field_name)
        _append_metric(metrics, SECTION_TELEMETRY, f"nvidia_{field_name.replace('.', '_')}", label, value, nvidia_snapshot, "nvidia_smi")

    for index, entry in enumerate(ensure_list(afterburner_snapshot.data.get("telemetry_entries")), start=1):
        value = entry.get("value")
        if not _is_real_afterburner_value(value):
            continue
        source_id = entry.get("source_id")
        label = entry.get("name") or f"Afterburner Metric {index}"
        metric_id = f"afterburner_{source_id}" if source_id is not None else f"afterburner_{index}"
        units = _sanitize_unit(entry.get("units"))
        display_value = format_display_value(value, units)
        _append_metric(metrics, SECTION_TELEMETRY, metric_id, label, value, afterburner_snapshot, "afterburner_shared_memory", display_value)

    return metrics


def normalize_software_inventory(software_snapshot: CollectedSource) -> list[SoftwareRecord]:
    records: list[SoftwareRecord] = []
    registry_items = ensure_list(software_snapshot.data.get("registry_software"))
    appx_items = ensure_list(software_snapshot.data.get("appx_software"))
    tool_files = ensure_list(software_snapshot.data.get("tool_files"))
    tool_file_map = {item.get("Name"): item for item in tool_files if item.get("Name")}

    for software_name, pattern in SOFTWARE_REGISTRY_PATTERNS.items():
        match = None
        for item in registry_items:
            display_name = item.get("DisplayName", "")
            if re.search(pattern, display_name, flags=re.IGNORECASE):
                match = item
                break
        file_match = tool_file_map.get(software_name)
        installed = match is not None or bool(file_match and file_match.get("Exists"))
        version = ""
        if match and match.get("DisplayVersion"):
            version = match.get("DisplayVersion")
        elif file_match and file_match.get("Version"):
            version = file_match.get("Version")
        install_path = ""
        if match and match.get("InstallLocation"):
            install_path = ""
        elif file_match and file_match.get("Path"):
            install_path = ""
        source_name = "Registry Software"
        if not match and file_match:
            source_name = "Tool Files"
        records.append(
            SoftwareRecord(
                name=software_name,
                installed=installed,
                version=version,
                install_path=install_path,
                source_name=source_name,
            )
        )

    for software_name, package_name in SOFTWARE_APPX_PACKAGES.items():
        match = None
        for item in appx_items:
            if item.get("Name") == package_name:
                match = item
                break
        records.append(
            SoftwareRecord(
                name=software_name,
                installed=match is not None,
                version=match.get("Version", "") if match else "",
                install_path="",
                source_name="Appx Software",
            )
        )

    return records


def normalize_process_inventory(process_snapshot: CollectedSource) -> list[ProcessRecord]:
    running_by_name = {}
    for process in ensure_list(process_snapshot.data.get("processes")):
        process_name = process.get("Name") or process.get("ProcessName")
        normalized_name = str(process_name).replace(".exe", "") if process_name else ""
        if normalized_name and normalized_name not in running_by_name:
            running_by_name[normalized_name] = process

    records: list[ProcessRecord] = []
    for process_name in RELEVANT_PROCESS_NAMES:
        match = running_by_name.get(process_name)
        records.append(
            ProcessRecord(
                name=process_name,
                running=match is not None,
                pid=(match.get("ProcessId") or match.get("Id")) if match else None,
                path="",
            )
        )

    return records


def normalize_service_inventory(service_snapshot: CollectedSource) -> list[ServiceRecord]:
    records: list[ServiceRecord] = []
    for service in ensure_list(service_snapshot.data.get("services")):
        records.append(
            ServiceRecord(
                name=service.get("DisplayName") or service.get("Name") or "Unknown Service",
                status=str(service.get("Status", "")),
                start_type=str(service.get("StartType", "")),
            )
        )
    return records


def collect_unavailable_metrics(*snapshots: CollectedSource) -> list[MetricRecord]:
    unavailable_metrics: list[MetricRecord] = []
    for snapshot in snapshots:
        for evidence_key, evidence in snapshot.evidence.items():
            if evidence.availability != AVAILABILITY_UNAVAILABLE:
                continue
            unavailable_metrics.append(
                MetricRecord(
                    metric_id=f"unavailable_{evidence_key}",
                    section="Unavailable Metrics",
                    label=evidence.source_name,
                    raw_value=None,
                    display_value=sanitize_text(evidence.stderr or "Unavailable"),
                    unit="",
                    availability=AVAILABILITY_UNAVAILABLE,
                    source_name=evidence.source_name,
                    source_command=str(sanitize_text(evidence.source_command)),
                    captured_at=evidence.captured_at,
                )
            )
    return unavailable_metrics










