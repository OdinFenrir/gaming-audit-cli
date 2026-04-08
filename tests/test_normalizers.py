from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / 'src'
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from gaming_audit.constants import AVAILABILITY_AVAILABLE, AVAILABILITY_UNAVAILABLE
from gaming_audit.models import CollectedSource, EvidenceRecord
from gaming_audit.normalizers import collect_unavailable_metrics, normalize_process_inventory, normalize_software_inventory, normalize_storage_metrics, normalize_system_metrics, normalize_telemetry_metrics


class NormalizerTests(unittest.TestCase):
    def test_normalize_software_inventory_uses_tool_file_fallback(self) -> None:
        snapshot = CollectedSource(
            data={
                "registry_software": [],
                "appx_software": [],
                "tool_files": [
                    {
                        "Name": "NVIDIA App",
                        "Exists": True,
                        "Path": r"C:\Program Files\NVIDIA Corporation\NVIDIA App\CEF\NVIDIA App.exe",
                        "Version": "11.0.6.383",
                    }
                ],
            }
        )
        items = normalize_software_inventory(snapshot)
        nvidia_app = next(item for item in items if item.name == "NVIDIA App")
        self.assertTrue(nvidia_app.installed)
        self.assertEqual(nvidia_app.version, "11.0.6.383")
        self.assertEqual("", nvidia_app.install_path)

    def test_normalize_process_inventory_handles_wmi_process_shape(self) -> None:
        snapshot = CollectedSource(
            data={
                "processes": [
                    {"Name": "MSIAfterburner.exe", "ProcessId": 1234, "ExecutablePath": r"C:\Tools\MSIAfterburner.exe"},
                    {"Name": "RTSS.exe", "ProcessId": 5678, "ExecutablePath": r"C:\Tools\RTSS.exe"},
                ]
            }
        )
        items = normalize_process_inventory(snapshot)
        msiafterburner = next(item for item in items if item.name == "MSIAfterburner")
        hwinfo = next(item for item in items if item.name == "HWiNFO64")
        self.assertTrue(msiafterburner.running)
        self.assertEqual(msiafterburner.pid, 1234)
        self.assertFalse(hwinfo.running)
    def test_normalize_process_inventory_omits_executable_paths(self) -> None:
        snapshot = CollectedSource(
            data={
                "processes": [
                    {"Name": "MSIAfterburner.exe", "ProcessId": 1234, "ExecutablePath": r"C:\Users\ldomi\AppData\Local\Tools\MSIAfterburner.exe"},
                ]
            }
        )
        items = normalize_process_inventory(snapshot)
        msiafterburner = next(item for item in items if item.name == "MSIAfterburner")
        self.assertEqual("", msiafterburner.path)
    def test_normalize_telemetry_metrics_skips_afterburner_sentinel_values(self) -> None:
        nvidia_snapshot = CollectedSource(data={"nvidia_smi": {}}, evidence={})
        afterburner_snapshot = CollectedSource(
            data={
                "telemetry_entries": [
                    {"source_id": 0x50, "name": "Framerate", "units": "FPS", "value": 3.4028234663852886e+38},
                    {"source_id": 0x00, "name": "GPU temperature", "units": "°C", "value": 50.0},
                ]
            },
            evidence={},
        )
        metrics = normalize_telemetry_metrics(nvidia_snapshot, afterburner_snapshot)
        self.assertEqual(len(metrics), 1)
        self.assertEqual(metrics[0].label, "GPU temperature")
        self.assertEqual(metrics[0].display_value, "50 C")
    def test_normalize_system_and_storage_metrics_omit_sensitive_identifiers(self) -> None:
        wmi_snapshot = CollectedSource(
            data={
                "operating_system": {
                    "caption": "Microsoft Windows 11 Home",
                    "version": "10.0.26200",
                    "build_number": "26200",
                    "architecture": "64-bit",
                    "machine_name": "DESKTOP-SECRET",
                    "last_boot_up_time": "2026-04-07T10:36:26.5+01:00",
                },
                "computer_system": {
                    "manufacturer": "ASUS",
                    "model": "System Product Name",
                    "total_physical_memory": 34273837056,
                },
                "processor": {
                    "Name": "AMD Ryzen 7 5800X3D",
                    "Manufacturer": "AuthenticAMD",
                    "NumberOfCores": 8,
                    "NumberOfLogicalProcessors": 16,
                    "MaxClockSpeed": 3400,
                    "CurrentClockSpeed": 3400,
                    "LoadPercentage": 8,
                    "SocketDesignation": "AM4",
                    "ProcessorId": "178BFBFF00A20F12",
                },
                "available_memory": {"available_memory_mb": 20881},
                "pagefile": [],
                "audio_devices": [],
            },
            evidence={},
        )
        network_snapshot = CollectedSource(
            data={
                "network_adapters": [
                    {
                        "Name": "Ethernet",
                        "InterfaceDescription": "Realtek PCIe GbE Family Controller",
                        "LinkSpeed": "1 Gbps",
                        "MacAddress": "04-42-1A-ED-86-F0",
                        "Status": "Up",
                    }
                ],
                "ping_sample": [],
            },
            evidence={},
        )
        storage_snapshot = CollectedSource(
            data={
                "physical_disks": [
                    {
                        "FriendlyName": "KINGSTON SNV2S500G",
                        "Model": "KINGSTON SNV2S500G",
                        "SerialNumber": "0000_0000_SECRET",
                        "MediaType": "SSD",
                        "HealthStatus": "Healthy",
                        "Size": 500107862016,
                        "BusType": "NVMe",
                        "FirmwareVersion": "EJFK3N.9",
                    }
                ],
                "volumes": [
                    {
                        "DriveLetter": "C",
                        "FileSystemLabel": "System",
                        "FileSystem": "NTFS",
                        "SizeRemaining": 125000000000,
                        "Size": 500000000000,
                        "HealthStatus": "Healthy",
                        "DriveType": "Fixed",
                        "Path": "\\\\?\\Volume{SECRET}\\",
                    }
                ],
            },
            evidence={},
        )

        system_metrics = normalize_system_metrics(wmi_snapshot, network_snapshot)
        storage_metrics = normalize_storage_metrics(storage_snapshot)
        metric_ids = {metric.metric_id for metric in system_metrics + storage_metrics}

        self.assertNotIn("machine_name", metric_ids)
        self.assertNotIn("cpu_processor_id", metric_ids)
        self.assertNotIn("network_adapter_1_mac_address", metric_ids)
        self.assertNotIn("physical_disk_1_serial_number", metric_ids)
        self.assertNotIn("volume_c_path", metric_ids)
    def test_collect_unavailable_metrics_only_returns_unavailable_sources(self) -> None:
        available_snapshot = CollectedSource(
            evidence={
                "ok": EvidenceRecord(
                    source_name="WMI processor",
                    source_command="powershell ...",
                    availability=AVAILABILITY_AVAILABLE,
                    captured_at="2026-04-07T22:00:00+01:00",
                    raw_output="{}",
                )
            }
        )
        unavailable_snapshot = CollectedSource(
            evidence={
                "missing": EvidenceRecord(
                    source_name="MSI Afterburner Shared Memory",
                    source_command="OpenFileMappingW(MAHMSharedMemory)",
                    availability=AVAILABILITY_UNAVAILABLE,
                    captured_at="2026-04-07T22:00:00+01:00",
                    raw_output="",
                    stderr="Shared memory was not initialized.",
                )
            }
        )
        metrics = collect_unavailable_metrics(available_snapshot, unavailable_snapshot)
        self.assertEqual(len(metrics), 1)
        self.assertEqual(metrics[0].label, "MSI Afterburner Shared Memory")
        self.assertEqual(metrics[0].availability, AVAILABILITY_UNAVAILABLE)


if __name__ == "__main__":
    unittest.main()




