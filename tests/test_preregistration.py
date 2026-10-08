"""Tests for the LLM A/B triage preregistration and its ordering guard.

The ordering check is the property that makes the preregistration real, so it is tested in both
directions: a provider-consuming registry run dated before ``frozen_at`` must fail, and one dated
after must pass. Failure cases use synthetic fixtures written under ``tmp_path``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.validate_preregistration import (
    DEFAULT_FREEZE,
    DEFAULT_PREREGISTRATION,
    DEFAULT_REGISTRY,
    collect_violations,
    main,
)

FROZEN_AT = "2026-10-09T00:00:00Z"
FREEZE_SPEND = "0 - nothing has been sent"
PROVIDER_COMMAND = "uv run python scripts/run_independent_triage.py"


def _prereg(**overrides: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "schema_version": "1.0.0",
        "preregistration_id": "synthetic-prereg-1.0.0",
        "frozen_at": FROZEN_AT,
        "status": "FROZEN_PRE_DATA",
        "primary_metric": [{"name": "mean_per_bundle_agreement_score"}],
        "refutation_condition": "Refuted if a complete run yields a mean below 0.50.",
        "secondary_metrics": [{"name": "escalation_rate", "exploratory": True}],
        "pre_data_attestation": {
            "provider_freeze_status": "BLOCKED_HUMAN",
            "measured_spend": FREEZE_SPEND,
        },
    }
    data.update(overrides)
    return data


def _write(tmp_path: Path, name: str, payload: Any) -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _paths(
    tmp_path: Path, prereg: dict[str, Any], runs: list[dict[str, Any]] | None = None
) -> tuple[Path, Path, Path]:
    freeze = _write(
        tmp_path,
        "freeze.json",
        {"status": "BLOCKED_HUMAN", "budget": {"measured_spend": FREEZE_SPEND}},
    )
    registry = _write(tmp_path, "registry.json", {"runs": runs or []})
    path = _write(tmp_path, "prereg.json", prereg)
    return path, freeze, registry


def _violations(
    tmp_path: Path, prereg: dict[str, Any], runs: list[dict[str, Any]] | None = None
) -> list[str]:
    return list(collect_violations(*_paths(tmp_path, prereg, runs)))


def _provider_run(
    created_at: str = "2026-10-08T22:00:00Z", **overrides: Any
) -> dict[str, Any]:
    run: dict[str, Any] = {
        "experiment_id": "synthetic-provider-run",
        "created_at": created_at,
        "command": PROVIDER_COMMAND,
        "configuration": {},
    }
    run.update(overrides)
    return run


def test_real_committed_preregistration_validates() -> None:
    assert collect_violations() == []


def test_non_frozen_status_is_rejected(tmp_path: Path) -> None:
    violations = _violations(tmp_path, _prereg(status="DRAFT"))
    assert any("FROZEN_PRE_DATA" in violation for violation in violations)


def test_missing_refutation_condition_is_rejected(tmp_path: Path) -> None:
    violations = _violations(tmp_path, _prereg(refutation_condition="  "))
    assert any("refutation_condition" in violation for violation in violations)


def test_zero_primary_metrics_is_rejected(tmp_path: Path) -> None:
    violations = _violations(tmp_path, _prereg(primary_metric=[]))
    assert any("exactly one metric" in violation for violation in violations)


def test_two_primary_metrics_are_rejected(tmp_path: Path) -> None:
    violations = _violations(
        tmp_path,
        _prereg(primary_metric=[{"name": "metric_a"}, {"name": "metric_b"}]),
    )
    assert any("exactly one metric" in violation for violation in violations)


def test_secondary_metric_without_exploratory_is_rejected(tmp_path: Path) -> None:
    violations = _violations(tmp_path, _prereg(secondary_metrics=[{"name": "escalation_rate"}]))
    assert any("exploratory: true" in violation for violation in violations)


def test_secondary_metric_with_exploratory_false_is_rejected(tmp_path: Path) -> None:
    violations = _violations(
        tmp_path,
        _prereg(secondary_metrics=[{"name": "escalation_rate", "exploratory": False}]),
    )
    assert any("exploratory: true" in violation for violation in violations)


def test_attestation_status_disagreement_is_rejected(tmp_path: Path) -> None:
    prereg = _prereg(
        pre_data_attestation={
            "provider_freeze_status": "APPROVED",
            "measured_spend": FREEZE_SPEND,
        }
    )
    violations = _violations(tmp_path, prereg)
    assert any("provider_freeze_status" in violation for violation in violations)


def test_attestation_spend_disagreement_is_rejected(tmp_path: Path) -> None:
    prereg = _prereg(
        pre_data_attestation={
            "provider_freeze_status": "BLOCKED_HUMAN",
            "measured_spend": "17.25 - a run already happened",
        }
    )
    violations = _violations(tmp_path, prereg)
    assert any("measured_spend" in violation for violation in violations)


def test_ordering_fails_when_provider_run_precedes_frozen_at(tmp_path: Path) -> None:
    violations = _violations(
        tmp_path, _prereg(), [_provider_run(created_at="2026-10-08T22:00:00Z")]
    )
    ordering = [violation for violation in violations if "ordering violation" in violation]
    assert len(ordering) == 1
    assert "strictly before" in ordering[0]


def test_ordering_passes_when_provider_run_follows_frozen_at(tmp_path: Path) -> None:
    violations = _violations(
        tmp_path, _prereg(), [_provider_run(created_at="2026-10-10T00:00:00Z")]
    )
    assert violations == []


def test_ordering_ignores_runs_that_do_not_reference_a_provider(tmp_path: Path) -> None:
    run = _provider_run(command="uv run python scripts/run_phase3_baselines.py")
    run["configuration"] = {"models": ["random_forest"]}
    violations = _violations(tmp_path, _prereg(), [run])
    assert violations == []


def test_ordering_detects_provider_reference_in_configuration(tmp_path: Path) -> None:
    run = _provider_run(command="uv run python scripts/runner.py")
    run["configuration"] = {"assessors": ["triage_analyst", "expert_adjudicator"]}
    violations = _violations(tmp_path, _prereg(), [run])
    assert any("ordering violation" in violation for violation in violations)


def test_ordering_fails_when_provider_run_has_unparseable_created_at(tmp_path: Path) -> None:
    run = _provider_run()
    run["created_at"] = "not-a-timestamp"
    violations = _violations(tmp_path, _prereg(), [run])
    assert any("cannot be proven to predate" in violation for violation in violations)


def test_main_prints_success_json_and_exits_zero(capsys: Any) -> None:
    assert main([]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["preregistration"] == DEFAULT_PREREGISTRATION
    assert payload["status"] == "FROZEN_PRE_DATA"
    assert payload["primary_metric"] == "mean_per_bundle_agreement_score"
    assert payload["frozen_at"] == FROZEN_AT
    assert payload["violations"] == []
    assert DEFAULT_FREEZE.endswith("triage_provider_freeze.json")
    assert DEFAULT_REGISTRY.endswith("experiment_registry.json")


def test_main_lists_every_violation_and_exits_one(tmp_path: Path, capsys: Any) -> None:
    prereg = _prereg(
        status="DRAFT",
        refutation_condition="",
        primary_metric=[{"name": "metric_a"}, {"name": "metric_b"}],
        secondary_metrics=[{"name": "escalation_rate"}],
    )
    path, freeze, registry = _paths(tmp_path, prereg)
    assert main([str(path), "--freeze", str(freeze), "--registry", str(registry)]) == 1
    err = capsys.readouterr().err
    payload = json.loads(err[err.index('{\n  "preregistration"') :])
    assert len(payload["violations"]) == 4
    assert sum(line.startswith("VIOLATION:") for line in err.splitlines()) == 4
