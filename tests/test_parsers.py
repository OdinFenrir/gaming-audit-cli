from __future__ import annotations

import ctypes
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / 'src'
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from gaming_audit.constants import AFTERBURNER_SIGNATURE
from gaming_audit.sources.afterburner_source import MAHMSharedMemoryEntry, MAHMSharedMemoryHeader, parse_afterburner_snapshot
from gaming_audit.utils.parsing import parse_dxdiag_text, parse_nvidia_smi_csv


class ParserTests(unittest.TestCase):
    def test_parse_nvidia_smi_csv(self) -> None:
        fields = ["name", "driver_version", "temperature.gpu"]
        payload = parse_nvidia_smi_csv("NVIDIA GeForce RTX 3070, 595.97, 50", fields)
        self.assertEqual(payload["name"], "NVIDIA GeForce RTX 3070")
        self.assertEqual(payload["driver_version"], "595.97")
        self.assertEqual(payload["temperature.gpu"], "50")

    def test_parse_dxdiag_text(self) -> None:
        dxdiag_text = """
System Information
------------------
Operating System: Windows 11 Home 64-bit
DirectX Version: DirectX 12

Display Devices
---------------
Card name: NVIDIA GeForce RTX 3070
Driver Model: WDDM 3.2
Current Mode: 2560 x 1440 (32 bit) (165Hz)
HDR Support: Not Supported
Display Color Space: DXGI_COLOR_SPACE_RGB_FULL_G22_NONE_P709
Monitor Model: XB271HU
"""
        payload = parse_dxdiag_text(dxdiag_text)
        self.assertEqual(payload["system"]["directx_version"], "DirectX 12")
        self.assertEqual(payload["displays"][0]["card_name"], "NVIDIA GeForce RTX 3070")
        self.assertEqual(payload["displays"][0]["monitor_model"], "XB271HU")

    def test_parse_afterburner_snapshot(self) -> None:
        header = MAHMSharedMemoryHeader()
        header.dwSignature = AFTERBURNER_SIGNATURE
        header.dwVersion = 0x00020000
        header.dwHeaderSize = ctypes.sizeof(MAHMSharedMemoryHeader)
        header.dwNumEntries = 1
        header.dwEntrySize = ctypes.sizeof(MAHMSharedMemoryEntry)
        header.dwNumGpuEntries = 0
        header.dwGpuEntrySize = 0

        entry = MAHMSharedMemoryEntry()
        entry.szSrcName = b"GPU temperature"
        entry.szSrcUnits = b"C"
        entry.data = 50.0
        entry.dwGpu = 0
        entry.dwSrcId = 0

        snapshot_bytes = bytes(header) + bytes(entry)
        payload = parse_afterburner_snapshot(snapshot_bytes)
        self.assertEqual(payload["header"]["entry_count"], 1)
        self.assertEqual(payload["telemetry_entries"][0]["name"], "GPU temperature")
        self.assertEqual(payload["telemetry_entries"][0]["units"], "C")
        self.assertEqual(payload["telemetry_entries"][0]["value"], 50.0)


if __name__ == "__main__":
    unittest.main()
