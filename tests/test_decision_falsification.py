"""Falsification suite for AegisTrace decision guards.

Every guard is executed against the input it exists to refuse, because a guard never observed
failing is an untested claim. A passing guard here has actually rejected its own worst case; where a
guard instead accepts that input, the test fails with an explicit ``# FINDING:`` comment rather than
weakening the input to make the suite green.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest

from aegistrace.detection.evidence import build_evidence_bundle
from aegistrace.detection.findings import aggregate_findings
from aegistrace.detection.ml import emit_ml_detections
from aegistrace.features.behavioral import audit_prior_window_causality
from aegistrace.features.causal import audit_causal_prior_window
from aegistrace.review.history import append_review, new_history
from aegistrace.review.tiers import classify_tier, machine_checks
from aegistrace.schemas.events import (
    Ctu13FlowDetails,
    EventProvenance,
    SecurityEvent,
    SourceRecordRef,
    SourceType,
    event_id_for,
)
from aegistrace.schemas.findings import (
    Claim,
    ClaimType,
    EvidenceBundle,
    EvidenceReference,
)
from aegistrace.schemas.review import (
    EscalationState,
    HumanReview,
    ReviewDecision,
    ReviewTier,
    review_id_for,
)
from aegistrace.schemas.triage import (
    AssessorRole,
    DisagreementReason,
    FailedAssessment,
    ProviderMetadata,
    RawResponseReference,
)
from aegistrace.spine import _assert_history_open, run_spine
from aegistrace.triage import build_assessment, compare_assessments
from aegistrace.triage.provider import (
    ProviderDescriptor,
    ProviderKind,
    StubTriageProvider,
)
from aegistrace.triage.run import (
    _independence_determination,
    assert_assessors_independent,
    assert_provider_permitted,
)
from aegistrace.verification.claims import verify_claim

REPO_ROOT = Path(__file__).resolve().parents[1]
FREEZE = json.loads(
    (REPO_ROOT / "configs" / "triage_provider_freeze.json").read_text(encoding="utf-8")
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


def _agreed(bundle: EvidenceBundle):
    analyst = _assess(bundle, AssessorRole.TRIAGE_ANALYST)
    adjudicator = _assess(bundle, AssessorRole.EXPERT_ADJUDICATOR)
    comparison = compare_assessments(analyst, adjudicator, created_at=CREATED_AT)
    return comparison, (analyst, adjudicator)


def _remote(name: str, model_id: str = "remote-model-v1", family: str = "remote-family"):
    return ProviderDescriptor(
        name=name,
        model_id=model_id,
        model_family=family,
        kind=ProviderKind.REMOTE,
        requires_egress=True,
    )


def _offline(name: str, model_id: str):
    return ProviderDescriptor(
        name=name,
        model_id=model_id,
        model_family="offline stub, not a model",
        kind=ProviderKind.OFFLINE_STUB,
        requires_egress=False,
    )


def _guard_refuses(analyst: ProviderDescriptor, adjudicator: ProviderDescriptor) -> bool:
    try:
        assert_assessors_independent(analyst, adjudicator)
    except ValueError:
        return True
    return False


# --- Guard 1: review tiers ---------------------------------------------------------------------


def test_tier_a_refused_with_zero_assessments() -> None:
    bundle = _bundle()
    comparison, _ = _agreed(bundle)

    assignment = classify_tier(bundle=bundle, comparison=comparison, assessments=())

    assert assignment.tier is not ReviewTier.A_MACHINE_CHECK
    # The machine checks must also refuse to pass vacuously on an empty assessment set.
    vacuous = {check.check_name for check in machine_checks(bundle, ()) if check.passed}
    assert "all_assessments_admissible" not in vacuous
    assert "citations_resolve_to_bundle_evidence" not in vacuous


def test_tier_a_refused_when_only_one_assessment() -> None:
    bundle = _bundle()
    comparison, (analyst, _) = _agreed(bundle)

    assignment = classify_tier(bundle=bundle, comparison=comparison, assessments=(analyst,))

    assert assignment.tier is not ReviewTier.A_MACHINE_CHECK


def test_tier_a_refused_when_one_assessment_cites_nothing() -> None:
    bundle = _bundle()
    analyst = _assess(bundle, AssessorRole.TRIAGE_ANALYST)
    uncited = _assess(bundle, AssessorRole.EXPERT_ADJUDICATOR, cited_evidence_ids=[])
    assert isinstance(uncited, FailedAssessment)

    comparison = compare_assessments(analyst, uncited, created_at=CREATED_AT)
    assignment = classify_tier(bundle=bundle, comparison=comparison, assessments=(analyst, uncited))

    assert assignment.tier is not ReviewTier.A_MACHINE_CHECK


# --- Guard 2: assessor independence ------------------------------------------------------------


def test_independence_refused_for_identical_descriptors() -> None:
    descriptor = _remote("remote-assessor")

    with pytest.raises(ValueError, match="answering twice"):
        assert_assessors_independent(descriptor, descriptor)


def test_independence_refused_for_name_only_clones() -> None:
    # Worst case: the same model and family, relabelled with two names. This is one assessor
    # answering twice and must be refused just like an identical descriptor.
    analyst = _remote("analyst-label", model_id="gpt-x", family="fam-a")
    adjudicator = _remote("adjudicator-label", model_id="gpt-x", family="fam-a")

    with pytest.raises(ValueError, match="answering twice"):
        assert_assessors_independent(analyst, adjudicator)


def test_guard_and_determination_never_disagree_across_descriptor_matrix() -> None:
    # The guard and the recorded determination must be one question asked twice, not two criteria
    # that drift. This matrix pins every descriptor pairing the two roles can present.
    identical = _remote("same-name")
    matrix = {
        # name -> (analyst, adjudicator, expected guard refusal, expected establishment)
        "identical descriptors": (identical, identical, True, False),
        "name-only clone": (
            _remote("analyst-label", model_id="gpt-x", family="fam-a"),
            _remote("adjudicator-label", model_id="gpt-x", family="fam-a"),
            True,
            False,
        ),
        "same model_id, different family": (
            _remote("analyst-label", model_id="gpt-x", family="fam-a"),
            _remote("adjudicator-label", model_id="gpt-x", family="fam-b"),
            True,
            False,
        ),
        "different model_id, same family": (
            _remote("analyst-label", model_id="gpt-x", family="fam-a"),
            _remote("adjudicator-label", model_id="gpt-y", family="fam-a"),
            False,
            False,
        ),
        "genuinely different models": (
            _remote("analyst-label", model_id="gpt-x", family="fam-a"),
            _remote("adjudicator-label", model_id="claude-y", family="fam-b"),
            False,
            True,
        ),
        "offline stand-ins": (
            _offline("stub-analyst", "stub-a"),
            _offline("stub-adjudicator", "stub-b"),
            False,
            False,
        ),
        "identical offline descriptor": (
            _offline("stub-analyst", "stub-a"),
            _offline("stub-analyst", "stub-a"),
            True,
            False,
        ),
    }

    for label, (analyst, adjudicator, expect_refusal, expect_established) in matrix.items():
        established, _basis = _independence_determination(analyst, adjudicator)
        refused = _guard_refuses(analyst, adjudicator)

        # The invariant the whole fix exists to enforce: the guard can never be weaker than the
        # determination about whether independence was established.
        if refused:
            assert established is False, (
                f"{label}: guard refused what the record would call independent"
            )
        if established:
            assert refused is False, f"{label}: record claims independence the guard refuses"
        assert refused is expect_refusal, f"{label}: guard refusal changed"
        assert established is expect_established, f"{label}: establishment changed"


# --- Guard 3: egress permission -----------------------------------------------------------------


def test_remote_provider_refused_when_freeze_blocks_egress() -> None:
    descriptor = _remote("remote-assessor")

    with pytest.raises(PermissionError, match="requires network egress"):
        assert_provider_permitted(descriptor, "BLOCKED_HUMAN")


# --- Guard 4: agreement engine -----------------------------------------------------------------


def test_compare_refuses_same_identifier() -> None:
    bundle = _bundle()
    analyst = _assess(bundle, AssessorRole.TRIAGE_ANALYST)

    with pytest.raises(ValueError, match="itself"):
        compare_assessments(analyst, analyst, created_at=CREATED_AT)


def test_compare_refuses_same_role_on_both_sides() -> None:
    bundle = _bundle()
    first = _assess(bundle, AssessorRole.TRIAGE_ANALYST, summary="first reading")
    second = _assess(bundle, AssessorRole.TRIAGE_ANALYST, summary="second reading")

    with pytest.raises(ValueError, match="share role"):
        compare_assessments(first, second, created_at=CREATED_AT)


def test_compare_marks_failed_side_zero_and_escalates() -> None:
    bundle = _bundle()
    analyst = _assess(bundle, AssessorRole.TRIAGE_ANALYST)
    failed = _assess(bundle, AssessorRole.EXPERT_ADJUDICATOR, cited_evidence_ids=[])
    assert isinstance(failed, FailedAssessment)

    comparison = compare_assessments(analyst, failed, created_at=CREATED_AT)

    assert comparison.agreement is False
    assert comparison.agreement_score == 0.0
    assert DisagreementReason.FAILED_ASSESSMENT in comparison.disagreement_reasons


def test_compare_disjoint_evidence_scores_zero_and_disagrees() -> None:
    bundle = _bundle()
    event_id = next(str(summary.event_id) for summary in bundle.event_summaries)
    analyst = _assess(
        bundle, AssessorRole.TRIAGE_ANALYST, cited_evidence_ids=[str(bundle.finding_id)]
    )
    adjudicator = _assess(
        bundle, AssessorRole.EXPERT_ADJUDICATOR, cited_evidence_ids=[event_id]
    )

    comparison = compare_assessments(analyst, adjudicator, created_at=CREATED_AT)

    assert comparison.agreement_score == 0.0
    assert DisagreementReason.EVIDENCE_DIVERGENCE in comparison.disagreement_reasons
    assert comparison.escalation_recommended is True


# --- Guard 5: claim verification --------------------------------------------------------------


def _claim(claim_type: ClaimType, kind: str) -> Claim:
    return Claim(
        claim_id=uuid4(),
        claim_type=claim_type,
        statement="a statement whose only support is a model score",
        evidence_references=(EvidenceReference(kind=kind, reference="score://model/x"),),
        created_at=CREATED_AT,
    )


def test_observed_fact_refused_with_only_a_model_score() -> None:
    verification = verify_claim(_claim(ClaimType.OBSERVED_FACT, "model_score"))

    assert verification.verified is False
    assert verification.effective_type is ClaimType.UNKNOWN_INSUFFICIENT_EVIDENCE


def test_deterministic_derivation_refused_with_only_a_model_score() -> None:
    verification = verify_claim(_claim(ClaimType.DETERMINISTIC_DERIVATION, "model_score"))

    assert verification.verified is False
    assert verification.effective_type is ClaimType.UNKNOWN_INSUFFICIENT_EVIDENCE


# --- Guard 6: prior-window causality audits -----------------------------------------------------


def test_behavioral_causality_audit_refuses_empty_baseline() -> None:
    assert audit_prior_window_causality(()) is False


def test_causal_causality_audit_refuses_empty_baseline() -> None:
    assert audit_causal_prior_window(()) is False


# --- Guard 7: the spine must end unreviewed -----------------------------------------------------


def test_spine_refuses_record_with_a_review() -> None:
    def _stub(name: str, model_id: str) -> StubTriageProvider:
        return StubTriageProvider(
            ProviderDescriptor(
                name=name,
                model_id=model_id,
                model_family="offline stub, not a model",
                kind=ProviderKind.OFFLINE_STUB,
                requires_egress=False,
            ),
            CREATED_AT,
        )

    record = run_spine(
        bundles=(_bundle(),),
        analyst_provider=_stub("stub-triage-analyst", "stub-analyst-1"),
        adjudicator_provider=_stub("stub-expert-adjudicator", "stub-adjudicator-1"),
        freeze=FREEZE,
        created_at=CREATED_AT,
    )[0]

    review = HumanReview(
        review_id=review_id_for(
            subject_triage_id=record.review_history.subject_triage_id,
            subject_role=AssessorRole.TRIAGE_ANALYST,
            reviewer_ref="falsification-suite",
            decision=ReviewDecision.CONFIRM,
            final_disposition="confirmed",
        ),
        subject_triage_id=record.review_history.subject_triage_id,
        subject_role=AssessorRole.TRIAGE_ANALYST,
        reviewer_ref="falsification-suite",
        tier=ReviewTier.A_MACHINE_CHECK,
        decision=ReviewDecision.CONFIRM,
        notes="a review the spine must never carry",
        reviewed_at=CREATED_AT,
        escalation_state=EscalationState.NONE,
        final_disposition="confirmed",
    )
    closed = record.model_copy(
        update={
            "review_history": append_review(
                new_history(record.review_history.subject_triage_id), review
            )
        }
    )

    with pytest.raises(RuntimeError, match="never append a review"):
        _assert_history_open(closed)


# --- Issue 41: the removed FAILED_ASSESSMENT branch -----------------------------------------


def test_issue_41_a_failed_assessor_reaches_tier_c_without_the_dead_branch() -> None:
    """Removing the unreachable branch changed no tier, and this pins what is recorded instead.

    The deleted branch tested `FAILED_ASSESSMENT in disagreement_reasons`, but `compare_assessments`
    adds that reason only when a side is a `FailedAssessment`, and a failed assessment is never
    admissible - so `not admissible` or `len(admissible) == 1` always fired first. It could never
    change the tier, only the recorded reason, which is why its removal is behaviour-preserving.
    """

    bundle = _bundle()
    analyst = _assess(bundle, AssessorRole.TRIAGE_ANALYST)
    failed = _assess(bundle, AssessorRole.EXPERT_ADJUDICATOR, cited_evidence_ids=[])
    assert isinstance(failed, FailedAssessment), "an uncited assessment must be refused"

    comparison = compare_assessments(analyst, failed, created_at=CREATED_AT)
    assert DisagreementReason.FAILED_ASSESSMENT in comparison.disagreement_reasons

    assignment = classify_tier(
        bundle=bundle, comparison=comparison, assessments=(analyst, failed)
    )

    # The tier a failed assessor produces: expert judgement, never the cheapest tier.
    assert assignment.tier is ReviewTier.C_EXPERT_JUDGMENT
    # The reason actually recorded. The removed branch would have said "an assessor failed, so any
    # conclusion rests on incomplete input"; the surviving rule explains the same fact differently.
    assert any("only one admissible assessment exists" in reason for reason in assignment.reasons)
    assert not any("an assessor failed" in reason for reason in assignment.reasons), (
        "the unreachable branch is gone; if this fires, the reason text was reinstated "
        "deliberately and this test must be updated as a decision rather than a fix"
    )
