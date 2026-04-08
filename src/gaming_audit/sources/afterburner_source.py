from __future__ import annotations

import ctypes
from ctypes import wintypes
from typing import Any

from ..constants import (
    AFTERBURNER_DEAD_SIGNATURE,
    AFTERBURNER_MAX_PATH,
    AFTERBURNER_METRIC_IDS,
    AFTERBURNER_SHARED_MEMORY_NAME,
    AFTERBURNER_SIGNATURE,
    AVAILABILITY_AVAILABLE,
    AVAILABILITY_UNAVAILABLE,
)
from ..models import CollectedSource, EvidenceRecord
from ..utils.time_utils import iso_timestamp

FILE_MAP_READ = 0x0004


class MAHMSharedMemoryHeader(ctypes.Structure):
    _fields_ = [
        ("dwSignature", wintypes.DWORD),
        ("dwVersion", wintypes.DWORD),
        ("dwHeaderSize", wintypes.DWORD),
        ("dwNumEntries", wintypes.DWORD),
        ("dwEntrySize", wintypes.DWORD),
        ("time", ctypes.c_int32),
        ("dwNumGpuEntries", wintypes.DWORD),
        ("dwGpuEntrySize", wintypes.DWORD),
    ]


class MAHMSharedMemoryEntry(ctypes.Structure):
    _fields_ = [
        ("szSrcName", ctypes.c_char * AFTERBURNER_MAX_PATH),
        ("szSrcUnits", ctypes.c_char * AFTERBURNER_MAX_PATH),
        ("szLocalizedSrcName", ctypes.c_char * AFTERBURNER_MAX_PATH),
        ("szLocalizedSrcUnits", ctypes.c_char * AFTERBURNER_MAX_PATH),
        ("szRecommendedFormat", ctypes.c_char * AFTERBURNER_MAX_PATH),
        ("data", ctypes.c_float),
        ("minLimit", ctypes.c_float),
        ("maxLimit", ctypes.c_float),
        ("dwFlags", wintypes.DWORD),
        ("dwGpu", wintypes.DWORD),
        ("dwSrcId", wintypes.DWORD),
    ]


def _decode_char_buffer(raw_value: ctypes.Array[ctypes.c_char]) -> str:
    return bytes(raw_value).split(b"\x00", 1)[0].decode("utf-8", errors="replace").strip()


def parse_afterburner_snapshot(snapshot_bytes: bytes) -> dict[str, Any]:
    header = MAHMSharedMemoryHeader.from_buffer_copy(snapshot_bytes)
    if header.dwSignature == AFTERBURNER_DEAD_SIGNATURE or header.dwSignature != AFTERBURNER_SIGNATURE:
        raise ValueError("MSI Afterburner shared memory is not initialized.")

    entries: list[dict[str, Any]] = []
    base_offset = header.dwHeaderSize
    for index in range(header.dwNumEntries):
        start = base_offset + (index * header.dwEntrySize)
        end = start + header.dwEntrySize
        entry = MAHMSharedMemoryEntry.from_buffer_copy(snapshot_bytes[start:end])
        entries.append(
            {
                "source_id": int(entry.dwSrcId),
                "gpu_index": int(entry.dwGpu),
                "name": _decode_char_buffer(entry.szSrcName),
                "units": _decode_char_buffer(entry.szSrcUnits),
                "value": float(entry.data),
            }
        )

    return {
        "header": {
            "version": int(header.dwVersion),
            "entry_count": int(header.dwNumEntries),
            "gpu_entry_count": int(header.dwNumGpuEntries),
        },
        "telemetry_entries": entries,
    }


def collect() -> CollectedSource:
    snapshot = CollectedSource()
    captured_at = iso_timestamp()

    kernel32 = ctypes.windll.kernel32
    kernel32.OpenFileMappingW.restype = wintypes.HANDLE
    kernel32.OpenFileMappingW.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]
    kernel32.MapViewOfFile.restype = ctypes.c_void_p
    kernel32.MapViewOfFile.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, ctypes.c_size_t]
    kernel32.UnmapViewOfFile.argtypes = [ctypes.c_void_p]
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]

    mapping = kernel32.OpenFileMappingW(FILE_MAP_READ, False, AFTERBURNER_SHARED_MEMORY_NAME)
    if not mapping:
        snapshot.evidence["afterburner_shared_memory"] = EvidenceRecord(
            source_name="MSI Afterburner Shared Memory",
            source_command=f"OpenFileMappingW({AFTERBURNER_SHARED_MEMORY_NAME})",
            availability=AVAILABILITY_UNAVAILABLE,
            captured_at=captured_at,
            raw_output="",
            artifact_filename="afterburner_shared_memory.txt",
            stderr="Shared memory mapping was not found.",
            return_code=None,
        )
        return snapshot

    view = kernel32.MapViewOfFile(mapping, FILE_MAP_READ, 0, 0, 0)
    try:
        if not view:
            snapshot.evidence["afterburner_shared_memory"] = EvidenceRecord(
                source_name="MSI Afterburner Shared Memory",
                source_command=f"MapViewOfFile({AFTERBURNER_SHARED_MEMORY_NAME})",
                availability=AVAILABILITY_UNAVAILABLE,
                captured_at=captured_at,
                raw_output="",
                artifact_filename="afterburner_shared_memory.txt",
                stderr="Shared memory mapping exists but could not be read.",
                return_code=None,
            )
            return snapshot

        header = MAHMSharedMemoryHeader.from_address(view)
        if header.dwSignature == AFTERBURNER_DEAD_SIGNATURE or header.dwSignature != AFTERBURNER_SIGNATURE:
            snapshot.evidence["afterburner_shared_memory"] = EvidenceRecord(
                source_name="MSI Afterburner Shared Memory",
                source_command=f"Read shared memory header from {AFTERBURNER_SHARED_MEMORY_NAME}",
                availability=AVAILABILITY_UNAVAILABLE,
                captured_at=captured_at,
                raw_output="",
                artifact_filename="afterburner_shared_memory.txt",
                stderr="Shared memory was present but not initialized with valid monitoring data.",
                return_code=None,
            )
            return snapshot

        total_size = header.dwHeaderSize + (header.dwNumEntries * header.dwEntrySize) + (header.dwNumGpuEntries * header.dwGpuEntrySize)
        snapshot_bytes = ctypes.string_at(view, total_size)
        parsed = parse_afterburner_snapshot(snapshot_bytes)
        interesting_entries = [
            entry
            for entry in parsed["telemetry_entries"]
            if entry["source_id"] in AFTERBURNER_METRIC_IDS or entry["name"]
        ]
        lines = []
        for entry in interesting_entries:
            source_id = int(entry["source_id"])
            label = AFTERBURNER_METRIC_IDS.get(source_id, str(entry["name"]))
            lines.append(f"{label}: {entry['value']} {entry['units']}".strip())

        snapshot.evidence["afterburner_shared_memory"] = EvidenceRecord(
            source_name="MSI Afterburner Shared Memory",
            source_command=f"OpenFileMappingW({AFTERBURNER_SHARED_MEMORY_NAME})",
            availability=AVAILABILITY_AVAILABLE,
            captured_at=captured_at,
            raw_output="\n".join(lines),
            artifact_filename="afterburner_shared_memory.txt",
            stderr="",
            return_code=None,
        )
        snapshot.data.update(parsed)
        snapshot.data["telemetry_entries"] = interesting_entries
        return snapshot
    finally:
        if view:
            kernel32.UnmapViewOfFile(view)
        kernel32.CloseHandle(mapping)
