from __future__ import annotations

APP_NAME = "PC Gaming System Audit"
REPORT_PREFIX = "system_audit"

SECTION_OVERVIEW = "Overview"
SECTION_SYSTEM = "System"
SECTION_GRAPHICS = "Graphics"
SECTION_DISPLAYS = "Displays"
SECTION_STORAGE = "Storage"
SECTION_SETTINGS = "Gaming Settings"
SECTION_TOOLS = "Performance Tools"
SECTION_PROCESSES = "Processes"
SECTION_SERVICES = "Services"
SECTION_TELEMETRY = "Live Telemetry"
SECTION_UNAVAILABLE = "Unavailable Metrics"

SECTION_ORDER = [
    SECTION_OVERVIEW,
    SECTION_SYSTEM,
    SECTION_GRAPHICS,
    SECTION_DISPLAYS,
    SECTION_STORAGE,
    SECTION_SETTINGS,
    SECTION_TOOLS,
    SECTION_PROCESSES,
    SECTION_SERVICES,
    SECTION_TELEMETRY,
    SECTION_UNAVAILABLE,
]

SCOPE_FULL = "full"
SCOPE_SYSTEM = "system"
SCOPE_GRAPHICS = "graphics"
SCOPE_DISPLAYS = "displays"
SCOPE_STORAGE = "storage"
SCOPE_SETTINGS = "settings"
SCOPE_TOOLS = "tools"
SCOPE_PROCESSES = "processes"
SCOPE_SERVICES = "services"
SCOPE_PROCESSES_SERVICES = "processes_services"
SCOPE_TELEMETRY = "telemetry"
SCOPE_DIAGNOSTICS = "diagnostics"

AVAILABILITY_AVAILABLE = "available"
AVAILABILITY_UNAVAILABLE = "unavailable"

AFTERBURNER_SHARED_MEMORY_NAME = "MAHMSharedMemory"
AFTERBURNER_SIGNATURE = int.from_bytes(b"MHAM", "little")
AFTERBURNER_DEAD_SIGNATURE = 0xDEAD
AFTERBURNER_MAX_PATH = 260

AFTERBURNER_METRIC_IDS = {
    0x00000000: "GPU Temperature",
    0x00000010: "GPU Fan Speed",
    0x00000020: "GPU Core Clock",
    0x00000022: "GPU Memory Clock",
    0x00000030: "GPU Usage",
    0x00000031: "GPU Memory Usage",
    0x00000032: "GPU Frame Buffer Usage",
    0x00000050: "Framerate",
    0x00000051: "Frametime",
    0x00000053: "Average Framerate",
    0x00000055: "1 Percent Low Framerate",
    0x00000056: "0.1 Percent Low Framerate",
    0x00000061: "GPU Power Draw",
    0x00000080: "CPU Temperature",
    0x00000090: "CPU Usage",
    0x00000091: "RAM Usage",
    0x00000092: "Pagefile Usage",
    0x000000A0: "CPU Clock",
}

SOFTWARE_REGISTRY_PATTERNS = {
    "NVIDIA App": r"^NVIDIA App(?:\\s+.*)?$",
    "MSI Afterburner": r"^MSI Afterburner",
    "RivaTuner Statistics Server": r"^RivaTuner Statistics Server$",
    "HWiNFO": r"^HWiNFO",
    "Visual C++ 2015-2022 x64 Runtime": r"Visual C\+\+.*(2022|2015-2022).*(x64|X64)",
    "Visual C++ 2015-2022 x86 Runtime": r"Visual C\+\+.*(2022|2015-2022).*(x86|X86)",
}

SOFTWARE_APPX_PACKAGES = {
    "NVIDIA Control Panel": "NVIDIACorp.NVIDIAControlPanel",
    "Xbox Gaming Overlay": "Microsoft.XboxGamingOverlay",
    "Microsoft Gaming App": "Microsoft.GamingApp",
}

RELEVANT_PROCESS_NAMES = [
    "MSIAfterburner",
    "RTSS",
    "RTSSHooksLoader64",
    "HWiNFO64",
]

RELEVANT_SERVICE_PATTERNS = [
    r"^NvContainer.*",
    r"^Steam Client Service$",
    r"^EasyAntiCheat.*",
    r"^BEService$",
    r"^vgc$",
]

NVIDIA_SMI_FIELDS = [
    "name",
    "driver_version",
    "temperature.gpu",
    "utilization.gpu",
    "utilization.memory",
    "power.draw",
    "clocks.current.graphics",
    "fan.speed",
]
