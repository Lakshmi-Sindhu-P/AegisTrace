"""Append-only review history.

The architecture requires that corrections create new history rather than overwriting earlier
records. That is enforced here rather than left to convention: a review may only supersede the most
recent review, and duplicate identifiers are rejected. The result is a linear chain in which the
last entry is unambiguously current and every earlier belief remains readable.
"""

from __future__ import annotations

from uuid import UUID

from aegistrace.schemas.review import HumanReview, ReviewHistory


def new_history(subject_triage_id: UUID) -> ReviewHistory:
    """Start an empty history for one triage subject."""

    return ReviewHistory(subject_triage_id=subject_triage_id)


def append_review(history: ReviewHistory, review: HumanReview) -> ReviewHistory:
    """Append a review, enforcing that corrections extend the chain instead of rewriting it."""

    if review.subject_triage_id != history.subject_triage_id:
        raise ValueError("review subject does not match the history subject")

    if any(existing.review_id == review.review_id for existing in history.reviews):
        raise ValueError("a review with this identity is already recorded")

    if history.reviews:
        latest = history.reviews[-1]
        if review.supersedes_review_id is None:
            raise ValueError("a later review must supersede the most recent review")
        if review.supersedes_review_id != latest.review_id:
            raise ValueError("a review may only supersede the most recent review")
    elif review.supersedes_review_id is not None:
        raise ValueError("the first review in a history cannot supersede anything")

    return history.model_copy(update={"reviews": (*history.reviews, review)})


def current_review(history: ReviewHistory) -> HumanReview | None:
    """Return the review currently in force, or None when nothing has been reviewed yet."""

    return history.reviews[-1] if history.reviews else None


__all__ = ["append_review", "current_review", "new_history"]
