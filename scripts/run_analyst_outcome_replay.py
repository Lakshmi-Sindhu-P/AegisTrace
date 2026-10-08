"""Replay the frozen Phase-3 policy through fixed alert-routing policies.

This runner fits the exact frozen model (``RandomForestClassifier``,
``class_weight='balanced'``, ``random_state=42``, ``max_depth=12``,
``n_estimators=200``, ``n_jobs=1``) on the frozen training captures, scores each
of the six evaluation captures at the frozen threshold, and then replays four
routing policies over the resulting scores: ``model_score``, ``uncertainty``
(closest to the decision boundary first), ``random`` (negative control), and
``oracle`` (label-aware upper bound).

What it measures is the value of the ROUTING of already-computed scores.  It is
not a study of human cognition, and nothing here is a claim about analyst
behaviour, over-reliance, trust calibration, or automation bias.  A policy that
beats ``model_score`` is only meaningful if it also beats ``random``.

Nothing is tuned: the threshold, the model, and the feature set are read from
the frozen policy and never searched.  ``GroundTruthLabel.UNKNOWN`` rows are
excluded from the labeled evaluation, never counted as false positives, and
reported separately as ``unknown_rows``.  Each capture is evaluated separately
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
    DEFAULT_RECALL_TARGETS,
    DEFAULT_SEED,
    BudgetSpec,
    CaptureReplay,
    replay_capture,
)
from aegistrace.schemas.common import normalize_utc

POLICY_PATH = Path("configs/phase3_frozen_policy.json")
CACHE_DIR = Path("data/evaluation/phase3_model_stability")
HELDOUT_DIR = Path("data/evaluation/phase3_heldout")
DEFAULT_OUTPUT = Path("data/evaluation/phase3_analyst_replay/replay_summary.json")
VALIDATION_SCENARIOS = ("CTU-Malware-Capture-Botnet-46", "CTU-Malware-Capture-Botnet-53")
HELDOUT_SCENARIOS = (
    "CTU-Malware-Capture-Botnet-48",
    "CTU-Malware-Capture-Botnet-49",
    "CTU-Malware-Capture-Botnet-50",
    "CTU-Malware-Capture-Botnet-54",
)
ABSOLUTE_BUDGETS = (10, 25, 50, 100, 200, 500)
FRACTION_BUDGETS = (("0.1%", 0.001), ("1%", 0.01), ("5%", 0.05))


def _budget_specs() -> tuple[BudgetSpec, ...]:
    specs = [
        BudgetSpec(label=str(k), kind="absolute", value=float(k)) for k in ABSOLUTE_BUDGETS
    ]
    specs.extend(
        BudgetSpec(label=label, kind="fraction", value=value)
        for label, value in FRACTION_BUDGETS
    )
    return tuple(specs)


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


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", type=Path, default=POLICY_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--created-at",
        required=True,
        help="ISO 8601 timestamp with timezone, e.g. 2026-10-08T21:00:00Z",
    )
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    created_at = normalize_utc(datetime.fromisoformat(args.created_at))
    policy = json.loads(args.policy.read_text(encoding="utf-8"))
    threshold = float(policy["threshold"])
    train_ids = tuple(str(value) for value in policy["training_scenarios"])
    evaluation_ids = (*VALIDATION_SCENARIOS, *HELDOUT_SCENARIOS)
    budgets = _budget_specs()
    recall_targets = tuple(float(value) for value in DEFAULT_RECALL_TARGETS)

    print(f"[model] fitting frozen model on {list(train_ids)}", flush=True)
    model = _fit_frozen_model(policy, train_ids)

    print(f"[replay] evaluating {len(evaluation_ids)} captures separately", flush=True)
    replays: list[CaptureReplay] = []
    for scenario_id in evaluation_ids:
        path = _capture_path(scenario_id)
        matrix, labels, known = load_feature_parquet(path)
        event_ids = load_event_ids(path)
        scores = np.asarray(model.predict_proba(matrix)[:, 1], dtype=np.float64)
        replay = replay_capture(
            scenario_id=scenario_id,
            event_ids=event_ids,
            scores=scores,
            labels=labels,
            known=known,
            threshold=threshold,
            budgets=budgets,
            recall_targets=recall_targets,
            seed=DEFAULT_SEED,
        )
        replays.append(replay)
        print(
            f"[replay] {scenario_id}: labeled={replay.labeled_rows} "
            f"malicious={replay.malicious_rows} unknown={replay.unknown_rows}",
            flush=True,
        )
        del matrix, labels, known, scores, event_ids
        gc.collect()

    payload = {
        "schema_version": "1.0.0",
        "experiment_name": "phase3_analyst_outcome_replay",
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
        "routing_seed": DEFAULT_SEED,
        "training_scenarios": list(train_ids),
        "evaluation_scenarios": list(evaluation_ids),
        "validation_scenarios": list(VALIDATION_SCENARIOS),
        "heldout_scenarios": list(HELDOUT_SCENARIOS),
        "budgets": [spec.model_dump(mode="json") for spec in budgets],
        "recall_targets": list(recall_targets),
        "sealed_scenario": policy["sealed_scenario"],
        "sealed_scenario_note": (
            "Capture 48 is the sealed scenario; it is replayed from the already-materialized "
            "behavioral feature artifact under the frozen policy. No raw re-ingestion, threshold "
            "search, or tuning occurs here."
        ),
        "methodology_note": (
            "Deterministic measurement of alert routing only. Unknown-label rows are excluded "
            "from every labeled evaluation, never counted as false positives, and reported "
            "separately as unknown_rows. Each capture is evaluated separately; no pooling is "
            "performed. oracle is a label-aware upper bound and random is the negative control; "
            "a policy beating model_score is only meaningful if it also beats random."
        ),
        "routing_value_disclaimer": (
            "This measures the value of the ROUTING of already-computed scores. It is not a "
            "study of human cognition and makes no claim about analyst behaviour, over-reliance, "
            "trust calibration, or automation bias."
        ),
        "pooled": {
            "reported": False,
            "note": (
                "No pooled figure is reported. Pooling captures would lose capture identity and "
                "let large captures dominate the headline numbers."
            ),
        },
        "captures": [replay.model_dump(mode="json") for replay in replays],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(
        f"{'capture':<36}{'labeled':>9}{'mal':>7}{'unknown':>9}"
        f"{'TP100_ms':>10}{'TP100_un':>10}{'TP100_rn':>10}{'auc_ms':>9}{'auc_un':>9}"
    )
    for replay in replays:
        by_policy = {result.policy: result for result in replay.policies}
        model_score = by_policy["model_score"]
        uncertainty = by_policy["uncertainty"]
        random_policy = by_policy["random"]
        model_100 = next(point for point in model_score.budgets if point.label == "100")
        uncertainty_100 = next(point for point in uncertainty.budgets if point.label == "100")
        random_100 = next(point for point in random_policy.budgets if point.label == "100")
        print(
            f"{replay.scenario_id:<36}{replay.labeled_rows:>9}{replay.malicious_rows:>7}"
            f"{replay.unknown_rows:>9}{model_100.true_positives:>10}"
            f"{uncertainty_100.true_positives:>10}{random_100.true_positives:>10}"
            f"{model_score.coverage_auc:>9.4f}{uncertainty.coverage_auc:>9.4f}"
        )
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
