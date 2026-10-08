"""Build immutable evidence bundles for findings.

A finding says *what was grouped*. A bundle says *what is actually behind it* — and, just as
importantly, *what is not*. The ``missing_context`` and ``limitations`` fields are part of the
contract rather than free commentary, because a bundle that omits its own gaps invites a reviewer to
over-read it.

The bundle copies the minimal event fields instead of pointing at the mutable event store, so a
reviewer sees the same values the detector saw even if upstream data is re-ingested later.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from aegistrace.schemas.detections import (
    DetectionEvidence,
    DetectionResult,
    DetectorType,
)
from aegistrace.schemas.events import SecurityEvent
from aegistrace.schemas.findings import (
    EventSummary,
    EvidenceBundle,
    ExternalFinding,
    Finding,
    ScoreReference,
    evidence_bundle_id_for,
)

EVIDENCE_BUNDLE_VERSION = "1.0.0"

DEFAULT_MISSING_CONTEXT: tuple[str, ...] = (
    "ground-truth labels are deliberately excluded; they are evaluation metadata, not evidence",
    "packet payloads are not available in the source flow records",
    "host identity is inferred from the observed source address, not an asset inventory",
)

DEFAULT_LIMITATIONS: tuple[str, ...] = (
    "a detector signal is not proof of compromise or an incident",
    "model scores are model-specific and were not compared across models",
    "absence of evidence in this bundle is not evidence of absence",
)


def _evidence_from(detection: DetectionResult, field_name: str) -> str | None:
    """Read one string-valued supporting-evidence field emitted by the detector."""

    for evidence in detection.supporting_evidence:
        if evidence.field == field_name:
            value = evidence.observed_value
            return value if isinstance(value, str) else json.dumps(value, default=str)
    return None


def _evidence_sort_key(evidence: DetectionEvidence) -> tuple[str, str, str]:
    return (
        evidence.field,
        json.dumps(evidence.observed_value, sort_keys=True, default=str),
        evidence.predicate,
    )


def _summarize(event: SecurityEvent) -> EventSummary:
    """Copy the minimal event fields a reviewer needs."""

    details = event.details
    src_ip = getattr(details, "src_ip", None) if details is not None else None
    dst_ip = getattr(details, "dst_ip", None) if details is not None else None
    dst_port = getattr(details, "dst_port", None) if details is not None else None
    protocol = getattr(details, "protocol", None) if details is not None else None
    return EventSummary(
        event_id=event.event_id,
        observed_at=event.observed_at,
        event_type=event.event_type,
        source_event_id=event.source.source_event_id,
        source_dataset=event.source.source_dataset,
        src_ip=str(src_ip) if src_ip is not None else None,
        dst_ip=str(dst_ip) if dst_ip is not None else None,
        dst_port=dst_port,
        protocol=protocol,
    )


@dataclass(frozen=True)
class EvidenceIndex:
    """Lookup tables shared across every finding in one batch.

    Building ``detections_by_id`` and ``events_by_id`` once is what removes the quadratic blow-up:
    the old per-finding rebuild re-iterated the inputs on every one of a batch's ``F`` bundle calls,
    making the pipeline O(F x D + F x E); iterating each input a single time collapses that to
    O(D + E).
    """

    detections_by_id: dict[UUID, DetectionResult]
    events_by_id: dict[UUID, SecurityEvent]

    @classmethod
    def from_inputs(
        cls,
        detections: Iterable[DetectionResult],
        events: Iterable[SecurityEvent],
    ) -> EvidenceIndex:
        """Materialize both inputs once, tolerating single-shot generators."""
        return cls(
            detections_by_id={detection.detection_id: detection for detection in detections},
            events_by_id={event.event_id: event for event in events},
        )


def _bundle_from_index(
    finding: Finding,
    index: EvidenceIndex,
    *,
    created_at: datetime,
    bundle_version: str,
    external_findings: Iterable[ExternalFinding],
    missing_context: Iterable[str],
    limitations: Iterable[str],
) -> EvidenceBundle:
    """Snapshot everything behind one finding using an already-built ``EvidenceIndex``."""

    wanted = set(finding.detection_ids)
    selected = sorted(
        (index.detections_by_id[did] for did in wanted if did in index.detections_by_id),
        key=lambda d: str(d.detection_id),
    )
    if not selected:
        if not index.detections_by_id:
            raise ValueError(
                "no matching detections to bundle: the detections input yielded no detections"
            )
        raise ValueError("finding has no matching detections to bundle")

    summaries = sorted(
        (
            _summarize(index.events_by_id[eid])
            for eid in finding.event_ids
            if eid in index.events_by_id
        ),
        key=lambda summary: (summary.observed_at, str(summary.event_id)),
    )
    if not summaries:
        if not index.events_by_id:
            raise ValueError(
                "finding has no matching events to bundle: the events input yielded no events"
            )
        raise ValueError("finding has no matching events to bundle")

    observed: dict[tuple[str, str, str], DetectionEvidence] = {}
    for detection in selected:
        for evidence in detection.supporting_evidence:
            observed[_evidence_sort_key(evidence)] = evidence

    scores: list[ScoreReference] = []
    feature_versions: set[str] = set()
    for detection in selected:
        feature_version = _evidence_from(detection, "feature_version")
        if feature_version is not None:
            feature_versions.add(feature_version)
        if detection.detector_type is not DetectorType.ML:
            continue
        model_name = _evidence_from(detection, "model_name")
        if model_name is None or feature_version is None:
            continue
        scores.append(
            ScoreReference(
                detection_id=detection.detection_id,
                detector_name=detection.detector_name,
                detector_version=detection.detector_version,
                model_name=model_name,
                model_score=detection.score,
                feature_version=feature_version,
            )
        )

    return EvidenceBundle(
        evidence_bundle_id=evidence_bundle_id_for(
            bundle_version=bundle_version,
            finding_id=finding.finding_id,
            detection_ids=finding.detection_ids,
        ),
        bundle_version=bundle_version,
        finding_id=finding.finding_id,
        detection_ids=tuple(sorted(wanted, key=str)),
        event_summaries=tuple(summaries),
        observed_values=tuple(observed[key] for key in sorted(observed)),
        score_references=tuple(sorted(scores, key=lambda s: str(s.detection_id))),
        feature_versions=tuple(sorted(feature_versions)),
        external_findings=tuple(external_findings),
        missing_context=tuple(missing_context),
        limitations=tuple(limitations),
        created_at=created_at,
    )


def build_evidence_bundle(
    finding: Finding,
    detections: Iterable[DetectionResult],
    events: Iterable[SecurityEvent],
    *,
    created_at: datetime,
    bundle_version: str = EVIDENCE_BUNDLE_VERSION,
    external_findings: Iterable[ExternalFinding] = (),
    missing_context: Iterable[str] = DEFAULT_MISSING_CONTEXT,
    limitations: Iterable[str] = DEFAULT_LIMITATIONS,
    index: EvidenceIndex | None = None,
) -> EvidenceBundle:
    """Snapshot everything behind one ``finding`` without losing a single identifier.

    ``detections`` and ``events`` are accepted as ``Iterable`` (either materialized or single-shot)
    and are materialized into an :class:`EvidenceIndex` exactly once. Pass a prebuilt ``index`` when
    bundling a batch of findings so the inputs are not re-iterated per finding.
    """

    built = EvidenceIndex.from_inputs(detections, events) if index is None else index
    return _bundle_from_index(
        finding,
        built,
        created_at=created_at,
        bundle_version=bundle_version,
        external_findings=external_findings,
        missing_context=missing_context,
        limitations=limitations,
    )


def build_evidence_bundles(
    findings: Iterable[Finding],
    detections: Iterable[DetectionResult],
    events: Iterable[SecurityEvent],
    *,
    created_at: datetime,
    bundle_version: str = EVIDENCE_BUNDLE_VERSION,
    external_findings: Iterable[ExternalFinding] = (),
    missing_context: Iterable[str] = DEFAULT_MISSING_CONTEXT,
    limitations: Iterable[str] = DEFAULT_LIMITATIONS,
    index: EvidenceIndex | None = None,
) -> tuple[EvidenceBundle, ...]:
    """Build a bundle for every finding while iterating the inputs exactly once.

    This is the scaling-safe entry point: one :class:`EvidenceIndex` is built from ``detections``
    and ``events`` and shared across all findings, so the cost is O(D + E), independent of the
    number of findings. Single-shot generators are accepted for any of the inputs.
    """

    built = EvidenceIndex.from_inputs(detections, events) if index is None else index
    return tuple(
        _bundle_from_index(
            finding,
            built,
            created_at=created_at,
            bundle_version=bundle_version,
            external_findings=external_findings,
            missing_context=missing_context,
            limitations=limitations,
        )
        for finding in findings
    )


__all__ = [
    "DEFAULT_LIMITATIONS",
    "DEFAULT_MISSING_CONTEXT",
    "EVIDENCE_BUNDLE_VERSION",
    "EvidenceIndex",
    "build_evidence_bundle",
    "build_evidence_bundles",
]
