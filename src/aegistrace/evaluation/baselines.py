"""Scenario-aware Logistic Regression and Random Forest baselines."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from aegistrace.evaluation.metrics import BinaryMetrics, compute_binary_metrics
from aegistrace.features.network import FeatureDataset, FeatureRecord
from aegistrace.schemas.events import GroundTruthLabel

BASELINE_SEED = 42
DEFAULT_THRESHOLD = 0.5


def _known(records: Iterable[FeatureRecord]) -> tuple[FeatureRecord, ...]:
    return tuple(
        record for record in records if record.ground_truth_label is not GroundTruthLabel.UNKNOWN
    )


def _labels(records: tuple[FeatureRecord, ...]) -> list[bool]:
    return [record.ground_truth_label is GroundTruthLabel.MALICIOUS for record in records]


def _models(seed: int) -> dict[str, Pipeline | RandomForestClassifier]:
    return {
        "logistic_regression": Pipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "classifier",
                    LogisticRegression(
                        class_weight="balanced",
                        max_iter=1000,
                        random_state=seed,
                        solver="liblinear",
                    ),
                ),
            ]
        ),
        "random_forest": RandomForestClassifier(
            class_weight="balanced",
            max_depth=12,
            n_estimators=200,
            n_jobs=1,
            random_state=seed,
        ),
    }


def _evaluate_model(
    model: Pipeline | RandomForestClassifier,
    *,
    name: str,
    train: tuple[FeatureRecord, ...],
    split_records: tuple[FeatureRecord, ...],
    split_name: str,
) -> tuple[BinaryMetrics, list[dict[str, Any]]]:
    model.fit(
        [record.values for record in train],
        _labels(train),
    )
    labels = _labels(split_records)
    scores = [
        float(score[1])
        for score in model.predict_proba([record.values for record in split_records])
    ]
    metrics = compute_binary_metrics(
        labels,
        scores,
        model_name=name,
        split_name=split_name,
        threshold=DEFAULT_THRESHOLD,
    )
    predictions = [score >= DEFAULT_THRESHOLD for score in scores]
    rows = [
        {
            "event_id": str(record.event_id),
            "scenario_id": record.scenario_id,
            "model_name": name,
            "ground_truth_label": record.ground_truth_label.value,
            "score": score,
            "prediction": "malicious" if prediction else "benign",
        }
        for record, score, prediction in zip(split_records, scores, predictions, strict=True)
    ]
    return metrics, rows


def evaluate_scenario_split(
    *,
    train_dataset: FeatureDataset,
    validation_dataset: FeatureDataset,
    test_dataset: FeatureDataset,
    seed: int = BASELINE_SEED,
) -> tuple[dict[str, tuple[BinaryMetrics, ...]], tuple[dict[str, Any], ...]]:
    """Fit on one scenario and report validation/test results on separate scenarios."""

    train = _known(train_dataset.records)
    validation = _known(validation_dataset.records)
    test = _known(test_dataset.records)
    if not train or not validation or not test:
        raise ValueError("each scenario split needs known benign and malicious rows")
    if {record.ground_truth_label for record in train} != {
        GroundTruthLabel.BENIGN,
        GroundTruthLabel.MALICIOUS,
    }:
        raise ValueError("training scenario must contain both known classes")

    all_metrics: dict[str, tuple[BinaryMetrics, ...]] = {}
    prediction_rows: list[dict[str, Any]] = []
    for name, model in _models(seed).items():
        validation_metrics, validation_rows = _evaluate_model(
            model,
            name=name,
            train=train,
            split_records=validation,
            split_name="validation",
        )
        test_metrics, test_rows = _evaluate_model(
            model,
            name=name,
            train=train,
            split_records=test,
            split_name="test",
        )
        all_metrics[name] = (validation_metrics, test_metrics)
        prediction_rows.extend(validation_rows)
        prediction_rows.extend(test_rows)
    return all_metrics, tuple(prediction_rows)
