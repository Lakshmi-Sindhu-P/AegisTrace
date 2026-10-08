"""Immutable, label-free finding, evidence-bundle, and claim contracts.

This module is the boundary between *detector output* and *human review*. Everything a reviewer
sees is built from these records, so they must satisfy three properties:

1. **Immutable.** Each record is frozen; a correction creates a new record rather than editing one.
   That is what lets the project reconstruct ``problem -> cause -> solution -> proof`` later.
2. **Provenance-preserving.** Every finding and bundle keeps the event and detection identifiers it
   was built from. Nothing is summarised away without an explicit field saying so.
3. **Label-free.** Nothing here may read ``GroundTruthLabel``. Research labels are evaluation
   metadata; letting them reach a finding would make the finding unfalsifiable as evidence.
"""

from __future__ import annotations

import json
from datetime import datetime
from enum import StrEnum
from typing import Literal
from uuid import NAMESPACE_URL, UUID, uuid5

from pydantic import Field, field_validator, model_validator

from aegistrace.schemas.common import FrozenSchema, NonEmptyText, SchemaVersion, normalize_utc
from aegistrace.schemas.detections import DetectionEvidence, DetectionSeverity

FINDING_SCHEMA_VERSION = "1.0.0"
EVIDENCE_BUNDLE_SCHEMA_VERSION = "1.0.0"
CLAIM_SCHEMA_VERSION = "1.0.0"

_BASE = "https://github.com/Lakshmi-Sindhu-P/AegisTrace"
FINDING_ID_NAMESPACE = uuid5(NAMESPACE_URL, f"{_BASE}/findings/v1")
EVIDENCE_BUNDLE_ID_NAMESPACE = uuid5(NAMESPACE_URL, f"{_BASE}/evidence-bundles/v1")
CLAIM_ID_NAMESPACE = uuid5(NAMESPACE_URL, f"{_BASE}/claims/v1")


class FindingStatus(StrEnum):
    """Lifecycle of a finding. Human review owns every transition out of OPEN."""

    OPEN = "open"
    TRIAGED = "triaged"
    DISMISSED = "dismissed"
    ESCALATED = "escalated"


class ClaimType(StrEnum):
    """Epistemic category of a statement, ordered from observed to inferred.

    The taxonomy exists so that a reader can tell "we measured this" apart from "an LLM said this".
    A statement whose category cannot be established is not promoted to a stronger category; it
    falls to UNKNOWN_INSUFFICIENT_EVIDENCE.
    """

    OBSERVED_FACT = "observed_fact"
    DETERMINISTIC_DERIVATION = "deterministic_derivation"
    REFERENCE_BACKED_FACT = "reference_backed_fact"
    MODEL_INFERENCE = "model_inference"
    AI_INTERPRETATION = "ai_interpretation"
    UNKNOWN_INSUFFICIENT_EVIDENCE = "unknown_insufficient_evidence"


class EvidenceReference(FrozenSchema):
    """A typed pointer from a finding, bundle, or claim back to supporting material."""

    kind: Literal[
        "event", "detection", "model_score", "feature_version", "external", "repository"
    ]
    reference: NonEmptyText
    locator: NonEmptyText | None = None


class EventSummary(FrozenSchema):
    """The minimal event fields a reviewer needs, copied rather than referenced."""

    event_id: UUID
    observed_at: datetime
    event_type: NonEmptyText
    source_event_id: NonEmptyText
    source_dataset: NonEmptyText
    src_ip: NonEmptyText | None = None
    dst_ip: NonEmptyText | None = None
    dst_port: int | None = Field(default=None, ge=0, le=65535)
    protocol: NonEmptyText | None = None

    @field_validator("observed_at")
    @classmethod
    def normalize_observed_at(cls, value: datetime) -> datetime:
        return normalize_utc(value)


class ScoreReference(FrozenSchema):
    """One model score, kept on its own model's scale.

    Scores from different models are **not** comparable. Each reference therefore carries the
    detector and model identity and the feature contract that produced it, so a consumer can tell
    which scale a number belongs to instead of silently ranking across models.
    """

    detection_id: UUID
    detector_name: NonEmptyText
    detector_version: SchemaVersion
    model_name: NonEmptyText
    model_score: float = Field(ge=0, le=1)
    feature_version: SchemaVersion


class ExternalFinding(FrozenSchema):
    """A third-party or scanner observation, preserved with its source and uncertainty."""

    source: NonEmptyText
    reference: NonEmptyText
    summary: NonEmptyText
    uncertainty: NonEmptyText


