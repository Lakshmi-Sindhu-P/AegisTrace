"""Strict, redacted execution-provenance records for agent work."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal, Self

from pydantic import Field, StringConstraints, field_validator, model_validator

from aegistrace.schemas.common import (
    FrozenSchema,
    NonEmptyText,
    SchemaVersion,
    Sha256,
    normalize_utc,
)

TraceId = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{16,64}$")]
CommitId = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{7,64}$")]

SourceKind = Literal["repository", "issue", "trace", "command", "artifact", "url"]
TraceAction = Literal[
    "inspect",
    "read",
    "edit",
    "test",
    "validate",
    "issue_create",
    "issue_update",
    "commit",
    "push",
    "retrospective",
    "lesson_propose",
    "lesson_validate",
    "escalate",
]
TraceOutcome = Literal["started", "completed", "failed", "blocked_human", "escalated"]
ApprovalState = Literal["not_required", "approved", "blocked_human"]
Confidence = Literal["high", "medium", "low", "unknown"]


class TraceSourceReference(FrozenSchema):
    """A deterministic pointer to evidence used by an agent action."""

    kind: SourceKind
    reference: NonEmptyText
    locator: NonEmptyText | None = None
    digest: Sha256 | None = None


class AgentTraceRecord(FrozenSchema):
    """One redacted JSONL event in the local execution-provenance ledger."""

    schema_version: SchemaVersion = "1.0.0"
    trace_id: TraceId
    span_id: TraceId
    parent_span_id: TraceId | None = None
    event_index: int = Field(ge=0)
    occurred_at: datetime
    issue_ref: NonEmptyText
    workspace_ref: NonEmptyText
    agent_ref: NonEmptyText
    branch: NonEmptyText
    code_version: CommitId | None = None
    action: TraceAction
    outcome: TraceOutcome
    approval_state: ApprovalState
    reason_code: NonEmptyText
    confidence: Confidence
    confidence_basis: NonEmptyText
    source_refs: tuple[TraceSourceReference, ...] = Field(min_length=1)
    command_digest: Sha256 | None = None
    input_digest: Sha256 | None = None
    output_digest: Sha256 | None = None
    validation_refs: tuple[NonEmptyText, ...] = ()
    solution_refs: tuple[NonEmptyText, ...] = ()
    escalation_request: NonEmptyText | None = None
    summary: NonEmptyText

    @field_validator("occurred_at")
    @classmethod
    def normalize_timestamp(cls, value: datetime) -> datetime:
        """Require timezone-aware timestamps and normalize them to UTC."""

        return normalize_utc(value)

    @model_validator(mode="after")
    def validate_escalation_state(self) -> Self:
        """Require an explicit human-input request for human-blocked actions."""

        if self.outcome in {"blocked_human", "escalated"} and self.escalation_request is None:
            raise ValueError("blocked or escalated traces require escalation_request")
        if self.outcome == "blocked_human" and self.approval_state != "blocked_human":
            raise ValueError("blocked_human traces require approval_state=blocked_human")
        return self


class LessonVersion(FrozenSchema):
    """One immutable version of a reusable, validated engineering lesson."""

    version: SchemaVersion
    status: Literal["current", "superseded"]
    originating_issue: NonEmptyText
    originating_trace: TraceId
    applicable_code_version: NonEmptyText
    problem_pattern: NonEmptyText
    solution_principle: NonEmptyText
    validation_refs: tuple[NonEmptyText, ...] = Field(min_length=1)
    evidence_refs: tuple[TraceSourceReference, ...] = Field(min_length=1)
    supersedes: NonEmptyText | None = None
    superseded_by: NonEmptyText | None = None

    @model_validator(mode="after")
    def validate_supersession(self) -> Self:
        """Keep current and superseded records explicit rather than overwriting history."""

        if self.status == "current" and self.superseded_by is not None:
            raise ValueError("current lesson versions cannot point to superseded_by")
        if self.status == "superseded" and self.superseded_by is None:
            raise ValueError("superseded lesson versions require superseded_by")
        return self


class SolutionEntry(FrozenSchema):
    """A reusable lesson with an append-only version history."""

    solution_id: NonEmptyText
    current_version: SchemaVersion
    versions: tuple[LessonVersion, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_versions(self) -> Self:
        version_names = [item.version for item in self.versions]
        if len(version_names) != len(set(version_names)):
            raise ValueError("solution versions must be unique")
        current = [item for item in self.versions if item.status == "current"]
        if len(current) != 1 or current[0].version != self.current_version:
            raise ValueError("exactly one version must match current_version and be current")
        return self


class SolutionKnowledge(FrozenSchema):
    """Tracked solution knowledge; issue and trace history remains elsewhere."""

    schema_version: SchemaVersion = "1.0.0"
    solutions: tuple[SolutionEntry, ...] = ()

    @model_validator(mode="after")
    def validate_solution_ids(self) -> Self:
        identifiers = [item.solution_id for item in self.solutions]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("solution_id values must be unique")
        return self
