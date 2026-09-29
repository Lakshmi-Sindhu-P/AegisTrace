"""Run the pre-final detector hardening pass on validation artifacts only.

This command has no Scenario 7 input and refuses a sealed scenario identifier. It
audits ablations, temporal causality, calibration, and alert workload before
writing a validation-frozen policy record.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq
from sklearn.calibration import CalibratedClassifierCV

from aegistrace.detection.rules import (
    CTU13_RULE_VERSION,
    HIGH_VOLUME_BYTES,
    ICMP_BURST_PACKETS,
    LONG_LIVED_BYTES,
    LONG_LIVED_SECONDS,
)
from aegistrace.evaluation.hardening import (
    BEHAVIORAL_FEATURE_GROUPS,
    alert_volume,
    calibration_summary,
)
from aegistrace.evaluation.improvement import make_model
from aegistrace.evaluation.metrics import compute_binary_metrics
from aegistrace.features.behavioral import audit_prior_window_causality
from aegistrace.ingestion.ctu13 import parse_ctu13_binetflow
from aegistrace.schemas.events import GroundTruthLabel

SEALED_SCENARIO_ID = "CTU-Malware-Capture-Botnet-48"
DEFAULT_THRESHOLD = 0.20
THRESHOLDS: tuple[float, ...] = (0.05, 0.10, 0.15, 0.20, 0.30, 0.50)
SEED = 42
FEATURE_PARQUET_DIR = Path("data/evaluation/phase3_improvement")
FIXTURE_PATH = Path("data/fixtures/ctu13/scenario_11.binetflow")


@dataclass(frozen=True, slots=True)
class ScenarioRows:
    scenario_id: str
    feature_names: tuple[str, ...]
    columns: tuple[tuple[float, ...], ...]
    labels: tuple[str, ...]

    @property
    def row_count(self) -> int:
        return len(self.labels)

    def indices(self, *, known_only: bool = False) -> list[int]:
        if not known_only:
            return list(range(self.row_count))
        return [
            index
            for index, label in enumerate(self.labels)
            if label in {GroundTruthLabel.BENIGN.value, GroundTruthLabel.MALICIOUS.value}
        ]

    def matrix(self, indices: list[int], keep: tuple[int, ...] | None = None) -> list[list[float]]:
        selected = range(len(self.columns)) if keep is None else keep
        return [[self.columns[column][index] for column in selected] for index in indices]


def _load(path: Path, scenario_id: str, expected_names: tuple[str, ...]) -> ScenarioRows:
    if scenario_id == SEALED_SCENARIO_ID:
        raise ValueError("Scenario 7 is sealed and cannot be loaded by the hardening runner")
    table = pq.read_table(path)
    metadata = table.schema.metadata or {}
    encoded_names = metadata.get(b"feature_names", b"")
    names = tuple(encoded_names.decode().split(",")) if encoded_names else ()
    # Feature names are stored as columns in the artifact; use the diagnostic contract explicitly.
    feature_columns = tuple(
        tuple(float(value) for value in table[name].combine_chunks().to_pylist())
        for name in expected_names
    )
    labels = tuple(str(value) for value in table["ground_truth_label"].combine_chunks().to_pylist())
    if names and names != expected_names:
        raise ValueError(f"feature metadata mismatch for {scenario_id}")
    if any(len(column) != len(labels) for column in feature_columns):
        raise ValueError(f"feature column length mismatch for {scenario_id}")
    return ScenarioRows(
        scenario_id=scenario_id,
        feature_names=expected_names,
        columns=feature_columns,
        labels=labels,
    )


def _known_labels(rows: list[ScenarioRows]) -> list[bool]:
    return [
        label == GroundTruthLabel.MALICIOUS.value
        for scenario in rows
        for label in scenario.labels
        if label in {GroundTruthLabel.BENIGN.value, GroundTruthLabel.MALICIOUS.value}
    ]


def _known_matrix(
    rows: list[ScenarioRows], keep: tuple[int, ...] | None = None
) -> list[list[float]]:
    return [
        vector
        for scenario in rows
        for vector in scenario.matrix(scenario.indices(known_only=True), keep)
    ]


def _metrics(
    labels: list[bool], scores: list[float], *, name: str, threshold: float
) -> dict[str, Any]:
    return compute_binary_metrics(
        labels,
        scores,
        model_name=name,
        split_name="validation",
        threshold=threshold,
    ).model_dump(mode="json")


def _fit_rf(
    train_rows: list[ScenarioRows],
    validation_rows: list[ScenarioRows],
    *,
    keep: tuple[int, ...] | None = None,
) -> tuple[Any, list[bool], list[float], list[float]]:
    train_values = _known_matrix(train_rows, keep)
    train_labels = _known_labels(train_rows)
    model = make_model("random_forest", class_weight="balanced", seed=SEED)
    model.fit(train_values, train_labels)
    validation_known_values = _known_matrix(validation_rows, keep)
    known_scores = [float(score[1]) for score in model.predict_proba(validation_known_values)]
    all_values = [
        vector
        for scenario in validation_rows
        for vector in scenario.matrix(scenario.indices(), keep)
    ]
    all_scores = [float(score[1]) for score in model.predict_proba(all_values)]
    return model, _known_labels(validation_rows), known_scores, all_scores


def _group_metrics(
    model: Any,
    validation_rows: list[ScenarioRows],
    *,
    keep: tuple[int, ...] | None,
    threshold: float,
) -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for scenario in validation_rows:
        indices = scenario.indices(known_only=True)
        labels = [
            label == GroundTruthLabel.MALICIOUS.value
            for label in scenario.labels
            if label in {GroundTruthLabel.BENIGN.value, GroundTruthLabel.MALICIOUS.value}
        ]
        scores = [float(score[1]) for score in model.predict_proba(scenario.matrix(indices, keep))]
        output[scenario.scenario_id] = _metrics(
            labels,
            scores,
            name="behavioral_random_forest",
            threshold=threshold,
        )
    return output


def _ablation(
    train_rows: list[ScenarioRows],
    validation_rows: list[ScenarioRows],
    feature_names: tuple[str, ...],
) -> dict[str, Any]:
    all_indices = tuple(range(len(feature_names)))
    groups: dict[str, tuple[str, ...]] = {"all_features": ()}
    groups.update({f"without_{name}": names for name, names in BEHAVIORAL_FEATURE_GROUPS.items()})
    output: dict[str, Any] = {}
    for name, removed_names in groups.items():
        removed = set(removed_names)
        keep = tuple(index for index in all_indices if feature_names[index] not in removed)
        model, labels, scores, _ = _fit_rf(train_rows, validation_rows, keep=keep)
        output[name] = {
            "removed_features": list(removed_names),
            "remaining_feature_count": len(keep),
            "threshold": DEFAULT_THRESHOLD,
            "metrics": _metrics(
                labels,
                scores,
                name=f"behavioral_random_forest:{name}",
                threshold=DEFAULT_THRESHOLD,
            ),
            "validation_scenario_metrics": _group_metrics(
                model, validation_rows, keep=keep, threshold=DEFAULT_THRESHOLD
            ),
        }
    return output


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("data/evaluation/phase3_hardening"))
    parser.add_argument(
        "--policy-path", type=Path, default=Path("configs/phase3_frozen_policy.json")
    )
    parser.add_argument("--created-at", default="2026-09-21T16:00:00Z")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    prior_artifact_path = FEATURE_PARQUET_DIR / "diagnostic.json"
    prior_artifact = json.loads(prior_artifact_path.read_text())
    feature_names = tuple(prior_artifact["feature_names"]["behavioral"])
    scenarios = prior_artifact["scenario_metadata"]
    train_rows = [
        _load(
            FEATURE_PARQUET_DIR / f"{item['scenario_id']}_behavioral.parquet",
            item["scenario_id"],
            feature_names,
        )
        for item in scenarios["train"]
    ]
    validation_rows = [
        _load(
            FEATURE_PARQUET_DIR / f"{item['scenario_id']}_behavioral.parquet",
            item["scenario_id"],
            feature_names,
        )
        for item in scenarios["validation"]
    ]

    full_model, labels, known_scores, all_scores = _fit_rf(train_rows, validation_rows)
    ablations = _ablation(train_rows, validation_rows, feature_names)
    temporal_result = parse_ctu13_binetflow(
        FIXTURE_PATH,
        ingested_at=datetime(2026, 9, 21, 1, tzinfo=UTC),
        scenario_id="CTU-Malware-Capture-Botnet-52",
        raw_reference=FIXTURE_PATH.as_posix(),
        report_generated_at=datetime(2026, 9, 21, 1, tzinfo=UTC),
    )
    temporal_audit = audit_prior_window_causality(temporal_result.events)

    calibration_validation_values = _known_matrix(validation_rows)
    raw_calibration = calibration_summary(labels, known_scores)
    calibrated_model = CalibratedClassifierCV(
        estimator=make_model("random_forest", class_weight="balanced", seed=SEED),
        method="sigmoid",
        cv=3,
        n_jobs=1,
    )
    calibrated_model.fit(_known_matrix(train_rows), _known_labels(train_rows))
    calibrated_scores = [
        float(score[1]) for score in calibrated_model.predict_proba(calibration_validation_values)
    ]
    sigmoid_calibration = calibration_summary(labels, calibrated_scores)
    calibration_decision = {
        "choice_for_frozen_policy": "none",
        "reason": (
            "Calibration is assessed with a training-only 3-fold sigmoid wrapper, but the frozen "
            "detector uses raw ranking scores because this pass targets evidence ranking and alert "
            "workload; calibrated probabilities are not treated as real-world probabilities."
        ),
        "raw_random_forest": raw_calibration,
        "sigmoid_cv3": sigmoid_calibration,
        "raw_threshold_metrics": _metrics(
            labels, known_scores, name="behavioral_random_forest:raw", threshold=DEFAULT_THRESHOLD
        ),
        "sigmoid_threshold_metrics": _metrics(
            labels,
            calibrated_scores,
            name="behavioral_random_forest:sigmoid_cv3",
            threshold=DEFAULT_THRESHOLD,
        ),
    }

    alert_rows = [
        alert_volume(labels, known_scores, all_scores, threshold=threshold)
        for threshold in THRESHOLDS
    ]
    frozen_policy = {
        "policy_id": "aegistrace-phase3-behavioral-rf-validation-frozen-v1",
        "status": "FROZEN_VALIDATION_POLICY",
        "scope": "validation-selected policy; do not tune after reopening sealed Scenario 7",
        "model": "random_forest",
        "feature_version": "1.1.0",
        "feature_family": "behavioral_ctu13_prior_window",
        "training_scenarios": [item["scenario_id"] for item in scenarios["train"]],
        "validation_scenarios": [item["scenario_id"] for item in scenarios["validation"]],
        "threshold": DEFAULT_THRESHOLD,
        "class_weight": "balanced",
        "preprocessing": "none",
        "hyperparameters": {
            "n_estimators": 200,
            "max_depth": 12,
            "n_jobs": 1,
        },
        "random_seed": SEED,
        "code_versions": {
            "behavioral_feature_builder": "1.1.0",
            "hardening_runner": "1.0.0",
            "metrics_schema": "1.0.0",
            "environment_lock": "uv.lock",
        },
        "calibration": "none",
        "threshold_selection_rationale": (
            "0.20 selected after validation-only workload review: compared with 0.15 it gives "
            "nearly identical F1, higher precision, and fewer alerts; it is not selected from the "
            "sealed test."
        ),
        "rule_configuration": {
            "detector_version": CTU13_RULE_VERSION,
            "high_volume_bytes": HIGH_VOLUME_BYTES,
            "long_lived_seconds": LONG_LIVED_SECONDS,
            "long_lived_bytes": LONG_LIVED_BYTES,
            "icmp_burst_packets": ICMP_BURST_PACKETS,
        },
        "dataset_checksums": prior_artifact["source_checksums"],
        "sealed_scenario": SEALED_SCENARIO_ID,
        "frozen_at": args.created_at,
    }
    args.policy_path.parent.mkdir(parents=True, exist_ok=True)
    args.policy_path.write_text(json.dumps(frozen_policy, indent=2, sort_keys=True) + "\n")

    summary = {
        "schema_version": "1.0.0",
        "experiment_name": "ctu13_phase3_pre_final_detector_hardening",
        "created_at": args.created_at,
        "seed": SEED,
        "feature_version": "1.1.0",
        "feature_names": feature_names,
        "training_scenarios": scenarios["train"],
        "validation_scenarios": scenarios["validation"],
        "dataset_checksums": prior_artifact["source_checksums"],
        "sealed_scenario": SEALED_SCENARIO_ID,
        "temporal_audit": {
            "passed": temporal_audit,
            "fixture": FIXTURE_PATH.as_posix(),
            "method": "append a deterministic future flow and compare every prior vector",
            "source_review": "builder sorts by observed_at and inserts only prior flows into state",
        },
        "feature_ablation": ablations,
        "calibration": calibration_decision,
        "alert_volume": alert_rows,
        "frozen_policy": frozen_policy,
        "frozen_policy_path": args.policy_path.as_posix(),
        "validation_metrics_at_frozen_policy": {
            "combined": _metrics(
                labels,
                known_scores,
                name="behavioral_random_forest:frozen",
                threshold=DEFAULT_THRESHOLD,
            ),
            "by_scenario": _group_metrics(
                full_model,
                validation_rows,
                keep=None,
                threshold=DEFAULT_THRESHOLD,
            ),
        },
        "methodology_note": (
            "All ablations, calibration comparisons, and alert-volume measurements use training "
            "scenarios 11/47 and validation scenarios 5/53 only. Scenario 7 was not loaded, "
            "scored, "
            "or used for any selection."
        ),
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "hardening_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n"
    )
    print(
        json.dumps(
            {
                "output_dir": str(args.output_dir),
                "policy_path": str(args.policy_path),
                "temporal_audit_passed": temporal_audit,
                "frozen_threshold": DEFAULT_THRESHOLD,
                "sealed_scenario": SEALED_SCENARIO_ID,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
