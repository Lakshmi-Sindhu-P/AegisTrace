"""Self-consistency tests for the committed evaluation artifacts.

Each committed summary contains a headline/summary block that restates what the raw per-capture
records already show.  These tests load only the committed JSON, re-derive every headline claim
from the raw records it carries, and fail if a summary ever drifts from its own data.

Artifacts that are deliberately not tracked in git are skipped rather than failed.

One deviation to note: ``simulation_summary.json`` declares ``ORACLE`` out of scope (it reads
ground truth and is not an achievable reviewer policy) in its own ``sweep_axes.oracle_excluded``.
Coverage therefore requires the artifact's own declared routing policies plus an explicit,
documented exclusion for any expected policy that is absent, so a *silently* dropped policy still
fails.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
REPLAY_PATH = REPO_ROOT / "data/evaluation/phase3_analyst_replay/replay_summary.json"
SIMULATION_PATH = (
    REPO_ROOT / "data/evaluation/phase3_reviewer_simulation/simulation_summary.json"
)
HELDOUT_PATH = REPO_ROOT / "data/evaluation/phase3_heldout/heldout_summary.json"

STAGE1_POLICIES = ("model_score", "uncertainty", "random", "oracle")
STAGE2_COMPARISON_POLICIES = ("model_score", "uncertainty", "random")
RATE_TOLERANCE = 1e-9


def _load(path: Path) -> Any:
    """Load a committed artifact, skipping the test when it is not tracked."""

    if not path.exists():
        pytest.skip(f"evaluation artifact not present (deliberately untracked?): {path}")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _stage1_by_policy(capture: dict[str, Any]) -> dict[str, dict[int, dict[str, Any]]]:
    """Map policy name -> budget -> raw budget record."""

    return {
        policy["policy"]: {record["budget"]: record for record in policy["budgets"]}
        for policy in capture["policies"]
    }


def _stage2_by_setting(
    capture: dict[str, Any],
) -> dict[tuple[float, int, str], dict[str, Any]]:
    """Map (strictness, shift_budget, routing_policy) -> raw outcome record."""

    return {
        (
            outcome["policy"]["strictness"],
            outcome["policy"]["shift_budget"],
            outcome["policy"]["routing_policy"],
        ): outcome
        for outcome in capture["outcomes"]
    }


def _stage2_settings(capture: dict[str, Any]) -> set[tuple[float, int]]:
    return {
        (outcome["policy"]["strictness"], outcome["policy"]["shift_budget"])
        for outcome in capture["outcomes"]
    }


def _beats_pairs(entries: Any) -> set[tuple[float, int]]:
    """Normalize a headline ``..._at`` list to (strictness, shift_budget) pairs."""

    pairs: set[tuple[float, int]] = set()
    for entry in entries:
        if isinstance(entry, dict):
            pairs.add((entry["strictness"], entry["shift_budget"]))
        else:
            first, second = entry
            pairs.add((first, second))
    return pairs


def _recomputed_beats(capture: dict[str, Any]) -> set[tuple[float, int]]:
    by_setting = _stage2_by_setting(capture)
    beats: set[tuple[float, int]] = set()
    for strictness, shift_budget in _stage2_settings(capture):
        uncertainty = by_setting[(strictness, shift_budget, "uncertainty")]
        model_score = by_setting[(strictness, shift_budget, "model_score")]
        if uncertainty["true_escalations"] > model_score["true_escalations"]:
            beats.add((strictness, shift_budget))
    return beats


# ---------------------------------------------------------------------------
# Stage 1: analyst replay
# ---------------------------------------------------------------------------


def test_stage1_no_uncertainty_policy_beats_model_score_on_true_positives() -> None:
    """Re-derive the stage 1 headline from raw budgets[] only."""

    artifact = _load(REPLAY_PATH)
    violations: list[tuple[str, int, int, int]] = []
    for capture in artifact["captures"]:
        by_policy = _stage1_by_policy(capture)
        for budget, model_record in by_policy["model_score"].items():
            uncertainty_record = by_policy["uncertainty"].get(budget)
            if uncertainty_record is None:
                continue
            if uncertainty_record["true_positives"] > model_record["true_positives"]:
                violations.append(
                    (
                        capture["scenario_id"],
                        budget,
                        uncertainty_record["true_positives"],
                        model_record["true_positives"],
                    )
                )
    assert violations == [], (
        "uncertainty beats model_score on true_positives at (capture, budget, "
        f"uncertainty_tp, model_tp): {violations}"
    )


def test_stage1_budget_100_uncertainty_never_beats_model_score() -> None:
    """The headline fact at budget 100: 0 of 6 captures favour uncertainty."""

    artifact = _load(REPLAY_PATH)
    captures = artifact["captures"]
    assert captures, "replay artifact has no captures to verify"
    favoured: list[str] = []
    for capture in captures:
        by_policy = _stage1_by_policy(capture)
        model_record = by_policy["model_score"].get(100)
        uncertainty_record = by_policy["uncertainty"].get(100)
        assert model_record is not None, capture["scenario_id"]
        assert uncertainty_record is not None, capture["scenario_id"]
        if uncertainty_record["true_positives"] > model_record["true_positives"]:
            favoured.append(capture["scenario_id"])
    assert favoured == [], f"captures where uncertainty beats model_score at budget 100: {favoured}"


# ---------------------------------------------------------------------------
# Stage 2: reviewer simulation
# ---------------------------------------------------------------------------


def test_stage2_paired_uncertainty_wins_total_is_zero() -> None:
    """Total paired settings across captures where uncertainty strictly beats model_score is 0."""

    artifact = _load(SIMULATION_PATH)
    beats: list[tuple[str, float, int]] = []
    for capture in artifact["captures"]:
        by_setting = _stage2_by_setting(capture)
        for strictness, shift_budget in _stage2_settings(capture):
            uncertainty = by_setting[(strictness, shift_budget, "uncertainty")]
            model_score = by_setting[(strictness, shift_budget, "model_score")]
            if uncertainty["true_escalations"] > model_score["true_escalations"]:
                beats.append((capture["scenario_id"], strictness, shift_budget))
    assert beats == [], (
        f"uncertainty strictly beats model_score at (capture, strictness, shift): {beats}"
    )


def test_stage2_headline_block_agrees_with_raw_outcomes() -> None:
    """The artifact's own headline block must match facts recomputed from outcomes[]."""

    artifact = _load(SIMULATION_PATH)
    headline = artifact["headline"]
    by_scenario = {entry["scenario_id"]: entry for entry in headline["per_capture"]}

    recomputed_flags: list[bool] = []
    for capture in artifact["captures"]:
        scenario_id = capture["scenario_id"]
        entry = by_scenario[scenario_id]
        beats = _recomputed_beats(capture)
        assert entry["uncertainty_ever_beats_model_score"] == bool(beats), (
            f"{scenario_id}: headline flag {entry['uncertainty_ever_beats_model_score']} "
            f"but raw data shows {sorted(beats)}"
        )
        assert _beats_pairs(entry["uncertainty_beats_model_score_at"]) == beats, (
            f"{scenario_id}: headline list disagrees with raw data "
            f"({entry['uncertainty_beats_model_score_at']!r} vs {sorted(beats)!r})"
        )

        by_setting = _stage2_by_setting(capture)
        model_best = all(
            by_setting[(strictness, shift_budget, "model_score")]["true_escalations"]
            >= by_setting[(strictness, shift_budget, policy)]["true_escalations"]
            for strictness, shift_budget in _stage2_settings(capture)
            for policy in STAGE2_COMPARISON_POLICIES
        )
        assert entry["model_score_best_at_every_strictness_and_budget"] == model_best, (
            f"{scenario_id}: model_score_best flag disagrees with raw outcomes"
        )
        recomputed_flags.append(bool(beats))

    assert headline["uncertainty_ever_beats_model_score_any_capture"] == any(recomputed_flags)
    assert headline["model_score_best_at_every_strictness_and_budget_all_captures"] == all(
        entry["model_score_best_at_every_strictness_and_budget"]
        for entry in headline["per_capture"]
    )


