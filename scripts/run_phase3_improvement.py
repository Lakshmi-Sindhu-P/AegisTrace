"""Run the Phase 3 detector-improvement study on training/validation scenarios only.

The command accepts explicit training and validation scenario lists. It has no test
argument by design: the final held-out capture is sealed during this investigation.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from aegistrace.evaluation.improvement import run_comparison
from aegistrace.features.behavioral import (
    BEHAVIORAL_BASE_FEATURE_COUNT,
    BEHAVIORAL_FEATURE_NAMES,
    BEHAVIORAL_FEATURE_VERSION,
    BehavioralFeatureDataset,
    build_ctu13_behavioral_features,
    write_behavioral_feature_parquet,
)
from aegistrace.features.network import FEATURE_NAMES
from aegistrace.ingestion.ctu13 import parse_ctu13_binetflow
from aegistrace.schemas.events import GroundTruthLabel

SEED = 42
SEALED_SCENARIO_ID = "CTU-Malware-Capture-Botnet-48"


@dataclass(frozen=True, slots=True)
class VectorRecord:
    """Small protocol-compatible view used by the shared evaluation helpers."""

    event_id: Any
    scenario_id: str
    source_event_id: str
    ground_truth_label: GroundTruthLabel
    values: tuple[float, ...]


def _timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _config(
    path: Path,
    scenario_id: str,
    *,
    ingested_at: datetime,
    output_dir: Path,
) -> tuple[BehavioralFeatureDataset, dict[str, Any]]:
    if scenario_id == SEALED_SCENARIO_ID:
        raise ValueError("the final held-out Scenario 7 is sealed for this improvement runner")
    result = parse_ctu13_binetflow(
        path,
        ingested_at=ingested_at,
        scenario_id=scenario_id,
        raw_reference=path.as_posix(),
        report_generated_at=ingested_at,
    )
    dataset = build_ctu13_behavioral_features(result.events)
    write_behavioral_feature_parquet(dataset, output_dir / f"{scenario_id}_behavioral.parquet")
    known_rows = dataset.supervised_records()
    return dataset, {
        "scenario_id": scenario_id,
        "dataset_version": result.report.dataset_version,
        "source_path": path.as_posix(),
        "source_checksum": result.report.raw_checksum,
        "source_size_bytes": path.stat().st_size,
        "rows_seen": result.report.rows_seen,
        "accepted_rows": result.report.accepted_rows,
        "rejected_rows": result.report.rejected_rows,
        "unknown_rows_excluded_from_supervised": sum(
            event.ground_truth_label is GroundTruthLabel.UNKNOWN for event in result.events
        ),
        "known_rows": len(known_rows),
        "label_distribution": result.report.label_distribution,
    }


def _baseline_view(dataset: BehavioralFeatureDataset) -> tuple[VectorRecord, ...]:
    return tuple(
        VectorRecord(
            event_id=record.event_id,
            scenario_id=record.scenario_id,
            source_event_id=record.source_event_id,
            ground_truth_label=record.ground_truth_label,
            values=record.values[:BEHAVIORAL_BASE_FEATURE_COUNT],
        )
        for record in dataset.records
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--train", action="append", nargs=2, metavar=("PATH", "SCENARIO"), required=True
    )
    parser.add_argument(
        "--validation", action="append", nargs=2, metavar=("PATH", "SCENARIO"), required=True
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path("data/evaluation/phase3_improvement")
    )
    parser.add_argument("--ingested-at", required=True)
    parser.add_argument("--created-at", required=True)
    parser.add_argument("--seed", type=int, default=SEED)
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    ingested_at = _timestamp(args.ingested_at)
    created_at = _timestamp(args.created_at)
    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    train_datasets: list[BehavioralFeatureDataset] = []
    validation_datasets: list[BehavioralFeatureDataset] = []
    metadata: dict[str, list[dict[str, Any]]] = {"train": [], "validation": []}
    for split_name, specs, target in (
        ("train", args.train, train_datasets),
        ("validation", args.validation, validation_datasets),
    ):
        for raw_path, scenario_id in specs:
            dataset, scenario_metadata = _config(
                Path(raw_path),
                scenario_id,
                ingested_at=ingested_at,
                output_dir=output_dir,
            )
            target.append(dataset)
            metadata[split_name].append(scenario_metadata)

    train_behavior = tuple(record for dataset in train_datasets for record in dataset.records)
    validation_behavior = tuple(
        record for dataset in validation_datasets for record in dataset.records
    )
    train_baseline = tuple(
        record for dataset in train_datasets for record in _baseline_view(dataset)
    )
    validation_baseline = tuple(
        record for dataset in validation_datasets for record in _baseline_view(dataset)
    )
    validation_behavior_groups = {
        metadata["validation"][index]["scenario_id"]: tuple(dataset.records)
        for index, dataset in enumerate(validation_datasets)
    }
    validation_baseline_groups = {
        metadata["validation"][index]["scenario_id"]: _baseline_view(dataset)
        for index, dataset in enumerate(validation_datasets)
    }
    baseline_results = run_comparison(
        train_records=train_baseline,
        validation_records=validation_baseline,
        feature_family="per_flow_v1.0.0",
        seed=args.seed,
        feature_names=FEATURE_NAMES,
        validation_groups=validation_baseline_groups,
    )
    behavioral_results = run_comparison(
        train_records=train_behavior,
        validation_records=validation_behavior,
        feature_family="behavioral_v1.1.0",
        seed=args.seed,
        feature_names=BEHAVIORAL_FEATURE_NAMES,
        validation_groups=validation_behavior_groups,
    )
    source_checksums = {
        item["scenario_id"]: item["source_checksum"]
        for split in metadata.values()
        for item in split
    }
    summary = {
        "schema_version": "1.0.0",
        "experiment_name": "ctu13_phase3_validation_only_detector_improvement",
        "feature_versions": {
            "baseline": "1.0.0",
            "behavioral": BEHAVIORAL_FEATURE_VERSION,
        },
        "feature_names": {
            "baseline": FEATURE_NAMES,
            "behavioral": BEHAVIORAL_FEATURE_NAMES,
        },
        "seed": args.seed,
        "ingested_at": ingested_at.isoformat(),
        "created_at": created_at.isoformat(),
        "source_checksums": source_checksums,
        "scenario_metadata": metadata,
        "split_policy": {
            "training_scenarios": [item["scenario_id"] for item in metadata["train"]],
            "validation_scenarios": [item["scenario_id"] for item in metadata["validation"]],
            "unknown_labels": (
                "excluded from supervised fitting and metrics; retained for aggregates"
            ),
            "final_test": "sealed and not loaded, tuned, or reported by this command",
        },
        "model_parameters": {
            "logistic_regression": {"max_iter": 1000, "solver": "liblinear"},
            "random_forest": {"max_depth": 12, "n_estimators": 200, "n_jobs": 1},
        },
        "threshold_selection": (
            "validation maximum F1; tie-break recall, precision, then lower threshold"
        ),
        "comparisons": {
            "per_flow_v1.0.0": baseline_results,
            "behavioral_v1.1.0": behavioral_results,
        },
        "methodology_note": (
            "Aggregates are computed separately within each scenario from prior observed flows. "
            "No labels, filenames, scenario IDs, source labels, or raw addresses are model "
            "features. "
            "Only authoritative benign/malicious labels enter supervised fitting and metrics."
        ),
    }
    (output_dir / "diagnostic.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n"
    )
    print(
        json.dumps(
            {
                "output_dir": str(output_dir),
                "train_scenarios": [item["scenario_id"] for item in metadata["train"]],
                "validation_scenarios": [item["scenario_id"] for item in metadata["validation"]],
                "feature_versions": summary["feature_versions"],
                "validation_known_rows": len(validation_baseline),
                "source_checksums": source_checksums,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
