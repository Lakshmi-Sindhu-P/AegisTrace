"""Report labeled metrics and unknown-label alert workload at the frozen threshold.

Read-only diagnostic. It fits the frozen validation policy on the frozen training
captures and scores the cached behavioral ``1.1.0`` artifacts for the validation
captures, reporting the unknown-label alert workload separately from labeled
metrics. Sealed Scenario 7 is rejected and is never loaded.

This script does not tune anything: the threshold, model, class weight, seed, and
feature version all come from ``configs/phase3_frozen_policy.json``.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pyarrow.parquet as pq
from numpy.typing import NDArray

from aegistrace.evaluation.improvement import make_model
from aegistrace.evaluation.metrics import compute_binary_metrics
from aegistrace.features.behavioral import BEHAVIORAL_FEATURE_NAMES
from aegistrace.schemas.events import GroundTruthLabel

POLICY_PATH = Path("configs/phase3_frozen_policy.json")
CACHE_DIR = Path("data/evaluation/phase3_model_stability")
DEFAULT_OUTPUT = Path("data/evaluation/phase3_unknown_workload/workload_summary.json")
EXTRA_VALIDATION = (
    "CTU-Malware-Capture-Botnet-45",
    "CTU-Malware-Capture-Botnet-51",
)
KNOWN_LABELS = frozenset({GroundTruthLabel.BENIGN.value, GroundTruthLabel.MALICIOUS.value})


def load_capture(
    scenario_id: str, *, sealed_scenario: str
) -> tuple[NDArray[np.float64], NDArray[np.bool_], NDArray[np.bool_]]:
    """Load one cached behavioral artifact as a feature matrix plus label masks."""

    if scenario_id == sealed_scenario:
        raise ValueError(f"{scenario_id} is the sealed scenario and must not be loaded")
    path = CACHE_DIR / f"{scenario_id}_behavioral.parquet"
    if not path.exists():
        raise FileNotFoundError(f"missing cached behavioral artifact: {path}")
    table = pq.read_table(path, columns=["ground_truth_label", *BEHAVIORAL_FEATURE_NAMES])
    label_values = np.asarray(
        table["ground_truth_label"].combine_chunks().to_pylist(), dtype=object
    )
    known = np.isin(label_values, list(KNOWN_LABELS))
    labels = label_values == GroundTruthLabel.MALICIOUS.value
    columns = [
        table[name].combine_chunks().to_numpy(zero_copy_only=False).astype(np.float64)
        for name in BEHAVIORAL_FEATURE_NAMES
    ]
    matrix = np.column_stack(columns)
    return matrix, labels, known


def capture_report(
    *,
    scenario_id: str,
    labels: NDArray[np.bool_],
    known: NDArray[np.bool_],
    scores: NDArray[np.float64],
    threshold: float,
) -> dict[str, Any]:
    """Summarize labeled metrics and unknown-label workload for one capture."""

    metrics = compute_binary_metrics(
        labels[known].tolist(),
        scores[known].tolist(),
        model_name="behavioral_random_forest",
        split_name="validation",
        threshold=threshold,
    )
    known_alerts = int(np.count_nonzero(scores[known] >= threshold))
    unknown_alerts = int(np.count_nonzero(scores[~known] >= threshold))
    unknown_rows = int(np.count_nonzero(~known))
    positive_count = int(np.count_nonzero(labels[known]))
    support = int(np.count_nonzero(known))
    return {
        "scenario_id": scenario_id,
        "threshold": threshold,
        "labeled": {
            "support": support,
            "positive_count": positive_count,
            "negative_count": support - positive_count,
            "prevalence": positive_count / support if support else None,
            "precision": metrics.precision,
            "recall": metrics.recall,
            "f1": metrics.f1,
            "pr_auc": metrics.pr_auc,
            "confusion_matrix": metrics.confusion_matrix,
        },
        "workload": {
            "known_alerts": known_alerts,
            "unknown_rows": unknown_rows,
            "unknown_alerts": unknown_alerts,
            "unknown_alert_share": unknown_alerts / unknown_rows if unknown_rows else None,
            "all_rows": support + unknown_rows,
            "all_alerts": known_alerts + unknown_alerts,
            "alerts_per_1000_labeled_flows": known_alerts / support * 1000 if support else None,
        },
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--validation",
        nargs="+",
        default=None,
        help="validation scenario identifiers (defaults to the frozen policy plus 45 and 51)",
    )
    parser.add_argument("--policy", type=Path, default=POLICY_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--created-at", default=None)
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    policy = json.loads(args.policy.read_text(encoding="utf-8"))
    sealed = str(policy["sealed_scenario"])
    threshold = float(policy["threshold"])
    train_ids = tuple(str(value) for value in policy["training_scenarios"])
    validation_ids = (
        tuple(str(value) for value in args.validation)
        if args.validation
        else tuple(str(value) for value in policy["validation_scenarios"]) + EXTRA_VALIDATION
    )

    train_parts = [load_capture(scenario_id, sealed_scenario=sealed) for scenario_id in train_ids]
    train_matrix = np.vstack([part[0] for part in train_parts])
    train_labels = np.concatenate([part[1] for part in train_parts])
    train_known = np.concatenate([part[2] for part in train_parts])

    model = make_model(
        str(policy["model"]),
        class_weight=policy["class_weight"],
        seed=int(policy["random_seed"]),
    )
    model.fit(train_matrix[train_known], train_labels[train_known])

    captures: list[dict[str, Any]] = []
    for scenario_id in validation_ids:
        matrix, labels, known = load_capture(scenario_id, sealed_scenario=sealed)
        scores = np.asarray(model.predict_proba(matrix)[:, 1], dtype=np.float64)
        captures.append(
            capture_report(
                scenario_id=scenario_id,
                labels=labels,
                known=known,
                scores=scores,
                threshold=threshold,
            )
        )

    created_at = args.created_at or datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = {
        "schema_version": "1.0.0",
        "experiment_name": "phase3_unknown_label_workload",
        "created_at": created_at,
        "policy_id": policy["policy_id"],
        "policy_path": str(args.policy),
        "feature_version": policy["feature_version"],
        "model": policy["model"],
        "class_weight": policy["class_weight"],
        "random_seed": policy["random_seed"],
        "threshold": threshold,
        "sealed_scenario": sealed,
        "training_scenarios": list(train_ids),
        "validation_scenarios": list(validation_ids),
        "methodology_note": (
            "Frozen-threshold scoring only. Unknown-label rows are scored and counted as a "
            "workload signal; they are not false positives and are excluded from labeled metrics."
        ),
        "captures": captures,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    header = (
        f"{'capture':<36}{'known':>8}{'mal':>8}{'prev':>7}{'P':>8}{'R':>8}"
        f"{'unk_rows':>10}{'unk_alerts':>11}{'unk_share':>10}"
    )
    print(header)
    for item in captures:
        labeled = item["labeled"]
        workload = item["workload"]
        prevalence = labeled["prevalence"] or 0.0
        precision = labeled["precision"] or 0.0
        recall = labeled["recall"] or 0.0
        share = workload["unknown_alert_share"] or 0.0
        print(
            f"{item['scenario_id']:<36}{labeled['support']:>8}{labeled['positive_count']:>8}"
            f"{prevalence:>7.3f}{precision:>8.4f}{recall:>8.4f}"
            f"{workload['unknown_rows']:>10}{workload['unknown_alerts']:>11}{share:>10.3f}"
        )
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