def test_stage2_outcome_arithmetic_is_internally_consistent() -> None:
    """false_escalations, false_escalation_rate, reviewer_load and missed_detections."""

    artifact = _load(SIMULATION_PATH)
    problems: list[str] = []
    for capture in artifact["captures"]:
        malicious_rows = capture["malicious_rows"]
        for outcome in capture["outcomes"]:
            label = (capture["scenario_id"], outcome["policy"])
            if outcome["false_escalations"] != outcome["escalations"] - outcome["true_escalations"]:
                problems.append(f"{label}: false_escalations != escalations - true_escalations")
            expected_rate = (
                outcome["false_escalations"] / outcome["escalations"]
                if outcome["escalations"] > 0
                else 0.0
            )
            if abs(outcome["false_escalation_rate"] - expected_rate) > RATE_TOLERANCE:
                problems.append(
                    f"{label}: false_escalation_rate {outcome['false_escalation_rate']} "
                    f"!= {expected_rate}"
                )
            if outcome["reviewer_load"] != outcome["policy"]["shift_budget"]:
                problems.append(
                    f"{label}: reviewer_load {outcome['reviewer_load']} "
                    f"!= shift_budget {outcome['policy']['shift_budget']}"
                )
            expected_missed = malicious_rows - outcome["true_escalations"]
            if outcome["missed_detections"] != expected_missed:
                problems.append(
                    f"{label}: missed_detections {outcome['missed_detections']} "
                    f"!= {expected_missed}"
                )
    assert problems == [], "; ".join(problems)


def test_stage2_escalation_totals_are_consistent() -> None:
    """escalations == true_escalations + false_escalations for every outcome."""

    artifact = _load(SIMULATION_PATH)
    problems = [
        f"{capture['scenario_id']} {outcome['policy']}: "
        f"{outcome['escalations']} != {outcome['true_escalations']} + "
        f"{outcome['false_escalations']}"
        for capture in artifact["captures"]
        for outcome in capture["outcomes"]
        if outcome["escalations"] != outcome["true_escalations"] + outcome["false_escalations"]
    ]
    assert problems == [], "; ".join(problems)


