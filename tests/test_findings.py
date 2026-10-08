"""Tests for the deterministic finding and evidence spine.

These tests defend the two properties the milestone exists for: provenance is never lost on the way
from an event to an evidence bundle, and the aggregation never consults a research label.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Literal

import pytest
from pydantic import BaseModel

from aegistrace.detection.evidence import build_evidence_bundle
from aegistrace.detection.findings import aggregate_findings
from aegistrace.detection.ml import emit_ml_detections, severity_for_score
from aegistrace.schemas.detections import DetectionResult, DetectionSeverity
from aegistrace.schemas.events import (
    Ctu13FlowDetails,
    EventProvenance,
    GroundTruthLabel,
    SecurityEvent,
    SourceRecordRef,
    SourceType,
    event_id_for,
)
from aegistrace.schemas.findings import (
    Claim,
    ClaimType,
    EvidenceReference,
    claim_id_for,
)
from aegistrace.verification import verify_claim

BASE = datetime(2026, 10, 8, 12, 0, tzinfo=UTC)
CREATED_AT = datetime(2026, 10, 8, 13, 0, tzinfo=UTC)
FEATURE_VERSION = "1.1.0"


def _event(
    *,
    src_ip: str,
    offset_seconds: float,
    dst_ip: str = "198.51.100.9",
    dst_port: int = 80,
    label: GroundTruthLabel = GroundTruthLabel.UNKNOWN,
) -> SecurityEvent:
    """Build one CTU-13-shaped event at a fixed offset from BASE."""

    observed_at = BASE + timedelta(seconds=offset_seconds)
    source = SourceRecordRef(
        source_type=SourceType.CTU13,
        source_dataset="CTU-13",
        scenario_id="11",
        dataset_version="1.0.0",
        source_event_id=f"{src_ip}@{offset_seconds}",
        raw_payload_reference="data/fixtures/ctu13/scenario_11.binetflow",
    )
    return SecurityEvent(
        event_id=event_id_for(source),
        source=source,
        observed_at=observed_at,
        ingested_at=observed_at,
        event_type="network_flow",
        provenance=EventProvenance(
            adapter_name="test_fixture",
            adapter_version="1.0.0",
            transformation_version="1.0.0",
            processed_at=observed_at,
        ),
        details=Ctu13FlowDetails(
            src_ip=src_ip,
            dst_ip=dst_ip,
            dst_port=dst_port,
            protocol="tcp",
            source_label="flow=Background",
        ),
        ground_truth_label=label,
        label_source=(
            None if label is GroundTruthLabel.UNKNOWN else "CTU-13 scenario label"
        ),
    )


def _detections(
    events: tuple[SecurityEvent, ...], *, score: float = 0.95, threshold: float = 0.2
) -> tuple[DetectionResult, ...]:
    """Emit ML detections for every event at a fixed score."""

    scores = {event.event_id: score for event in events}
    return emit_ml_detections(
        events,
        scores,
        detector_name="ctu13_phase3_random_forest",
        detector_version="1.0.0",
        model_name="random_forest",
        feature_version=FEATURE_VERSION,
        threshold=threshold,
        created_at=CREATED_AT,
    )


def _dump(records: tuple[BaseModel, ...]) -> str:
    return json.dumps([record.model_dump(mode="json") for record in records], sort_keys=True)


def test_event_to_detection_to_finding_to_bundle_preserves_provenance() -> None:
    events = (
        _event(src_ip="10.0.0.1", offset_seconds=0, dst_port=80),
        _event(src_ip="10.0.0.1", offset_seconds=10, dst_port=443),
        _event(src_ip="10.0.0.2", offset_seconds=5, dst_port=22),
    )
    detections = _detections(events)
    assert len(detections) == 3

    findings = aggregate_findings(detections, events, created_at=CREATED_AT)
    assert {finding.source_host for finding in findings} == {"10.0.0.1", "10.0.0.2"}

    event_ids = {event.event_id for event in events}
    detection_ids = {detection.detection_id for detection in detections}
    for finding in findings:
        assert set(finding.event_ids) <= event_ids
        assert set(finding.detection_ids) <= detection_ids

        bundle = build_evidence_bundle(finding, detections, events, created_at=CREATED_AT)
        assert bundle.finding_id == finding.finding_id
        assert set(bundle.detection_ids) == set(finding.detection_ids)
        assert {summary.event_id for summary in bundle.event_summaries} == set(finding.event_ids)
        assert bundle.observed_values
        assert bundle.score_references
        assert all(ref.feature_version == FEATURE_VERSION for ref in bundle.score_references)
        assert all(ref.model_name == "random_forest" for ref in bundle.score_references)

    host_one = next(finding for finding in findings if finding.source_host == "10.0.0.1")
    assert len(host_one.event_ids) == 2
    assert host_one.destination_ports == (80, 443)
    assert host_one.window_end > host_one.window_start


def test_aggregation_never_consults_research_labels() -> None:
    offsets = (0.0, 20.0, 40.0)
    benign = tuple(
        _event(src_ip="10.0.0.1", offset_seconds=o, label=GroundTruthLabel.BENIGN) for o in offsets
    )
    malicious = tuple(
        _event(src_ip="10.0.0.1", offset_seconds=o, label=GroundTruthLabel.MALICIOUS)
        for o in offsets
    )
    unknown = tuple(
        _event(src_ip="10.0.0.1", offset_seconds=o, label=GroundTruthLabel.UNKNOWN) for o in offsets
    )

    baseline = _dump(aggregate_findings(_detections(benign), benign, created_at=CREATED_AT))
    assert baseline == _dump(
        aggregate_findings(_detections(malicious), malicious, created_at=CREATED_AT)
    )
    assert baseline == _dump(
        aggregate_findings(_detections(unknown), unknown, created_at=CREATED_AT)
    )


def test_grouping_is_stable_across_window_changes_and_input_order() -> None:
    """Two bursts, 20s apart within a burst and 540s apart between bursts.

    Any window in (20, 540) must produce the same two findings. Windows from 120s to 500s are
    therefore asserted identical, which is the stability tolerance this aggregation guarantees.
    """

    events = tuple(
        [_event(src_ip="10.0.0.1", offset_seconds=float(t)) for t in (0, 20, 40, 60)]
        + [_event(src_ip="10.0.0.1", offset_seconds=float(t)) for t in (600, 620, 640)]
    )
    detections = _detections(events)
    expected = _dump(
        aggregate_findings(detections, events, created_at=CREATED_AT, window_seconds=300.0)
    )
    assert len(aggregate_findings(detections, events, created_at=CREATED_AT)) == 2

    for window in (120.0, 200.0, 300.0, 400.0, 500.0):
        assert (
            _dump(
                aggregate_findings(
                    detections, events, created_at=CREATED_AT, window_seconds=window
                )
            )
            == expected
        )

    shuffled = tuple(reversed(events))
    shuffled_detections = tuple(reversed(detections))
    assert (
        _dump(
            aggregate_findings(
                shuffled_detections, shuffled, created_at=CREATED_AT, window_seconds=300.0
            )
        )
        == expected
    )


def test_aggregation_rejects_a_non_positive_window() -> None:
    events = (_event(src_ip="10.0.0.1", offset_seconds=0),)
    with pytest.raises(ValueError, match="window_seconds must be positive"):
        aggregate_findings(_detections(events), events, created_at=CREATED_AT, window_seconds=0)


def test_ml_scores_keep_model_identity_and_are_not_compared_across_models() -> None:
    events = (_event(src_ip="10.0.0.1", offset_seconds=0),)
    event_id = events[0].event_id

    forest = emit_ml_detections(
        events,
        {event_id: 0.73},
        detector_name="ctu13_phase3_random_forest",
        detector_version="1.0.0",
        model_name="random_forest",
        feature_version="1.1.0",
        threshold=0.2,
        created_at=CREATED_AT,
    )
    svm = emit_ml_detections(
        events,
        {event_id: 0.73},
        detector_name="ctu13_phase3_linear_svm",
        detector_version="1.0.0",
        model_name="linear_svm",
        feature_version="1.2.0",
        threshold=0.2,
        created_at=CREATED_AT,
    )

    assert "model:random_forest" in forest[0].triggered_rules
    assert "model:linear_svm" in svm[0].triggered_rules
    assert forest[0].detection_id != svm[0].detection_id

    bundles = [
        build_evidence_bundle(
            aggregate_findings(records, events, created_at=CREATED_AT)[0],
            records,
            events,
            created_at=CREATED_AT,
        )
        for records in (forest, svm)
    ]
    assert bundles[0].score_references[0].model_name == "random_forest"
    assert bundles[1].score_references[0].model_name == "linear_svm"
    assert bundles[0].feature_versions == ("1.1.0",)
    assert bundles[1].feature_versions == ("1.2.0",)
    assert bundles[0].evidence_bundle_id != bundles[1].evidence_bundle_id


def test_ml_emits_nothing_below_threshold() -> None:
    events = (_event(src_ip="10.0.0.1", offset_seconds=0),)
    assert _detections(events, score=0.19, threshold=0.2) == ()


def test_severity_bands_and_bounds() -> None:
    assert severity_for_score(0.95) is DetectionSeverity.CRITICAL
    assert severity_for_score(0.80) is DetectionSeverity.HIGH
    assert severity_for_score(0.60) is DetectionSeverity.MEDIUM
    assert severity_for_score(0.30) is DetectionSeverity.LOW
    assert severity_for_score(0.10) is DetectionSeverity.INFORMATIONAL
    with pytest.raises(ValueError, match=r"score must be within \[0, 1\]"):
        severity_for_score(1.5)


def test_claim_verification_enforces_the_taxonomy() -> None:
    statement = "host 10.0.0.1 raised three alerts in five minutes"
    uncited = Claim(
        claim_id=claim_id_for(claim_type="observed_fact", statement=statement),
        claim_type=ClaimType.OBSERVED_FACT,
        statement=statement,
        created_at=CREATED_AT,
    )
    result = verify_claim(uncited)
    assert result.verified is False
    assert result.effective_type is ClaimType.UNKNOWN_INSUFFICIENT_EVIDENCE

    unsupported_inference = Claim(
        claim_id=claim_id_for(claim_type="model_inference", statement="the host is compromised"),
        claim_type=ClaimType.MODEL_INFERENCE,
        statement="the host is compromised",
        evidence_references=(EvidenceReference(kind="event", reference="event:1"),),
        created_at=CREATED_AT,
    )
    assert verify_claim(unsupported_inference).verified is False

    supported_inference = unsupported_inference.model_copy(
        update={
            "evidence_references": (
                EvidenceReference(kind="model_score", reference="detection:1"),
            )
        }
    )
    verified = verify_claim(supported_inference)
    assert verified.verified is True
    assert verified.effective_type is ClaimType.MODEL_INFERENCE

    abstention = Claim(
        claim_id=claim_id_for(
            claim_type="unknown_insufficient_evidence", statement="cannot decide"
        ),
        claim_type=ClaimType.UNKNOWN_INSUFFICIENT_EVIDENCE,
        statement="cannot decide",
        created_at=CREATED_AT,
    )
    assert verify_claim(abstention).verified is True

    uncited_reference = Claim(
        claim_id=claim_id_for(claim_type="reference_backed_fact", statement="CVE-2024-0001"),
        claim_type=ClaimType.REFERENCE_BACKED_FACT,
        statement="CVE-2024-0001",
        evidence_references=(EvidenceReference(kind="event", reference="event:1"),),
        created_at=CREATED_AT,
    )
    assert verify_claim(uncited_reference).verified is False


EvidenceKind = Literal[
    "event", "detection", "model_score", "feature_version", "external", "repository"
]


def _claim(claim_type: ClaimType, *kinds: EvidenceKind) -> Claim:
    """Build a cited claim of one category from its evidence kinds."""

    statement = f"a {claim_type.value} claim"
    return Claim(
        claim_id=claim_id_for(claim_type=claim_type.value, statement=statement),
        claim_type=claim_type,
        statement=statement,
        evidence_references=tuple(
            EvidenceReference(kind=kind, reference=f"{kind}:1") for kind in kinds
        ),
        created_at=CREATED_AT,
    )


def test_observed_and_deterministic_claims_require_observational_evidence() -> None:
    """Issue #15: the two weakest evidence tiers must not carry the strongest categories."""

    unsupported_observation = verify_claim(_claim(ClaimType.OBSERVED_FACT, "model_score"))
    assert unsupported_observation.verified is False
    assert unsupported_observation.effective_type is ClaimType.UNKNOWN_INSUFFICIENT_EVIDENCE

    unsupported_derivation = verify_claim(
        _claim(ClaimType.DETERMINISTIC_DERIVATION, "model_score")
    )
    assert unsupported_derivation.verified is False
    assert unsupported_derivation.effective_type is ClaimType.UNKNOWN_INSUFFICIENT_EVIDENCE

    observed = verify_claim(_claim(ClaimType.OBSERVED_FACT, "event"))
    assert observed.verified is True
    assert observed.effective_type is ClaimType.OBSERVED_FACT

    derived = verify_claim(_claim(ClaimType.DETERMINISTIC_DERIVATION, "detection"))
    assert derived.verified is True
    assert derived.effective_type is ClaimType.DETERMINISTIC_DERIVATION

    observed_with_score = verify_claim(
        _claim(ClaimType.OBSERVED_FACT, "event", "model_score")
    )
    assert observed_with_score.verified is True
    assert observed_with_score.effective_type is ClaimType.OBSERVED_FACT

    interpretation = verify_claim(_claim(ClaimType.AI_INTERPRETATION, "model_score"))
    assert interpretation.verified is True
    assert interpretation.effective_type is ClaimType.AI_INTERPRETATION

    abstention = verify_claim(_claim(ClaimType.UNKNOWN_INSUFFICIENT_EVIDENCE))
    assert abstention.verified is True
    assert abstention.effective_type is ClaimType.UNKNOWN_INSUFFICIENT_EVIDENCE

    inference = verify_claim(_claim(ClaimType.MODEL_INFERENCE, "model_score"))
    assert inference.verified is True
    assert inference.effective_type is ClaimType.MODEL_INFERENCE

    reference_backed = verify_claim(_claim(ClaimType.REFERENCE_BACKED_FACT, "model_score"))
    assert reference_backed.verified is False
    assert reference_backed.effective_type is ClaimType.UNKNOWN_INSUFFICIENT_EVIDENCE


def test_evidence_bundle_states_its_own_missing_context() -> None:
    events = (_event(src_ip="10.0.0.1", offset_seconds=0),)
    detections = _detections(events)
    finding = aggregate_findings(detections, events, created_at=CREATED_AT)[0]
    bundle = build_evidence_bundle(finding, detections, events, created_at=CREATED_AT)

    assert bundle.missing_context
    assert bundle.limitations
    assert any("label" in item for item in bundle.missing_context)

    with pytest.raises(ValueError, match="no matching detections"):
        build_evidence_bundle(finding, (), events, created_at=CREATED_AT)
