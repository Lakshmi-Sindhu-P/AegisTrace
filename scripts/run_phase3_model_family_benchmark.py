"""Run the post-amendment CTU-13 model-family benchmark.

The command accepts training and validation scenarios only. Scenario 7 is
explicitly rejected and there is no test argument. Supervised models fit only
known labels; Isolation Forest is reported separately as an unlabeled anomaly
prioritization experiment.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from aegistrace.detection.rules import apply_ctu13_rules, rule_predictions
from aegistrace.evaluation.metrics import compute_binary_metrics
from aegistrace.evaluation.model_family import (
    FIXED_POLICY_THRESHOLD,
    MODEL_FAMILY_NAMES,
    MODEL_FAMILY_VERSION,
    alert_volume_for_scores,
    artifact_fit_metadata,
    disagreement_report,
    fit_isolation_forest_scores,
    fit_supervised_scores,
    known,
    metrics_for_scores,
    scenario_metrics,
    select_validation_threshold,
)
from aegistrace.features.behavioral import (
    BEHAVIORAL_FEATURE_NAMES,
    BEHAVIORAL_FEATURE_VERSION,
    BehavioralFeatureDataset,
    build_ctu13_behavioral_features,
    write_behavioral_feature_parquet,
)
from aegistrace.ingestion.ctu13 import parse_ctu13_binetflow
from aegistrace.schemas.events import GroundTruthLabel, SecurityEvent

SEED = 42
SEALED_SCENARIO_ID = "CTU-Malware-Capture-Botnet-48"
INTERPRETABILITY: dict[str, str] = {
    "rules": "high; explicit predicates and observed-value evidence",
    "logistic_regression": "high; linear coefficients after standardized inputs",
    "decision_tree": "high; shallow path-based decisions",
    "random_forest": "medium; feature importance and multiple trees",
    "extra_trees": "medium-low; randomized tree ensemble",
    "hist_gradient_boosting": "medium; additive tree stages",
    "svm": "medium-low; linear margin is less directly inspectable",
    "isolation_forest": "medium-low; anomaly path lengths, not class evidence",
}


@dataclass(frozen=True, slots=True)
class ScenarioData:
    """Loaded events and behavioral features for one complete scenario."""

    events: tuple[SecurityEvent, ...]
    dataset: BehavioralFeatureDataset
    metadata: dict[str, Any]


def _timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _load_scenario(
    path: Path,
    scenario_id: str,
    *,
    ingested_at: datetime,
    output_dir: Path,
) -> ScenarioData:
    if scenario_id == SEALED_SCENARIO_ID:
        raise ValueError("the final held-out Scenario 7 is sealed for this benchmark")
    result = parse_ctu13_binetflow(
        path,
        ingested_at=ingested_at,
        scenario_id=scenario_id,
        raw_reference=path.as_posix(),
        report_generated_at=ingested_at,
    )
    dataset = build_ctu13_behavioral_features(result.events)
    write_behavioral_feature_parquet(dataset, output_dir / f"{scenario_id}_behavioral.parquet")
    metadata = {
        "scenario_id": scenario_id,
        "dataset_version": result.report.dataset_version,
        "source_path": path.as_posix(),
        "source_checksum": result.report.raw_checksum,
        "source_size_bytes": path.stat().st_size,
        "rows_seen": result.report.rows_seen,
        "accepted_rows": result.report.accepted_rows,
        "rejected_rows": result.report.rejected_rows,
        "known_rows": len(dataset.supervised_records()),
        "unknown_rows_excluded_from_supervised": sum(
            event.ground_truth_label is GroundTruthLabel.UNKNOWN for event in result.events
        ),
        "label_distribution": result.report.label_distribution,
    }
    return ScenarioData(events=tuple(result.events), dataset=dataset, metadata=metadata)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--train", action="append", nargs=2, metavar=("PATH", "SCENARIO"), required=True
    )
    parser.add_argument(
        "--validation", action="append", nargs=2, metavar=("PATH", "SCENARIO"), required=True
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path("data/evaluation/phase3_model_family")
    )
    parser.add_argument("--ingested-at", required=True)
    parser.add_argument("--created-at", required=True)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument(
        "--skip-svm",
        action="store_true",
        help="Skip SVM only when resource limits make the explicitly scoped run impractical.",
    )
    return parser


def _rule_result(
    validation_events: tuple[SecurityEvent, ...],
    validation_records: tuple[Any, ...],
    *,
    created_at: datetime,
) -> tuple[dict[str, Any], dict[str, bool]]:
    detections = apply_ctu13_rules(validation_events, created_at=created_at)
    predictions = rule_predictions(validation_events, detections)
    scores = {
        str(record.event_id): float(predictions.get(record.event_id, False))
        for record in validation_records
    }
    metrics = compute_binary_metrics(
        [
            record.ground_truth_label is GroundTruthLabel.MALICIOUS
            for record in known(validation_records)
        ],
        [scores[str(record.event_id)] for record in known(validation_records)],
        model_name="rules:ctu13_flow_rules:v1.0.0",
        split_name="validation",
        threshold=0.5,
    )
    return (
        {
            "status": "completed",
            "feature_version": "rules_v1.0.0",
            "threshold": 0.5,
            "fixed_policy_metrics": metrics.model_dump(mode="json"),
            "validation_scenario_metrics": scenario_metrics(
                detector_name="rules:ctu13_flow_rules:v1.0.0",
                validation_records=validation_records,
                scores=scores,
                threshold=0.5,
            ),
            "alert_volume": {
                "known_alerts": sum(
                    scores[str(record.event_id)] >= 0.5 for record in known(validation_records)
                ),
                "unknown_rows": len(validation_records) - len(known(validation_records)),
                "unknown_alerts": sum(
                    scores[str(record.event_id)] >= 0.5
                    for record in validation_records
                    if record.ground_truth_label is GroundTruthLabel.UNKNOWN
                ),
                "all_validation_alerts": sum(scores.values()),
            },
            "interpretability": INTERPRETABILITY["rules"],
            "rule_count": len(detections),
        },
        {str(event_id): prediction for event_id, prediction in predictions.items()},
    )


def _family_result(
    name: str,
    *,
    train_records: tuple[Any, ...],
    validation_records: tuple[Any, ...],
    validation_metadata: dict[str, Any],
    seed: int,
) -> tuple[dict[str, Any], dict[str, bool]]:
    scores, runtime = fit_supervised_scores(
        name,
        train_records=train_records,
        validation_records=validation_records,
        seed=seed,
    )
    detector_name = f"behavioral_{BEHAVIORAL_FEATURE_VERSION}:{name}"
    print(f"fit_seconds[{name}]: {runtime['fit_seconds']:.6f}", file=sys.stderr)
    fixed = metrics_for_scores(
        detector_name=detector_name,
        validation_records=validation_records,
        scores=scores,
        threshold=FIXED_POLICY_THRESHOLD,
    )
    selected, tradeoff = select_validation_threshold(
        detector_name=detector_name,
        validation_records=validation_records,
        scores=scores,
    )
    predictions = {event_id: score >= FIXED_POLICY_THRESHOLD for event_id, score in scores.items()}
    return (
        {
            "status": "completed",
            "feature_version": BEHAVIORAL_FEATURE_VERSION,
            "fixed_policy_threshold": FIXED_POLICY_THRESHOLD,
            "fixed_policy_metrics": fixed.model_dump(mode="json"),
            "validation_selected_threshold": selected.model_dump(mode="json"),
            "threshold_tradeoff": [metric.model_dump(mode="json") for metric in tradeoff],
            "validation_scenario_metrics_at_fixed_policy": scenario_metrics(
                detector_name=detector_name,
                validation_records=validation_records,
                scores=scores,
                threshold=FIXED_POLICY_THRESHOLD,
            ),
            "alert_volume_at_fixed_policy": alert_volume_for_scores(
                validation_records=validation_records,
                scores=scores,
                threshold=FIXED_POLICY_THRESHOLD,
            ),
            "fit_metadata": artifact_fit_metadata(runtime),
            "interpretability": INTERPRETABILITY[name],
            "parameters": {
                "class_weight": "balanced"
                if name != "hist_gradient_boosting"
                else "balanced_sample_weight",
                "seed": seed,
            },
            "validation_scenario_count": len(validation_metadata),
        },
        predictions,
    )


def _anomaly_result(
    *,
    train_records: tuple[Any, ...],
    validation_records: tuple[Any, ...],
    validation_metadata: dict[str, Any],
    seed: int,
) -> tuple[dict[str, Any], dict[str, bool]]:
    scores, runtime = fit_isolation_forest_scores(
        train_records=train_records,
        validation_records=validation_records,
        seed=seed,
    )
    detector_name = f"behavioral_{BEHAVIORAL_FEATURE_VERSION}:isolation_forest"
    print(f"fit_seconds[isolation_forest]: {runtime['fit_seconds']:.6f}", file=sys.stderr)
    fixed = metrics_for_scores(
        detector_name=detector_name,
        validation_records=validation_records,
        scores=scores,
        threshold=FIXED_POLICY_THRESHOLD,
    )
    selected, tradeoff = select_validation_threshold(
        detector_name=detector_name,
        validation_records=validation_records,
        scores=scores,
    )
    predictions = {event_id: score >= FIXED_POLICY_THRESHOLD for event_id, score in scores.items()}
    return (
        {
            "status": "completed",
            "feature_version": BEHAVIORAL_FEATURE_VERSION,
            "fixed_policy_threshold": FIXED_POLICY_THRESHOLD,
            "fixed_policy_metrics": fixed.model_dump(mode="json"),
            "validation_selected_threshold": selected.model_dump(mode="json"),
            "threshold_tradeoff": [metric.model_dump(mode="json") for metric in tradeoff],
            "validation_scenario_metrics_at_fixed_policy": scenario_metrics(
                detector_name=detector_name,
                validation_records=validation_records,
                scores=scores,
                threshold=FIXED_POLICY_THRESHOLD,
            ),
            "alert_volume_at_fixed_policy": alert_volume_for_scores(
                validation_records=validation_records,
                scores=scores,
                threshold=FIXED_POLICY_THRESHOLD,
            ),
            "fit_metadata": artifact_fit_metadata(runtime),
            "interpretability": INTERPRETABILITY["isolation_forest"],
            "parameters": {"contamination": "auto", "n_estimators": 100, "seed": seed},
            "validation_scenario_count": len(validation_metadata),
            "evaluation_note": (
                "Unsupervised ranking experiment. Unknown rows remain unknown and are not used as "
                "benign ground truth. The practical baseline was fit on known feature rows without "
                "passing labels to Isolation Forest; unknown validation rows were scored only for "
                "separate workload analysis."
            ),
        },
        predictions,
    )


def main() -> int:
    args = _build_parser().parse_args()
    ingested_at = _timestamp(args.ingested_at)
    created_at = _timestamp(args.created_at)
    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    train_data: list[ScenarioData] = []
    validation_data: list[ScenarioData] = []
    metadata: dict[str, list[dict[str, Any]]] = {"train": [], "validation": []}
    for specs, target in ((args.train, train_data), (args.validation, validation_data)):
        for raw_path, scenario_id in specs:
            loaded = _load_scenario(
                Path(raw_path),
                scenario_id,
                ingested_at=ingested_at,
                output_dir=output_dir,
            )
            target.append(loaded)
            metadata["train" if target is train_data else "validation"].append(loaded.metadata)

    train_records = tuple(record for item in train_data for record in item.dataset.records)
    validation_records = tuple(
        record for item in validation_data for record in item.dataset.records
    )
    validation_events = tuple(event for item in validation_data for event in item.events)
    validation_metadata = {item["scenario_id"]: item for item in metadata["validation"]}

    model_results: dict[str, dict[str, Any]] = {}
    prediction_sets: dict[str, dict[str, bool]] = {}
    rule_result, rule_predictions_by_event = _rule_result(
        validation_events,
        validation_records,
        created_at=created_at,
    )
    model_results["rules"] = rule_result
    prediction_sets["rules"] = rule_predictions_by_event

    for family in MODEL_FAMILY_NAMES:
        if family == "svm" and args.skip_svm:
            model_results[family] = {
                "status": "skipped",
                "reason": "explicit --skip-svm configuration",
                "interpretability": INTERPRETABILITY[family],
            }
            continue
        try:
            result, predictions = _family_result(
                family,
                train_records=train_records,
                validation_records=validation_records,
                validation_metadata=validation_metadata,
                seed=args.seed,
            )
        except (MemoryError, RuntimeError, ValueError) as error:
            model_results[family] = {
                "status": "failed_or_not_practical",
                "error": f"{type(error).__name__}: {error}",
                "interpretability": INTERPRETABILITY[family],
            }
            continue
        model_results[family] = result
        prediction_sets[family] = predictions

    anomaly_result, anomaly_predictions = _anomaly_result(
        train_records=train_records,
        validation_records=validation_records,
        validation_metadata=validation_metadata,
        seed=args.seed,
    )
    model_results["isolation_forest"] = anomaly_result
    prediction_sets["isolation_forest"] = anomaly_predictions

    summary = {
        "schema_version": "1.0.0",
        "experiment_name": "ctu13_phase3_post_amendment_model_family_benchmark",
        "model_family_version": MODEL_FAMILY_VERSION,
        "feature_version": BEHAVIORAL_FEATURE_VERSION,
        "feature_names": BEHAVIORAL_FEATURE_NAMES,
        "seed": args.seed,
        "ingested_at": ingested_at.isoformat(),
        "created_at": created_at.isoformat(),
        "source_checksums": {
            item["scenario_id"]: item["source_checksum"]
            for split in metadata.values()
            for item in split
        },
        "scenario_metadata": metadata,
        "split_policy": {
            "training_scenarios": [item["scenario_id"] for item in metadata["train"]],
            "validation_scenarios": [item["scenario_id"] for item in metadata["validation"]],
            "unknown_labels": (
                "excluded from supervised fitting and labeled metrics; retained for context and "
                "separately scored by the unsupervised experiment"
            ),
            "final_test": "Scenario 7 sealed and not loaded, tuned, or reported",
        },
        "fixed_policy_threshold": FIXED_POLICY_THRESHOLD,
        "model_results": model_results,
        "disagreement": disagreement_report(
            validation_records=validation_records,
            detector_predictions=prediction_sets,
        ),
        "methodology_note": (
            "All models use behavioral feature version 1.1.0, scenario-local prior-only "
            "aggregates, complete scenario boundaries, and no labels, filenames, scenario IDs, "
            "source labels, or raw addresses in model matrices. No fusion, neural network, "
            "semi-supervised method, "
            "clustering, LLM, or Scenario 7 evaluation was performed."
        ),
    }
    output_path = output_dir / "benchmark_summary.json"
    output_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "output": str(output_path),
                "training_scenarios": summary["split_policy"]["training_scenarios"],
                "validation_scenarios": summary["split_policy"]["validation_scenarios"],
                "completed_detectors": [
                    name
                    for name, result in model_results.items()
                    if result["status"] == "completed"
                ],
                "non_completed_detectors": {
                    name: result["status"]
                    for name, result in model_results.items()
                    if result["status"] != "completed"
                },
                "scenario_7": "sealed",
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
