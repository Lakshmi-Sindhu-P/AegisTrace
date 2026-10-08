"""Deterministic tier assignment and Tier A machine checks.

Tier assignment decides how much scarce human expertise a case consumes, so it must not be a
judgement call. It is computed from the assessment and comparison records alone, using no research
label and no model opinion: disagreement escalates, abstention is recorded as such, and only
evidence mechanics are treated as machine-checkable.

The checks are deliberately about *mechanics*, not about whether an assessment is correct. A
machine can prove that a citation resolves, that both assessors saw identical input, and that a
bundle states its own gaps. It cannot prove that a conclusion is right, which is why a failing check
can push a case *up* a tier but a passing check can never push a case *down* one.
"""

from __future__ import annotations

from aegistrace.schemas.findings import EvidenceBundle
from aegistrace.schemas.review import MachineCheck, ReviewTier, TierAssignment
from aegistrace.schemas.triage import (
    DisagreementReason,
    TriageAssessment,
    TriageCategory,
    TriageComparison,
)
from aegistrace.triage.assessment import AssessmentOutcome
from aegistrace.triage.snapshot import bundle_evidence_ids


def machine_checks(
    bundle: EvidenceBundle, assessments: tuple[AssessmentOutcome, ...]
) -> tuple[MachineCheck, ...]:
    """Run the deterministic evidence-mechanics checks that constitute Tier A."""

    allowed = bundle_evidence_ids(bundle)
    admissible = [item for item in assessments if isinstance(item, TriageAssessment)]

    snapshot_digests = {item.input_snapshot_digest for item in admissible}

    unresolved = sorted(
        {
            str(cited)
            for assessment in admissible
            for cited in assessment.cited_evidence_ids
            if str(cited) not in allowed
        }
    )
    checks = [
        MachineCheck(
            check_name="all_assessments_admissible",
            passed=bool(assessments) and len(admissible) == len(assessments),
            detail=(
                "zero assessments were supplied, so admissibility cannot be confirmed"
                if not assessments
                else f"{len(admissible)} of {len(assessments)} assessments were admissible"
            ),
        ),
        MachineCheck(
            check_name="citations_resolve_to_bundle_evidence",
            passed=bool(admissible) and not unresolved,
            detail=(
                "no citations were available to resolve; zero admissible assessments were supplied"
                if not admissible
                else "every cited identifier resolves to evidence in the bundle"
                if not unresolved
                else f"unresolved citations: {', '.join(unresolved)}"
            ),
        ),
        MachineCheck(
            check_name="assessors_saw_identical_input",
            passed=bool(admissible) and len(snapshot_digests) <= 1,
            detail=(
                "no admissible assessments were compared; identical input cannot be confirmed"
                if not admissible
                else "all admissible assessments share one input snapshot digest"
            ),
        ),
        MachineCheck(
            check_name="bundle_states_its_own_gaps",
            passed=bool(bundle.missing_context and bundle.limitations),
            detail="the evidence bundle records both missing context and limitations",
        ),
    ]
    return tuple(checks)


def classify_tier(
    *,
    bundle: EvidenceBundle,
    comparison: TriageComparison,
    assessments: tuple[AssessmentOutcome, ...],
) -> TierAssignment:
    """Assign the lowest tier that is genuinely qualified to decide this subject."""

    checks = machine_checks(bundle, assessments)
    admissible = [item for item in assessments if isinstance(item, TriageAssessment)]
    reasons: list[str] = []

    abstained = bool(admissible) and all(
        item.category is TriageCategory.INSUFFICIENT_EVIDENCE for item in admissible
    )

    if abstained:
        tier = ReviewTier.D_INSUFFICIENT_EVIDENCE
        reasons.append("every admissible assessment abstained; there is no conclusion to confirm")
    elif not admissible:
        # Issue #13: with no admissible assessment there is no conclusion to confirm, so this is
        # Tier D on the same ground as mutual abstention.
        tier = ReviewTier.D_INSUFFICIENT_EVIDENCE
        reasons.append("no admissible assessment exists; there is no conclusion to confirm")
    elif len(admissible) == 1:
        # Issue #13 design choice, not a derivation: a single unconfirmed opinion needs expertise,
        # not a signature, so one admissible assessment cannot qualify for the cheapest tier.
        tier = ReviewTier.C_EXPERT_JUDGMENT
        reasons.append("only one admissible assessment exists; it is unconfirmed by a second role")
    elif DisagreementReason.FAILED_ASSESSMENT in comparison.disagreement_reasons:
        tier = ReviewTier.C_EXPERT_JUDGMENT
        reasons.append("an assessor failed, so any conclusion rests on incomplete input")
    elif comparison.disagreement_reasons:
        tier = ReviewTier.C_EXPERT_JUDGMENT
        joined = ", ".join(reason.value for reason in comparison.disagreement_reasons)
        reasons.append(
            f"independent assessors disagreed ({joined}); resolving that needs expertise"
        )
    else:
        flagged = any(item.unsupported_claim_flags or item.uncertainties for item in admissible)
        if flagged:
            tier = ReviewTier.B_GUIDED_JUNIOR
            reasons.append("assessors agreed but flagged uncertainty or unsupported claims")
        else:
            tier = ReviewTier.A_MACHINE_CHECK
            reasons.append("assessors agreed without flags; only evidence mechanics need checking")

    failed_checks = [check.check_name for check in checks if not check.passed]
    if failed_checks:
        reasons.append(f"failed machine checks: {', '.join(failed_checks)}")
        if tier is ReviewTier.A_MACHINE_CHECK:
            tier = ReviewTier.B_GUIDED_JUNIOR

    return TierAssignment(tier=tier, reasons=tuple(reasons), machine_checks=checks)


__all__ = ["classify_tier", "machine_checks"]
