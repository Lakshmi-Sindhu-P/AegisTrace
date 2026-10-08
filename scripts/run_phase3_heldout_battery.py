"""Run the frozen-policy held-out exam battery on capture-grouped exam captures.

This runner ingests each exam capture, builds behavioral ``1.1.0`` features, fits
the frozen validation policy on the frozen training captures, and scores every
exam capture at the frozen threshold. It never searches for a threshold and never
tunes after a result.

Sealed capture 48 (Scenario 7) may be included only with an explicit
``--acknowledge-sealed-opening`` flag, because including it consumes the one-time
Scenario 7 opening recorded in ``docs/evaluation.md``.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pyarrow.parquet as pq
from numpy.typing import NDArray

from aegistrace.evaluation.improvement import make_model
from aegistrace.evaluation.metrics import compute_binary_metrics
from aegistrace.features.behavioral import (
    BEHAVIORAL_FEATURE_NAMES,
    BehavioralFeatureDataset,
    build_ctu13_behavioral_features,
    write_behavioral_feature_parquet,
)
from aegistrace.ingestion.ctu13 import parse_ctu13_binetflow
from aegistrace.schemas.events import GroundTruthLabel

POLICY_PATH = Path("configs/phase3_frozen_policy.json")
CACHE_DIR = Path("data/evaluation/phase3_model_stability")
FEATURE_DIR = Path("data/evaluation/phase3_heldout")
DEFAULT_OUTPUT = Path("data/evaluation/phase3_heldout/heldout_summary.json")
KNOWN_LABELS = frozenset({GroundTruthLabel.BENIGN.value, GroundTruthLabel.MALICIOUS.value})

Matrix = NDArray[np.float64]
Mask = NDArray[np.bool_]


def load_feature_parquet(path: Path) -> tuple[Matrix, Mask, Mask]:
    """Load one behavioral feature artifact as a matrix plus label masks."""

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
    return np.column_stack(columns), labels, known


def load_cached(scenario_id: str, *, cache_dir: Path, sealed: str) -> tuple[Matrix, Mask, Mask]:
    """Load one cached training artifact, refusing the sealed scenario."""

    if scenario_id == sealed:
        raise ValueError(f"{scenario_id} is sealed and must be opened through the battery runner")
    path = cache_dir / f"{scenario_id}_behavioral.parquet"
    if not path.exists():
        raise FileNotFoundError(f"missing cached behavioral artifact: {path}")
    return load_feature_parquet(path)


def _dataset_arrays(dataset: BehavioralFeatureDataset) -> tuple[Matrix, Mask, Mask]:
    matrix = np.asarray([record.values for record in dataset.records], dtype=np.float64)
    labels = np.asarray(
        [record.ground_truth_label is GroundTruthLabel.MALICIOUS for record in dataset.records],
        dtype=bool,
    )
    known = np.asarray(
        [record.ground_truth_label in (GroundTruthLabel.BENIGN, GroundTruthLabel.MALICIOUS)
         for record in dataset.records],
        dtype=bool,
    )
    return matrix, labels, known


def load_or_build_exam(
    path: Path,
    scenario_id: str,
    *,
    ingested_at: datetime,
    feature_dir: Path,
    rebuild: bool,
) -> tuple[Matrix, Mask, Mask, dict[str, Any]]:
    """Load a cached exam feature artifact, or ingest and build it once."""

    feature_path = feature_dir / f"{scenario_id}_behavioral.parquet"
    if feature_path.exists() and not rebuild:
        print(f"[features] reusing {feature_path}", file=sys.stderr, flush=True)
        matrix, labels, known = load_feature_parquet(feature_path)
        return matrix, labels, known, {
            "scenario_id": scenario_id,
            "feature_path": feature_path.as_posix(),
            "source": "cache",
        }
    print(f"[features] parsing {scenario_id} from {path}", file=sys.stderr, flush=True)
    result = parse_ctu13_binetflow(
        path,
        ingested_at=ingested_at,
        scenario_id=scenario_id,
        raw_reference=path.as_posix(),
        report_generated_at=ingested_at,
    )
    print(
        f"[features] parsed {scenario_id}: accepted={result.report.accepted_rows} "
        f"rejected={result.report.rejected_rows}",
        file=sys.stderr,
        flush=True,
    )
    dataset = build_ctu13_behavioral_features(result.events)
    print(
        f"[features] built {scenario_id}: {len(dataset.records)} records",
        file=sys.stderr,
        flush=True,
    )
    feature_dir.mkdir(parents=True, exist_ok=True)
    write_behavioral_feature_parquet(dataset, feature_path)
    matrix, labels, known = _dataset_arrays(dataset)
    metadata = {
        "scenario_id": scenario_id,
        "feature_path": feature_path.as_posix(),
        "source": "built",
        "source_path": path.as_posix(),
        "source_checksum": result.report.raw_checksum,
        "source_size_bytes": path.stat().st_size,
        "rows_seen": result.report.rows_seen,
        "accepted_rows": result.report.accepted_rows,
        "rejected_rows": result.report.rejected_rows,
        "label_distribution": result.report.label_distribution,
    }
    return matrix, labels, known, metadata


def capture_report(
    *,
    scenario_id: str,
    labels: Mask,
    known: Mask,
    scores: Matrix,
    threshold: float,
) -> dict[str, Any]:
    """Summarize labeled metrics and unknown-label workload for one capture."""

    metrics = compute_binary_metrics(
        labels[known].tolist(),
        scores[known].tolist(),
        model_name="behavioral_random_forest",
        split_name="held_out",
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
        "--exam",
        action="append",
        nargs=2,
        metavar=("PATH", "SCENARIO"),
        required=True,
        help="exam capture raw path and scenario identifier; repeat per capture",
    )
    parser.add_argument("--policy", type=Path, default=POLICY_PATH)
    parser.add_argument("--cache-dir", type=Path, default=CACHE_DIR)
    parser.add_argument("--feature-dir", type=Path, default=FEATURE_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--ingested-at", default=None)
    parser.add_argument("--created-at", default=None)
    parser.add_argument("--acknowledge-sealed-opening", action="store_true")
    parser.add_argument(
        "--features-only",
        action="store_true",
        help="build or reuse the exam feature artifacts and exit without scoring",
    )
    parser.add_argument(
        "--rebuild-features",
        action="store_true",
        help="rebuild exam feature artifacts even when a cached artifact exists",
    )
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    policy = json.loads(args.policy.read_text(encoding="utf-8"))
    sealed = str(policy["sealed_scenario"])
    threshold = float(policy["threshold"])
    train_ids = tuple(str(value) for value in policy["training_scenarios"])
    ingested_at = (
        datetime.fromisoformat(args.ingested_at) if args.ingested_at else datetime.now(UTC)
    )
    if ingested_at.tzinfo is None:
        ingested_at = ingested_at.replace(tzinfo=UTC)
    for _, scenario_id in args.exam:
        if scenario_id == sealed and not args.acknowledge_sealed_opening:
            raise ValueError(
                f"{scenario_id} is the sealed scenario; pass --acknowledge-sealed-opening "
                "to consume the one-time opening"
            )
    if args.features_only:
        for raw_path, scenario_id in args.exam:
            load_or_build_exam(
                Path(raw_path),
                scenario_id,
                ingested_at=ingested_at,
                feature_dir=args.feature_dir,
                rebuild=args.rebuild_features,
            )
        return 0

    train_parts = [
        load_cached(scenario_id, cache_dir=args.cache_dir, sealed=sealed)
        for scenario_id in train_ids
    ]
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
    metadata: list[dict[str, Any]] = []
    for raw_path, scenario_id in args.exam:
        matrix, labels, known, item_metadata = load_or_build_exam(
            Path(raw_path),
            scenario_id,
            ingested_at=ingested_at,
            feature_dir=args.feature_dir,
            rebuild=args.rebuild_features,
        )
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
        metadata.append(item_metadata)

    created_at = args.created_at or datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = {
        "schema_version": "1.0.0",
        "experiment_name": "phase3_heldout_exam_battery",
        "created_at": created_at,
        "policy_id": policy["policy_id"],
        "policy_path": str(args.policy),
        "feature_version": policy["feature_version"],
        "model": policy["model"],
        "class_weight": policy["class_weight"],
        "random_seed": policy["random_seed"],
        "threshold": threshold,
        "threshold_search": "none",
        "sealed_scenario": sealed,
        "sealed_opening_acknowledged": bool(args.acknowledge_sealed_opening),
        "training_scenarios": list(train_ids),
        "exam_scenarios": [scenario_id for _, scenario_id in args.exam],
        "methodology_note": (
            "Frozen-policy scoring only, no threshold search. Unknown-label rows are scored and "
            "counted as a workload signal; they are not false positives and are excluded from "
            "precision, recall, and PR-AUC. Every capture is reported individually."
        ),
        "capture_metadata": metadata,
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
        print(
            f"{item['scenario_id']:<36}{labeled['support']:>8}{labeled['positive_count']:>8}"
            f"{(labeled['prevalence'] or 0.0):>7.3f}{(labeled['precision'] or 0.0):>8.4f}"
            f"{(labeled['recall'] or 0.0):>8.4f}{workload['unknown_rows']:>10}"
            f"{workload['unknown_alerts']:>11}{(workload['unknown_alert_share'] or 0.0):>10.3f}"
        )
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
