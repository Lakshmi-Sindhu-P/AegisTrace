"""Evaluate the causal ``1.2.0`` host/time representation without Scenario 7.

The runner preserves the frozen ``1.1.0`` RF/HGB/SVM stability result as the
reference and evaluates one new, prior-only feature family with the same
scenario boundaries, model constructors, operating policy, and seed.  It does
not accept a test argument and refuses the sealed Scenario 7 identifier.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

import pyarrow.parquet as pq

from aegistrace.evaluation.model_family import (
    FIXED_POLICY_THRESHOLD,
    OPERATING_ALERTS_PER_1000_CAP,
    OPERATING_PRECISION_FLOOR,
    alert_volume_for_scores,
    disagreement_report,
    fit_supervised_scores,
    metrics_for_scores,
    scenario_metrics,
    select_operating_threshold,
)
from aegistrace.features.causal import (
    CAUSAL_FEATURE_NAMES,
    CAUSAL_FEATURE_VERSION,
    CausalFeatureDataset,
    build_ctu13_causal_features,
    write_causal_feature_parquet,
)
from aegistrace.ingestion.ctu13 import ctu13_source_url, parse_ctu13_binetflow
from aegistrace.schemas.events import GroundTruthLabel

SEED = 42
FOCUSED_MODELS = ("random_forest", "hist_gradient_boosting", "svm")
SEALED_SCENARIO_ID = "CTU-Malware-Capture-Botnet-48"
REFERENCE_FEATURE_VERSION = "1.1.0"
REFERENCE_ARTIFACT = Path("data/evaluation/phase3_model_stability/stability_summary.json")
REFERENCE_FEATURE_ROOT = Path("data/evaluation/phase3_model_stability")


@dataclass(frozen=True, slots=True)
class FeatureRecord:
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


def _timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _load_causal_features(path: Path, scenario_id: str) -> tuple[FeatureRecord, ...]:
    if scenario_id == SEALED_SCENARIO_ID:
        raise ValueError("Scenario 7 is sealed and cannot be loaded")
    columns = (
        "event_id",
        "scenario_id",
        "source_event_id",
        "ground_truth_label",
        *CAUSAL_FEATURE_NAMES,
    )
    records: list[FeatureRecord] = []
    for batch in pq.ParquetFile(path).iter_batches(columns=list(columns), batch_size=100_000):
        values = batch.to_pydict()
        for index in range(batch.num_rows):
            records.append(
                FeatureRecord(
                    event_id=UUID(values["event_id"][index]),
                    scenario_id=str(values["scenario_id"][index]),
                    source_event_id=str(values["source_event_id"][index]),
                    ground_truth_label=GroundTruthLabel(values["ground_truth_label"][index]),
                    values=tuple(float(values[name][index]) for name in CAUSAL_FEATURE_NAMES),
                )
            )
    return tuple(records)


def _build_scenario(
    raw_path: Path,
    scenario_id: str,
    *,
    ingested_at: datetime,
    output_path: Path,
    rebuild: bool,
) -> dict[str, Any]:
    if scenario_id == SEALED_SCENARIO_ID:
        raise ValueError("Scenario 7 is sealed and cannot be loaded")
    if rebuild or not output_path.exists():
        result = parse_ctu13_binetflow(
            raw_path,
            ingested_at=ingested_at,
            scenario_id=scenario_id,
            raw_reference=raw_path.as_posix(),
            report_generated_at=ingested_at,
        )
        dataset: CausalFeatureDataset = build_ctu13_causal_features(result.events)
        write_causal_feature_parquet(dataset, output_path)
        report = result.report
        return {
            "scenario_id": scenario_id,
            "source_url": ctu13_source_url(scenario_id, raw_path.name),
            "source_path": raw_path.as_posix(),
            "source_checksum": report.raw_checksum,
            "source_size_bytes": raw_path.stat().st_size,
            "accepted_rows": report.accepted_rows,
            "rejected_rows": report.rejected_rows,
            "known_rows": len(dataset.supervised_records()),
            "unknown_rows": len(dataset.records) - len(dataset.supervised_records()),
            "label_distribution": report.label_distribution,
            "feature_artifact": output_path.as_posix(),
        }
    records = _load_causal_features(output_path, scenario_id)
    labels = [record.ground_truth_label.value for record in records]
    return {
        "scenario_id": scenario_id,
        "source_url": ctu13_source_url(scenario_id, raw_path.name),
        "source_path": raw_path.as_posix(),
        "source_checksum": _sha256(raw_path),
        "source_size_bytes": raw_path.stat().st_size,
        "accepted_rows": len(records),
        "rejected_rows": None,
        "known_rows": sum(label != GroundTruthLabel.UNKNOWN.value for label in labels),
        "unknown_rows": labels.count(GroundTruthLabel.UNKNOWN.value),
        "label_distribution": {label: labels.count(label) for label in sorted(set(labels))},
        "feature_artifact": output_path.as_posix(),
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--train", action="append", nargs=2, metavar=("PATH", "SCENARIO"), required=True
    )
    parser.add_argument(
        "--validation", action="append", nargs=2, metavar=("PATH", "SCENARIO"), required=True
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path("data/evaluation/phase3_causal_representation")
    )
    parser.add_argument("--ingested-at", required=True)
    parser.add_argument("--created-at", required=True)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--rebuild", action="store_true", help="rebuild causal Parquet artifacts")
    return parser


def _model_result(
    name: str,
    *,
    train_records: tuple[FeatureRecord, ...],
    validation_records: tuple[FeatureRecord, ...],
    scenario_count: int,
    seed: int,
) -> tuple[dict[str, Any], dict[str, bool]]:
    scores, runtime = fit_supervised_scores(
        name,
        train_records=train_records,
        validation_records=validation_records,
        seed=seed,
    )
    detector_name = f"causal_{CAUSAL_FEATURE_VERSION}:{name}"
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
    threshold = selected.threshold
    predictions = {
        str(record.event_id): scores[str(record.event_id)] >= threshold
        for record in validation_records
    }
    return (
        {
            "status": "completed",
            "feature_version": CAUSAL_FEATURE_VERSION,
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
            "alert_volume_at_operating_point": alert_volume_for_scores(
                validation_records=validation_records,
                scores=scores,
                threshold=threshold,
            ),
            "fit_runtime_seconds": runtime["fit_seconds"],
            "runtime": runtime,
            "parameters": {
                "class_weight": "balanced"
                if name != "hist_gradient_boosting"
                else "balanced_sample_weight",
                "seed": seed,
            },
            "validation_scenario_count": scenario_count,
        },
        predictions,
    )


def _residuals(
    records: tuple[FeatureRecord, ...], predictions: dict[str, dict[str, bool]]
) -> dict[str, Any]:
    malicious = tuple(
        record
        for record in records
        if record.ground_truth_label is GroundTruthLabel.MALICIOUS
    )
    missed = tuple(
        record
        for record in malicious
        if not any(predictions[name].get(str(record.event_id), False) for name in FOCUSED_MODELS)
    )
    return {
        "definition": (
            "malicious validation cases missed by RF, HGB, and SVM at their pooled "
            "validation thresholds"
        ),
        "total_cases": len(missed),
        "by_scenario": {
            scenario_id: sum(record.scenario_id == scenario_id for record in missed)
            for scenario_id in sorted({record.scenario_id for record in malicious})
        },
        "feature_summary": _feature_summary(missed),
    }


def _feature_summary(records: tuple[FeatureRecord, ...]) -> dict[str, Any]:
    if not records:
        return {"count": 0}
    index = {name: position for position, name in enumerate(CAUSAL_FEATURE_NAMES)}
    selected_names = (
        "prior_source_connections_60s",
        "prior_source_connections_300s",
        "prior_unique_destinations_60s",
        "prior_unique_destinations_300s",
        "prior_unique_protocols_300s",
        "prior_destination_reuse_300s",
        "log_seconds_since_prior_source_flow",
        "log_prior_total_bytes_300s",
    )
    return {
        "count": len(records),
        "medians": {
            name: statistics.median(record.values[index[name]] for record in records)
            for name in selected_names
        },
        "means": {
            name: statistics.fmean(record.values[index[name]] for record in records)
            for name in selected_names
        },
    }


def _reference_snapshot() -> dict[str, Any]:
    if not REFERENCE_ARTIFACT.exists():
        raise FileNotFoundError(f"missing frozen reference artifact: {REFERENCE_ARTIFACT}")
    summary = json.loads(REFERENCE_ARTIFACT.read_text(encoding="utf-8"))
    if summary.get("feature_version") != REFERENCE_FEATURE_VERSION:
        raise ValueError("frozen reference artifact is not behavioral feature version 1.1.0")
    return {
        "artifact": REFERENCE_ARTIFACT.as_posix(),
        "artifact_sha256": _sha256(REFERENCE_ARTIFACT),
        "feature_version": summary["feature_version"],
        "training_scenarios": summary["training_scenarios"],
        "validation_scenarios": summary["validation_scenarios"],
        "model_results": {
            name: {
                "operating_threshold": summary["model_results"][name]["operating_threshold"],
                "operating_policy": summary["model_results"][name]["operating_policy"],
                "operating_metrics": summary["model_results"][name]["operating_metrics"],
                "validation_scenario_metrics_at_operating_point": summary["model_results"][name][
                    "validation_scenario_metrics_at_operating_point"
                ],
                "alert_volume_at_operating_point": summary["model_results"][name][
                    "alert_volume_at_operating_point"
                ],
            }
            for name in FOCUSED_MODELS
        },
        "residual_error_analysis": summary["residual_error_analysis"],
    }


def main() -> int:
    args = _parser().parse_args()
    ingested_at = _timestamp(args.ingested_at)
    created_at = _timestamp(args.created_at)
    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    metadata: dict[str, list[dict[str, Any]]] = {"train": [], "validation": []}
    paths: dict[str, list[Path]] = {"train": [], "validation": []}
    for specs, split in ((args.train, "train"), (args.validation, "validation")):
        for raw_name, scenario_id in specs:
            raw_path = Path(raw_name)
            output_path = output_dir / f"{scenario_id}_causal.parquet"
            metadata[split].append(
                _build_scenario(
                    raw_path,
                    scenario_id,
                    ingested_at=ingested_at,
                    output_path=output_path,
                    rebuild=args.rebuild,
                )
            )
            paths[split].append(output_path)

    train_records = tuple(
        record
        for path, (_, scenario_id) in zip(paths["train"], args.train, strict=True)
        for record in _load_causal_features(path, scenario_id)
    )
    validation_records = tuple(
        record
        for path, (_, scenario_id) in zip(paths["validation"], args.validation, strict=True)
        for record in _load_causal_features(path, scenario_id)
    )
    predictions: dict[str, dict[str, bool]] = {}
    model_results: dict[str, dict[str, Any]] = {}
    for name in FOCUSED_MODELS:
        result, prediction_set = _model_result(
            name,
            train_records=train_records,
            validation_records=validation_records,
            scenario_count=len(metadata["validation"]),
            seed=args.seed,
        )
        model_results[name] = result
        predictions[name] = prediction_set

    reference = _reference_snapshot()
    comparison: dict[str, Any] = {}
    for name in FOCUSED_MODELS:
        baseline_metrics = reference["model_results"][name]["operating_metrics"]
        candidate_metrics = model_results[name]["operating_metrics"]
        comparison[name] = {
            "reference_feature_version": REFERENCE_FEATURE_VERSION,
            "candidate_feature_version": CAUSAL_FEATURE_VERSION,
            "reference_operating_threshold": reference["model_results"][name][
                "operating_threshold"
            ],
            "candidate_operating_threshold": model_results[name]["operating_threshold"],
            "delta_precision": (candidate_metrics["precision"] or 0.0)
            - (baseline_metrics["precision"] or 0.0),
            "delta_recall": (candidate_metrics["recall"] or 0.0)
            - (baseline_metrics["recall"] or 0.0),
            "delta_f1": (candidate_metrics["f1"] or 0.0) - (baseline_metrics["f1"] or 0.0),
            "delta_pr_auc": (candidate_metrics["pr_auc"] or 0.0)
            - (baseline_metrics["pr_auc"] or 0.0),
            "reference_metrics": baseline_metrics,
            "candidate_metrics": candidate_metrics,
        }

    summary = {
        "schema_version": "1.0.0",
        "experiment_name": "ctu13_phase3_causal_representation",
        "created_at": created_at.isoformat(),
        "ingested_at": ingested_at.isoformat(),
        "seed": args.seed,
        "feature_version": CAUSAL_FEATURE_VERSION,
        "feature_names": CAUSAL_FEATURE_NAMES,
        "feature_count": len(CAUSAL_FEATURE_NAMES),
        "feature_lineage": {
            "base_behavioral_version": REFERENCE_FEATURE_VERSION,
            "causal_extension": "prior-only source-host windows of 60 and 300 seconds",
            "source_fields": [
                "StartTime",
                "SrcAddr",
                "DstAddr",
                "Dport",
                "Proto",
                "Dur",
                "TotPkts",
                "TotBytes",
            ],
            "missingness": (
                "zero-valued aggregates have explicit missing indicators where source totals "
                "may be unavailable"
            ),
            "leakage_guard": (
                "events sorted by observed time; current and future rows and all labels "
                "excluded from aggregate state"
            ),
            "raw_identity_usage": (
                "source and destination addresses are aggregation keys only and never numeric "
                "model columns"
            ),
        },
        "training_scenarios": [item["scenario_id"] for item in metadata["train"]],
        "validation_scenarios": [item["scenario_id"] for item in metadata["validation"]],
        "source_checksums": {
            item["scenario_id"]: item["source_checksum"]
            for split in metadata.values()
            for item in split
        },
        "scenario_metadata": metadata,
        "operating_policy": {
            "objective": "maximize recall on pooled validation labels",
            "precision_floor": OPERATING_PRECISION_FLOOR,
            "alerts_per_1000_labeled_flows_cap": OPERATING_ALERTS_PER_1000_CAP,
            "threshold_selection": (
                "validation-only; 0.01 increments on each model's own score scale"
            ),
            "unknown_rows": (
                "excluded from fitting and supervised metrics; retained only as unlabeled "
                "context"
            ),
        },
        "model_results": model_results,
        "reference": reference,
        "comparison_to_reference": comparison,
        "disagreement": disagreement_report(
            validation_records=validation_records,
            detector_predictions=predictions,
        ),
        "residual_error_analysis": _residuals(validation_records, predictions),
        "scenario_7": "sealed; not loaded, scored, tuned, or used for feature selection",
        "methodology_note": (
            "This is a validation-only representation study. It does not introduce a new "
            "model family, fusion, LLM, scheduler, or governance change."
        ),
    }
    output_path = output_dir / "causal_summary.json"
    output_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": output_path.as_posix(), "scenario_7": "sealed"}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
