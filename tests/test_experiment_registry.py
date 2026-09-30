"""Tests for tracked experiment lineage and aggregate uncertainty helpers."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from aegistrace.evaluation.uncertainty import confusion_intervals, wilson_interval
from aegistrace.schemas.experiments import ExperimentArtifact, ExperimentRegistry, ExperimentRun

SHA = "a" * 64


def _run(experiment_id: str = "run-1") -> ExperimentRun:
    return ExperimentRun(
        experiment_id=experiment_id,
        name="test experiment",
        status="VALIDATED",
        created_at=datetime(2026, 9, 30, tzinfo=UTC),
        code_version="a" * 7,
        dataset_versions=("ctu13-v1",),
        feature_versions=("1.1.0",),
        training_scenarios=("CTU-Malware-Capture-Botnet-52",),
        validation_scenarios=("CTU-Malware-Capture-Botnet-46",),
        seed=42,
        command="uv run pytest",
        artifact_refs=(
            ExperimentArtifact(path="data/run.json", digest=SHA, kind="artifact", tracked=False),
        ),
        documentation_refs=("docs/evaluation.md",),
        claim_boundary="validation-only evidence",
    )


def test_experiment_registry_preserves_unique_run_linkage() -> None:
    registry = ExperimentRegistry(runs=(_run(),))
    assert registry.runs[0].sealed_scenarios == ("CTU-Malware-Capture-Botnet-48",)


def test_experiment_registry_rejects_sealed_scenario_and_duplicate_ids() -> None:
    with pytest.raises(ValueError, match="sealed Scenario 7"):
        ExperimentRun(
            **_run().model_dump(exclude={"validation_scenarios"}),
            validation_scenarios=("CTU-Malware-Capture-Botnet-48",),
        )
    with pytest.raises(ValueError, match="experiment_id values must be unique"):
        ExperimentRegistry(runs=(_run(), _run()))


def test_experiment_artifact_paths_must_be_relative() -> None:
    with pytest.raises(ValueError, match="relative"):
        ExperimentArtifact(path="/tmp/run.json", digest=SHA, kind="artifact", tracked=False)


def test_wilson_interval_handles_counts_and_empty_denominators() -> None:
    interval = wilson_interval(5, 10)
    assert interval is not None
    assert 0.2 < interval[0] < 0.3
    assert 0.7 < interval[1] < 0.8
    assert wilson_interval(0, 0) is None
    with pytest.raises(ValueError, match="between zero and trials"):
        wilson_interval(2, 1)
    with pytest.raises(ValueError, match="between zero and one"):
        wilson_interval(1, 2, confidence=1.0)


def test_confusion_intervals_keep_zero_alert_precision_unknown() -> None:
    intervals = confusion_intervals(
        {"true_positive": 0, "false_positive": 0, "true_negative": 10, "false_negative": 4}
    )
    assert intervals["precision"] is None
    assert intervals["recall"] is not None
    assert intervals["false_positive_rate"] is not None
