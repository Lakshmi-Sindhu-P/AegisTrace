"""Immutable human-review contracts and the append-only review history.

Human review is where this project's central promise is kept: no autonomous action, and no model
conclusion that is treated as a decision. Three properties make that structural rather than
aspirational.

1. **A review never overwrites an earlier review.** Corrections set ``supersedes_review_id`` and are
   appended, so the record shows what was believed and when, not just the final answer.
2. **A review is linked to a specific triage subject.** ``subject_triage_id`` is required, so a
   disposition can always be traced back to the exact assessment it judged.
3. **Tier is a claim about who is qualified to decide**, not a severity. Tier A is machine-checkable
   evidence mechanics, Tier B is guided review, Tier C needs genuine expertise, and Tier D records
   that the evidence does not support a decision.
"""

from __future__ import annotations

import json
from datetime import datetime
from enum import StrEnum
from uuid import NAMESPACE_URL, UUID, uuid5

from pydantic import Field, field_validator, model_validator

from aegistrace.schemas.common import FrozenSchema, NonEmptyText, SchemaVersion, normalize_utc
from aegistrace.schemas.triage import AssessorRole

REVIEW_SCHEMA_VERSION = "1.0.0"
REVIEW_HISTORY_SCHEMA_VERSION = "1.0.0"

REVIEW_ID_NAMESPACE = uuid5(
    NAMESPACE_URL, "https://github.com/Lakshmi-Sindhu-P/AegisTrace/reviews/v1"
)


class ReviewTier(StrEnum):
    """Who is qualified to decide. Not a severity and not a priority."""

    A_MACHINE_CHECK = "tier_a_machine_check"
    B_GUIDED_JUNIOR = "tier_b_guided_junior"
    C_EXPERT_JUDGMENT = "tier_c_expert_judgment"
    D_INSUFFICIENT_EVIDENCE = "tier_d_insufficient_evidence"


class ReviewDecision(StrEnum):
    """What the reviewer concluded."""

    CONFIRM = "confirm"
    REVISE = "revise"
    DISMISS = "dismiss"
    ESCALATE = "escalate"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class EscalationState(StrEnum):
    """Whether a review has been handed on, and where it stands."""

    NONE = "none"
    PENDING = "pending"
    ESCALATED = "escalated"


class MachineCheck(FrozenSchema):
    """One deterministic check of evidence mechanics. Tier A consists only of these."""

    check_name: NonEmptyText
    passed: bool
    detail: NonEmptyText


class TierAssignment(FrozenSchema):
    """The deterministic explanation of which review tier a subject requires."""

    tier: ReviewTier
    reasons: tuple[NonEmptyText, ...] = Field(min_length=1)
    machine_checks: tuple[MachineCheck, ...] = ()


def _identity(*parts: object) -> str:
    return json.dumps(parts, ensure_ascii=False, separators=(",", ":"), default=str)


def review_id_for(
    *,
    subject_triage_id: UUID,
    reviewer_ref: str,
    decision: str,
    reviewed_at: datetime,
) -> UUID:
    """Derive a review identity from its subject, reviewer, decision, and time."""

    return uuid5(
        REVIEW_ID_NAMESPACE,
        _identity(
            str(subject_triage_id),
            reviewer_ref,
            str(decision),
            normalize_utc(reviewed_at).isoformat(),
        ),
    )


class HumanReview(FrozenSchema):
    """One reviewer's immutable disposition of one triage assessment."""

    schema_version: SchemaVersion = REVIEW_SCHEMA_VERSION
    review_id: UUID
    subject_triage_id: UUID
    subject_role: AssessorRole
    reviewer_ref: NonEmptyText
    tier: ReviewTier
    decision: ReviewDecision
    notes: NonEmptyText
    reviewed_at: datetime
    escalation_state: EscalationState
    final_disposition: NonEmptyText
    supersedes_review_id: UUID | None = None

    @field_validator("reviewed_at")
    @classmethod
    def normalize_reviewed_at(cls, value: datetime) -> datetime:
        return normalize_utc(value)

    @model_validator(mode="after")
    def validate_correction_is_linked(self) -> HumanReview:
        if self.decision is ReviewDecision.REVISE and self.supersedes_review_id is None:
            raise ValueError("a revising review must reference the review it supersedes")
        return self

    @model_validator(mode="after")
    def validate_review_coherence(self) -> HumanReview:
        if (
            self.decision is ReviewDecision.ESCALATE
            and self.escalation_state is EscalationState.NONE
        ):
            raise ValueError("an escalating review must carry a non-NONE escalation state")
        if (
            self.escalation_state is not EscalationState.NONE
            and self.decision is not ReviewDecision.ESCALATE
        ):
            raise ValueError(
                "a non-NONE escalation state requires an escalate decision"
            )
        expected_id = review_id_for(
            subject_triage_id=self.subject_triage_id,
            reviewer_ref=self.reviewer_ref,
            decision=self.decision,
            reviewed_at=self.reviewed_at,
        )
        if self.review_id != expected_id:
            raise ValueError(
                f"review_id {self.review_id} does not match the expected "
                f"review_id_for(...) value {expected_id}"
            )
        return self


class ReviewHistory(FrozenSchema):
    """The append-only chain of reviews for one triage subject."""

    schema_version: SchemaVersion = REVIEW_HISTORY_SCHEMA_VERSION
    subject_triage_id: UUID
    reviews: tuple[HumanReview, ...] = ()

    @model_validator(mode="after")
    def validate_subjects_match(self) -> ReviewHistory:
        for review in self.reviews:
            if review.subject_triage_id != self.subject_triage_id:
                raise ValueError("every review in a history must share the subject triage id")
        return self


__all__ = [
    "REVIEW_HISTORY_SCHEMA_VERSION",
    "REVIEW_SCHEMA_VERSION",
    "EscalationState",
    "HumanReview",
    "MachineCheck",
    "ReviewDecision",
    "ReviewHistory",
    "ReviewTier",
    "TierAssignment",
    "review_id_for",
]
