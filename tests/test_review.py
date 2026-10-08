"""Tests for deterministic tier assignment and the append-only review history.

Tier assignment decides how much human expertise a case consumes, so it is asserted to be a pure
function of the assessment records: disagreement escalates, abstention is recorded, and a failing
machine check can raise a tier but never lower one.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from aegistrace.detection.evidence import build_evidence_bundle
from aegistrace.detection.findings import aggregate_findings
from aegistrace.detection.ml import emit_ml_detections
from aegistrace.review import (
    append_review,
    classify_tier,
    current_review,
    machine_checks,
    new_history,
)
from aegistrace.schemas.events import (
    Ctu13FlowDetails,
    EventProvenance,
    SecurityEvent,
    SourceRecordRef,
    SourceType,
    event_id_for,
)
from aegistrace.schemas.findings import EvidenceBundle
from aegistrace.schemas.review import (
    EscalationState,
    HumanReview,
    ReviewDecision,
    ReviewTier,
    review_id_for,
)
from aegistrace.schemas.triage import (
    AssessorRole,
    ProviderMetadata,
    RawResponseReference,
    TriageAssessment,
)
from aegistrace.triage import build_assessment, compare_assessments

BASE = datetime(2026, 10, 8, 12, 0, tzinfo=UTC)
CREATED_AT = datetime(2026, 10, 8, 13, 0, tzinfo=UTC)
REVIEWED_AT = datetime(2026, 10, 8, 14, 0, tzinfo=UTC)
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


def _assess(bundle: EvidenceBundle, role: AssessorRole, **overrides: object):
    payload: dict = {
        "category": "suspicious",
        "severity": "medium",
        "summary": "three flows from one host within twenty seconds",
        "evidence_summary": "one finding covering three events",
        "confidence_statement": "moderate; the grouping is deterministic but not proof",
        "cited_evidence_ids": [str(bundle.finding_id)],
        "uncertainties": [],
        "unsupported_claim_flags": [],
        "next_step": "route the finding to human review",
    }
    payload.update(overrides)
    return build_assessment(
        role=role,
        bundle=bundle,
        payload=payload,
        provider_metadata=PROVIDER,
        raw_response=RAW,
        created_at=CREATED_AT,
    )


def _agreed(bundle: EvidenceBundle, **overrides: object):
    analyst = _assess(bundle, AssessorRole.TRIAGE_ANALYST, **overrides)
    adjudicator = _assess(bundle, AssessorRole.EXPERT_ADJUDICATOR, **overrides)
    comparison = compare_assessments(analyst, adjudicator, created_at=CREATED_AT)
    return comparison, (analyst, adjudicator)


def test_machine_checks_verify_evidence_mechanics() -> None:
    bundle = _bundle()
    comparison, assessments = _agreed(bundle)

    checks = machine_checks(bundle, assessments)

    assert [check.check_name for check in checks] == [
        "all_assessments_admissible",
        "citations_resolve_to_bundle_evidence",
        "assessors_saw_identical_input",
        "bundle_states_its_own_gaps",
    ]
    assert all(check.passed for check in checks)
    assert comparison.agreement is True


def test_clean_agreement_is_tier_a() -> None:
    bundle = _bundle()
    comparison, assessments = _agreed(bundle)

    assignment = classify_tier(bundle=bundle, comparison=comparison, assessments=assessments)

    assert assignment.tier is ReviewTier.A_MACHINE_CHECK
    assert assignment.reasons


def test_flagged_uncertainty_is_tier_b() -> None:
    bundle = _bundle()
    comparison, assessments = _agreed(bundle, uncertainties=["no payload inspection was possible"])

    assignment = classify_tier(bundle=bundle, comparison=comparison, assessments=assessments)

    assert comparison.agreement is True
    assert assignment.tier is ReviewTier.B_GUIDED_JUNIOR


def test_unsupported_claim_flags_are_tier_b() -> None:
    bundle = _bundle()
    comparison, assessments = _agreed(bundle, unsupported_claim_flags=["asserts exfiltration"])

    assignment = classify_tier(bundle=bundle, comparison=comparison, assessments=assessments)

    assert assignment.tier is ReviewTier.B_GUIDED_JUNIOR


def test_disagreement_is_tier_c() -> None:
    bundle = _bundle()
    analyst = _assess(bundle, AssessorRole.TRIAGE_ANALYST, category="likely_malicious")
    adjudicator = _assess(bundle, AssessorRole.EXPERT_ADJUDICATOR, category="likely_benign")
    comparison = compare_assessments(analyst, adjudicator, created_at=CREATED_AT)

    assignment = classify_tier(
        bundle=bundle, comparison=comparison, assessments=(analyst, adjudicator)
    )

    assert assignment.tier is ReviewTier.C_EXPERT_JUDGMENT


def test_failed_assessor_is_tier_c() -> None:
    bundle = _bundle()
    good = _assess(bundle, AssessorRole.TRIAGE_ANALYST)
    bad = _assess(bundle, AssessorRole.EXPERT_ADJUDICATOR, cited_evidence_ids=[])
    comparison = compare_assessments(good, bad, created_at=CREATED_AT)

    assignment = classify_tier(bundle=bundle, comparison=comparison, assessments=(good, bad))

    assert assignment.tier is ReviewTier.C_EXPERT_JUDGMENT
    assert not all(check.passed for check in assignment.machine_checks)


def test_mutual_abstention_is_tier_d() -> None:
    bundle = _bundle()
    comparison, assessments = _agreed(bundle, category="insufficient_evidence")

    assignment = classify_tier(bundle=bundle, comparison=comparison, assessments=assessments)

    assert assignment.tier is ReviewTier.D_INSUFFICIENT_EVIDENCE


def test_a_failing_machine_check_raises_a_tier_but_never_lowers_one() -> None:
    bundle = _bundle()
    comparison, (analyst, adjudicator) = _agreed(bundle)

    forged = analyst.model_copy(update={"cited_evidence_ids": ("ghost-evidence",)})
    assert isinstance(forged, TriageAssessment)

    assignment = classify_tier(
        bundle=bundle, comparison=comparison, assessments=(forged, adjudicator)
    )

    assert assignment.tier is not ReviewTier.A_MACHINE_CHECK
    assert assignment.tier is ReviewTier.B_GUIDED_JUNIOR
    assert any("failed machine checks" in reason for reason in assignment.reasons)
    assert any(
        "ghost-evidence" in check.detail
        for check in assignment.machine_checks
        if check.check_name == "citations_resolve_to_bundle_evidence"
    )


def test_zero_assessments_cannot_reach_tier_a() -> None:
    bundle = _bundle()
    comparison, _ = _agreed(bundle)

    assignment = classify_tier(bundle=bundle, comparison=comparison, assessments=())

    assert assignment.tier is ReviewTier.D_INSUFFICIENT_EVIDENCE
    assert assignment.tier is not ReviewTier.A_MACHINE_CHECK
    assert assignment.reasons


def test_one_assessment_cannot_reach_tier_a() -> None:
    bundle = _bundle()
    comparison, (analyst, _) = _agreed(bundle)

    assignment = classify_tier(bundle=bundle, comparison=comparison, assessments=(analyst,))

    assert assignment.tier is ReviewTier.C_EXPERT_JUDGMENT
    assert assignment.tier is not ReviewTier.A_MACHINE_CHECK


def test_two_agreeing_assessments_still_reach_tier_a() -> None:
    bundle = _bundle()
    comparison, assessments = _agreed(bundle)

    assignment = classify_tier(bundle=bundle, comparison=comparison, assessments=assessments)

    assert comparison.agreement is True
    assert assignment.tier is ReviewTier.A_MACHINE_CHECK


def test_all_assessments_admissible_fails_for_an_empty_set() -> None:
    bundle = _bundle()

    checks = machine_checks(bundle, ())

    # Assert the exact expected outcome of every check, so a future check cannot pass vacuously
    # on an empty assessment set without this test failing.
    assert {check.check_name: check.passed for check in checks} == {
        "all_assessments_admissible": False,
        "citations_resolve_to_bundle_evidence": False,
        "assessors_saw_identical_input": False,
        "bundle_states_its_own_gaps": True,
    }
    details = {check.check_name: check.detail for check in checks}
    assert "zero" in details["all_assessments_admissible"]
    assert "no citations were available to resolve" in details[
        "citations_resolve_to_bundle_evidence"
    ]
    assert "no admissible assessments were compared" in details["assessors_saw_identical_input"]


def test_two_assessment_case_passes_every_machine_check() -> None:
    bundle = _bundle()
    comparison, assessments = _agreed(bundle)

    checks = machine_checks(bundle, assessments)

    assert comparison.agreement is True
    assert {check.check_name: check.passed for check in checks} == {
        "all_assessments_admissible": True,
        "citations_resolve_to_bundle_evidence": True,
        "assessors_saw_identical_input": True,
        "bundle_states_its_own_gaps": True,
    }


def test_a_failing_machine_check_cannot_lower_a_filled_gap_tier() -> None:
    bundle = _bundle()
    comparison, (analyst, _) = _agreed(bundle)
    forged = analyst.model_copy(update={"cited_evidence_ids": ("ghost-evidence",)})
    assert isinstance(forged, TriageAssessment)

    one = classify_tier(bundle=bundle, comparison=comparison, assessments=(forged,))
    none = classify_tier(bundle=bundle, comparison=comparison, assessments=())

    assert one.tier is ReviewTier.C_EXPERT_JUDGMENT
    assert none.tier is ReviewTier.D_INSUFFICIENT_EVIDENCE
    assert any(not item.passed for item in one.machine_checks)
    assert any(not item.passed for item in none.machine_checks)


def _review(
    subject_id,
    reviewer: str,
    decision: ReviewDecision,
    minutes: int,
    supersedes=None,
) -> HumanReview:
    reviewed_at = REVIEWED_AT + timedelta(minutes=minutes)
    return HumanReview(
        review_id=review_id_for(
            subject_triage_id=subject_id,
            subject_role=AssessorRole.EXPERT_ADJUDICATOR,
            reviewer_ref=reviewer,
            decision=decision,
            final_disposition="no action taken; this is a research record",
            supersedes_review_id=supersedes,
        ),
        subject_triage_id=subject_id,
        subject_role=AssessorRole.EXPERT_ADJUDICATOR,
        reviewer_ref=reviewer,
        tier=ReviewTier.C_EXPERT_JUDGMENT,
        decision=decision,
        notes="reviewed against the cited evidence",
        reviewed_at=reviewed_at,
        escalation_state=EscalationState.NONE,
        final_disposition="no action taken; this is a research record",
        supersedes_review_id=supersedes,
    )


def test_history_appends_without_overwriting() -> None:
    subject = _assess(_bundle(), AssessorRole.EXPERT_ADJUDICATOR).triage_id
    history = new_history(subject)
    assert current_review(history) is None

    first = _review(subject, "analyst-a", ReviewDecision.CONFIRM, 0)
    history = append_review(history, first)

    second = _review(subject, "analyst-b", ReviewDecision.REVISE, 10, supersedes=first.review_id)
    history = append_review(history, second)

    assert len(history.reviews) == 2
    assert history.reviews[0] == first
    assert current_review(history) == second


def test_history_requires_corrections_to_supersede_the_latest() -> None:
    subject = _assess(_bundle(), AssessorRole.EXPERT_ADJUDICATOR).triage_id
    first = _review(subject, "analyst-a", ReviewDecision.CONFIRM, 0)
    history = append_review(new_history(subject), first)

    unsuperseded = _review(subject, "analyst-b", ReviewDecision.CONFIRM, 10)
    with pytest.raises(ValueError, match="must supersede the most recent review"):
        append_review(history, unsuperseded)

    second = _review(subject, "analyst-b", ReviewDecision.REVISE, 10, supersedes=first.review_id)
    advanced = append_review(history, second)

    stale = _review(subject, "analyst-c", ReviewDecision.REVISE, 20, supersedes=first.review_id)
    with pytest.raises(ValueError, match="most recent review"):
        append_review(advanced, stale)


def test_history_rejects_duplicates_foreign_subjects_and_orphan_supersessions() -> None:
    subject = _assess(_bundle(), AssessorRole.EXPERT_ADJUDICATOR).triage_id
    first = _review(subject, "analyst-a", ReviewDecision.CONFIRM, 0)
    history = append_review(new_history(subject), first)

    with pytest.raises(ValueError, match="already recorded"):
        append_review(history, first)

    orphan = _review(subject, "analyst-b", ReviewDecision.REVISE, 10, supersedes=first.review_id)
    with pytest.raises(ValueError, match="cannot supersede anything"):
        append_review(new_history(subject), orphan)

    other = _assess(_bundle("10.0.0.7"), AssessorRole.EXPERT_ADJUDICATOR).triage_id
    with pytest.raises(ValueError, match="does not match the history subject"):
        append_review(history, _review(other, "analyst-b", ReviewDecision.CONFIRM, 10))


def test_a_revising_review_must_reference_what_it_supersedes() -> None:
    subject = _assess(_bundle(), AssessorRole.EXPERT_ADJUDICATOR).triage_id

    with pytest.raises(ValidationError, match="must reference the review it supersedes"):
        _review(subject, "analyst-a", ReviewDecision.REVISE, 0)
