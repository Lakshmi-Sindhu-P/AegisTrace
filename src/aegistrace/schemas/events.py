"""Canonical security-event envelope and source-specific detail records."""

from __future__ import annotations

import json
from datetime import datetime
from enum import StrEnum
from typing import Annotated, Any, Literal, Self
from uuid import NAMESPACE_URL, UUID, uuid5

from pydantic import (
    Field,
    IPvAnyAddress,
    JsonValue,
    StringConstraints,
    field_validator,
    model_validator,
)

from aegistrace.schemas.common import (
    FrozenSchema,
    NonEmptyText,
    SchemaVersion,
    Sha256,
    normalize_utc,
)

EVENT_SCHEMA_VERSION = "1.0.0"
EVENT_ID_NAMESPACE = uuid5(
    NAMESPACE_URL, "https://github.com/Lakshmi-Sindhu-P/AegisTrace/events/v1"
)


class SourceType(StrEnum):
    """Approved classes of upstream evidence."""

    CTU13 = "ctu13"
    IOT23 = "iot23"
    COWRIE = "cowrie"
    DSHIELD = "dshield"
    EXTERNAL_SCANNER = "external_scanner"
    SYNTHETIC = "synthetic"


class GroundTruthLabel(StrEnum):
    """Coarse label with unknown as the safe default."""

    BENIGN = "benign"
    MALICIOUS = "malicious"
    UNKNOWN = "unknown"


class AuthenticationOutcome(StrEnum):
    """Normalized authentication outcome."""

    SUCCESS = "success"
    FAILURE = "failure"
    UNKNOWN = "unknown"


class SourceRecordRef(FrozenSchema):
    """Stable pointer from a canonical event back to its source record."""

    source_type: SourceType
    source_dataset: NonEmptyText
    scenario_id: NonEmptyText | None = None
    dataset_version: NonEmptyText
    source_event_id: NonEmptyText
    raw_payload_reference: NonEmptyText
    raw_checksum: Sha256 | None = None


class EventProvenance(FrozenSchema):
    """Transformation identity required to reproduce one canonical event."""

    adapter_name: NonEmptyText
    adapter_version: SchemaVersion
    transformation_version: SchemaVersion
    processed_at: datetime
    quality_flags: tuple[NonEmptyText, ...] = ()

    _normalize_processed_at = field_validator("processed_at")(normalize_utc)


class NetworkEventDetails(FrozenSchema):
    """Network-flow fields shared by sources such as IoT-23."""

    kind: Literal["network"] = "network"
    src_ip: IPvAnyAddress | None = None
    dst_ip: IPvAnyAddress | None = None
    src_port: int | None = Field(default=None, ge=0, le=65535)
    dst_port: int | None = Field(default=None, ge=0, le=65535)
    protocol: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] | None = None
    service: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] | None = None
    connection_state: (
        Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] | None
    ) = None
    history: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] | None = None
    tunnel_parents: tuple[NonEmptyText, ...] = ()
    orig_bytes: int | None = Field(default=None, ge=0)
    resp_bytes: int | None = Field(default=None, ge=0)
    missed_bytes: int | None = Field(default=None, ge=0)
    orig_packets: int | None = Field(default=None, ge=0)
    resp_packets: int | None = Field(default=None, ge=0)
    network_bytes: int | None = Field(default=None, ge=0)
    packet_count: int | None = Field(default=None, ge=0)
    session_duration_seconds: float | None = Field(default=None, ge=0)


class Ctu13FlowDetails(FrozenSchema):
    """Argus-specific fields retained when normalizing a CTU-13 flow."""

    kind: Literal["ctu13_flow"] = "ctu13_flow"
    src_ip: IPvAnyAddress | None = None
    dst_ip: IPvAnyAddress | None = None
    source_src_address: NonEmptyText | None = None
    source_dst_address: NonEmptyText | None = None
    src_port: int | None = Field(default=None, ge=0, le=65535)
    dst_port: int | None = Field(default=None, ge=0, le=65535)
    protocol: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] | None = None
    service: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] | None = None
    connection_state: (
        Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] | None
    ) = None
    history: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] | None = None
    tunnel_parents: tuple[NonEmptyText, ...] = ()
    orig_bytes: int | None = Field(default=None, ge=0)
    resp_bytes: int | None = Field(default=None, ge=0)
    missed_bytes: int | None = Field(default=None, ge=0)
    orig_packets: int | None = Field(default=None, ge=0)
    resp_packets: int | None = Field(default=None, ge=0)
    network_bytes: int | None = Field(default=None, ge=0)
    packet_count: int | None = Field(default=None, ge=0)
    session_duration_seconds: float | None = Field(default=None, ge=0)
    flow_direction: NonEmptyText | None = None
    source_tos: int | None = Field(default=None, ge=0, le=255)
    destination_tos: int | None = Field(default=None, ge=0, le=255)
    source_label: NonEmptyText


