"""Run reproducible Phase 3 feature, rule, and scenario-aware ML baselines."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from aegistrace.detection.rules import apply_ctu13_rules, rule_predictions, write_detection_json
from aegistrace.evaluation.baselines import BASELINE_SEED, evaluate_scenario_split
from aegistrace.evaluation.metrics import compute_binary_metrics
from aegistrace.features.network import FEATURE_VERSION, build_ctu13_features, write_feature_parquet
from aegistrace.ingestion.ctu13 import parse_ctu13_binetflow
from aegistrace.schemas.events import GroundTruthLabel


def _timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _scenario_config(
    path: Path,
    scenario_id: str,
    *,
    ingested_at: datetime,
) -> tuple[Any, dict[str, Any], Any]:
    result = parse_ctu13_binetflow(
        path,
        ingested_at=ingested_at,
        scenario_id=scenario_id,
        raw_reference=path.as_posix(),
        report_generated_at=ingested_at,
    )
    dataset = build_ctu13_features(result.events)
    return (
        result,
        {
            "scenario_id": scenario_id,
            "source_path": path.as_posix(),
            "source_checksum": result.report.raw_checksum,
            "rows_seen": result.report.rows_seen,
            "accepted_rows": result.report.accepted_rows,
            "rejected_rows": result.report.rejected_rows,
            "unknown_rows_excluded_from_supervised": sum(
                event.ground_truth_label is GroundTruthLabel.UNKNOWN for event in result.events
            ),
            "known_rows": len(dataset.supervised_records()),
        },
        dataset,
    )


def _rule_metrics(
    result: Any, scenario_id: str, created_at: datetime
) -> tuple[Any, tuple[Any, ...]]:
    detections = apply_ctu13_rules(result.events, created_at=created_at)
    predictions = rule_predictions(result.events, detections)
    known_events = tuple(
        event for event in result.events if event.ground_truth_label is not GroundTruthLabel.UNKNOWN
    )
    metrics = compute_binary_metrics(
        [event.ground_truth_label is GroundTruthLabel.MALICIOUS for event in known_events],
        [float(predictions[event.event_id]) for event in known_events],
        model_name="ctu13_flow_rules",
        split_name=scenario_id,
    )
    return metrics, detections


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train", type=Path, required=True)
    parser.add_argument("--validation", type=Path, required=True)
    parser.add_argument("--test", type=Path, required=True)
    parser.add_argument("--train-scenario", required=True)
    parser.add_argument("--validation-scenario", required=True)
    parser.add_argument("--test-scenario", required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("data/evaluation/phase3_baselines"))
    parser.add_argument("--ingested-at", required=True)
    parser.add_argument("--created-at", required=True)
    parser.add_argument("--seed", type=int, default=BASELINE_SEED)
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    ingested_at = _timestamp(args.ingested_at)
    created_at = _timestamp(args.created_at)
    scenarios = (
        ("train", args.train, args.train_scenario),
        ("validation", args.validation, args.validation_scenario),
        ("test", args.test, args.test_scenario),
    )
    parsed: dict[str, Any] = {}
    datasets: dict[str, Any] = {}
    metadata: dict[str, Any] = {}
    for split_name, path, scenario_id in scenarios:
        result, scenario_metadata, dataset = _scenario_config(
            path, scenario_id, ingested_at=ingested_at
        )
        parsed[split_name] = result
        datasets[split_name] = dataset
        metadata[split_name] = scenario_metadata

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    for split_name, dataset in datasets.items():
        write_feature_parquet(dataset, output_dir / f"{split_name}_features.parquet")

    rule_metrics: dict[str, Any] = {}
    rule_detection_counts: dict[str, int] = {}
    for split_name in ("train", "validation", "test"):
        metrics, detections = _rule_metrics(
            parsed[split_name], metadata[split_name]["scenario_id"], created_at
        )
        rule_metrics[split_name] = metrics.model_dump(mode="json")
        rule_detection_counts[split_name] = len(detections)
        write_detection_json(detections, output_dir / f"{split_name}_rule_detections.json")

    ml_metrics, predictions = evaluate_scenario_split(
        train_dataset=datasets["train"],
        validation_dataset=datasets["validation"],
        test_dataset=datasets["test"],
        seed=args.seed,
    )
    summary = {
        "schema_version": "1.0.0",
        "experiment_name": "ctu13_scenario_aware_phase3_baselines",
        "feature_version": FEATURE_VERSION,
        "seed": args.seed,
        "threshold": 0.5,
        "ingested_at": ingested_at.isoformat(),
        "created_at": created_at.isoformat(),
        "scenario_metadata": metadata,
        "rule_baseline": {
            "detector_version": "1.0.0",
            "detection_counts": rule_detection_counts,
            "metrics": rule_metrics,
        },
        "ml_baselines": {
            model_name: [metric.model_dump(mode="json") for metric in metrics]
            for model_name, metrics in ml_metrics.items()
        },
        "model_parameters": {
            "logistic_regression": {
                "class_weight": "balanced",
                "max_iter": 1000,
                "solver": "liblinear",
            },
            "random_forest": {
                "class_weight": "balanced",
                "max_depth": 12,
                "n_estimators": 200,
                "n_jobs": 1,
            },
        },
        "predictions": list(predictions),
        "methodology_note": (
            "Fit on the train scenario only; validation and test scenarios are held out. "
            "Unknown labels are excluded from supervised fitting and metrics. No scenario, "
            "filename, source label, or label-derived field is a model feature."
        ),
    }
    (output_dir / "experiment_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n"
    )
    print(
        json.dumps(
            {
                "output_dir": str(output_dir),
                "feature_version": FEATURE_VERSION,
                "seed": args.seed,
                "train_known_rows": metadata["train"]["known_rows"],
                "validation_known_rows": metadata["validation"]["known_rows"],
                "test_known_rows": metadata["test"]["known_rows"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
