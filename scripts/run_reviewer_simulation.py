"""Sweep an explicit reviewer policy over the frozen Phase-3 policy (stage 2).

Stage 1 showed that routing by decision-boundary uncertainty lost to routing by model score on all
six captures.  This runner asks whether that negative result is an artifact of one routing rule: it
fits the exact frozen model (``RandomForestClassifier``, ``class_weight='balanced'``,
``random_state=42``, ``max_depth=12``, ``n_estimators=200``, ``n_jobs=1``) on the frozen training
captures, scores the same six evaluation captures at the frozen threshold, and sweeps a stated
reviewer policy over strictness x shift budget x routing policy.

The reviewer is a POLICY, not a person: it works alerts in routing order up to a shift budget and
escalates iff ``score >= strictness``.  This is a stated assumption set, is NOT observed analyst
behaviour, and is not evidence about analyst decision quality, over-reliance, trust calibration, or
automation bias.  ``model_score`` is the incumbent baseline from stage 1, and ``ORACLE`` is omitted
because it reads ground-truth labels and is not achievable.

Nothing is tuned: the threshold, the model, and the feature set come from the frozen policy and are
never searched.  ``GroundTruthLabel.UNKNOWN`` rows are excluded from every queue, never counted as
false positives, and reported separately as ``unknown_rows``.  Each capture is evaluated separately
and the per-capture figures are never pooled.
"""

from __future__ import annotations

import argparse
import gc
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pyarrow.parquet as pq
from numpy.typing import NDArray
from sklearn.ensemble import RandomForestClassifier

try:
    from scripts.run_phase3_heldout_battery import load_feature_parquet
except ModuleNotFoundError:  # executed as a plain script with ``scripts`` on sys.path
    from run_phase3_heldout_battery import load_feature_parquet

from aegistrace.evaluation.analyst_replay import (
    DEFAULT_SEED,
    BudgetSpec,
    RoutingPolicy,
)
from aegistrace.evaluation.reviewer_simulation import (
    DEFAULT_SHIFT_BUDGETS,
    DEFAULT_STRICTNESS_VALUES,
    CaptureSimulation,
    ReviewerOutcome,
    simulate_capture,
)
from aegistrace.schemas.common import normalize_utc

POLICY_PATH = Path("configs/phase3_frozen_policy.json")
CACHE_DIR = Path("data/evaluation/phase3_model_stability")
HELDOUT_DIR = Path("data/evaluation/phase3_heldout")
DEFAULT_OUTPUT = Path("data/evaluation/phase3_reviewer_simulation/simulation_summary.json")
VALIDATION_SCENARIOS = ("CTU-Malware-Capture-Botnet-46", "CTU-Malware-Capture-Botnet-53")
HELDOUT_SCENARIOS = (
    "CTU-Malware-Capture-Botnet-48",
    "CTU-Malware-Capture-Botnet-49",
    "CTU-Malware-Capture-Botnet-50",
    "CTU-Malware-Capture-Botnet-54",
)
SWEEP_POLICIES = (
    RoutingPolicy.MODEL_SCORE,
    RoutingPolicy.UNCERTAINTY,
    RoutingPolicy.RANDOM,
)
SIMULATION_DISCLAIMER = (
    "This is a simulated reviewer under stated assumptions. It is not observed human behaviour and "
    "is not evidence about analyst decision quality, over-reliance, trust calibration, or "
    "automation bias."
)
BASELINE_NOTE = (
    "model_score is the incumbent baseline established by stage 1; a swept reviewer policy is only "
    "interesting where it beats model_score at the same strictness and shift budget."
)


def _shift_budget_specs() -> tuple[BudgetSpec, ...]:
    return tuple(
        BudgetSpec(label=str(k), kind="absolute", value=float(k)) for k in DEFAULT_SHIFT_BUDGETS
    )


def _capture_path(scenario_id: str) -> Path:
    """Locate a behavioral feature artifact for one capture."""

    cache_path = CACHE_DIR / f"{scenario_id}_behavioral.parquet"
    if cache_path.exists():
        return cache_path
    heldout_path = HELDOUT_DIR / f"{scenario_id}_behavioral.parquet"
    if heldout_path.exists():
        return heldout_path
    raise FileNotFoundError(f"missing behavioral artifact for {scenario_id}")


def load_event_ids(path: Path) -> list[str]:
    """Read only the ``event_id`` column for deterministic tie-breaking."""

    table = pq.read_table(path, columns=["event_id"])
    return [str(value) for value in table["event_id"].combine_chunks().to_pylist()]