class Finding(FrozenSchema):
    """A deterministic grouping of related detections and the events behind them."""

    schema_version: SchemaVersion = FINDING_SCHEMA_VERSION
    finding_id: UUID
    aggregation_version: SchemaVersion
    event_ids: tuple[UUID, ...] = Field(min_length=1)
    detection_ids: tuple[UUID, ...] = Field(min_length=1)
    source_host: NonEmptyText
    window_start: datetime
    window_end: datetime
    destinations: tuple[NonEmptyText, ...] = ()
    destination_ports: tuple[int, ...] = ()
    proposed_severity: DetectionSeverity
    status: FindingStatus = FindingStatus.OPEN
    created_at: datetime
    note: NonEmptyText

    @field_validator("window_start", "window_end", "created_at")
    @classmethod
    def normalize_timestamps(cls, value: datetime) -> datetime:
        return normalize_utc(value)

    @model_validator(mode="after")
    def validate_window(self) -> Finding:
        if self.window_end < self.window_start:
            raise ValueError("window_end must not precede window_start")
        return self


class EvidenceBundle(FrozenSchema):
    """An immutable snapshot of everything behind one finding, including what is missing.

    ``missing_context`` and ``limitations`` are required parts of the contract rather than
    optional commentary: a bundle that does not say what it lacks invites over-reading.
    """

    schema_version: SchemaVersion = EVIDENCE_BUNDLE_SCHEMA_VERSION
    evidence_bundle_id: UUID
    bundle_version: SchemaVersion
    finding_id: UUID
    detection_ids: tuple[UUID, ...] = Field(min_length=1)
    event_summaries: tuple[EventSummary, ...] = Field(min_length=1)
    observed_values: tuple[DetectionEvidence, ...] = ()
    score_references: tuple[ScoreReference, ...] = ()
    feature_versions: tuple[SchemaVersion, ...] = ()
    external_findings: tuple[ExternalFinding, ...] = ()
    missing_context: tuple[NonEmptyText, ...] = ()
    limitations: tuple[NonEmptyText, ...] = ()
    created_at: datetime

    @field_validator("created_at")
    @classmethod
    def normalize_created_at(cls, value: datetime) -> datetime:
        return normalize_utc(value)


class Claim(FrozenSchema):
    """A statement plus the evidence it cites, tagged with its epistemic category."""

    schema_version: SchemaVersion = CLAIM_SCHEMA_VERSION
    claim_id: UUID
    claim_type: ClaimType
    statement: NonEmptyText
    evidence_references: tuple[EvidenceReference, ...] = ()
    created_at: datetime

    @field_validator("created_at")
    @classmethod
    def normalize_created_at(cls, value: datetime) -> datetime:
        return normalize_utc(value)


class ClaimVerification(FrozenSchema):
    """The outcome of checking a claim against the taxonomy, never an edit of the claim."""

    claim_id: UUID
    verified: bool
    effective_type: ClaimType
    reasons: tuple[NonEmptyText, ...] = ()


def _identity(*parts: object) -> str:
    """Serialize identity parts into a stable, order-explicit string for hashing."""

    return json.dumps(parts, ensure_ascii=False, separators=(",", ":"), default=str)


def finding_id_for(
    *,
    aggregation_version: str,
    source_host: str,
    window_start: datetime,
    event_ids: tuple[UUID, ...],
) -> UUID:
    """Derive a finding identity that does not depend on detection or input ordering."""

    ordered = sorted(str(event_id) for event_id in event_ids)
    return uuid5(
        FINDING_ID_NAMESPACE,
        _identity(
            aggregation_version, source_host, normalize_utc(window_start).isoformat(), ordered
        ),
    )


def evidence_bundle_id_for(
    *, bundle_version: str, finding_id: UUID, detection_ids: tuple[UUID, ...]
) -> UUID:
    """Derive a bundle identity from its finding and the detections it snapshots."""

    ordered = sorted(str(detection_id) for detection_id in detection_ids)
    return uuid5(
        EVIDENCE_BUNDLE_ID_NAMESPACE,
        _identity(bundle_version, str(finding_id), ordered),
    )


def claim_id_for(*, claim_type: str, statement: str) -> UUID:
    """Derive a claim identity from its category and text."""

    return uuid5(CLAIM_ID_NAMESPACE, _identity(claim_type, statement))


__all__ = [
    "CLAIM_SCHEMA_VERSION",
    "EVIDENCE_BUNDLE_SCHEMA_VERSION",
    "FINDING_SCHEMA_VERSION",
    "Claim",
    "ClaimType",
    "ClaimVerification",
    "EventSummary",
    "EvidenceBundle",
    "EvidenceReference",
    "ExternalFinding",
    "Finding",
    "FindingStatus",
    "ScoreReference",
    "claim_id_for",
    "evidence_bundle_id_for",
    "finding_id_for",
]
