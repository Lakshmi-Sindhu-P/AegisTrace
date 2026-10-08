"""Pin what ``left`` and ``right`` mean in a stored :class:`TriageComparison`.

The comparison engine re-orders the two assessments by role so that a comparison is identical
whichever way the pair is passed in. That is deliberate and load-bearing: it is what makes the
escalation rate reproducible rather than dependent on call-site style.

The cost of that choice is that the fields ``left_only_evidence_ids`` and
``right_only_evidence_ids`` do **not** describe the arguments named ``left`` and ``right``. These
tests exist so the convention cannot drift silently in either direction: if someone later makes the
fields track argument order, or makes the identity order-dependent, one of these fails.

See issue #33.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from aegistrace.detection.evidence import build_evidence_bundle
from aegistrace.detection.findings import aggregate_findings
from aegistrace.detection.ml import emit_ml_detections
from aegistrace.ingestion.ctu13 import parse_ctu13_binetflow
from aegistrace.schemas.findings import EvidenceBundle
from aegistrace.schemas.triage import (
    AssessorRole,
    ProviderMetadata,
    RawResponseReference,
    TriageComparison,
)
from aegistrace.triage.agreement import compare_assessments
from aegistrace.triage.assessment import build_assessment

CREATED_AT = datetime(2026, 10, 9, 12, 0, tzinfo=UTC)
FIXTURE = Path("data/fixtures/ctu13/scenario_11.binetflow")
PROVIDER = ProviderMetadata(
    provider="test-provider",
    model="test-model",
    model_version="1.0.0",
    prompt_version="1.0.0",
)
RAW = RawResponseReference(reference="raw://attempt.json", digest="a" * 64, structured=True)


def _bundle() -> EvidenceBundle:
    parsed = parse_ctu13_binetflow(
        FIXTURE,
        ingested_at=CREATED_AT,
        scenario_id="11",
        raw_reference=FIXTURE.as_posix(),
        report_generated_at=CREATED_AT,
    )
    events = tuple(parsed.events)
    detections = emit_ml_detections(
        events,
        {event.event_id: 0.95 for event in events},
        detector_name="ctu13_phase3_random_forest",
        detector_version="1.0.0",
        model_name="random_forest",
        feature_version="1.1.0",
        threshold=0.2,
        created_at=CREATED_AT,
    )
    finding = aggregate_findings(detections, events, created_at=CREATED_AT)[0]
    return build_evidence_bundle(finding, detections, events, created_at=CREATED_AT)


def _assess(bundle: EvidenceBundle, role: AssessorRole, cites: list[str]):
    return build_assessment(
        role=role,
        bundle=bundle,
        provider_metadata=PROVIDER,
        raw_response=RAW,
        created_at=CREATED_AT,
        payload={
            "category": "suspicious",
            "severity": "medium",
            "summary": "three flows from one host within twenty seconds",
            "evidence_summary": "one finding covering three events",
            "confidence_statement": "moderate; the grouping is deterministic but not proof",
            "cited_evidence_ids": cites,
            "uncertainties": ["no payload inspection was possible"],
            "unsupported_claim_flags": [],
            "next_step": "route the finding to human review",
        },
    )


def _pair() -> tuple[object, object, str, str]:
    bundle = _bundle()
    analyst_cite = str(bundle.finding_id)
    adjudicator_cite = str(bundle.detection_ids[0])
    analyst = _assess(bundle, AssessorRole.TRIAGE_ANALYST, [analyst_cite])
    adjudicator = _assess(bundle, AssessorRole.EXPERT_ADJUDICATOR, [adjudicator_cite])
    return analyst, adjudicator, analyst_cite, adjudicator_cite


def test_left_means_the_canonical_first_role_not_the_left_argument() -> None:
    """Passing the adjudicator as ``left`` still fills ``left_only`` from the ANALYST."""

    analyst, adjudicator, analyst_cite, adjudicator_cite = _pair()

    forward = compare_assessments(analyst, adjudicator, created_at=CREATED_AT)
    reversed_ = compare_assessments(adjudicator, analyst, created_at=CREATED_AT)

    # The convention: roles are always canonical, and left/right follow roles.
    assert forward.roles == (AssessorRole.TRIAGE_ANALYST, AssessorRole.EXPERT_ADJUDICATOR)
    assert reversed_.roles == forward.roles

    assert forward.left_only_evidence_ids == (analyst_cite,)
    assert forward.right_only_evidence_ids == (adjudicator_cite,)

    # Even when the adjudicator IS the ``left`` argument, ``left_only`` is the analyst's.
    assert reversed_.left_only_evidence_ids == (analyst_cite,)
    assert reversed_.right_only_evidence_ids == (adjudicator_cite,)


def test_comparison_identity_is_independent_of_argument_order() -> None:
    """The whole point of the canonical ordering: one comparison per pair, however passed."""

    analyst, adjudicator, _, _ = _pair()

    forward = compare_assessments(analyst, adjudicator, created_at=CREATED_AT)
    reversed_ = compare_assessments(adjudicator, analyst, created_at=CREATED_AT)

    assert forward.comparison_id == reversed_.comparison_id


def test_agreement_score_is_symmetric_under_argument_order() -> None:
    """The preregistered primary metric must not depend on call-site style."""

    analyst, adjudicator, _, _ = _pair()

    forward = compare_assessments(analyst, adjudicator, created_at=CREATED_AT)
    reversed_ = compare_assessments(adjudicator, analyst, created_at=CREATED_AT)

    assert forward.agreement_score == reversed_.agreement_score
    assert forward.agreement == reversed_.agreement


def test_roles_and_left_right_are_consistent_with_each_other() -> None:
    """``roles`` is the mapping a reader needs to interpret left/right; it must agree."""

    analyst, adjudicator, analyst_cite, adjudicator_cite = _pair()
    comparison = compare_assessments(analyst, adjudicator, created_at=CREATED_AT)

    assert comparison.roles[0] is AssessorRole.TRIAGE_ANALYST
    assert comparison.roles[1] is AssessorRole.EXPERT_ADJUDICATOR
    # left_only belongs to roles[0], right_only to roles[1]
    assert set(comparison.left_only_evidence_ids).isdisjoint(comparison.right_only_evidence_ids)
    assert set(comparison.left_only_evidence_ids) == {analyst_cite}
    assert set(comparison.right_only_evidence_ids) == {adjudicator_cite}


def test_the_convention_is_documented_on_the_schema() -> None:
    """A reader must be able to learn the convention from the schema alone (issue #33)."""

    doc = TriageComparison.__doc__ or ""
    assert "roles[0]" in doc
    assert "left" in doc and "right" in doc

    for name in ("left_only_evidence_ids", "right_only_evidence_ids"):
        description = TriageComparison.model_fields[name].description or ""
        assert "roles[" in description
