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

#: Identity algorithm versions. See `docs/identity_rule.md`.
#:
#: v1 hashed `(source_type, source_dataset, scenario_id, dataset_version, source_event_id)`. Because
#: `source_event_id` is `line-N` - arrival bookkeeping, numbered per file - two different records in
#: two different files of the same scenario could share one id (issue #38). v1 is retained so a
#: historical id can still be attributed to the version that produced it; it must never be used to
#: mint new ids.
EVENT_ID_NAMESPACE_V1 = uuid5(
    NAMESPACE_URL, "https://github.com/Lakshmi-Sindhu-P/AegisTrace/events/v1"
)
#: v2 adds `raw_checksum`, qualifying `line-N` to the file it was read from.
EVENT_ID_NAMESPACE = uuid5(
    NAMESPACE_URL, "https://github.com/Lakshmi-Sindhu-P/AegisTrace/events/v2"
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


def event_id_v1_for(source: SourceRecordRef) -> UUID:
    """Reproduce a pre-#38 event id. Historical reconciliation ONLY.

    v1 hashed `(source_type, source_dataset, scenario_id, dataset_version, source_event_id)`. Since
    `source_event_id` is `line-N`, numbered per file, two different records in two different files
    of
    the same scenario could share one id. Never use this to mint new ids.
    """

    return uuid5(
        EVENT_ID_NAMESPACE_V1,
        _identity(
            source.source_type.value,
            source.source_dataset,
            source.scenario_id,
            source.dataset_version,
            source.source_event_id,
        ),
    )


def event_id_for(source: SourceRecordRef) -> UUID:
    """Derive a repeatable event ID from the source record, by the identity rule.

    The rule (`docs/identity_rule.md`): an id covers exactly the fields that make the entity the
    entity it is, and nothing else.

    `source_event_id` is `line-N`, which is *arrival bookkeeping* - it says where a record sat in a
    file, not which record it was. Used alone it made two different flows in two different files of
    the same scenario share one id (issue #38). `raw_checksum` qualifies it to the file it was read
    from, which the ingestion adapters already compute.

    Both required properties now hold: re-ingesting the same file yields the same ids (a file's
    checksum is stable), and distinct files cannot collide. When `raw_checksum` is absent the
    identity degrades to v1's field set; ingestion always populates it, so this affects only
    hand-built references.

    Use :func:`event_id_v1_for` to reproduce a pre-change id for historical reconciliation.
    """

    return uuid5(
        EVENT_ID_NAMESPACE,
        _identity(
            source.source_type.value,
            source.source_dataset,
            source.scenario_id,
            source.dataset_version,
            source.source_event_id,
            source.raw_checksum,
        ),
    )


def _identity(*parts: object) -> str:
    return json.dumps(list(parts), ensure_ascii=False, separators=(",", ":"), default=str)


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
