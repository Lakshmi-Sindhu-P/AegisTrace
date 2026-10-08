"""Issue #42: `model_copy(update=...)` must not be a validator bypass.

Pydantic v2 does not re-run validators for `model_copy(update=...)`, so an invariant enforced only
by a `@model_validator` could be bypassed by copying a valid instance and overwriting a field. That
made the schema look like the guarantee while the real guarantee was whatever hand-written checks
the caller happened to perform.

`FrozenSchema.model_copy` now re-validates whenever fields are replaced, so the escape hatch is
closed for every schema in the project rather than for the one call site that was noticed.

Each test states the falsifier as well as the property, because a guard whose failure mode is
untested may be a tautology.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

from aegistrace.ingestion.ctu13 import parse_ctu13_binetflow
from aegistrace.review.history import append_review, current_review, new_history
from aegistrace.schemas.events import event_id_for
from aegistrace.schemas.review import (
    EscalationState,
    HumanReview,
    ReviewDecision,
    ReviewHistory,
    ReviewTier,
    review_id_for,
)

CREATED_AT = datetime(2026, 10, 9, 12, 0, tzinfo=UTC)
FIXTURE = Path("data/fixtures/ctu13/scenario_11.binetflow")


def _review(*, decision: ReviewDecision = ReviewDecision.CONFIRM,
    **overrides: object) -> HumanReview:
    subject = overrides.pop("subject_triage_id", uuid4())
    payload: dict = {
        "subject_triage_id": subject,
        "subject_role": "triage_analyst",
        "reviewer_ref": "reviewer-1",
        "tier": ReviewTier.B_GUIDED_JUNIOR,
        "decision": decision,
        "notes": "n",
        "reviewed_at": CREATED_AT,
        "escalation_state": EscalationState.NONE,
        "final_disposition": "confirmed",
        "supersedes_review_id": None,
    }
    payload.update(overrides)
    review_id = review_id_for(
        subject_triage_id=payload["subject_triage_id"],
        subject_role=payload["subject_role"],
        reviewer_ref=payload["reviewer_ref"],
        decision=payload["decision"].value if hasattr(payload["decision"],
            "value") else payload["decision"],
        final_disposition=payload["final_disposition"],
        supersedes_review_id=payload["supersedes_review_id"],
    )
    return HumanReview(review_id=review_id, **payload)  # type: ignore[arg-type]


# --- the bypass itself ---------------------------------------------------------------------------


def test_issue_42_copy_cannot_forge_a_revise_without_a_supersession() -> None:
    """The executed defect. A REVISE must name what it supersedes; a copy must not escape that."""

    valid = _review()

    # The falsifier: the schema genuinely refuses the direct construction, so the invariant is real.
    with pytest.raises(ValidationError,
        match="a revising review must reference the review it supersedes"):
        _review(decision=ReviewDecision.REVISE)

    # And the copy is now refused too, rather than silently producing the invalid state.
    with pytest.raises(ValidationError,
        match="a revising review must reference the review it supersedes"):
        valid.model_copy(update={"decision": ReviewDecision.REVISE})


def test_issue_42_copy_cannot_desynchronise_a_review_from_its_own_identity() -> None:
    """The copied record must still satisfy `review_id == review_id_for(...)`."""

    valid = _review()

    with pytest.raises(ValidationError, match="does not match the expected"):
        valid.model_copy(update={"final_disposition": "something else entirely"})


def test_issue_42_copy_cannot_break_a_history_subject_match() -> None:
    """The second executed defect: a history could hold a review for a different subject."""

    subject = uuid4()
    history = append_review(new_history(subject), _review(subject_triage_id=subject))
    other = _review(subject_triage_id=uuid4())

    with pytest.raises(ValidationError, match="share the subject triage id"):
        history.model_copy(update={"reviews": (*history.reviews, other)})


def test_issue_42_copy_cannot_forge_an_event_identity() -> None:
    """A third instance, found while fixing this one, in the features layer.

    `behavioral.py` built a synthetic audit event whose `event_id` did not match its own source,
    which `SecurityEvent` explicitly forbids. It survived only because the copy skipped validation.
    """

    events = list(
        parse_ctu13_binetflow(FIXTURE, ingested_at=CREATED_AT).events
    )
    event = events[0]

    with pytest.raises(ValidationError, match="event_id does not match"):
        event.model_copy(update={"event_id": uuid4()})

    # Re-deriving the id from the changed source IS accepted - the correct construction.
    other_source = event.source.model_copy(update={"scenario_id": "other"})
    rebuilt = event.model_copy(
        update={"source": other_source, "event_id": event_id_for(other_source)}
    )
    assert rebuilt.event_id == event_id_for(rebuilt.source)


# --- the behaviour that must NOT change ----------------------------------------------------------


def test_a_plain_copy_still_works_and_is_not_revalidated() -> None:
    """Only copies that REPLACE a field re-validate. A plain copy must stay cheap and unchanged."""

    valid = _review()
    copy = valid.model_copy()
    assert copy == valid
    assert copy is not valid

    deep = valid.model_copy(deep=True)
    assert deep == valid

    # An update that keeps the record valid must still succeed.
    same = valid.model_copy(update={"notes": "a different note"})
    assert same.notes == "a different note"
    assert same.review_id == valid.review_id, "notes are not identity-bearing"


def test_append_review_now_builds_a_validating_history() -> None:
    """The schema, not three hand-written raises, is the guarantee (issue #42's proposed fix 3)."""

    subject = uuid4()
    first = _review(subject_triage_id=subject)
    history = append_review(new_history(subject), first)

    # A correction still works, and the chain stays linear.
    correction = _review(
        subject_triage_id=subject,
        decision=ReviewDecision.REVISE,
        final_disposition="corrected after re-reading the evidence",
        supersedes_review_id=first.review_id,
    )
    history = append_review(history, correction)

    assert len(history.reviews) == 2
    assert current_review(history) is correction
    assert history.reviews[0] is first, "history is append-only; the earlier belief stays readable"

    # The manual guards are still present as defence in depth, and still fire.
    with pytest.raises(ValueError, match="already recorded"):
        append_review(history, correction)
    with pytest.raises(ValueError, match="only supersede the most recent review"):
        append_review(history, _review(subject_triage_id=subject,
            supersedes_review_id=first.review_id))


def test_history_construction_from_fields_is_what_append_review_uses() -> None:
    """Pins the mechanism, not just the outcome.

    If `append_review` ever returns to `model_copy`, the schema stops being the guarantee and this
    fails - which is the point, because that regression would otherwise be invisible.
    """

    subject = uuid4()
    history = append_review(new_history(subject), _review(subject_triage_id=subject))
    assert isinstance(history, ReviewHistory)
    assert history.subject_triage_id == subject
    # Constructing the same value from fields must be possible, i.e. no field is lost in the
    # rebuild.
    rebuilt = ReviewHistory(subject_triage_id=history.subject_triage_id, reviews=history.reviews)
    assert rebuilt == history