def _fit_frozen_model(
    policy: dict[str, Any], train_ids: tuple[str, ...]
) -> RandomForestClassifier:
    """Fit the frozen model on known-label training rows only."""

    matrices: list[NDArray[np.float64]] = []
    labels: list[NDArray[np.bool_]] = []
    for scenario_id in train_ids:
        matrix, capture_labels, known = load_feature_parquet(_capture_path(scenario_id))
        matrices.append(matrix[known])
        labels.append(capture_labels[known])
    train_matrix = np.vstack(matrices)
    train_labels = np.concatenate(labels)
    hyperparameters = dict(policy["hyperparameters"])
    model = RandomForestClassifier(
        class_weight=policy["class_weight"],
        max_depth=int(hyperparameters["max_depth"]),
        n_estimators=int(hyperparameters["n_estimators"]),
        n_jobs=int(hyperparameters["n_jobs"]),
        random_state=int(policy["random_seed"]),
    )
    model.fit(train_matrix, train_labels)
    return model


def _best_true_escalations(
    outcomes: list[ReviewerOutcome], policy: RoutingPolicy, shift_budget: int
) -> int:
    """Best (largest) true-escalation count for one policy at one shift budget."""

    values = [
        outcome.true_escalations
        for outcome in outcomes
        if outcome.policy.routing_policy is policy and outcome.policy.shift_budget == shift_budget
    ]
    return max(values) if values else 0


