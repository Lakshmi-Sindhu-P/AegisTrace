"""Immutable triage-assessment and comparison contracts.

These records are the boundary between **deterministic evidence** and **model interpretation**. Two
properties matter most and are enforced by construction rather than by convention:

1. **An uncited assessment is unrepresentable.** ``TriageAssessment.cited_evidence_ids`` requires at
   least one entry, so a response that cites nothing cannot be stored as a valid assessment. It
   is stored as a :class:`FailedAssessment` instead. This follows the architecture rule that invalid
   or uncited output is preserved as a failed attempt, never silently coerced into a valid one.
2. **Abstention is a first-class outcome.** ``TriageCategory.INSUFFICIENT_EVIDENCE`` is a valid
   category, so "the evidence does not support a conclusion" is representable rather than forcing a
   binary guess.

A third property is scoped honestly: mutual blindness between assessors is enforced by what the
*input snapshot* can contain (see :mod:`aegistrace.triage.snapshot`). That is a contract over the
input this project controls. It cannot prove what a third-party provider does with data it receives.
"""

from __future__ import annotations

import json
from datetime import datetime
from enum import StrEnum
from uuid import NAMESPACE_URL, UUID, uuid5

from pydantic import Field, field_validator, model_validator

from aegistrace.schemas.common import (
    FrozenSchema,
    NonEmptyText,
    SchemaVersion,
    Sha256,
    normalize_utc,
)
from aegistrace.schemas.detections import DetectionSeverity

TRIAGE_ASSESSMENT_SCHEMA_VERSION = "1.0.0"
FAILED_ASSESSMENT_SCHEMA_VERSION = "1.0.0"
TRIAGE_COMPARISON_SCHEMA_VERSION = "1.0.0"

_BASE = "https://github.com/Lakshmi-Sindhu-P/AegisTrace"
#: Identity algorithm versions. See `docs/identity_rule.md`.
#:
#: v1 hashed `(role, evidence_bundle_id, input_snapshot_digest, category, summary)`, omitting
#: `severity` and `cited_evidence_ids` - both of which the agreement engine already treats as
#: distinguishing, since it reports `severity_mismatch` and `evidence_divergence` (issue #35). v1 is
#: retained so a historical id can still be attributed to the version that produced it; it must
#: never be used to mint new ids.
TRIAGE_ID_NAMESPACE_V1 = uuid5(NAMESPACE_URL, f"{_BASE}/triage-assessments/v1")
#: v2 adds the severity and the cited evidence, so an admitted assessment is identified by its
#: conclusion rather than only by its summary line.
TRIAGE_ID_NAMESPACE = uuid5(NAMESPACE_URL, f"{_BASE}/triage-assessments/v2")
FAILED_ATTEMPT_ID_NAMESPACE = uuid5(NAMESPACE_URL, f"{_BASE}/failed-assessments/v1")
COMPARISON_ID_NAMESPACE = uuid5(NAMESPACE_URL, f"{_BASE}/triage-comparisons/v1")


class AssessorRole(StrEnum):
    """Which frozen role produced an assessment.

    The two roles exist to be independent. Neither may read the other's output, and the comparison
    that follows is a separate record rather than a merge.
    """

    TRIAGE_ANALYST = "triage_analyst"
    EXPERT_ADJUDICATOR = "expert_adjudicator"


class TriageCategory(StrEnum):
    """Proposed disposition. INSUFFICIENT_EVIDENCE is a valid answer, not a failure."""

    LIKELY_MALICIOUS = "likely_malicious"
    SUSPICIOUS = "suspicious"
    LIKELY_BENIGN = "likely_benign"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class ReviewStatus(StrEnum):
    """Where an assessment sits in human review. Only humans leave PENDING_REVIEW."""

    PENDING_REVIEW = "pending_review"
    REVIEWED = "reviewed"
    REJECTED = "rejected"


class DisagreementReason(StrEnum):
    """Why two independent assessments do not agree. Disagreement is the escalation signal."""

    CATEGORY_MISMATCH = "category_mismatch"
    SEVERITY_MISMATCH = "severity_mismatch"
    EVIDENCE_DIVERGENCE = "evidence_divergence"
    ONE_SIDE_INSUFFICIENT_EVIDENCE = "one_side_insufficient_evidence"
    FAILED_ASSESSMENT = "failed_assessment"


class ProviderMetadata(FrozenSchema):
    """Which provider, model, and prompt produced a response. Pinned for reproducibility."""

    provider: NonEmptyText
    model: NonEmptyText
    model_version: NonEmptyText
    prompt_version: SchemaVersion
    temperature: float = Field(default=0.0, ge=0.0)


class RawResponseReference(FrozenSchema):
    """A content-addressed pointer to the unedited response, kept alongside any interpretation."""

    reference: NonEmptyText
    digest: Sha256
    structured: bool


