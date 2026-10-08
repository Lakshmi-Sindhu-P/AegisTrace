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

#: Identity algorithm versions. See `docs/identity_rule.md`.
#:
#: v1 hashed `(subject_triage_id, reviewer_ref, decision, reviewed_at)`. `reviewed_at` is *recording
#: bookkeeping* rather than a property of the judgment, and including it is what made two distinct
#: dispositions at the same instant collide (issue #40); it also omitted `final_disposition` and
#: `subject_role`, which are defining. v1 is retained so a historical id can still be attributed to
#: the version that produced it; it must never be used to mint new ids.
REVIEW_ID_NAMESPACE_V1 = uuid5(
    NAMESPACE_URL, "https://github.com/Lakshmi-Sindhu-P/AegisTrace/reviews/v1"
)
#: v2 covers the substance of the judgment (role, decision, disposition, superseded link) and drops
#: the timestamp.
REVIEW_ID_NAMESPACE = uuid5(
    NAMESPACE_URL, "https://github.com/Lakshmi-Sindhu-P/AegisTrace/reviews/v2"
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


def review_id_v1_for(
    *,
    subject_triage_id: UUID,
    reviewer_ref: str,
    decision: str,
    reviewed_at: datetime,
) -> UUID:
    """Reproduce a pre-#40 review id. Historical reconciliation ONLY.

    v1 hashed `(subject_triage_id, reviewer_ref, decision, reviewed_at)`. It omitted the substance
    of
    the judgment and included the recording time, which is what made two distinct dispositions in
    the same instant collide. Never use this to mint new ids.
    """

    return uuid5(
        REVIEW_ID_NAMESPACE_V1,
        _identity(
            str(subject_triage_id),
            reviewer_ref,
            str(decision),
            normalize_utc(reviewed_at).isoformat(),
        ),
    )


def review_id_for(
    *,
    subject_triage_id: UUID,
    subject_role: str,
    reviewer_ref: str,
    decision: str,
    final_disposition: str,
    supersedes_review_id: UUID | None = None,
) -> UUID:
    """Derive a review identity from the substance of the judgment, by the identity rule.

    The rule (`docs/identity_rule.md`): an id covers exactly the fields that make the entity the
    entity it is, and nothing else.

    The substance of a human judgment is *who reviewed which conclusion of which role, deciding
    what,
    and correcting what*. That is what the identity covers. `reviewed_at` is deliberately excluded:
    it records *when* the judgment was written down, not *what* it was, and including it made two
    genuinely distinct dispositions recorded in the same instant collide, so `append_review` refused
    the second as a duplicate (issue #40).

    `tier` and `escalation_state` are excluded as derived - `tier` follows from the subject via
    `classify_tier`, and `escalation_state` is tied to `decision` by the coherence invariant.
    `notes` is excluded because free text makes a fragile content address.

    Use :func:`review_id_v1_for` to reproduce a pre-change id for historical reconciliation.
    """

    return uuid5(
        REVIEW_ID_NAMESPACE,
        _identity(
            str(subject_triage_id),
            str(subject_role),
            reviewer_ref,
            str(decision),
            final_disposition,
            str(supersedes_review_id) if supersedes_review_id is not None else None,
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
            subject_role=self.subject_role,
            reviewer_ref=self.reviewer_ref,
            decision=self.decision,
            final_disposition=self.final_disposition,
            supersedes_review_id=self.supersedes_review_id,
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
    "review_id_v1_for",
]