def _headline_entry(
    simulation: CaptureSimulation,
    *,
    largest_shift_budget: int,
    strictness_values: tuple[float, ...],
    shift_budgets: tuple[int, ...],
) -> dict[str, Any]:
    """Best-at-largest-budget comparison plus any equal-setting uncertainty win."""

    outcomes = list(simulation.outcomes)
    lookup = {
        (outcome.policy.routing_policy, outcome.policy.strictness, outcome.policy.shift_budget): (
            outcome.true_escalations
        )
        for outcome in outcomes
    }
    wins: list[dict[str, Any]] = []
    model_score_never_beaten = True
    for strictness in strictness_values:
        for shift_budget in shift_budgets:
            model_score = lookup[(RoutingPolicy.MODEL_SCORE, strictness, shift_budget)]
            uncertainty = lookup[(RoutingPolicy.UNCERTAINTY, strictness, shift_budget)]
            random_policy = lookup[(RoutingPolicy.RANDOM, strictness, shift_budget)]
            if uncertainty > model_score:
                wins.append(
                    {
                        "strictness": strictness,
                        "shift_budget": shift_budget,
                        "model_score_true_escalations": model_score,
                        "uncertainty_true_escalations": uncertainty,
                    }
                )
            if uncertainty > model_score or random_policy > model_score:
                model_score_never_beaten = False
    best_by_policy = {
        policy.value: _best_true_escalations(outcomes, policy, largest_shift_budget)
        for policy in SWEEP_POLICIES
    }
    best_value = max(best_by_policy.values())
    if best_by_policy[RoutingPolicy.MODEL_SCORE.value] == best_value:
        winning_policy = RoutingPolicy.MODEL_SCORE.value
    else:
        winning_policy = next(
            name for name, value in best_by_policy.items() if value == best_value
        )
    return {
        "scenario_id": simulation.scenario_id,
        "largest_shift_budget": largest_shift_budget,
        "best_true_escalations_at_largest_budget": best_by_policy,
        "best_policy_at_largest_budget": winning_policy,
        "uncertainty_ever_beats_model_score": bool(wins),
        "uncertainty_beats_model_score_at": wins,
        "model_score_best_at_every_strictness_and_budget": model_score_never_beaten,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", type=Path, default=POLICY_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--created-at",
        required=True,
        help="ISO 8601 timestamp with timezone, e.g. 2026-10-08T22:00:00Z",
    )
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    created_at = normalize_utc(datetime.fromisoformat(args.created_at))
    policy = json.loads(args.policy.read_text(encoding="utf-8"))
    threshold = float(policy["threshold"])
    train_ids = tuple(str(value) for value in policy["training_scenarios"])
    evaluation_ids = (*VALIDATION_SCENARIOS, *HELDOUT_SCENARIOS)
    strictness_values = tuple(float(value) for value in DEFAULT_STRICTNESS_VALUES)
    shift_budgets = tuple(int(value) for value in DEFAULT_SHIFT_BUDGETS)
    largest_shift_budget = max(shift_budgets)

    print(f"[model] fitting frozen model on {list(train_ids)}", flush=True)
    model = _fit_frozen_model(policy, train_ids)

    print(
        f"[simulate] sweeping {len(evaluation_ids)} captures separately over "
        f"{len(strictness_values) * len(shift_budgets) * len(SWEEP_POLICIES)} reviewer policies",
        flush=True,
    )
    simulations: list[CaptureSimulation] = []
    for scenario_id in evaluation_ids:
        path = _capture_path(scenario_id)
        matrix, labels, known = load_feature_parquet(path)
        event_ids = load_event_ids(path)
        scores = np.asarray(model.predict_proba(matrix)[:, 1], dtype=np.float64)
        simulation = simulate_capture(
            scenario_id=scenario_id,
            scores=scores,
            labels=labels,
            known=known,
            threshold=threshold,
            strictness_values=strictness_values,
            shift_budgets=shift_budgets,
            policies=SWEEP_POLICIES,
            seed=DEFAULT_SEED,
            event_ids=event_ids,
        )
        simulations.append(simulation)
        print(
            f"[simulate] {scenario_id}: labeled={simulation.labeled_rows} "
            f"malicious={simulation.malicious_rows} unknown={simulation.unknown_rows}",
            flush=True,
        )
        del matrix, labels, known, scores, event_ids
        gc.collect()

    headline_entries = [
        _headline_entry(
            simulation,
            largest_shift_budget=largest_shift_budget,
            strictness_values=strictness_values,
            shift_budgets=shift_budgets,
        )
        for simulation in simulations
    ]
    headline = {
        "largest_shift_budget": largest_shift_budget,
        "per_capture": headline_entries,
        "uncertainty_ever_beats_model_score_any_capture": any(
            entry["uncertainty_ever_beats_model_score"] for entry in headline_entries
        ),
        "model_score_best_at_every_strictness_and_budget_all_captures": all(
            entry["model_score_best_at_every_strictness_and_budget"]
            for entry in headline_entries
        ),
        "question": (
            "Does uncertainty ever beat model_score at equal strictness and shift budget?"
        ),
    }

    payload = {
        "schema_version": "1.0.0",
        "experiment_name": "phase3_reviewer_simulation",
        "created_at": created_at.isoformat().replace("+00:00", "Z"),
        "policy_id": policy["policy_id"],
        "policy_path": args.policy.as_posix(),
        "feature_version": policy["feature_version"],
        "model": policy["model"],
        "class_weight": policy["class_weight"],
        "random_seed": policy["random_seed"],
        "hyperparameters": policy["hyperparameters"],
        "threshold": threshold,
        "threshold_search": "none",
        "simulation_seed": DEFAULT_SEED,
        "training_scenarios": list(train_ids),
        "evaluation_scenarios": list(evaluation_ids),
        "validation_scenarios": list(VALIDATION_SCENARIOS),
        "heldout_scenarios": list(HELDOUT_SCENARIOS),
        "sealed_scenario": policy["sealed_scenario"],
        "sealed_scenario_note": (
            "Capture 48 is the sealed scenario; it is simulated from the already-materialized "
            "behavioral feature artifact under the frozen policy. No raw re-ingestion, threshold "
            "search, or tuning occurs here."
        ),
        "sweep_axes": {
            "strictness_values": list(strictness_values),
            "shift_budgets": [spec.model_dump(mode="json") for spec in _shift_budget_specs()],
            "routing_policies": [policy_name.value for policy_name in SWEEP_POLICIES],
            "oracle_excluded": (
                "ORACLE is omitted: it reads ground-truth labels and is not an achievable "
                "reviewer policy."
            ),
        },
        "reviewer_model": {
            "queue_order": "routing policy order over known-label rows only",
            "shift_budget": "alerts worked, min(shift_budget, labeled_rows)",
            "escalation_rule": "escalate iff score >= strictness",
            "unworked": "alerts beyond the shift budget are never worked",
            "assumption_note": (
                "The reviewer is an explicit policy, not a human model. These are stated "
                "assumptions and are not calibrated to, or validated against, observed analysts."
            ),
            "uncertainty_definition": "ascending |score - threshold|, as in stage 1",
        },
        "simulation_disclaimer": SIMULATION_DISCLAIMER,
        "baseline_note": BASELINE_NOTE,
        "methodology_note": (
            "Deterministic sweep of a stated reviewer policy. Unknown-label rows are excluded from "
            "every queue, never counted as false positives, and reported separately as "
            "unknown_rows. Each capture is evaluated separately; no pooling is performed. "
            "false_escalation_rate is false_escalations / escalations and missed_detection_rate is "
            "missed_detections / malicious_rows."
        ),
        "pooled": {
            "reported": False,
            "note": (
                "No pooled figure is reported. Pooling captures would lose capture identity and "
                "let large captures dominate the headline numbers."
            ),
        },
        "headline": headline,
        "captures": [simulation.model_dump(mode="json") for simulation in simulations],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(
        f"{'capture':<36}{'malicious':>10}{'ms@200':>8}{'un@200':>8}{'rn@200':>8}"
        f"{'un>ms':>7}{'ms_best':>9}"
    )
    malicious_by_id = {
        simulation.scenario_id: simulation.malicious_rows for simulation in simulations
    }
    for entry in headline_entries:
        best = entry["best_true_escalations_at_largest_budget"]
        print(
            f"{entry['scenario_id']:<36}"
            f"{malicious_by_id[entry['scenario_id']]:>10}"
            f"{best['model_score']:>8}{best['uncertainty']:>8}{best['random']:>8}"
            f"{entry['uncertainty_ever_beats_model_score']!s:>7}"
            f"{entry['model_score_best_at_every_strictness_and_budget']!s:>9}"
        )
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
