"""Minimal immutable detection records for the Phase 3 rule baseline."""

from __future__ import annotations

import json
from datetime import datetime
from enum import StrEnum
from uuid import NAMESPACE_URL, UUID, uuid5

from pydantic import Field, JsonValue, field_validator

from aegistrace.schemas.common import FrozenSchema, NonEmptyText, SchemaVersion, normalize_utc

DETECTION_SCHEMA_VERSION = "1.0.0"
DETECTION_ID_NAMESPACE = uuid5(
    NAMESPACE_URL, "https://github.com/Lakshmi-Sindhu-P/AegisTrace/detections/v1"
)


class DetectorType(StrEnum):
    """Approved detector families."""

    RULE = "rule"
    STATISTICAL = "statistical"
    ML = "ml"
    EXTERNAL_SCANNER = "external_scanner"


class DetectionSeverity(StrEnum):
    """Priority of a detector signal, not an incident disposition."""

    INFORMATIONAL = "informational"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DetectionEvidence(FrozenSchema):
    """One observed value and predicate supporting a detector signal."""

    field: NonEmptyText
    observed_value: JsonValue
    predicate: NonEmptyText


class DetectionResult(FrozenSchema):
    """Reproducible event-linked detection output."""

    schema_version: SchemaVersion = DETECTION_SCHEMA_VERSION
    detection_id: UUID
    event_id: UUID
    detector_type: DetectorType
    detector_name: NonEmptyText
    detector_version: SchemaVersion
    severity: DetectionSeverity
    score: float = Field(ge=0, le=1)
    triggered_rules: tuple[NonEmptyText, ...] = Field(min_length=1)
    supporting_evidence: tuple[DetectionEvidence, ...] = Field(min_length=1)
    created_at: datetime
    note: NonEmptyText

    @field_validator("created_at")
    @classmethod
    def normalize_created_at(cls, value: datetime) -> datetime:
        return normalize_utc(value)


def detection_id_for(
    *, event_id: UUID, detector_name: str, detector_version: str, rule_id: str
) -> UUID:
    """Derive an idempotent detection identity from detector and event identity."""

    identity = json.dumps(
        [str(event_id), detector_name, detector_version, rule_id],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return uuid5(DETECTION_ID_NAMESPACE, identity)