class TriageAssessment(FrozenSchema):
    """One frozen assessor's structured, evidence-cited reading of an evidence bundle."""

    schema_version: SchemaVersion = TRIAGE_ASSESSMENT_SCHEMA_VERSION
    triage_id: UUID
    role: AssessorRole
    evidence_bundle_id: UUID
    bundle_version: SchemaVersion
    finding_ids: tuple[UUID, ...] = Field(min_length=1)
    input_snapshot_digest: Sha256
    category: TriageCategory
    severity: DetectionSeverity
    summary: NonEmptyText
    evidence_summary: NonEmptyText
    confidence_statement: NonEmptyText
    cited_evidence_ids: tuple[NonEmptyText, ...] = Field(min_length=1)
    uncertainties: tuple[NonEmptyText, ...] = ()
    unsupported_claim_flags: tuple[NonEmptyText, ...] = ()
    next_step: NonEmptyText
    provider_metadata: ProviderMetadata
    raw_response: RawResponseReference
    created_at: datetime
    review_status: ReviewStatus = ReviewStatus.PENDING_REVIEW

    @field_validator("created_at")
    @classmethod
    def normalize_created_at(cls, value: datetime) -> datetime:
        return normalize_utc(value)


class FailedAssessment(FrozenSchema):
    """A preserved failed attempt: malformed, uncited, or rejected output.

    Keeping the raw reference means the failure is auditable. Discarding it would erase the evidence
    that a provider misbehaved.
    """

    schema_version: SchemaVersion = FAILED_ASSESSMENT_SCHEMA_VERSION
    attempt_id: UUID
    role: AssessorRole
    evidence_bundle_id: UUID
    input_snapshot_digest: Sha256
    failure_reasons: tuple[NonEmptyText, ...] = Field(min_length=1)
    provider_metadata: ProviderMetadata
    raw_response: RawResponseReference
    created_at: datetime

    @field_validator("created_at")
    @classmethod
    def normalize_created_at(cls, value: datetime) -> datetime:
        return normalize_utc(value)


class TriageComparison(FrozenSchema):
    """The deterministic adjudication of two independent assessments.

    This record is separate from both assessments and retains their raw outputs, so a reader can
    always reconstruct what each side actually said before any comparison was computed.

    **What "left" and "right" mean, stated explicitly.** The comparison engine orders the two
    assessments by *role*, not by argument order, so that a comparison is identical whichever way
    the pair is passed in. ``left`` therefore means ``roles[0]`` and ``right`` means ``roles[1]``
    -- which in practice is the ``triage_analyst`` first and the ``expert_adjudicator`` second.
    These field names do **not** refer to the ``left`` and ``right`` parameters of
    :func:`aegistrace.triage.agreement.compare_assessments`; passing the adjudicator as that
    function's ``left`` argument still populates ``left_only_evidence_ids`` with the analyst's
    unique citations. ``roles`` is stored alongside and gives the mapping.
    """

    schema_version: SchemaVersion = TRIAGE_COMPARISON_SCHEMA_VERSION
    comparison_id: UUID
    evidence_bundle_id: UUID
    assessment_ids: tuple[UUID, ...] = Field(min_length=1)
    roles: tuple[AssessorRole, ...] = ()
    agreement: bool
    agreement_score: float = Field(ge=0, le=1)
    disagreement_reasons: tuple[DisagreementReason, ...] = ()
    shared_evidence_ids: tuple[NonEmptyText, ...] = ()
    left_only_evidence_ids: tuple[NonEmptyText, ...] = Field(
        default=(),
        description=(
            "evidence cited only by roles[0] (the triage analyst); NOT the argument named 'left'"
        ),
    )
    right_only_evidence_ids: tuple[NonEmptyText, ...] = Field(
        default=(),
        description=(
            "evidence cited only by roles[1] (the expert adjudicator); "
            "NOT the argument named 'right'"
        ),
    )
    escalation_recommended: bool
    raw_output_references: tuple[RawResponseReference, ...] = ()
    validator_results: tuple[NonEmptyText, ...] = ()
    created_at: datetime

    @field_validator("created_at")
    @classmethod
    def normalize_created_at(cls, value: datetime) -> datetime:
        return normalize_utc(value)

    @model_validator(mode="after")
    def validate_agreement_is_consistent(self) -> TriageComparison:
        if self.agreement and self.disagreement_reasons:
            raise ValueError("an agreeing comparison cannot carry disagreement reasons")
        return self

    @model_validator(mode="after")
    def validate_roles_map_assessments(self) -> TriageComparison:
        """Require ``roles`` to be a one-to-one, distinct mapping onto ``assessment_ids``.

        Both rules were already contracts of the comparison engine, which builds the two tuples in
        parallel and refuses two assessments that share a role because independence needs one
        assessment per role. The schema did not state them, and a comparison is read back from
        stored artifacts rather than rebuilt, so a record whose ``roles`` could not map its
        ``assessment_ids`` loaded without complaint. That matters because
        ``left_only_evidence_ids`` is interpreted through ``roles[0]``: a misaligned record silently
        attributes evidence to the wrong assessor, and a same-role record claims an independence it
        does not have.

        An empty ``roles`` is the "not recorded" state and stays legal.
        """

        # Checked before the early return below, because it does not depend on `roles`: two
        # entries naming the same assessment mean the same assessor was recorded twice, which is
        # the shape `compare_assessments` refuses as "an assessment with itself".
        if len(set(self.assessment_ids)) != len(self.assessment_ids):
            raise ValueError(
                "assessment_ids must be distinct: a comparison needs two independent assessments, "
                "and a repeated identifier means one assessment was recorded twice"
            )

        if not self.roles:
            return self
        if len(self.roles) != len(self.assessment_ids):
            raise ValueError(
                "roles must map assessment_ids one-to-one: "
                f"{len(self.roles)} roles for {len(self.assessment_ids)} assessments"
            )
        if len(set(self.roles)) != len(self.roles):
            raise ValueError(
                "each assessment must come from a distinct role; independence requires one "
                "assessment per role"
            )
        return self


