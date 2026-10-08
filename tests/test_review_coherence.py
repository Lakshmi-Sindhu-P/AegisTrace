"""Tests for the HumanReview governance invariants added for issue #30.

Two relationships must hold on every review:
  1. A review's decision and escalation state must be coherent: ESCALATE is the only decision that
     may carry a non-NONE escalation state, and an ESCALATE decision must be backed by a concrete
     escalation state.
  2. ``review_id`` must match ``review_id_for(...)`` computed from the record's own fields, so the
     append-only chain and deduplication rest on a value that is verified, not assumed.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from aegistrace.schemas.review import (
    EscalationState,
    HumanReview,
    ReviewDecision,
    ReviewTier,
    review_id_for,
)
from aegistrace.schemas.triage import AssessorRole

REVIEWED_AT = datetime(2026, 10, 8, 14, 0, tzinfo=UTC)
SUBJECT_ID = uuid4()
REVIEWER = "coherence-test"
OTHER_SUBJECT = uuid4()
OTHER_REVIEWER = "some-other-reviewer"


def _review_id(**overrides: object) -> object:
    payload: dict = {
        "subject_triage_id": SUBJECT_ID,
        "subject_role": AssessorRole.EXPERT_ADJUDICATOR,
        "reviewer_ref": REVIEWER,
        "decision": ReviewDecision.CONFIRM,
        "final_disposition": "no action taken; this is a research record",
        "supersedes_review_id": None,
    }
    payload.update(overrides)
    return review_id_for(
        subject_triage_id=payload["subject_triage_id"],
        subject_role=payload["subject_role"],
        reviewer_ref=payload["reviewer_ref"],
        decision=payload["decision"],
        final_disposition=payload["final_disposition"],
        supersedes_review_id=payload["supersedes_review_id"],
    )


def _review(**overrides: object) -> dict:
    payload: dict = {
        "subject_triage_id": SUBJECT_ID,
        "subject_role": AssessorRole.EXPERT_ADJUDICATOR,
        "reviewer_ref": REVIEWER,
        "tier": ReviewTier.C_EXPERT_JUDGMENT,
        "decision": ReviewDecision.CONFIRM,
        "notes": "reviewed against the cited evidence",
        "reviewed_at": REVIEWED_AT,
        "escalation_state": EscalationState.NONE,
        "final_disposition": "no action taken; this is a research record",
    }
    payload.update(overrides)
    # Derived from the FINAL payload: every identity-bearing field may be overridden, and an id
    # computed before the overrides would not match the record it is supposed to name. An explicit
    # `review_id` override is preserved, because several tests deliberately supply a wrong one.
    if "review_id" in overrides:
        return payload
    payload["review_id"] = review_id_for(
        subject_triage_id=payload["subject_triage_id"],
        subject_role=payload["subject_role"],
        reviewer_ref=payload["reviewer_ref"],
        decision=payload["decision"],
        final_disposition=payload["final_disposition"],
        supersedes_review_id=payload.get("supersedes_review_id"),
    )
    return payload


def test_escalate_with_none_state_is_refused() -> None:
    payload = _review(decision=ReviewDecision.ESCALATE, escalation_state=EscalationState.NONE)

    with pytest.raises(ValidationError, match="escalating review must carry a non-NONE"):
        HumanReview(**payload)


def test_non_none_state_without_escalate_is_refused() -> None:
    payload = _review(decision=ReviewDecision.CONFIRM, escalation_state=EscalationState.PENDING)

    with pytest.raises(ValidationError, match="non-NONE escalation state requires an escalate"):
        HumanReview(**payload)


def test_random_review_id_is_refused() -> None:
    payload = _review(review_id=uuid4())

    with pytest.raises(ValidationError, match="does not match the expected"):
        HumanReview(**payload)


def test_review_id_from_different_subject_is_refused() -> None:
    payload = _review(review_id=_review_id(subject_triage_id=OTHER_SUBJECT))

    with pytest.raises(ValidationError, match="does not match the expected"):
        HumanReview(**payload)


def test_review_id_from_different_reviewer_is_refused() -> None:
    payload = _review(review_id=_review_id(reviewer_ref=OTHER_REVIEWER))

    with pytest.raises(ValidationError, match="does not match the expected"):
        HumanReview(**payload)


def test_review_id_from_different_decision_is_refused() -> None:
    payload = _review(review_id=_review_id(decision=ReviewDecision.DISMISS))

    with pytest.raises(ValidationError, match="does not match the expected"):
        HumanReview(**payload)


def test_fully_coherent_review_is_accepted() -> None:
    review = HumanReview(**_review())

    assert review.review_id == review_id_for(
        subject_triage_id=review.subject_triage_id,
        subject_role=review.subject_role,
        reviewer_ref=review.reviewer_ref,
        decision=review.decision,
        final_disposition=review.final_disposition,
        supersedes_review_id=review.supersedes_review_id,
    )


def test_coherent_escalate_is_accepted() -> None:
    payload = _review(decision=ReviewDecision.ESCALATE, escalation_state=EscalationState.ESCALATED)

    review = HumanReview(**payload)

    assert review.decision is ReviewDecision.ESCALATE
    assert review.escalation_state is EscalationState.ESCALATED


def test_revise_still_requires_supersedes_review_id() -> None:
    payload = _review(decision=ReviewDecision.REVISE)

    with pytest.raises(ValidationError, match="must reference the review it supersedes"):
        HumanReview(**payload)