"""Tests for issue-linked execution traces and versioned solution knowledge."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from aegistrace.schemas.agent_trace import (
    AgentTraceRecord,
    LessonVersion,
    SolutionEntry,
    SolutionKnowledge,
    TraceSourceReference,
)

SHA = "a" * 64


def _source() -> TraceSourceReference:
    return TraceSourceReference(
        kind="repository",
        reference="src/aegistrace/schemas/agent_trace.py",
        locator="blob:abc123#L1-L10",
        digest="b" * 64,
    )


def test_agent_trace_normalizes_time_and_preserves_linkage() -> None:
    record = AgentTraceRecord(
        trace_id=SHA,
        span_id="c" * 32,
        event_index=0,
        occurred_at=datetime(2026, 9, 29, 12, 0, tzinfo=UTC),
        issue_ref="Lakshmi-Sindhu-P/AegisTrace#1",
        workspace_ref="workspace-1",
        agent_ref="codex-session-1",
        branch="trace-foundation",
        code_version="d" * 40,
        action="validate",
        outcome="completed",
        approval_state="approved",
        reason_code="schema_validation",
        confidence="high",
        confidence_basis="repository test result",
        source_refs=(_source(),),
        command_digest="e" * 64,
        validation_refs=("uv run pytest tests/test_agent_trace.py",),
        solution_refs=("solution-knowledge:trace-redaction@1.0.0",),
        summary="Validated one issue-linked trace record.",
    )

    assert record.occurred_at.tzinfo is UTC
    assert record.issue_ref.endswith("#1")
    assert record.source_refs[0].digest == "b" * 64


def test_blocked_trace_requires_explicit_human_input() -> None:
    with pytest.raises(ValueError, match="escalation_request"):
        AgentTraceRecord(
            trace_id=SHA,
            span_id="c" * 32,
            event_index=1,
            occurred_at=datetime.now(UTC),
            issue_ref="owner/repo#2",
            workspace_ref="workspace-1",
            agent_ref="codex-session-1",
            branch="trace-foundation",
            action="escalate",
            outcome="blocked_human",
            approval_state="blocked_human",
            reason_code="missing_authorization",
            confidence="high",
            confidence_basis="owner policy",
            source_refs=(_source(),),
            summary="Waiting for the owner to confirm authorization.",
        )


def test_solution_knowledge_requires_current_version_and_preserves_history() -> None:
    old = LessonVersion(
        version="1.0.0",
        status="superseded",
        originating_issue="owner/repo#3",
        originating_trace=SHA,
        applicable_code_version="commit-old",
        problem_pattern="Trace output contained unredacted fields.",
        solution_principle="Redact before persistence.",
        validation_refs=("tests/test_agent_trace.py::test_agent_trace_normalizes_time_and_preserves_linkage",),
        evidence_refs=(_source(),),
        superseded_by="trace-redaction@1.1.0",
    )
    current = LessonVersion(
        version="1.1.0",
        status="current",
        originating_issue="owner/repo#4",
        originating_trace="f" * 64,
        applicable_code_version="commit-current",
        problem_pattern="Trace output must remain local and redacted.",
        solution_principle="Store digests and concise rationale instead of raw output.",
        validation_refs=("uv run pytest",),
        evidence_refs=(_source(),),
        supersedes="trace-redaction@1.0.0",
    )
    knowledge = SolutionKnowledge(
        solutions=(
            SolutionEntry(
                solution_id="trace-redaction",
                current_version="1.1.0",
                versions=(old, current),
            ),
        )
    )

    assert knowledge.solutions[0].current_version == "1.1.0"
    assert knowledge.solutions[0].versions[0].status == "superseded"


def test_solution_knowledge_rejects_duplicate_solution_ids() -> None:
    with pytest.raises(ValueError, match="solution_id values must be unique"):
        SolutionKnowledge(
            solutions=(
                SolutionEntry(
                    solution_id="duplicate",
                    current_version="1.0.0",
                    versions=(
                        LessonVersion(
                            version="1.0.0",
                            status="current",
                            originating_issue="owner/repo#5",
                            originating_trace=SHA,
                            applicable_code_version="commit",
                            problem_pattern="pattern",
                            solution_principle="principle",
                            validation_refs=("test",),
                            evidence_refs=(_source(),),
                        ),
                    ),
                ),
                SolutionEntry(
                    solution_id="duplicate",
                    current_version="1.0.0",
                    versions=(
                        LessonVersion(
                            version="1.0.0",
                            status="current",
                            originating_issue="owner/repo#6",
                            originating_trace=SHA,
                            applicable_code_version="commit",
                            problem_pattern="pattern",
                            solution_principle="principle",
                            validation_refs=("test",),
                            evidence_refs=(_source(),),
                        ),
                    ),
                ),
            )
        )
