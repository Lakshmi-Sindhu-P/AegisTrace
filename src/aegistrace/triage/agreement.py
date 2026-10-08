"""Deterministic adjudication of two independently frozen assessments.

This module is the project's sharpest claim made concrete: disagreement between two mutually blind
assessors is the escalation signal. Two design rules follow from that and are worth stating plainly.

1. **The engine is code, not a model.** It never calls a provider. Given the same two records it
   returns a byte-identical comparison, so the escalation rate is reproducible rather than sampled.
   If a third model adjudicated the first two, the experiment would measure that model, not the
   assessors.
2. **The engine never resolves a disagreement.** It records one and recommends escalation. Deciding
   which assessor is right is exactly the judgement reserved for a human reviewer, so the engine has
   no code path that picks a winner.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from aegistrace.schemas.triage import (
    AssessorRole,
    DisagreementReason,
    FailedAssessment,
    TriageAssessment,
    TriageCategory,
    TriageComparison,
    comparison_id_for,
)
from aegistrace.triage.assessment import AssessmentOutcome

_CANONICAL_ROLE_ORDER: dict[AssessorRole, int] = {
    AssessorRole.TRIAGE_ANALYST: 0,
    AssessorRole.EXPERT_ADJUDICATOR: 1,
}


def _identifier(item: AssessmentOutcome) -> str:
    return str(item.triage_id) if isinstance(item, TriageAssessment) else str(item.attempt_id)


def _sort_key(item: AssessmentOutcome) -> tuple[int, str]:
    """Order the pair canonically so comparison is independent of argument order."""

    return (_CANONICAL_ROLE_ORDER.get(item.role, len(_CANONICAL_ROLE_ORDER)), _identifier(item))


def _cited(item: AssessmentOutcome) -> frozenset[str]:
    if isinstance(item, TriageAssessment):
        return frozenset(item.cited_evidence_ids)
    return frozenset()


def _validator_result(item: AssessmentOutcome) -> str:
    if isinstance(item, TriageAssessment):
        return f"{item.role.value}: admissible"
    return f"{item.role.value}: failed attempt ({'; '.join(item.failure_reasons)})"


def _agreement_score(left: frozenset[str], right: frozenset[str]) -> float:
    """Jaccard overlap of cited evidence, defined as 0.0 when nothing is cited."""

    union = left | right
    if not union:
        return 0.0
    return len(left & right) / len(union)


def compare_assessments(
    left: AssessmentOutcome, right: AssessmentOutcome, *, created_at: datetime
) -> TriageComparison:
    """Compare two independent assessments of the same bundle and record any disagreement."""

    if left.evidence_bundle_id != right.evidence_bundle_id:
        raise ValueError("cannot compare assessments of different evidence bundles")
    if _identifier(left) == _identifier(right):
        raise ValueError(
            "cannot compare an assessment with itself: both identifiers are identical, which "
            "means the same assessment was passed twice rather than two independent assessors"
        )
    if left.role is right.role:
        raise ValueError(
            f"cannot compare two assessments that share role {left.role.value!r}; independence "
            "requires one assessment per role, so one assessor answering twice under two labels "
            "is not an independent comparison"
        )

    ordered = sorted((left, right), key=_sort_key)
    first, second = ordered

    failed = isinstance(first, FailedAssessment) or isinstance(second, FailedAssessment)
    reasons: set[DisagreementReason] = set()
    if failed:
        reasons.add(DisagreementReason.FAILED_ASSESSMENT)
    else:
        assert isinstance(first, TriageAssessment) and isinstance(second, TriageAssessment)
        if first.category is not second.category:
            reasons.add(DisagreementReason.CATEGORY_MISMATCH)
        if first.severity is not second.severity:
            reasons.add(DisagreementReason.SEVERITY_MISMATCH)
        first_insufficient = first.category is TriageCategory.INSUFFICIENT_EVIDENCE
        second_insufficient = second.category is TriageCategory.INSUFFICIENT_EVIDENCE
        if first_insufficient != second_insufficient:
            reasons.add(DisagreementReason.ONE_SIDE_INSUFFICIENT_EVIDENCE)

    first_cited, second_cited = _cited(first), _cited(second)
    if not failed and first_cited != second_cited:
        reasons.add(DisagreementReason.EVIDENCE_DIVERGENCE)

    score = 0.0 if failed else _agreement_score(first_cited, second_cited)

    ordered_reasons = tuple(sorted(reasons, key=lambda reason: reason.value))
    return TriageComparison(
        comparison_id=comparison_id_for(
            evidence_bundle_id=first.evidence_bundle_id,
            assessment_ids=(first_id := _as_uuid(first), _as_uuid(second)),
        ),
        evidence_bundle_id=first.evidence_bundle_id,
        assessment_ids=(first_id, _as_uuid(second)),
        roles=(first.role, second.role),
        agreement=not ordered_reasons,
        agreement_score=score,
        disagreement_reasons=ordered_reasons,
        shared_evidence_ids=tuple(sorted(first_cited & second_cited)),
        left_only_evidence_ids=tuple(sorted(first_cited - second_cited)),
        right_only_evidence_ids=tuple(sorted(second_cited - first_cited)),
        escalation_recommended=bool(ordered_reasons),
        raw_output_references=(first.raw_response, second.raw_response),
        validator_results=(_validator_result(first), _validator_result(second)),
        created_at=created_at,
    )


def _as_uuid(item: AssessmentOutcome) -> UUID:
    return item.triage_id if isinstance(item, TriageAssessment) else item.attempt_id


__all__ = ["compare_assessments"]