class AuthenticationEventDetails(FrozenSchema):
    """Authentication observation without storing a credential value."""

    kind: Literal["authentication"] = "authentication"
    username: NonEmptyText | None = None
    outcome: AuthenticationOutcome = AuthenticationOutcome.UNKNOWN
    method: NonEmptyText | None = None


class CommandEventDetails(FrozenSchema):
    """An inert command string observed by a controlled telemetry source."""

    kind: Literal["command"] = "command"
    command: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=8192)]


class HttpEventDetails(FrozenSchema):
    """Minimal HTTP request metadata; bodies are not canonical event fields."""

    kind: Literal["http"] = "http"
    request_path: Annotated[str, StringConstraints(min_length=1, max_length=4096)] | None = None
    user_agent: Annotated[str, StringConstraints(min_length=1, max_length=2048)] | None = None
    method: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] | None = None


class GenericEventDetails(FrozenSchema):
    """Bounded escape hatch for source fields not yet promoted to a typed detail model."""

    kind: Literal["generic"] = "generic"
    fields: dict[NonEmptyText, JsonValue] = Field(default_factory=dict)


EventDetails = Annotated[
    NetworkEventDetails
    | Ctu13FlowDetails
    | AuthenticationEventDetails
    | CommandEventDetails
    | HttpEventDetails
    | GenericEventDetails,
    Field(discriminator="kind"),
]


def event_id_for(source: SourceRecordRef) -> UUID:
    """Derive a repeatable event ID solely from stable source identity."""

    identity = json.dumps(
        [
            source.source_type.value,
            source.source_dataset,
            source.scenario_id,
            source.dataset_version,
            source.source_event_id,
        ],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return uuid5(EVENT_ID_NAMESPACE, identity)


class SecurityEvent(FrozenSchema):
    """Versioned canonical event envelope with exactly one optional typed detail payload."""

    schema_version: SchemaVersion = EVENT_SCHEMA_VERSION
    event_id: UUID
    source: SourceRecordRef
    observed_at: datetime
    ingested_at: datetime
    event_type: NonEmptyText
    session_id: NonEmptyText | None = None
    details: EventDetails | None = None
    ground_truth_label: GroundTruthLabel = GroundTruthLabel.UNKNOWN
    label_source: NonEmptyText | None = None
    attack_category: NonEmptyText | None = None
    provenance: EventProvenance

    @model_validator(mode="before")
    @classmethod
    def populate_event_id(cls, value: Any) -> Any:
        """Populate the deterministic ID when callers provide only a source reference."""

        if not isinstance(value, dict) or value.get("event_id") is not None:
            return value
        source = SourceRecordRef.model_validate(value.get("source"))
        return {**value, "event_id": event_id_for(source)}

    @field_validator("observed_at", "ingested_at")
    @classmethod
    def normalize_event_timestamp(cls, value: datetime) -> datetime:
        """Require timezone-aware event timestamps and normalize them to UTC."""

        return normalize_utc(value)

    @model_validator(mode="after")
    def validate_evidence_identity(self) -> Self:
        """Reject mismatched identities and labels with missing provenance."""

        expected_event_id = event_id_for(self.source)
        if self.event_id != expected_event_id:
            raise ValueError("event_id does not match the stable source identity")
        if self.ground_truth_label is not GroundTruthLabel.UNKNOWN and self.label_source is None:
            raise ValueError("label_source is required for benign or malicious ground truth")
        if self.ground_truth_label is GroundTruthLabel.UNKNOWN and self.attack_category is not None:
            raise ValueError("attack_category requires a non-unknown ground-truth label")
        return self