def _identity(*parts: object) -> str:
    return json.dumps(parts, ensure_ascii=False, separators=(",", ":"), default=str)


def triage_id_v1_for(
    *,
    role: str,
    evidence_bundle_id: UUID,
    input_snapshot_digest: str,
    category: str,
    summary: str,
) -> UUID:
    """Reproduce a pre-#35 assessment id. Historical reconciliation ONLY.

    v1 omitted `severity` and `cited_evidence_ids`, which the agreement engine already distinguishes
    on. Never use this to mint new ids.
    """

    return uuid5(
        TRIAGE_ID_NAMESPACE_V1,
        _identity(
            str(role), str(evidence_bundle_id), input_snapshot_digest, str(category), summary
        ),
    )


def triage_id_for(
    *,
    role: str,
    evidence_bundle_id: UUID,
    input_snapshot_digest: str,
    category: str,
    summary: str,
    severity: str | None = None,
    cited_evidence_ids: tuple[str, ...] = (),
) -> UUID:
    """Derive an assessment identity from its conclusion, by the identity rule.

    The rule (`docs/identity_rule.md`): an id covers exactly the fields that make the entity the
    entity it is, and nothing else.

    v1 covered `(role, bundle, snapshot, category, summary)` and omitted `severity` and
    `cited_evidence_ids`. That was inconsistent with the rest of the system, which **already treats
    both as distinguishing**: the agreement engine reports `severity_mismatch` and
    `evidence_divergence` for a genuine pair of assessors whose severity or citations differ. An
    identity that disagrees with the engine about what makes two assessments different let a changed
    severity keep the same id (issue #35).

    The asymmetry was the strongest evidence this was an oversight: `failed_attempt_id_for` IS
    content-addressed over `raw_digest`, so a *rejected* assessment was more uniquely identified
    than
    an *admitted* one.

    Citations are sorted, so the order an assessor happened to list them in cannot change the id.
    `input_snapshot_digest` is retained deliberately: it is the exact input the assessor saw, and
    recording it is load-bearing for mutual blindness even though it is derivable from the bundle.

    Use :func:`triage_id_v1_for` to reproduce a pre-change id for historical reconciliation.
    """

    return uuid5(
        TRIAGE_ID_NAMESPACE,
        _identity(
            str(role),
            str(evidence_bundle_id),
            input_snapshot_digest,
            str(category),
            summary,
            str(severity) if severity is not None else None,
            sorted(str(citation) for citation in cited_evidence_ids),
        ),
    )


def failed_attempt_id_for(
    *, role: str, evidence_bundle_id: UUID, input_snapshot_digest: str, raw_digest: str
) -> UUID:
    """Derive a failed-attempt identity from the role, snapshot, and the raw response digest."""

    return uuid5(
        FAILED_ATTEMPT_ID_NAMESPACE,
        _identity(str(role), str(evidence_bundle_id), input_snapshot_digest, raw_digest),
    )


def comparison_id_for(*, evidence_bundle_id: UUID, assessment_ids: tuple[UUID, ...]) -> UUID:
    """Derive a comparison identity that does not depend on which side was passed first."""

    ordered = sorted(str(assessment_id) for assessment_id in assessment_ids)
    return uuid5(COMPARISON_ID_NAMESPACE, _identity(str(evidence_bundle_id), ordered))


__all__ = [
    "FAILED_ASSESSMENT_SCHEMA_VERSION",
    "TRIAGE_ASSESSMENT_SCHEMA_VERSION",
    "TRIAGE_COMPARISON_SCHEMA_VERSION",
    "AssessorRole",
    "DisagreementReason",
    "FailedAssessment",
    "ProviderMetadata",
    "RawResponseReference",
    "ReviewStatus",
    "TriageAssessment",
    "TriageCategory",
    "TriageComparison",
    "comparison_id_for",
    "failed_attempt_id_for",
    "triage_id_for",
    "triage_id_v1_for",
]