# ---------------------------------------------------------------------------
# Held-out confusion matrices
# ---------------------------------------------------------------------------


def test_heldout_confusion_matrices_are_coherent() -> None:
    """Matrix totals match support/counts, and precision/recall re-derive from the matrix."""

    artifact = _load(HELDOUT_PATH)
    assert artifact["captures"], "held-out artifact has no captures to verify"
    problems: list[str] = []
    for capture in artifact["captures"]:
        labeled = capture["labeled"]
        (tn, fp), (fn, tp) = labeled["confusion_matrix"]
        scenario_id = capture["scenario_id"]

        if tn + fp + fn + tp != labeled["support"]:
            problems.append(f"{scenario_id}: matrix sum != support")
        if tp + fn != labeled["positive_count"]:
            problems.append(f"{scenario_id}: matrix positives != positive_count")
        if tn + fp != labeled["negative_count"]:
            problems.append(f"{scenario_id}: matrix negatives != negative_count")

        precision = tp / (tp + fp) if tp + fp > 0 else 0.0
        recall = tp / (tp + fn) if tp + fn > 0 else 0.0
        if abs(precision - labeled["precision"]) > RATE_TOLERANCE:
            problems.append(
                f"{scenario_id}: stored precision {labeled['precision']} != {precision}"
            )
        if abs(recall - labeled["recall"]) > RATE_TOLERANCE:
            problems.append(f"{scenario_id}: stored recall {labeled['recall']} != {recall}")
    assert problems == [], "; ".join(problems)


# ---------------------------------------------------------------------------
# Cross-artifact sanity and policy coverage
# ---------------------------------------------------------------------------


def test_no_capture_claims_more_true_positives_than_malicious_rows() -> None:
    """No artifact may report more hits than the capture has malicious rows."""

    replay = _load(REPLAY_PATH)
    problems = [
        f"replay {capture['scenario_id']} {policy['policy']} budget {record['budget']}: "
        f"{record['true_positives']} > {capture['malicious_rows']}"
        for capture in replay["captures"]
        for policy in capture["policies"]
        for record in policy["budgets"]
        if record["true_positives"] > capture["malicious_rows"]
    ]

    simulation = _load(SIMULATION_PATH)
    problems += [
        f"simulation {capture['scenario_id']} {outcome['policy']}: "
        f"{outcome['true_escalations']} > {capture['malicious_rows']}"
        for capture in simulation["captures"]
        for outcome in capture["outcomes"]
        if outcome["true_escalations"] > capture["malicious_rows"]
    ]

    heldout = _load(HELDOUT_PATH)
    problems += [
        f"heldout {capture['scenario_id']}: matrix true positives "
        f"{capture['labeled']['confusion_matrix'][1][1]} > positive_count "
        f"{capture['labeled']['positive_count']}"
        for capture in heldout["captures"]
        if capture["labeled"]["confusion_matrix"][1][1] > capture["labeled"]["positive_count"]
    ]

    assert problems == [], "; ".join(problems)


def test_stage1_policy_coverage_is_complete() -> None:
    """Every replay capture carries all four routing policies at every budget."""

    artifact = _load(REPLAY_PATH)
    for capture in artifact["captures"]:
        by_policy = _stage1_by_policy(capture)
        assert set(by_policy) == set(STAGE1_POLICIES), (
            f"{capture['scenario_id']}: policies {sorted(by_policy)} "
            f"!= {sorted(STAGE1_POLICIES)}"
        )
        budget_sets = {policy: set(records) for policy, records in by_policy.items()}
        reference = budget_sets["model_score"]
        for policy, budgets in budget_sets.items():
            assert budgets == reference, (
                f"{capture['scenario_id']} {policy}: budget set {sorted(budgets)} "
                f"!= model_score {sorted(reference)}"
            )


def test_stage2_policy_coverage_is_complete_and_drops_are_documented() -> None:
    """Every simulation capture carries every declared policy at every (strictness, budget).

    ``ORACLE`` is expected here yet is declared out of scope by the artifact itself; a policy that
    is missing without such a declaration is a silent drop and fails the test.
    """

    artifact = _load(SIMULATION_PATH)
    expected = tuple(artifact["sweep_axes"]["routing_policies"])
    declared_exclusions = artifact["sweep_axes"].get("oracle_excluded", "")
    for capture in artifact["captures"]:
        by_setting = _stage2_by_setting(capture)
        for strictness, shift_budget in _stage2_settings(capture):
            present = {
                policy
                for (setting_strictness, setting_budget, policy) in by_setting
                if (setting_strictness, setting_budget) == (strictness, shift_budget)
            }
            assert present == set(expected), (
                f"{capture['scenario_id']} strictness={strictness} budget={shift_budget}: "
                f"policies {sorted(present)} != {sorted(expected)}"
            )
        missing = set(STAGE1_POLICIES) - set(expected)
        if missing:
            assert declared_exclusions, (
                f"{capture['scenario_id']}: policies {sorted(missing)} are silently dropped "
                "with no documented exclusion"
            )
