"""Run the sealed-test-safe RF/HGB/linear-SVM stability pass.

This runner is intentionally narrower than the earlier model-family benchmark:
it evaluates only retained rules, Random Forest, HistGradientBoosting, and a
linear SVM.  It accepts training and validation scenarios only and refuses the
sealed CTU-13 Scenario 7 identifier.  Operating thresholds are selected on the
pooled validation labels under an explicit precision/workload policy.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from aegistrace.detection.rules import apply_ctu13_rules, rule_predictions
from aegistrace.evaluation.metrics import compute_binary_metrics
from aegistrace.evaluation.model_family import (
    FIXED_POLICY_THRESHOLD,
    OPERATING_ALERTS_PER_1000_CAP,
    OPERATING_PRECISION_FLOOR,
    alert_volume_for_scores,
    disagreement_report,
    fit_supervised_scores,
    known,
    metrics_for_scores,
    scenario_metrics,
    select_operating_threshold,
)
from aegistrace.features.behavioral import (
    BEHAVIORAL_FEATURE_NAMES,
    BEHAVIORAL_FEATURE_VERSION,
    BehavioralFeatureDataset,
    BehavioralFeatureRecord,
    build_ctu13_behavioral_features,
    write_behavioral_feature_parquet,
)
from aegistrace.ingestion.ctu13 import ctu13_source_url, parse_ctu13_binetflow
from aegistrace.schemas.events import GroundTruthLabel, SecurityEvent

SEED = 42
SEALED_SCENARIO_ID = "CTU-Malware-Capture-Botnet-48"
FOCUSED_MODELS = ("random_forest", "hist_gradient_boosting", "svm")
INTERPRETABILITY: dict[str, str] = {
    "rules": "high; explicit predicates and observed-value evidence",
    "random_forest": "medium; feature importance and multiple trees",
    "hist_gradient_boosting": "medium; additive tree stages",
    "svm": "medium-low; linear margin is less directly inspectable",
}


@dataclass(frozen=True, slots=True)
class ScenarioData:
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
        raise ValueError("the final held-out Scenario 7 is sealed for this stability pass")
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
        "source_url": ctu13_source_url(scenario_id, path.name),
        "source_path": path.as_posix(),
        "source_checksum": result.report.raw_checksum,
        "source_size_bytes": path.stat().st_size,
        "dataset_version": result.report.dataset_version,
        "rows_seen": result.report.rows_seen,
        "accepted_rows": result.report.accepted_rows,
        "rejected_rows": result.report.rejected_rows,
        "known_rows": len(dataset.supervised_records()),
        "unknown_rows": sum(
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
        "--output-dir", type=Path, default=Path("data/evaluation/phase3_model_stability")
    )
    parser.add_argument("--ingested-at", required=True)
    parser.add_argument("--created-at", required=True)
    parser.add_argument("--seed", type=int, default=SEED)
    return parser


def _rule_result(
    validation_records: tuple[BehavioralFeatureRecord, ...],
    *,
    scores: dict[str, float],
    rule_count: int,
) -> tuple[dict[str, Any], dict[str, bool]]:
    predictions = {event_id: score >= 0.5 for event_id, score in scores.items()}
    labeled = known(validation_records)
    metrics = compute_binary_metrics(
        [record.ground_truth_label is GroundTruthLabel.MALICIOUS for record in labeled],
        [scores[str(record.event_id)] for record in labeled],
        model_name="rules:ctu13_flow_rules:v1.0.0",
        split_name="validation",
        threshold=0.5,
    )
    return (
        {
            "status": "completed",
            "score_semantics": (
                "binary rule trigger score: 1.0 when an evidence-traceable rule fires, else 0.0"
            ),
            "threshold_policy": "native deterministic threshold 0.5; no validation tuning",
            "operating_metrics": metrics.model_dump(mode="json"),
            "validation_scenario_metrics": scenario_metrics(
                detector_name="rules:ctu13_flow_rules:v1.0.0",
                validation_records=validation_records,
                scores=scores,
                threshold=0.5,
            ),
            "alert_volume": alert_volume_for_scores(
                validation_records=validation_records, scores=scores, threshold=0.5
            ),
            "interpretability": INTERPRETABILITY["rules"],
            "rule_count": rule_count,
        },
        {str(event_id): prediction for event_id, prediction in predictions.items()},
    )


def _model_result(
    name: str,
    *,
    train_records: tuple[BehavioralFeatureRecord, ...],
    validation_records: tuple[BehavioralFeatureRecord, ...],
    validation_scenario_count: int,
    seed: int,
) -> tuple[dict[str, Any], dict[str, float], dict[str, bool]]:
    scores, runtime = fit_supervised_scores(
        name,
        train_records=train_records,
        validation_records=validation_records,
        seed=seed,
    )
    detector_name = f"behavioral_{BEHAVIORAL_FEATURE_VERSION}:{name}"
    fixed = metrics_for_scores(
        detector_name=detector_name,
        validation_records=validation_records,
        scores=scores,
        threshold=FIXED_POLICY_THRESHOLD,
    )
    selected, tradeoff, policy = select_operating_threshold(
        detector_name=detector_name,
        validation_records=validation_records,
        scores=scores,
    )
    operating_threshold = selected.threshold
    predictions = {event_id: score >= operating_threshold for event_id, score in scores.items()}
    result = {
        "status": "completed",
        "feature_version": BEHAVIORAL_FEATURE_VERSION,
        "score_semantics": {
            "random_forest": (
                "sklearn predict_proba positive-class column; ranking/probability-like, "
                "not independently calibrated"
            ),
            "hist_gradient_boosting": (
                "sklearn predict_proba positive-class column; ranking/probability-like, "
                "not independently calibrated"
            ),
            "svm": (
                "LinearSVC decision_function margin, min-max normalized using training margins; "
                "not a probability"
            ),
        }[name],
        "fixed_policy_threshold": FIXED_POLICY_THRESHOLD,
        "fixed_policy_metrics": fixed.model_dump(mode="json"),
        "operating_threshold": operating_threshold,
        "operating_policy": policy,
        "operating_metrics": selected.model_dump(mode="json"),
        "threshold_tradeoff": list(tradeoff),
        "validation_scenario_metrics_at_operating_point": scenario_metrics(
            detector_name=detector_name,
            validation_records=validation_records,
            scores=scores,
            threshold=operating_threshold,
        ),
        "alert_volume_at_operating_point": alert_volume_for_scores(
            validation_records=validation_records,
            scores=scores,
            threshold=operating_threshold,
        ),
        "fit_runtime_seconds": runtime["fit_seconds"],
        "runtime": runtime,
        "interpretability": INTERPRETABILITY[name],
        "parameters": {
            "class_weight": "balanced"
            if name != "hist_gradient_boosting"
            else "balanced_sample_weight",
            "seed": seed,
        },
        "validation_scenario_count": validation_scenario_count,
    }
    return result, scores, predictions


def _quantile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = min(len(ordered) - 1, max(0, math.floor((len(ordered) - 1) * fraction)))
    return ordered[position]


def _feature_summary(
    records: tuple[BehavioralFeatureRecord, ...],
    *,
    reference_malicious: tuple[BehavioralFeatureRecord, ...],
) -> dict[str, Any]:
    if not records:
        return {"count": 0}
    index = {name: position for position, name in enumerate(BEHAVIORAL_FEATURE_NAMES)}
    numeric: dict[str, Any] = {}
    for name in (
        "prior_source_connections_60s",
        "prior_unique_destinations_300s",
        "prior_unique_destination_ports_300s",
        "source_traffic_asymmetry",
        "source_traffic_asymmetry_missing",
        "prior_repeated_short_connections_300s",
        "duration_seconds",
        "log_total_bytes",
        "log_packet_count",
    ):
        values = [record.values[index[name]] for record in records]
        numeric[name] = {
            "median": statistics.median(values),
            "mean": statistics.fmean(values),
        }
    protocol_names = (
        "protocol_tcp",
        "protocol_udp",
        "protocol_icmp",
        "protocol_other",
        "protocol_missing",
    )
    numeric["protocol_mix"] = {
        name: statistics.fmean(record.values[index[name]] for record in records)
        for name in protocol_names
    }
    reference_values = {
        name: [record.values[index[name]] for record in reference_malicious]
        for name in (
            "prior_source_connections_60s",
            "prior_unique_destinations_300s",
            "prior_unique_destination_ports_300s",
        )
    }
    low_activity = sum(
        record.values[index["prior_source_connections_60s"]]
        <= _quantile(reference_values["prior_source_connections_60s"], 0.25)
        for record in records
    )
    low_destination_diversity = sum(
        record.values[index["prior_unique_destinations_300s"]]
        <= _quantile(reference_values["prior_unique_destinations_300s"], 0.25)
        for record in records
    )
    low_port_diversity = sum(
        record.values[index["prior_unique_destination_ports_300s"]]
        <= _quantile(reference_values["prior_unique_destination_ports_300s"], 0.25)
        for record in records
    )
    return {
        "count": len(records),
        "features": numeric,
        "reference_q25": {
            name: _quantile(values, 0.25) for name, values in reference_values.items()
        },
        "fraction_at_or_below_reference_q25": {
            "low_activity": low_activity / len(records),
            "low_destination_diversity": low_destination_diversity / len(records),
            "low_port_diversity": low_port_diversity / len(records),
        },
    }


def _unique_svm_analysis(
    *,
    validation_records: tuple[BehavioralFeatureRecord, ...],
    predictions: dict[str, dict[str, bool]],
) -> dict[str, Any]:
    malicious = tuple(
        record
        for record in validation_records
        if record.ground_truth_label is GroundTruthLabel.MALICIOUS
    )
    unique = tuple(
        record
        for record in malicious
        if predictions["svm"].get(str(record.event_id), False)
        and not predictions["random_forest"].get(str(record.event_id), False)
        and not predictions["hist_gradient_boosting"].get(str(record.event_id), False)
    )
    by_scenario: dict[str, dict[str, Any]] = {}
    for scenario_id in sorted({record.scenario_id for record in malicious}):
        scenario_malicious = tuple(
            record for record in malicious if record.scenario_id == scenario_id
        )
        scenario_unique = tuple(record for record in unique if record.scenario_id == scenario_id)
        by_scenario[scenario_id] = {
            "malicious_cases": len(scenario_malicious),
            "unique_svm_cases": len(scenario_unique),
            "unique_svm_rate": len(scenario_unique) / len(scenario_malicious)
            if scenario_malicious
            else None,
        }
    unique_ids = {str(record.event_id) for record in unique}
    others = tuple(record for record in malicious if str(record.event_id) not in unique_ids)
    return {
        "definition": (
            "malicious cases caught by SVM and missed by both RF and HGB at their pooled "
            "validation operating thresholds"
        ),
        "total_unique_cases": len(unique),
        "scenario_breakdown": by_scenario,
        "scenarios_with_unique_cases": sum(
            bool(item["unique_svm_cases"]) for item in by_scenario.values()
        ),
        "scenario_count": len(by_scenario),
        "unique_cases": _feature_summary(unique, reference_malicious=malicious),
        "other_malicious_cases": _feature_summary(others, reference_malicious=malicious),
        "stability_interpretation": (
            "descriptive only; subgroup labels and quantiles were not used for threshold selection"
        ),
    }


def _residual_error_analysis(
    *,
    validation_records: tuple[BehavioralFeatureRecord, ...],
    predictions: dict[str, dict[str, bool]],
) -> dict[str, Any]:
    malicious = tuple(
        record
        for record in validation_records
        if record.ground_truth_label is GroundTruthLabel.MALICIOUS
    )
    missed = tuple(
        record
        for record in malicious
        if not any(predictions[name].get(str(record.event_id), False) for name in FOCUSED_MODELS)
    )
    by_scenario = {
        scenario_id: sum(record.scenario_id == scenario_id for record in missed)
        for scenario_id in sorted({record.scenario_id for record in malicious})
    }
    return {
        "definition": (
            "malicious validation cases missed by RF, HGB, and SVM at their pooled validation "
            "operating thresholds"
        ),
        "total_cases": len(missed),
        "by_scenario": by_scenario,
        "feature_summary": _feature_summary(missed, reference_malicious=malicious),
    }


def main() -> int:
    args = _build_parser().parse_args()
    ingested_at = _timestamp(args.ingested_at)
    created_at = _timestamp(args.created_at)
    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    train_datasets: list[BehavioralFeatureDataset] = []
    validation_datasets: list[BehavioralFeatureDataset] = []
    metadata: dict[str, list[dict[str, Any]]] = {"train": [], "validation": []}
    rule_scores: dict[str, float] = {}
    rule_count = 0
    for specs, target, split in (
        (args.train, train_datasets, "train"),
        (args.validation, validation_datasets, "validation"),
    ):
        for raw_path, scenario_id in specs:
            loaded = _load_scenario(
                Path(raw_path),
                scenario_id,
                ingested_at=ingested_at,
                output_dir=output_dir,
            )
            if split == "validation":
                validation_events = loaded.events
                detections = apply_ctu13_rules(validation_events, created_at=created_at)
                scenario_rule_predictions = rule_predictions(validation_events, detections)
                rule_count += len(detections)
                rule_scores.update(
                    {
                        str(record.event_id): float(
                            scenario_rule_predictions.get(record.event_id, False)
                        )
                        for record in loaded.dataset.records
                    }
                )
            target.append(loaded.dataset)
            metadata[split].append(loaded.metadata)
            del loaded

    train_records = tuple(record for item in train_datasets for record in item.records)
    validation_records = tuple(record for item in validation_datasets for record in item.records)
    prediction_sets: dict[str, dict[str, bool]] = {}
    model_results: dict[str, dict[str, Any]] = {}

    rule_result, rule_prediction_set = _rule_result(
        validation_records, scores=rule_scores, rule_count=rule_count
    )
    model_results["rules"] = rule_result
    prediction_sets["rules"] = rule_prediction_set

    for name in FOCUSED_MODELS:
        result, _scores, predictions = _model_result(
            name,
            train_records=train_records,
            validation_records=validation_records,
            validation_scenario_count=len(metadata["validation"]),
            seed=args.seed,
        )
        model_results[name] = result
        prediction_sets[name] = predictions

    learned_disagreement = disagreement_report(
        validation_records=validation_records,
        detector_predictions={name: prediction_sets[name] for name in FOCUSED_MODELS},
    )
    all_disagreement = disagreement_report(
        validation_records=validation_records,
        detector_predictions=prediction_sets,
    )
    summary = {
        "schema_version": "1.0.0",
        "experiment_name": "ctu13_phase3_cross_scenario_model_stability",
        "created_at": created_at.isoformat(),
        "ingested_at": ingested_at.isoformat(),
        "seed": args.seed,
        "feature_version": BEHAVIORAL_FEATURE_VERSION,
        "feature_names": BEHAVIORAL_FEATURE_NAMES,
        "training_scenarios": [item["scenario_id"] for item in metadata["train"]],
        "validation_scenarios": [item["scenario_id"] for item in metadata["validation"]],
        "source_checksums": {
            item["scenario_id"]: item["source_checksum"]
            for split in metadata.values()
            for item in split
        },
        "scenario_metadata": metadata,
        "score_and_threshold_semantics": {
            "fixed_threshold_comparison": (
                "Historical 0.20 comparisons are only within each model's own score scale; "
                "0.20 is not equivalent evidence across RF/HGB probabilities, SVM normalized "
                "margins, Isolation Forest normalized anomaly scores, or binary rules."
            ),
            "random_forest": (
                "predict_proba positive-class output; threshold is a model-specific score cutoff, "
                "not assumed calibrated probability"
            ),
            "hist_gradient_boosting": (
                "predict_proba positive-class output; threshold is a model-specific score cutoff, "
                "not assumed calibrated probability"
            ),
            "linear_svm": (
                "decision_function margin min-max normalized using training margins; threshold is "
                "a normalized margin cutoff and is not a probability"
            ),
            "isolation_forest": (
                "negative decision_function (higher means more anomalous) min-max normalized "
                "using training anomaly scores; threshold is an anomaly-prioritization cutoff "
                "and unknown rows remain unknown"
            ),
            "rules": "binary trigger score with native threshold 0.5",
        },
        "operating_policy": {
            "objective": "maximize recall on pooled validation labels",
            "precision_floor": OPERATING_PRECISION_FLOOR,
            "alerts_per_1000_labeled_flows_cap": OPERATING_ALERTS_PER_1000_CAP,
            "threshold_selection": (
                "validation-only; 0.01 candidate increments on each detector's own score scale"
            ),
            "unknown_rows": (
                "excluded from supervised fitting, precision, recall, PR-AUC, and constraint "
                "denominators; unknown alert workload reported separately"
            ),
        },
        "model_results": model_results,
        "disagreement": {
            "learned_models": learned_disagreement,
            "including_rules": all_disagreement,
        },
        "svm_unique_coverage": _unique_svm_analysis(
            validation_records=validation_records,
            predictions=prediction_sets,
        ),
        "residual_error_analysis": _residual_error_analysis(
            validation_records=validation_records,
            predictions=prediction_sets,
        ),
        "methodology_note": (
            "Training uses known Normal/Botnet labels from the original Scenario 11 and 47 pool. "
            "Validation is pooled across four complete non-sealed scenarios; scenario-local "
            "prior-only behavioral features are rebuilt independently per scenario. No label, "
            "source filename, "
            "scenario ID, raw address, Scenario 7 row, fusion, or additional model family was used."
        ),
    }
    output_path = output_dir / "stability_summary.json"
    output_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "output": str(output_path),
                "training_scenarios": summary["training_scenarios"],
                "validation_scenarios": summary["validation_scenarios"],
                "models": list(FOCUSED_MODELS),
                "scenario_7": "sealed",
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
