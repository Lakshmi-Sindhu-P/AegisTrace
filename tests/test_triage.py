"""Tests for the LLM triage layer: input isolation, assessment admission, and adjudication.

The properties defended here are the ones the research claim depends on: an assessor cannot see
anything but the evidence bundle, an uncited response cannot become a valid assessment, and the
comparison is deterministic and never picks a winner.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from pydantic import BaseModel, ValidationError

from aegistrace.detection.evidence import build_evidence_bundle
from aegistrace.detection.findings import aggregate_findings
from aegistrace.detection.ml import emit_ml_detections
from aegistrace.schemas.events import (
    Ctu13FlowDetails,
    EventProvenance,
    SecurityEvent,
    SourceRecordRef,
    SourceType,
    event_id_for,
)
from aegistrace.schemas.findings import EvidenceBundle
from aegistrace.schemas.triage import (
    AssessorRole,
    DisagreementReason,
    FailedAssessment,
    ProviderMetadata,
    RawResponseReference,
    TriageAssessment,
    TriageCategory,
    TriageComparison,
)
from aegistrace.triage import (
    SNAPSHOT_FIELDS,
    build_assessment,
    compare_assessments,
    input_snapshot,
    snapshot_digest,
)

BASE = datetime(2026, 10, 8, 12, 0, tzinfo=UTC)
CREATED_AT = datetime(2026, 10, 8, 13, 0, tzinfo=UTC)
DIGEST = "a" * 64

PROVIDER = ProviderMetadata(
    provider="test-provider",
    model="test-model",
    model_version="1.0.0",
    prompt_version="1.0.0",
)
RAW = RawResponseReference(reference="raw://attempt.json", digest=DIGEST, structured=True)


def _event(offset_seconds: float, src_ip: str) -> SecurityEvent:
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
            dst_ip="198.51.100.9",
            dst_port=80,
            protocol="tcp",
            source_label="flow=Background",
        ),
    )


def _bundle(src_ip: str = "10.0.0.1") -> EvidenceBundle:
    events = tuple(_event(offset, src_ip) for offset in (0.0, 10.0, 20.0))
    scores = {event.event_id: 0.95 for event in events}
    detections = emit_ml_detections(
        events,
        scores,
        detector_name="ctu13_phase3_random_forest",
        detector_version="1.0.0",
        model_name="random_forest",
        feature_version="1.1.0",
        threshold=0.2,
        created_at=CREATED_AT,
    )
    finding = aggregate_findings(detections, events, created_at=CREATED_AT)[0]
    return build_evidence_bundle(finding, detections, events, created_at=CREATED_AT)


def _payload(bundle: EvidenceBundle, **overrides: object) -> dict:
    payload: dict = {
        "category": "suspicious",
        "severity": "medium",
        "summary": "three flows from one host within twenty seconds",
        "evidence_summary": "one finding covering three events",
        "confidence_statement": "moderate; the grouping is deterministic but not proof",
        "cited_evidence_ids": [str(bundle.finding_id)],
        "uncertainties": ["no payload inspection was possible"],
        "unsupported_claim_flags": [],
        "next_step": "route the finding to human review",
    }
    payload.update(overrides)
    return payload


def _assess(bundle: EvidenceBundle, role: AssessorRole, **overrides: object):
    return build_assessment(
        role=role,
        bundle=bundle,
        payload=_payload(bundle, **overrides),
        provider_metadata=PROVIDER,
        raw_response=RAW,
        created_at=CREATED_AT,
    )


def _dump(record: BaseModel) -> str:
    return json.dumps(record.model_dump(mode="json"), sort_keys=True)


def test_snapshot_admits_nothing_beyond_the_evidence_bundle() -> None:
    bundle = _bundle()
    snapshot = input_snapshot(bundle)

    assert set(snapshot) == set(EvidenceBundle.model_fields)
    assert frozenset(EvidenceBundle.model_fields) == SNAPSHOT_FIELDS
    assert json.dumps(snapshot, sort_keys=True)
    assert snapshot_digest(bundle) == snapshot_digest(bundle)
    assert len(snapshot_digest(bundle)) == 64


def test_uncited_payload_is_preserved_as_a_failed_attempt() -> None:
    outcome = _assess(_bundle(), AssessorRole.TRIAGE_ANALYST, cited_evidence_ids=[])

    assert isinstance(outcome, FailedAssessment)
    assert any("cites no evidence" in reason for reason in outcome.failure_reasons)


def test_citing_evidence_outside_the_bundle_is_a_failed_attempt() -> None:
    outcome = _assess(
        _bundle(), AssessorRole.TRIAGE_ANALYST, cited_evidence_ids=["not-in-this-bundle"]
    )

    assert isinstance(outcome, FailedAssessment)
    assert any("not present in the bundle" in reason for reason in outcome.failure_reasons)
    assert any("not-in-this-bundle" in reason for reason in outcome.failure_reasons)


def test_malformed_payload_collects_every_reason() -> None:
    bundle = _bundle()
    outcome = build_assessment(
        role=AssessorRole.TRIAGE_ANALYST,
        bundle=bundle,
        payload={"category": "nonsense", "severity": "nonsense", "cited_evidence_ids": []},
        provider_metadata=PROVIDER,
        raw_response=RAW,
        created_at=CREATED_AT,
    )

    assert isinstance(outcome, FailedAssessment)
    # Four missing text fields, one unknown category, one unknown severity, one citation failure.
    assert len(outcome.failure_reasons) == 7

    not_an_object = build_assessment(
        role=AssessorRole.TRIAGE_ANALYST,
        bundle=bundle,
        payload="this is not a structured object",
        provider_metadata=PROVIDER,
        raw_response=RAW,
        created_at=CREATED_AT,
    )
    assert isinstance(not_an_object, FailedAssessment)
    assert not_an_object.failure_reasons == ("response is not a structured object",)


def test_insufficient_evidence_is_admissible_end_to_end() -> None:
    outcome = _assess(_bundle(), AssessorRole.TRIAGE_ANALYST, category="insufficient_evidence")

    assert isinstance(outcome, TriageAssessment)
    assert outcome.category is TriageCategory.INSUFFICIENT_EVIDENCE
    assert outcome.cited_evidence_ids
    assert outcome.review_status.value == "pending_review"


def test_full_agreement_produces_no_disagreement() -> None:
    bundle = _bundle()
    analyst = _assess(bundle, AssessorRole.TRIAGE_ANALYST)
    adjudicator = _assess(bundle, AssessorRole.EXPERT_ADJUDICATOR)

    comparison = compare_assessments(analyst, adjudicator, created_at=CREATED_AT)

    assert comparison.agreement is True
    assert comparison.disagreement_reasons == ()
    assert comparison.escalation_recommended is False
    assert comparison.agreement_score == 1.0
    assert len(comparison.raw_output_references) == 2
    assert comparison.validator_results == (
        "triage_analyst: admissible",
        "expert_adjudicator: admissible",
    )


def test_comparison_is_order_independent() -> None:
    bundle = _bundle()
    analyst = _assess(bundle, AssessorRole.TRIAGE_ANALYST)
    adjudicator = _assess(bundle, AssessorRole.EXPERT_ADJUDICATOR, category="likely_benign")

    forward = compare_assessments(analyst, adjudicator, created_at=CREATED_AT)
    backward = compare_assessments(adjudicator, analyst, created_at=CREATED_AT)

    assert _dump(forward) == _dump(backward)


def test_category_disagreement_is_recorded_and_escalated() -> None:
    bundle = _bundle()
    analyst = _assess(bundle, AssessorRole.TRIAGE_ANALYST, category="likely_malicious")
    adjudicator = _assess(bundle, AssessorRole.EXPERT_ADJUDICATOR, category="likely_benign")

    comparison = compare_assessments(analyst, adjudicator, created_at=CREATED_AT)

    assert comparison.agreement is False
    assert DisagreementReason.CATEGORY_MISMATCH in comparison.disagreement_reasons
    assert comparison.escalation_recommended is True


def test_one_side_insufficient_evidence_is_called_out() -> None:
    bundle = _bundle()
    analyst = _assess(bundle, AssessorRole.TRIAGE_ANALYST, category="insufficient_evidence")
    adjudicator = _assess(bundle, AssessorRole.EXPERT_ADJUDICATOR, category="suspicious")

    comparison = compare_assessments(analyst, adjudicator, created_at=CREATED_AT)

    assert DisagreementReason.ONE_SIDE_INSUFFICIENT_EVIDENCE in comparison.disagreement_reasons


def test_evidence_divergence_lowers_the_agreement_score() -> None:
    bundle = _bundle()
    event_id = next(str(summary.event_id) for summary in bundle.event_summaries)
    analyst = _assess(
        bundle, AssessorRole.TRIAGE_ANALYST, cited_evidence_ids=[str(bundle.finding_id)]
    )
    adjudicator = _assess(bundle, AssessorRole.EXPERT_ADJUDICATOR, cited_evidence_ids=[event_id])

    comparison = compare_assessments(analyst, adjudicator, created_at=CREATED_AT)

    assert DisagreementReason.EVIDENCE_DIVERGENCE in comparison.disagreement_reasons
    assert comparison.agreement_score == 0.0
    assert comparison.left_only_evidence_ids
    assert comparison.right_only_evidence_ids
    assert comparison.shared_evidence_ids == ()


def test_a_failed_side_forces_zero_score_and_escalation() -> None:
    bundle = _bundle()
    good = _assess(bundle, AssessorRole.TRIAGE_ANALYST)
    bad = _assess(bundle, AssessorRole.EXPERT_ADJUDICATOR, cited_evidence_ids=[])
    assert isinstance(bad, FailedAssessment)

    comparison = compare_assessments(good, bad, created_at=CREATED_AT)

    assert comparison.agreement is False
    assert comparison.agreement_score == 0.0
    assert DisagreementReason.FAILED_ASSESSMENT in comparison.disagreement_reasons
    assert comparison.escalation_recommended is True
    assert any("failed attempt" in result for result in comparison.validator_results)


def test_comparing_assessments_of_different_bundles_is_rejected() -> None:
    first = _assess(_bundle("10.0.0.1"), AssessorRole.TRIAGE_ANALYST)
    second = _assess(_bundle("10.0.0.2"), AssessorRole.EXPERT_ADJUDICATOR)

    with pytest.raises(ValueError, match="different evidence bundles"):
        compare_assessments(first, second, created_at=CREATED_AT)


def test_comparison_rejects_agreement_carrying_disagreement_reasons() -> None:
    with pytest.raises(ValidationError, match="cannot carry disagreement reasons"):
        TriageComparison(
            comparison_id=uuid4(),
            evidence_bundle_id=uuid4(),
            assessment_ids=(uuid4(),),
            agreement=True,
            disagreement_reasons=(DisagreementReason.CATEGORY_MISMATCH,),
            agreement_score=1.0,
            escalation_recommended=False,
            created_at=CREATED_AT,
        )
