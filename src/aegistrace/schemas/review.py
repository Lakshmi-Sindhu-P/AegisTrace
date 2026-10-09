"""Immutable human-review contracts and the append-only review history.

Human review is where this project's central promise is kept: no autonomous action, and no model
conclusion that is treated as a decision. Three properties make that structural rather than
aspirational.

1. **A review never overwrites an earlier review.** Corrections set ``supersedes_review_id`` and are
   appended, so the record shows what was believed and when, not just the final answer.
2. **A review is linked to a specific triage subject.** ``subject_triage_id`` is required, so a
   disposition can always be traced back to the exact assessment it judged.
3. **Tier is a claim about who is qualified to decide**, not a severity and not a priority. Tier
   A is machine-checkable evidence mechanics, Tier B is guided review, Tier C needs genuine
   expertise, and Tier D records that the evidence does not support a decision.

   ``HumanReview.tier`` is the tier **actually conducted** - the level of human scrutiny the
   reviewer really applied. ``TierAssignment.tier`` is the tier **required** for the subject. The
   two are *reconciled* by :class:`TierReconciliation`, which records explicitly whether the review
   met the assignment's requirement (see ``REQUIREMENT_SATISFIED_BY`` for the non-ordinal
   relationship).
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


#: Which CONDUCTED tiers satisfy which REQUIRED tier. Deliberately an explicit map, not a scale.
#:
#: "Satisfies" here means: the review **actually conducted** (_conducted_) applied at least as much
#: human scrutiny as the subject's assignment **required**. Among the qualification tiers the three
#: that demand human judgment form a chain - ``A_MACHINE_CHECK < B_GUIDED_JUNIOR <
#: C_EXPERT_JUDGMENT`` - in the sense that a reviewer qualified for a higher one is qualified for a
#: lower one, so a review conducted at a higher tier satisfies a lower requirement.
#:
#: ``D_INSUFFICIENT_EVIDENCE`` is deliberately NOT part of that chain and it is its own case: it
#: is a terminal *outcome* (the reviewer concludes there is not enough evidence to decide), not a
#: level of expertise that is "more than" C. Consequently it never satisfies an A/B/C requirement
#: - a case that required expert judgment is not resolved by someone declaring the evidence thin -
#: and a D requirement is satisfied only by a review conducted at D: a D assignment says there is no
#: conclusion to confirm, so the review that meets it is the one that records that insufficiency,
#: not a staged A/B/C review pretending a conclusion exists. In both directions D is its own
#: category, which is why the map is written out explicitly rather than inferred from an ordering.
#:
#: This is the single source of truth for the reconciliation in :class:`TierReconciliation`.
#: Writing it here, in the schema module, keeps the relationship inspectable and reusable rather
#: than buried in a builder that ``model_validate`` would bypass.
_REQUIREMENT_SATISFIED_BY: dict[ReviewTier, frozenset[ReviewTier]] = {
    ReviewTier.A_MACHINE_CHECK: frozenset(
        {
            ReviewTier.A_MACHINE_CHECK,
            ReviewTier.B_GUIDED_JUNIOR,
            ReviewTier.C_EXPERT_JUDGMENT,
        }
    ),
    ReviewTier.B_GUIDED_JUNIOR: frozenset(
        {
            ReviewTier.B_GUIDED_JUNIOR,
            ReviewTier.C_EXPERT_JUDGMENT,
        }
    ),
    ReviewTier.C_EXPERT_JUDGMENT: frozenset({ReviewTier.C_EXPERT_JUDGMENT}),
    ReviewTier.D_INSUFFICIENT_EVIDENCE: frozenset({ReviewTier.D_INSUFFICIENT_EVIDENCE}),
}


def tier_satisfies_requirement(
    *, conducted: ReviewTier, required: ReviewTier
) -> bool:
    """Whether a review conducted at ``conducted`` satisfies the requirement of ``required``.

    Pure and derived from ``_REQUIREMENT_SATISFIED_BY``. The meaningful tests read this function
    directly, but :class:`TierReconciliation` carries the schema-level guarantee that the recorded
    ``requirement_met`` fact always equals this value (see
    :meth:`TierReconciliation.reconcile_tier`).
    """

    return conducted in _REQUIREMENT_SATISFIED_BY[required]


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
    """One reviewer's immutable disposition of one triage assessment.

    ``tier`` here is the tier **actually conducted** - the level of human scrutiny this reviewer
    really applied to the subject. It is *not* the tier the subject required; that requirement lives
    on the subject's :class:`TierAssignment` and is reconciled against this conducted tier by
    :class:`TierReconciliation`. The two are intentionally separate so that an under-reviewed case
    (conducted tier below required tier) is recorded as a discrepancy rather than silently accepted.
    """

    schema_version: SchemaVersion = REVIEW_SCHEMA_VERSION
    review_id: UUID
    subject_triage_id: UUID
    subject_role: AssessorRole
    reviewer_ref: NonEmptyText
    #: The tier actually conducted for this review. Not the tier the subject required.
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
    """The append-only chain of reviews for one triage subject.

    The chain is validated here rather than left to :func:`aegistrace.review.history.append_review`,
    because that helper is bypassed by the path that reads durable records:
    ``ReviewHistory.model_validate(...)`` from stored JSON. A history whose links dangled or forked
    used to load without complaint and present a broken lineage as authoritative. The rules are the
    ones the helper has always enforced, so every history it can build still validates.
    """

    schema_version: SchemaVersion = REVIEW_HISTORY_SCHEMA_VERSION
    subject_triage_id: UUID
    reviews: tuple[HumanReview, ...] = ()

    @model_validator(mode="after")
    def validate_subjects_match(self) -> ReviewHistory:
        for review in self.reviews:
            if review.subject_triage_id != self.subject_triage_id:
                raise ValueError("every review in a history must share the subject triage id")
        return self

    @model_validator(mode="after")
    def validate_chain_is_linear(self) -> ReviewHistory:
        """Require one linear chain, so the last entry is unambiguously current.

        Enforced on every construction path. The messages match ``append_review``'s, which keeps its
        checks as defence in depth rather than the only guarantee (same shape as issue #42).
        """

        seen: set[UUID] = set()
        previous: HumanReview | None = None
        for review in self.reviews:
            if review.review_id in seen:
                raise ValueError("a review with this identity is already recorded")
            seen.add(review.review_id)

            if previous is None:
                if review.supersedes_review_id is not None:
                    raise ValueError("the first review in a history cannot supersede anything")
            else:
                if review.supersedes_review_id is None:
                    raise ValueError("a later review must supersede the most recent review")
                if review.supersedes_review_id != previous.review_id:
                    raise ValueError("a review may only supersede the most recent review")
            previous = review
        return self


class TierReconciliation(FrozenSchema):
    """Pair the tier a subject *required* with the tier a review *actually conducted*, and
    reconcile them.

    This is the object that owns the data needed to answer issue #30: whether the review met
    the assignment's tier requirement. Both halves must be present and reconciled here, on the
    schema, because the alternative - a helper that knows the relationship but lives elsewhere -
    is bypassed by ``model_validate`` when a durable record is read back. Enforcing the check in
    this model validators means it runs on construction, ``model_validate`` of stored JSON, and
    ``model_copy(update=...)`` alike.

    Design choice: **recorded, not fatal.** An under-reviewed case is *not* a hard crash. It
    produces a valid :class:`TierReconciliation` whose ``requirement_met`` is ``False`` and whose
    ``unmet_requirement`` states exactly what was missing. That makes the discrepancy an
    inspectable, immutable, serialized fact - impossible to lose by accident - while still allowing
    the record to exist so a human can escalate a case that neither the cheapest tier nor the
    assigned tier fully covered. ``requirement_met`` and ``unmet_requirement`` are stored fields
    that the after-validator *always recomputes from the two tiers*, so a stored record claiming a
    satisfied requirement for a genuinely under-reviewed case is corrected (or refused, where the
    claimed value conflicts) on load rather than trusted. The relationship itself is the explicit
    non-ordinal map in ``_REQUIREMENT_SATISFIED_BY`` - crucially, ``D_INSUFFICIENT_EVIDENCE`` is
    its own case and never "more than" C.
    """

    schema_version: SchemaVersion = REVIEW_SCHEMA_VERSION
    subject_triage_id: UUID
    assignment: TierAssignment  # tier REQUIRED
    review: HumanReview  # tier CONDUCTED
    requirement_met: bool = False
    unmet_requirement: NonEmptyText | None = None

    @model_validator(mode="after")
    def validate_subjects_match(self) -> TierReconciliation:
        if self.review.subject_triage_id != self.subject_triage_id:
            raise ValueError(
                "the review being reconciled must belong to the reconciliation's subject "
                f"(review subject {self.review.subject_triage_id} != "
                f"subject {self.subject_triage_id})"
            )
        return self

    @model_validator(mode="after")
    def reconcile_tier(self) -> TierReconciliation:
        """(Re)compute ``requirement_met`` and ``unmet_requirement`` from the two tiers.

        Recomputed rather than trusted to close the recurring escape hatch: ``model_validate`` reads
        whatever was serialized, so if ``requirement_met`` were stored as-is a forged record could
        claim a satisfied requirement while the tiers say otherwise. Recomputation from the
        authoritative tiers on every construction path makes the discrepancy impossible to lose.
        """

        required = self.assignment.tier
        conducted = self.review.tier
        met = tier_satisfies_requirement(conducted=conducted, required=required)
        # If the caller explicitly supplied a value (direct construction, or a stored record read
        # back through `model_validate`), it must agree with the authoritative relationship. A value
        # that silently disagrees is a lie - e.g. a forged record claiming a met requirement for an
        # under-reviewed case - and must be refused, not trusted. When the caller supplied nothing,
        # the field holds its default and is simply recomputed.
        if "requirement_met" in self.model_fields_set and self.requirement_met != met:
            raise ValueError(
                "recorded requirement_met contradicts the tier relationship: "
                f"assignment required {required.value}, review conducted {conducted.value}, "
                f"so requirement_met must be {met!r}"
            )
        self.__dict__["requirement_met"] = met
        if met:
            self.__dict__["unmet_requirement"] = None
        else:
            self.__dict__["unmet_requirement"] = (
                f"this subject required a review at tier {required.value} "
                f"(who is qualified to decide), but the review was conducted at tier "
                f"{conducted.value}; the requirement was not met"
            )
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
    "TierReconciliation",
    "review_id_for",
    "review_id_v1_for",
    "tier_satisfies_requirement",
]
