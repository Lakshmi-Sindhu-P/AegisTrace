"""Evaluate the stability pass from immutable behavioral feature artifacts.

The raw-ingestion runner writes versioned Parquet artifacts.  This companion
command reuses those artifacts for expensive model scoring, avoiding a second
materialization of the same large canonical event files.  It has the same
training/validation policy and never accepts or opens Scenario 7.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

import pyarrow.parquet as pq

try:
    from scripts.run_phase3_model_stability import (
        FOCUSED_MODELS,
        INTERPRETABILITY,
        SEALED_SCENARIO_ID,
        _residual_error_analysis,
        _unique_svm_analysis,
    )
except ModuleNotFoundError:
    from run_phase3_model_stability import (
        FOCUSED_MODELS,
        INTERPRETABILITY,
        SEALED_SCENARIO_ID,
        _residual_error_analysis,
        _unique_svm_analysis,
    )

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
from aegistrace.features.behavioral import BEHAVIORAL_FEATURE_NAMES, BEHAVIORAL_FEATURE_VERSION
from aegistrace.schemas.events import GroundTruthLabel

SEED = 42
RAW_ROOT = Path("data/raw/ctu13")
RAW_FILES: dict[str, Path] = {
    "CTU-Malware-Capture-Botnet-45": RAW_ROOT
    / "CTU-Malware-Capture-Botnet-45/capture20110815.binetflow",
    "CTU-Malware-Capture-Botnet-46": RAW_ROOT
    / "CTU-Malware-Capture-Botnet-46/capture20110815-2.binetflow",
    "CTU-Malware-Capture-Botnet-47": RAW_ROOT
    / "CTU-Malware-Capture-Botnet-47/capture20110816.binetflow",
    "CTU-Malware-Capture-Botnet-51": RAW_ROOT
    / "CTU-Malware-Capture-Botnet-51/capture20110818.binetflow",
    "CTU-Malware-Capture-Botnet-52": RAW_ROOT
    / "CTU-Malware-Capture-Botnet-52/capture20110818-2.binetflow",
    "CTU-Malware-Capture-Botnet-53": RAW_ROOT
    / "CTU-Malware-Capture-Botnet-53/capture20110819.binetflow",
}


@dataclass(frozen=True, slots=True)
class CachedRecord:
    event_id: UUID
    scenario_id: str
    source_event_id: str
    ground_truth_label: GroundTruthLabel
    values: tuple[float, ...]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_features(path: Path, scenario_id: str) -> tuple[tuple[CachedRecord, ...], dict[str, Any]]:
    if scenario_id == SEALED_SCENARIO_ID:
        raise ValueError("the final held-out Scenario 7 is sealed for this stability pass")
    parquet = pq.ParquetFile(path)
    columns = (
        "event_id",
        "scenario_id",
        "source_event_id",
        "ground_truth_label",
        *BEHAVIORAL_FEATURE_NAMES,
    )
    records: list[CachedRecord] = []
    for batch in parquet.iter_batches(columns=list(columns), batch_size=100_000):
        values = batch.to_pydict()
        for index in range(batch.num_rows):
            records.append(
                CachedRecord(
                    event_id=UUID(values["event_id"][index]),
                    scenario_id=str(values["scenario_id"][index]),
                    source_event_id=str(values["source_event_id"][index]),
                    ground_truth_label=GroundTruthLabel(values["ground_truth_label"][index]),
                    values=tuple(float(values[name][index]) for name in BEHAVIORAL_FEATURE_NAMES),
                )
            )
    raw_path = RAW_FILES.get(scenario_id)
    if raw_path is None or not raw_path.exists():
        raise FileNotFoundError(f"raw source needed for provenance metadata: {scenario_id}")
    labels = [record.ground_truth_label.value for record in records]
    metadata = {
        "scenario_id": scenario_id,
        "feature_artifact": path.as_posix(),
        "source_path": raw_path.as_posix(),
        "source_checksum": _sha256(raw_path),
        "source_size_bytes": raw_path.stat().st_size,
        "accepted_rows": len(records),
        "known_rows": sum(label != GroundTruthLabel.UNKNOWN.value for label in labels),
        "unknown_rows": labels.count(GroundTruthLabel.UNKNOWN.value),
        "label_distribution": {label: labels.count(label) for label in sorted(set(labels))},
    }
    return tuple(records), metadata


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--train-feature", action="append", nargs=2, metavar=("PATH", "SCENARIO"), required=True
    )
    parser.add_argument(
        "--validation-feature",
        action="append",
        nargs=2,
        metavar=("PATH", "SCENARIO"),
        required=True,
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path("data/evaluation/phase3_model_stability")
    )
    parser.add_argument("--created-at", required=True)
    parser.add_argument("--seed", type=int, default=SEED)
    return parser


def _rule_scores(records: tuple[CachedRecord, ...]) -> tuple[dict[str, float], int]:
    index = {name: position for position, name in enumerate(BEHAVIORAL_FEATURE_NAMES)}
    scores: dict[str, float] = {}
    rule_count = 0
    for record in records:
        values = record.values
        total_bytes = (
            math.expm1(values[index["log_total_bytes"]])
            if not values[index["total_bytes_missing"]]
            else None
        )
        packets = (
            math.expm1(values[index["log_packet_count"]])
            if not values[index["packet_count_missing"]]
            else None
        )
        duration = (
            values[index["duration_seconds"]] if not values[index["duration_missing"]] else None
        )
        high_volume = total_bytes is not None and total_bytes >= 10_000_000
        long_lived = (
            duration is not None
            and total_bytes is not None
            and duration >= 300.0
            and total_bytes >= 1_000_000
        )
        icmp_burst = (
            values[index["protocol_icmp"]] == 1.0 and packets is not None and packets >= 100
        )
        triggered = high_volume or long_lived or icmp_burst
        scores[str(record.event_id)] = float(triggered)
        rule_count += int(triggered)
    return scores, rule_count


def _model_result(
    name: str,
    *,
    train_records: tuple[CachedRecord, ...],
    validation_records: tuple[CachedRecord, ...],
    validation_scenario_count: int,
    seed: int,
) -> tuple[dict[str, Any], dict[str, float], dict[str, bool]]:
    labeled_validation = known(validation_records)
    scores, runtime = fit_supervised_scores(
        name,
        train_records=train_records,
        validation_records=labeled_validation,
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
        validation_records=labeled_validation,
        scores=scores,
    )
    threshold = selected.threshold
    predictions = {event_id: score >= threshold for event_id, score in scores.items()}
    semantics = {
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
    }[name]
    alert_volume = alert_volume_for_scores(
        validation_records=labeled_validation, scores=scores, threshold=threshold
    )
    alert_volume.update(
        {
            "known_alerts": alert_volume["known_alerts"],
            "labeled_rows_scored": len(labeled_validation),
            "unknown_rows": len(validation_records) - len(labeled_validation),
            "unknown_alerts": None,
            "all_validation_alerts": None,
            "unknown_scoring": "not performed; unknown rows remain unknown",
        }
    )
    return (
        {
            "status": "completed",
            "feature_version": BEHAVIORAL_FEATURE_VERSION,
            "score_semantics": semantics,
            "fixed_policy_threshold": FIXED_POLICY_THRESHOLD,
            "fixed_policy_metrics": fixed.model_dump(mode="json"),
            "operating_threshold": threshold,
            "operating_policy": policy,
            "operating_metrics": selected.model_dump(mode="json"),
            "threshold_tradeoff": list(tradeoff),
            "validation_scenario_metrics_at_operating_point": scenario_metrics(
                detector_name=detector_name,
                validation_records=validation_records,
                scores=scores,
                threshold=threshold,
            ),
            "alert_volume_at_operating_point": alert_volume,
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
        },
        scores,
        predictions,
    )


def main() -> int:
    args = _build_parser().parse_args()
    created_at = datetime.fromisoformat(args.created_at.replace("Z", "+00:00"))
    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    train_sets: list[tuple[CachedRecord, ...]] = []
    validation_sets: list[tuple[CachedRecord, ...]] = []
    metadata: dict[str, list[dict[str, Any]]] = {"train": [], "validation": []}
    for specs, target, split in (
        (args.train_feature, train_sets, "train"),
        (args.validation_feature, validation_sets, "validation"),
    ):
        for path, scenario_id in specs:
            records, scenario_metadata = _load_features(Path(path), scenario_id)
            target.append(records)
            metadata[split].append(scenario_metadata)
    train_records = tuple(record for dataset in train_sets for record in dataset)
    validation_records = tuple(record for dataset in validation_sets for record in dataset)
    rule_scores, rule_count = _rule_scores(validation_records)
    labeled = known(validation_records)
    rule_metrics = compute_binary_metrics(
        [record.ground_truth_label is GroundTruthLabel.MALICIOUS for record in labeled],
        [rule_scores[str(record.event_id)] for record in labeled],
        model_name="rules:ctu13_flow_rules:v1.0.0",
        split_name="validation",
        threshold=0.5,
    )
    model_results: dict[str, dict[str, Any]] = {
        "rules": {
            "status": "completed",
            "score_semantics": (
                "binary rule trigger score: 1.0 when an evidence-traceable rule fires, else 0.0"
            ),
            "threshold_policy": "native deterministic threshold 0.5; no validation tuning",
            "operating_metrics": rule_metrics.model_dump(mode="json"),
            "validation_scenario_metrics": scenario_metrics(
                detector_name="rules:ctu13_flow_rules:v1.0.0",
                validation_records=validation_records,
                scores=rule_scores,
                threshold=0.5,
            ),
            "alert_volume": alert_volume_for_scores(
                validation_records=validation_records, scores=rule_scores, threshold=0.5
            ),
            "interpretability": INTERPRETABILITY["rules"],
            "rule_count": rule_count,
        }
    }
    prediction_sets: dict[str, dict[str, bool]] = {
        "rules": {event_id: score >= 0.5 for event_id, score in rule_scores.items()}
    }
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
    summary = {
        "schema_version": "1.0.0",
        "experiment_name": "ctu13_phase3_cross_scenario_model_stability",
        "created_at": created_at.isoformat(),
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
                "predict_proba positive-class output; model-specific score cutoff, "
                "not assumed calibrated probability"
            ),
            "hist_gradient_boosting": (
                "predict_proba positive-class output; model-specific score cutoff, "
                "not assumed calibrated probability"
            ),
            "linear_svm": (
                "decision_function margin min-max normalized with training margins; "
                "normalized margin cutoff, not a probability"
            ),
            "isolation_forest": (
                "negative decision_function min-max normalized with training anomaly scores; "
                "anomaly cutoff, not a probability"
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
                "excluded from supervised fitting, precision, recall, PR-AUC, and constraints; "
                "supervised models score authoritative labels only and report unknown population "
                "without converting it to benign ground truth"
            ),
        },
        "model_results": model_results,
        "disagreement": {
            "learned_models": disagreement_report(
                validation_records=validation_records,
                detector_predictions={name: prediction_sets[name] for name in FOCUSED_MODELS},
            ),
            "including_rules": disagreement_report(
                validation_records=validation_records,
                detector_predictions=prediction_sets,
            ),
        },
        "svm_unique_coverage": _unique_svm_analysis(
            validation_records=validation_records, predictions=prediction_sets
        ),
        "residual_error_analysis": _residual_error_analysis(
            validation_records=validation_records, predictions=prediction_sets
        ),
        "methodology_note": (
            "Training uses known Normal/Botnet labels from Scenarios 11 and 47. Validation is "
            "pooled across four complete non-sealed scenarios using immutable behavioral Parquet "
            "artifacts. No label, source filename, scenario ID, raw address, Scenario 7 row, "
            "fusion, or additional model family was used."
        ),
    }
    output_path = output_dir / "stability_summary.json"
    output_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"output": str(output_path), "scenario_7": "sealed"}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
