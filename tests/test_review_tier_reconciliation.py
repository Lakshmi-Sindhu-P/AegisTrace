"""Issue #30: a conducted review must be reconciled with the tier its assignment required.

Today a ``HumanReview`` carries a ``tier`` but nothing ever compares it to the
``TierAssignment.tier`` for the same subject, so a case that *required* expert judgment but was
only machine-checked is silently accepted. The reconciliation lives on the schema - on
:class:`TierReconciliation` - not in a helper, so it runs on every construction path including the
``model_validate`` read path that durable records take.

The ``satisfies`` relationship is an explicit, non-ordinal map (:data:`_REQUIREMENT_SATISFIED_BY`),
exposed here through ``tier_satisfies_requirement``. ``D_INSUFFICIENT_EVIDENCE`` is its own case,
never "more than" C.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from aegistrace.schemas.review import (
    EscalationState,
    HumanReview,
    ReviewDecision,
    ReviewHistory,
    ReviewTier,
    TierAssignment,
    TierReconciliation,
    review_id_for,
    tier_satisfies_requirement,
)
from aegistrace.schemas.triage import AssessorRole

REVIEWED_AT = datetime(2026, 10, 9, 12, 0, tzinfo=UTC)
SUBJECT = uuid4()

#: (conducted, required) pairs that MUST satisfy, and pairs that MUST NOT.
SATISFIES_TRUE: list[tuple[ReviewTier, ReviewTier]] = [
    (ReviewTier.A_MACHINE_CHECK, ReviewTier.A_MACHINE_CHECK),
    (ReviewTier.B_GUIDED_JUNIOR, ReviewTier.A_MACHINE_CHECK),
    (ReviewTier.C_EXPERT_JUDGMENT, ReviewTier.A_MACHINE_CHECK),
    (ReviewTier.B_GUIDED_JUNIOR, ReviewTier.B_GUIDED_JUNIOR),
    (ReviewTier.C_EXPERT_JUDGMENT, ReviewTier.B_GUIDED_JUNIOR),
    (ReviewTier.C_EXPERT_JUDGMENT, ReviewTier.C_EXPERT_JUDGMENT),
    (ReviewTier.D_INSUFFICIENT_EVIDENCE, ReviewTier.D_INSUFFICIENT_EVIDENCE),
]

#: Conducted D must never satisfy an A/B/C requirement (D is a different kind of outcome, not a
#: higher tier); a D requirement is satisfied only by a D-conducted review.
SATISFIES_FALSE: list[tuple[ReviewTier, ReviewTier]] = [
    (ReviewTier.A_MACHINE_CHECK, ReviewTier.B_GUIDED_JUNIOR),
    (ReviewTier.A_MACHINE_CHECK, ReviewTier.C_EXPERT_JUDGMENT),
    (ReviewTier.B_GUIDED_JUNIOR, ReviewTier.C_EXPERT_JUDGMENT),
    (ReviewTier.D_INSUFFICIENT_EVIDENCE, ReviewTier.A_MACHINE_CHECK),
    (ReviewTier.D_INSUFFICIENT_EVIDENCE, ReviewTier.B_GUIDED_JUNIOR),
    (ReviewTier.D_INSUFFICIENT_EVIDENCE, ReviewTier.C_EXPERT_JUDGMENT),
    (ReviewTier.A_MACHINE_CHECK, ReviewTier.D_INSUFFICIENT_EVIDENCE),
    (ReviewTier.B_GUIDED_JUNIOR, ReviewTier.D_INSUFFICIENT_EVIDENCE),
    (ReviewTier.C_EXPERT_JUDGMENT, ReviewTier.D_INSUFFICIENT_EVIDENCE),
]


@pytest.mark.parametrize("conducted,required", SATISFIES_TRUE)
def test_conducted_tier_satisfies_required(conducted: ReviewTier, required: ReviewTier) -> None:
    """The explicit map - which conducted tiers meet which requirement - accepts the true pairs."""

    assert tier_satisfies_requirement(conducted=conducted, required=required) is True


@pytest.mark.parametrize("conducted,required", SATISFIES_FALSE)
def test_conducted_tier_does_not_satisfy_required(
    conducted: ReviewTier, required: ReviewTier
) -> None:
    """The explicit map refuses the false pairs, pinning D as its own non-ordinal case."""

    assert tier_satisfies_requirement(conducted=conducted, required=required) is False


def _review(tier: ReviewTier, *, subject: object = None) -> HumanReview:
    subject_id = SUBJECT if subject is None else subject
    return HumanReview(
        review_id=review_id_for(
            subject_triage_id=subject_id,
            subject_role=AssessorRole.TRIAGE_ANALYST,
            reviewer_ref="reconciler",
            decision=ReviewDecision.CONFIRM,
            final_disposition="disposition",
        ),
        subject_triage_id=subject_id,
        subject_role=AssessorRole.TRIAGE_ANALYST,
        reviewer_ref="reconciler",
        tier=tier,
        decision=ReviewDecision.CONFIRM,
        notes="note",
        reviewed_at=REVIEWED_AT,
        escalation_state=EscalationState.NONE,
        final_disposition="disposition",
    )


def _assignment(required: ReviewTier) -> TierAssignment:
    return TierAssignment(tier=required, reasons=("because the analysis requires it",))


# (a) a review that MEETS the requirement ----------------------------------------------


def test_reconciliation_records_a_met_requirement() -> None:
    assignment = _assignment(ReviewTier.C_EXPERT_JUDGMENT)
    review = _review(ReviewTier.C_EXPERT_JUDGMENT)

    reconciliation = TierReconciliation(
        subject_triage_id=SUBJECT,
        assignment=assignment,
        review=review,
    )

    assert reconciliation.requirement_met is True
    assert reconciliation.unmet_requirement is None
    # The conducted tier must match the review's own tier and the required tier the assignment.
    assert reconciliation.review.tier is ReviewTier.C_EXPERT_JUDGMENT
    assert reconciliation.assignment.tier is ReviewTier.C_EXPERT_JUDGMENT


# (b) a review that does NOT meet, and how that is represented -------------------------


def test_reconciliation_records_an_unmet_requirement() -> None:
    # A case that required EXPERT judgment was only machine-checked: the issue #30 hazard.
    assignment = _assignment(ReviewTier.C_EXPERT_JUDGMENT)
    review = _review(ReviewTier.A_MACHINE_CHECK)

    reconciliation = TierReconciliation(
        subject_triage_id=SUBJECT,
        assignment=assignment,
        review=review,
    )

    # Not a crash: the discrepancy is a recorded, inspectable, immutable fact.
    assert reconciliation.requirement_met is False
    assert reconciliation.unmet_requirement is not None
    assert "required a review at tier tier_c_expert_judgment" in reconciliation.unmet_requirement
    assert "conducted at tier tier_a_machine_check" in reconciliation.unmet_requirement


def test_unmet_requirement_survives_json_round_trip() -> None:
    assignment = _assignment(ReviewTier.C_EXPERT_JUDGMENT)
    review = _review(ReviewTier.A_MACHINE_CHECK)
    reconciliation = TierReconciliation(
        subject_triage_id=SUBJECT, assignment=assignment, review=review
    )

    reloaded = TierReconciliation.model_validate(
        json.loads(reconciliation.model_dump_json())
    )

    assert reloaded.requirement_met is False
    assert reloaded.unmet_requirement is not None
    assert "was not met" in reloaded.unmet_requirement


# (c) the D case specifically ----------------------------------------------------------


def test_d_conducted_review_never_satisfies_an_a_b_c_requirement() -> None:
    for required in (
        ReviewTier.A_MACHINE_CHECK,
        ReviewTier.B_GUIDED_JUNIOR,
        ReviewTier.C_EXPERT_JUDGMENT,
    ):
        assignment = _assignment(required)
        review = _review(ReviewTier.D_INSUFFICIENT_EVIDENCE)

        reconciliation = TierReconciliation(
            subject_triage_id=SUBJECT, assignment=assignment, review=review
        )

        assert reconciliation.requirement_met is False
        assert reconciliation.unmet_requirement is not None


def test_d_requirement_is_met_only_by_a_d_conducted_review() -> None:
    met = _review(ReviewTier.D_INSUFFICIENT_EVIDENCE)
    reconciliation = TierReconciliation(
        subject_triage_id=SUBJECT,
        assignment=_assignment(ReviewTier.D_INSUFFICIENT_EVIDENCE),
        review=met,
    )
    assert reconciliation.requirement_met is True
    assert reconciliation.unmet_requirement is None

    # A staged A/B/C review cannot claim to meet a D requirement (no conclusion to confirm).
    staged_tiers = (
        ReviewTier.A_MACHINE_CHECK,
        ReviewTier.B_GUIDED_JUNIOR,
        ReviewTier.C_EXPERT_JUDGMENT,
    )
    for staged in staged_tiers:
        reconciliation = TierReconciliation(
            subject_triage_id=SUBJECT,
            assignment=_assignment(ReviewTier.D_INSUFFICIENT_EVIDENCE),
            review=_review(staged),
        )
        assert reconciliation.requirement_met is False


# (d) the JSON load path - the rule must not be bypassable -----------------------------


def test_json_load_path_refuses_a_flipped_requirement_met() -> None:
    """A forged stored record claiming success must be refused, not trusted.

    A rule that only lived in a helper would be bypassed here: ``model_validate`` reads the
    serialized payload verbatim. The schema validator recomputes ``requirement_met`` and refuses a
    claim that contradicts the authoritative tiers.
    """

    assignment = _assignment(ReviewTier.C_EXPERT_JUDGMENT)
    review = _review(ReviewTier.A_MACHINE_CHECK)
    reconciliation = TierReconciliation(
        subject_triage_id=SUBJECT, assignment=assignment, review=review
    )
    assert reconciliation.requirement_met is False

    payload = json.loads(reconciliation.model_dump_json())

    # Forge success in the stored bytes - the load path must not accept the lie.
    payload["requirement_met"] = True
    payload["unmet_requirement"] = None
    with pytest.raises(ValidationError, match="requirement_met"):
        TierReconciliation.model_validate(payload)


def test_json_load_path_refuses_a_flipped_unmet_review_on_met_case() -> None:
    """Same guard the other way: a met case cannot be stored as unmet either."""

    reconciliation = TierReconciliation(
        subject_triage_id=SUBJECT,
        assignment=_assignment(ReviewTier.C_EXPERT_JUDGMENT),
        review=_review(ReviewTier.C_EXPERT_JUDGMENT),
    )
    assert reconciliation.requirement_met is True

    payload = json.loads(reconciliation.model_dump_json())
    payload["requirement_met"] = False
    payload["unmet_requirement"] = "this requirement was definitely not met"
    with pytest.raises(ValidationError, match="requirement_met"):
        TierReconciliation.model_validate(payload)


def test_subject_mismatch_between_assignment_and_review_is_rejected() -> None:
    other = uuid4()

    with pytest.raises(ValidationError, match="must belong to the reconciliation's subject"):
        TierReconciliation(
            subject_triage_id=SUBJECT,
            assignment=_assignment(ReviewTier.A_MACHINE_CHECK),
            review=_review(ReviewTier.A_MACHINE_CHECK, subject=other),
        )


# (e) a repeated / duplicate decision still behaves correctly --------------------------


def test_duplicate_review_still_reconciles_identically() -> None:
    assignment = _assignment(ReviewTier.B_GUIDED_JUNIOR)
    review = _review(ReviewTier.B_GUIDED_JUNIOR)

    first = TierReconciliation(subject_triage_id=SUBJECT, assignment=assignment, review=review)
    second = TierReconciliation(subject_triage_id=SUBJECT, assignment=assignment, review=review)

    # Idempotent and deterministic: reconciling the identical decision twice yields the same result.
    assert first == second
    assert first.requirement_met is True
    assert second.requirement_met is True


def test_repeated_review_history_does_not_change_reconciliation() -> None:
    """The reconciliation is independent of history ordering: same decision, same verdict."""

    assignment = _assignment(ReviewTier.A_MACHINE_CHECK)
    review = _review(ReviewTier.A_MACHINE_CHECK)

    reconciliation = TierReconciliation(
        subject_triage_id=SUBJECT, assignment=assignment, review=review
    )
    history = ReviewHistory(subject_triage_id=SUBJECT, reviews=(review,))

    assert reconciliation.requirement_met is True
    assert history.reviews[0].tier is review.tier

    # Reconciliation recomputes from the review object itself; a history that repeats the review
    # does not alter what is recorded about the requirement.
    again = TierReconciliation(
        subject_triage_id=SUBJECT, assignment=assignment, review=history.reviews[0]
    )
    assert again == reconciliation