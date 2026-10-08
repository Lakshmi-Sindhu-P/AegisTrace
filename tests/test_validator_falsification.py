"""Falsification suite for the pydantic model validators that guard AegisTrace records.

A validator is a *claim* that some family of bad input is rejected.  A guard that is never observed
rejecting anything is an untested claim, and this project has repeatedly shipped guards that
accepted their own worst-case input.  Every test in this module therefore takes one guard, builds
the exact input the guard exists to reject, calls the model, and asserts that construction raises.

These tests are deliberately adversarial: the fixture is the *worst case*, never a softened one.
If a guard here accepts its violating input, the test goes red on purpose (marked with a
``# FINDING:`` comment) rather than being rewritten to pass.  Valid base fixtures are reused from
the existing contract tests (``test_event_schema``, ``test_manifest_schema``, ``test_agent_trace``,
``test_experiment_registry``, ``test_triage_provider``) and only the field under test is changed.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from aegistrace.schemas.agent_trace import (
    AgentTraceRecord,
    LessonVersion,
    SolutionEntry,
    SolutionKnowledge,
)
from aegistrace.schemas.detections import DetectionSeverity
from aegistrace.schemas.events import SecurityEvent
from aegistrace.schemas.experiments import ExperimentRegistry, ExperimentRun
from aegistrace.schemas.findings import Finding
from aegistrace.schemas.manifests import DatasetManifest
from aegistrace.schemas.review import (
    EscalationState,
    HumanReview,
    ReviewDecision,
    ReviewHistory,
    ReviewTier,
    review_id_for,
)
from aegistrace.schemas.triage import (
    AssessorRole,
    DisagreementReason,
    TriageComparison,
)
from aegistrace.triage.provider import (
    ProviderDescriptor,
    ProviderKind,
    ProviderResponse,
)
from aegistrace.triage.run import RunBudget, TriageRun
from test_agent_trace import _source
from test_event_schema import fixture_payload
from test_experiment_registry import _run
from test_manifest_schema import valid_manifest_payload
from test_triage_provider import _recorded_descriptor

EARLY = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
LATE = datetime(2026, 1, 2, 0, 0, tzinfo=UTC)
REVIEWED_AT = datetime(2026, 1, 3, 0, 0, tzinfo=UTC)


def _finding(**overrides: object) -> Finding:
    """A valid finding whose window can be falsified by overriding the endpoints."""

    values: dict[str, object] = {
        "finding_id": uuid4(),
        "aggregation_version": "1.0.0",
        "event_ids": (uuid4(),),
        "detection_ids": (uuid4(),),
        "source_host": "host-1",
        "window_start": EARLY,
        "window_end": LATE,
        "proposed_severity": DetectionSeverity.MEDIUM,
        "created_at": LATE,
        "note": "deterministic grouping",
    }
    values.update(overrides)
    return Finding(**values)  # type: ignore[arg-type]


def _trace(**overrides: object) -> AgentTraceRecord:
    """A valid completed-escalation trace; callers override only the state under test."""

    values: dict[str, object] = {
        "trace_id": "a" * 32,
        "span_id": "c" * 32,
        "event_index": 0,
        "occurred_at": LATE,
        "issue_ref": "owner/repo#1",
        "workspace_ref": "workspace-1",
        "agent_ref": "agent-1",
        "branch": "main",
        "action": "escalate",
        "outcome": "blocked_human",
        "approval_state": "blocked_human",
        "reason_code": "missing_authorization",
        "confidence": "high",
        "confidence_basis": "owner policy",
        "source_refs": (_source(),),
        "escalation_request": "operator must confirm authorization",
        "summary": "Waiting on the owner.",
    }
    values.update(overrides)
    return AgentTraceRecord(**values)  # type: ignore[arg-type]


def _lesson(**overrides: object) -> LessonVersion:
    """A valid current lesson version; supersession fields are overridden per case."""

    values: dict[str, object] = {
        "version": "1.0.0",
        "status": "current",
        "originating_issue": "owner/repo#2",
        "originating_trace": "a" * 32,
        "applicable_code_version": "commit-a",
        "problem_pattern": "pattern",
        "solution_principle": "principle",
        "validation_refs": ("uv run pytest",),
        "evidence_refs": (_source(),),
    }
    values.update(overrides)
    return LessonVersion(**values)  # type: ignore[arg-type]


def _solution(solution_id: str = "solution-a", **overrides: object) -> SolutionEntry:
    """A valid single-version solution entry; callers override version history or identity."""

    values: dict[str, object] = {
        "solution_id": solution_id,
        "current_version": "1.0.0",
        "versions": (_lesson(),),
    }
    values.update(overrides)
    return SolutionEntry(**values)  # type: ignore[arg-type]


def _human_review(
    subject_triage_id: object,
    *,
    reviewer: str = "reviewer-a",
    decision: ReviewDecision = ReviewDecision.CONFIRM,
    supersedes: object = None,
    reviewed_at: datetime = REVIEWED_AT,
) -> HumanReview:
    """A valid human review, parameterized by decision and supersession link."""

    return HumanReview(
        review_id=review_id_for(
            subject_triage_id=subject_triage_id,  # type: ignore[arg-type]
            reviewer_ref=reviewer,
            decision=decision,
            reviewed_at=reviewed_at,
        ),
        subject_triage_id=subject_triage_id,  # type: ignore[arg-type]
        subject_role=AssessorRole.EXPERT_ADJUDICATOR,
        reviewer_ref=reviewer,
        tier=ReviewTier.C_EXPERT_JUDGMENT,
        decision=decision,
        notes="reviewed against the cited evidence",
        reviewed_at=reviewed_at,
        escalation_state=EscalationState.NONE,
        final_disposition="no action taken; this is a research record",
        supersedes_review_id=supersedes,  # type: ignore[arg-type]
    )


def _experiment(**overrides: object) -> ExperimentRun:
    """Rebuild the existing registry fixture with one field falsified, re-validating it."""

    payload = _run().model_dump()
    payload.update(overrides)
    return ExperimentRun(**payload)


# 1. schemas/findings.py :: Finding.validate_window


def test_finding_rejects_window_end_before_start() -> None:
    with pytest.raises(ValidationError, match="window_end must not precede window_start"):
        _finding(window_start=LATE, window_end=EARLY)


# 2. schemas/manifests.py :: DatasetManifest.validate_time_range_and_counts


def test_manifest_rejects_partial_observed_range() -> None:
    payload = valid_manifest_payload()
    payload["observed_end"] = None

    with pytest.raises(ValidationError, match="must be provided together"):
        DatasetManifest.model_validate(payload)


def test_manifest_rejects_observed_end_before_start() -> None:
    payload = valid_manifest_payload()
    payload["observed_start"] = LATE
    payload["observed_end"] = EARLY

    with pytest.raises(ValidationError, match="observed_end must not precede observed_start"):
        DatasetManifest.model_validate(payload)


def test_manifest_rejects_empty_label_distribution_with_records() -> None:
    payload = valid_manifest_payload()
    payload["record_count"] = 1
    payload["label_distribution"] = {}

    with pytest.raises(ValidationError, match="label_distribution must not be empty"):
        DatasetManifest.model_validate(payload)


# 3. schemas/events.py :: SecurityEvent.validate_evidence_identity


def test_event_rejects_event_id_detached_from_source_identity() -> None:
    payload = fixture_payload()
    payload["event_id"] = str(uuid4())

    with pytest.raises(ValidationError, match="stable source identity"):
        SecurityEvent.model_validate(payload)


def test_event_rejects_known_label_without_label_source() -> None:
    payload = fixture_payload()
    payload["ground_truth_label"] = "malicious"
    payload["label_source"] = None

    with pytest.raises(ValidationError, match="label_source is required"):
        SecurityEvent.model_validate(payload)


def test_event_rejects_attack_category_with_unknown_label() -> None:
    payload = fixture_payload()
    payload["ground_truth_label"] = "unknown"
    payload["label_source"] = None
    payload["attack_category"] = "command_and_control"

    with pytest.raises(ValidationError, match="attack_category requires"):
        SecurityEvent.model_validate(payload)


# 4. schemas/triage.py :: TriageComparison.validate_agreement_is_consistent


def test_comparison_rejects_agreement_with_disagreement_reasons() -> None:
    with pytest.raises(ValidationError, match="cannot carry disagreement reasons"):
        TriageComparison(
            comparison_id=uuid4(),
            evidence_bundle_id=uuid4(),
            assessment_ids=(uuid4(),),
            agreement=True,
            agreement_score=1.0,
            disagreement_reasons=(DisagreementReason.CATEGORY_MISMATCH,),
            escalation_recommended=False,
            created_at=LATE,
        )


# 5. schemas/agent_trace.py :: AgentTraceRecord.validate_escalation_state


def test_trace_rejects_blocked_human_without_escalation_request() -> None:
    with pytest.raises(ValidationError, match="require escalation_request"):
        _trace(outcome="blocked_human", escalation_request=None)


def test_trace_rejects_blocked_human_with_non_blocking_approval_state() -> None:
    with pytest.raises(ValidationError, match="require approval_state=blocked_human"):
        _trace(
            outcome="blocked_human",
            approval_state="approved",
            escalation_request="operator must confirm authorization",
        )


# 6. schemas/agent_trace.py :: LessonVersion.validate_supersession


def test_lesson_rejects_current_status_with_superseded_by() -> None:
    with pytest.raises(ValidationError, match="current lesson versions cannot point"):
        _lesson(status="current", superseded_by="lesson@1.1.0")


def test_lesson_rejects_superseded_status_without_superseded_by() -> None:
    with pytest.raises(ValidationError, match="superseded lesson versions require"):
        _lesson(status="superseded", superseded_by=None)


# 7. schemas/agent_trace.py :: SolutionEntry.validate_versions


def test_solution_rejects_duplicate_version_strings() -> None:
    duplicate_current = _lesson(version="1.0.0", status="current")
    duplicate_superseded = _lesson(
        version="1.0.0", status="superseded", superseded_by="lesson@1.1.0"
    )

    with pytest.raises(ValidationError, match="solution versions must be unique"):
        _solution(
            current_version="1.0.0",
            versions=(duplicate_current, duplicate_superseded),
        )


def test_solution_rejects_current_version_naming_a_different_version() -> None:
    current = _lesson(version="1.0.0", status="current")
    superseded = _lesson(version="2.0.0", status="superseded", superseded_by="lesson@1.1.0")

    with pytest.raises(ValidationError, match="exactly one version must match current_version"):
        _solution(current_version="2.0.0", versions=(current, superseded))


# 8. schemas/agent_trace.py :: SolutionKnowledge.validate_solution_ids


def test_solution_knowledge_rejects_duplicate_solution_ids() -> None:
    with pytest.raises(ValidationError, match="solution_id values must be unique"):
        SolutionKnowledge(solutions=(_solution("duplicate"), _solution("duplicate")))


# 9. triage/provider.py :: ProviderDescriptor.validate_egress_matches_kind


def test_descriptor_rejects_remote_without_required_egress() -> None:
    with pytest.raises(ValidationError, match="REMOTE provider must declare requires_egress=True"):
        ProviderDescriptor(
            name="contradiction",
            model_id="remote-model",
            model_family="remote-family",
            kind=ProviderKind.REMOTE,
            requires_egress=False,
        )


def test_descriptor_rejects_offline_kind_requiring_egress() -> None:
    with pytest.raises(ValidationError, match="must declare requires_egress=False"):
        ProviderDescriptor(
            name="contradiction",
            model_id="stub-model",
            model_family="deterministic-stub",
            kind=ProviderKind.OFFLINE_STUB,
            requires_egress=True,
        )


# 10. triage/provider.py :: ProviderResponse.validate_synthetic_matches_descriptor


def test_response_rejects_non_synthetic_from_offline_descriptor() -> None:
    with pytest.raises(ValidationError, match="must be synthetic=True"):
        ProviderResponse(
            descriptor=_recorded_descriptor(),
            role=AssessorRole.TRIAGE_ANALYST,
            snapshot_digest="b" * 64,
            raw_text='{"category": "suspicious"}',
            request_digest="c" * 64,
            response_digest="d" * 64,
            synthetic=False,
            created_at=LATE,
        )


# 11. triage/run.py :: TriageRun.validate_abort_reason


def _triage_run(**overrides: object) -> TriageRun:
    """A valid, non-aborted run over the offline recorded descriptor."""

    descriptor = _recorded_descriptor()
    values: dict[str, object] = {
        "run_id": uuid4(),
        "created_at": LATE,
        "freeze_version": "1.0.0",
        "analyst_descriptor": descriptor,
        "adjudicator_descriptor": descriptor,
        "budget": RunBudget(max_bundles_per_run=1, max_assessments_per_run=2, max_total_calls=2),
        "calls_made": 0,
        "synthetic": True,
        "aborted": False,
    }
    values.update(overrides)
    return TriageRun(**values)  # type: ignore[arg-type]


def test_triage_run_rejects_aborted_without_abort_reason() -> None:
    with pytest.raises(ValidationError, match="must record an abort_reason"):
        _triage_run(aborted=True, abort_reason=None)


def test_triage_run_rejects_abort_reason_on_completed_run() -> None:
    with pytest.raises(ValidationError, match="must not record an abort_reason"):
        _triage_run(aborted=False, abort_reason="this run did not abort")


# 12. schemas/review.py :: HumanReview.validate_correction_is_linked


def test_review_rejects_revise_without_superseded_review() -> None:
    with pytest.raises(ValidationError, match="must reference the review it supersedes"):
        _human_review(uuid4(), decision=ReviewDecision.REVISE, supersedes=None)


# 13. schemas/review.py :: ReviewHistory.validate_subjects_match


def test_review_history_rejects_review_of_a_different_subject() -> None:
    history_subject = uuid4()
    foreign_review = _human_review(uuid4())

    with pytest.raises(ValidationError, match="share the subject triage id"):
        ReviewHistory(subject_triage_id=history_subject, reviews=(foreign_review,))


# 14. schemas/experiments.py :: enforce_sealed_scenario_boundary + require_unique_experiment_ids


def test_experiment_run_must_explicitly_list_sealed_scenario() -> None:
    with pytest.raises(ValidationError, match="must explicitly list sealed Scenario 7"):
        _experiment(sealed_scenarios=())


def test_experiment_run_rejects_sealed_scenario_in_training_or_validation() -> None:
    with pytest.raises(ValidationError, match="cannot be a training or validation scenario"):
        _experiment(training_scenarios=("CTU-Malware-Capture-Botnet-48",))


def test_experiment_registry_rejects_duplicate_experiment_ids() -> None:
    with pytest.raises(ValidationError, match="experiment_id values must be unique"):
        ExperimentRegistry(runs=(_run(), _run()))
