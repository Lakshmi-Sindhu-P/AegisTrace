"""The append-only guarantee must hold on every construction path, not only in `append_review`.

`review/history.py` has always enforced that a correction may only supersede the most recent review
and that identifiers are unique. But the module docstring's guarantee - "a linear chain in which the
last entry is unambiguously current" - was only true for histories built through that helper.

The path that reads durable records is `ReviewHistory.model_validate(...)` from stored JSON, and it
bypassed the helper entirely. A history whose links dangled or forked loaded without complaint and
presented a broken lineage as authoritative.

These tests pin the guarantee at the schema, where every path goes through it.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from aegistrace.review.history import append_review, new_history
from aegistrace.schemas.review import (
    EscalationState,
    HumanReview,
    ReviewDecision,
    ReviewHistory,
    ReviewTier,
    review_id_for,
)
from aegistrace.schemas.triage import AssessorRole

SUBJECT = uuid4()
REVIEWED_AT = datetime(2026, 10, 9, 12, 0, tzinfo=UTC)


def _review(
    *,
    reviewer: str = "r1",
    decision: ReviewDecision = ReviewDecision.CONFIRM,
    supersedes=None,
) -> HumanReview:
    """Build a valid review; identity derived so the coherence check is satisfied."""

    return HumanReview(
        review_id=review_id_for(
            subject_triage_id=SUBJECT,
            subject_role=AssessorRole.TRIAGE_ANALYST,
            reviewer_ref=reviewer,
            decision=decision,
            final_disposition="disposition",
            supersedes_review_id=supersedes,
        ),
        subject_triage_id=SUBJECT,
        subject_role=AssessorRole.TRIAGE_ANALYST,
        reviewer_ref=reviewer,
        tier=ReviewTier.A_MACHINE_CHECK,
        decision=decision,
        notes="note",
        reviewed_at=REVIEWED_AT,
        escalation_state=EscalationState.NONE,
        final_disposition="disposition",
        supersedes_review_id=supersedes,
    )


def _history(*reviews: HumanReview) -> ReviewHistory:
    return ReviewHistory(subject_triage_id=SUBJECT, reviews=reviews)


@pytest.fixture
def first() -> HumanReview:
    return _review(reviewer="r1")


@pytest.fixture
def second(first: HumanReview) -> HumanReview:
    return _review(reviewer="r2", decision=ReviewDecision.REVISE, supersedes=first.review_id)


def test_a_valid_chain_is_still_accepted(first: HumanReview, second: HumanReview) -> None:
    """The control. Tightening must not reject histories the helper can build."""

    history = _history(first, second)
    assert [r.review_id for r in history.reviews] == [first.review_id, second.review_id]
    assert history.reviews[-1].review_id == second.review_id

    # An empty history is the legal starting point.
    assert _history().reviews == ()

    # And a three-link chain is fine.
    third = _review(reviewer="r3", decision=ReviewDecision.DISMISS, supersedes=second.review_id)
    assert len(_history(first, second, third).reviews) == 3


def test_a_supersede_link_may_not_dangle() -> None:
    """The link must resolve inside this history, or the chain is not a chain.

    This also covers the first-entry case: a first review with a supersede link has nothing in the
    history to point at, and the schema reports the same violation for both.
    """

    with pytest.raises(ValueError, match="cannot supersede anything"):
        _history(_review(supersedes=uuid4()))


def test_a_later_review_must_supersede_the_most_recent(
    first: HumanReview, second: HumanReview
) -> None:
    """Skipping the latest entry forks the lineage, so 'current' stops being unambiguous."""

    fork = _review(reviewer="r3", decision=ReviewDecision.DISMISS, supersedes=first.review_id)
    with pytest.raises(ValueError, match="may only supersede the most recent review"):
        _history(first, second, fork)


def test_a_later_review_must_supersede_something(
    first: HumanReview, second: HumanReview
) -> None:
    """A second review with no link is an unexplained second opinion, not a correction."""

    independent = _review(reviewer="r3", decision=ReviewDecision.DISMISS)
    with pytest.raises(ValueError, match="must supersede the most recent review"):
        _history(first, independent)


def test_duplicate_identifiers_are_rejected(first: HumanReview) -> None:
    with pytest.raises(ValueError, match="identity is already recorded"):
        _history(first, first)


def test_the_guarantee_holds_on_the_json_load_path(
    first: HumanReview, second: HumanReview
) -> None:
    """This is the path that mattered: durable records are read, not rebuilt through the helper."""

    payload = json.loads(_history(first, second).model_dump_json())
    reloaded = ReviewHistory.model_validate(payload)
    assert reloaded.reviews[-1].review_id == second.review_id

    # Forge a forked chain in the stored bytes and confirm the load now refuses it.
    fork = _review(reviewer="r3", decision=ReviewDecision.DISMISS, supersedes=first.review_id)
    payload["reviews"].append(json.loads(fork.model_dump_json()))
    with pytest.raises(ValueError, match="may only supersede the most recent review"):
        ReviewHistory.model_validate(payload)


def test_the_helper_and_the_schema_agree(
    first: HumanReview, second: HumanReview
) -> None:
    """`append_review`'s manual checks are now defence in depth, not the only guarantee.

    Every rule the helper enforces must also be enforced by the schema, so that removing the helper
    cannot silently reopen the gap. This test drives the helper's own rejections and asserts the
    schema rejects the same shape.
    """

    history = append_review(new_history(SUBJECT), first)
    history = append_review(history, second)
    assert len(history.reviews) == 2

    # The helper's "may only supersede the most recent review" case.
    fork = _review(reviewer="r3", decision=ReviewDecision.DISMISS, supersedes=first.review_id)
    with pytest.raises(ValueError, match="may only supersede the most recent review"):
        append_review(history, fork)
    with pytest.raises(ValueError, match="may only supersede the most recent review"):
        _history(first, second, fork)

    # The helper's duplicate case.
    with pytest.raises(ValueError, match="identity is already recorded"):
        append_review(history, first)
    with pytest.raises(ValueError, match="identity is already recorded"):
        _history(first, first)
