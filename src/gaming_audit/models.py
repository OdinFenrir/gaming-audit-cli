from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any


@dataclass(slots=True)
class EvidenceRecord:
    source_name: str
    source_command: str
    availability: str
    captured_at: str
    raw_output: str
    artifact_filename: str | None = None
    artifact_path: str = ""
    stderr: str = ""
    return_code: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> EvidenceRecord:
        return cls(
            source_name=str(payload.get("source_name", "")),
            source_command=str(payload.get("source_command", "")),
            availability=str(payload.get("availability", "")),
            captured_at=str(payload.get("captured_at", "")),
            raw_output=str(payload.get("raw_output", "")),
            artifact_filename=payload.get("artifact_filename"),
            artifact_path=str(payload.get("artifact_path", "")),
            stderr=str(payload.get("stderr", "")),
            return_code=payload.get("return_code"),
        )


@dataclass(slots=True)
class MetricRecord:
    metric_id: str
    section: str
    label: str
    raw_value: Any
    display_value: str
    unit: str
    availability: str
    source_name: str
    source_command: str
    captured_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> MetricRecord:
        return cls(
            metric_id=str(payload.get("metric_id", "")),
            section=str(payload.get("section", "")),
            label=str(payload.get("label", "")),
            raw_value=payload.get("raw_value"),
            display_value=str(payload.get("display_value", "")),
            unit=str(payload.get("unit", "")),
            availability=str(payload.get("availability", "")),
            source_name=str(payload.get("source_name", "")),
            source_command=str(payload.get("source_command", "")),
            captured_at=str(payload.get("captured_at", "")),
        )


@dataclass(slots=True)
class SoftwareRecord:
    name: str
    installed: bool
    version: str
    install_path: str
    source_name: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> SoftwareRecord:
        return cls(
            name=str(payload.get("name", "")),
            installed=bool(payload.get("installed", False)),
            version=str(payload.get("version", "")),
            install_path=str(payload.get("install_path", "")),
            source_name=str(payload.get("source_name", "")),
        )


@dataclass(slots=True)
class ProcessRecord:
    name: str
    running: bool
    pid: int | None
    path: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ProcessRecord:
        raw_pid = payload.get("pid")
        pid = int(raw_pid) if raw_pid is not None else None
        return cls(
            name=str(payload.get("name", "")),
            running=bool(payload.get("running", False)),
            pid=pid,
            path=str(payload.get("path", "")),
        )


@dataclass(slots=True)
class ServiceRecord:
    name: str
    status: str
    start_type: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ServiceRecord:
        return cls(
            name=str(payload.get("name", "")),
            status=str(payload.get("status", "")),
            start_type=str(payload.get("start_type", "")),
        )


@dataclass(slots=True)
class DiagnosticRecord:
    source_key: str
    source_name: str
    availability: str
    source_command: str
    captured_at: str
    artifact_filename: str = ""
    artifact_path: str = ""
    stderr: str = ""
    return_code: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SavedRunRecord:
    run_stamp: str
    generated_at: str
    text_report_path: str
    json_report_path: str
    evidence_directory: str
    section_counts: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ReadinessRecord:
    label: str
    status: str


@dataclass(slots=True)
class RuntimePaths:
    evidence_dir: Path | None = None
    text_report: Path | None = None
    json_report: Path | None = None
    latest_snapshot: Path | None = None


@dataclass(slots=True)
class CollectedSource:
    data: dict[str, Any] = field(default_factory=dict)
    evidence: dict[str, EvidenceRecord] = field(default_factory=dict)


@dataclass(slots=True)
class CollectionBundle:
    scope: str
    run_stamp: str
    snapshots: dict[str, CollectedSource] = field(default_factory=dict)
    evidence_records: list[EvidenceRecord] = field(default_factory=list)
    diagnostics: list[DiagnosticRecord] = field(default_factory=list)
    runtime_paths: RuntimePaths = field(default_factory=RuntimePaths)
    temporary_directory: TemporaryDirectory[str] | None = None

    def cleanup(self) -> None:
        if self.temporary_directory is not None:
            self.temporary_directory.cleanup()
            self.temporary_directory = None


@dataclass(slots=True)
class AuditReport:
    metadata: dict[str, Any]
    system_metrics: list[MetricRecord]
    graphics_metrics: list[MetricRecord]
    display_metrics: list[MetricRecord]
    storage_metrics: list[MetricRecord]
    settings_metrics: list[MetricRecord]
    telemetry_metrics: list[MetricRecord]
    software_inventory: list[SoftwareRecord]
    process_inventory: list[ProcessRecord]
    service_inventory: list[ServiceRecord]
    unavailable_metrics: list[MetricRecord]
    evidence_records: list[EvidenceRecord]

    def to_dict(self) -> dict[str, Any]:
        return {
            "metadata": self.metadata,
            "system_metrics": [metric.to_dict() for metric in self.system_metrics],
            "graphics_metrics": [metric.to_dict() for metric in self.graphics_metrics],
            "display_metrics": [metric.to_dict() for metric in self.display_metrics],
            "storage_metrics": [metric.to_dict() for metric in self.storage_metrics],
            "settings_metrics": [metric.to_dict() for metric in self.settings_metrics],
            "software_inventory": [item.to_dict() for item in self.software_inventory],
            "process_inventory": [item.to_dict() for item in self.process_inventory],
            "service_inventory": [item.to_dict() for item in self.service_inventory],
            "telemetry_metrics": [metric.to_dict() for metric in self.telemetry_metrics],
            "unavailable_metrics": [metric.to_dict() for metric in self.unavailable_metrics],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> AuditReport:
        return cls(
            metadata=dict(payload.get("metadata", {})),
            system_metrics=[MetricRecord.from_dict(item) for item in payload.get("system_metrics", [])],
            graphics_metrics=[MetricRecord.from_dict(item) for item in payload.get("graphics_metrics", [])],
            display_metrics=[MetricRecord.from_dict(item) for item in payload.get("display_metrics", [])],
            storage_metrics=[MetricRecord.from_dict(item) for item in payload.get("storage_metrics", [])],
            settings_metrics=[MetricRecord.from_dict(item) for item in payload.get("settings_metrics", [])],
            telemetry_metrics=[MetricRecord.from_dict(item) for item in payload.get("telemetry_metrics", [])],
            software_inventory=[SoftwareRecord.from_dict(item) for item in payload.get("software_inventory", [])],
            process_inventory=[ProcessRecord.from_dict(item) for item in payload.get("process_inventory", [])],
            service_inventory=[ServiceRecord.from_dict(item) for item in payload.get("service_inventory", [])],
            unavailable_metrics=[MetricRecord.from_dict(item) for item in payload.get("unavailable_metrics", [])],
            evidence_records=[],
        )
