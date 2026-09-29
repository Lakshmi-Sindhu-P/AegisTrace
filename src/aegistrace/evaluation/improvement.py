"""Validation-only detector improvement helpers for Phase 3.

This module deliberately has no test-scenario argument. Callers provide a training
pool and a validation pool; threshold selection and class-weight comparisons are
therefore impossible to run against the sealed final test by accident.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Protocol

from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from aegistrace.evaluation.metrics import BinaryMetrics, compute_binary_metrics
from aegistrace.schemas.events import GroundTruthLabel

BASELINE_THRESHOLD = 0.5
THRESHOLD_GRID: tuple[float, ...] = tuple(index / 20 for index in range(1, 20))


class RecordLike(Protocol):
    values: tuple[float, ...]
    ground_truth_label: GroundTruthLabel
    event_id: Any
    scenario_id: str


def known(records: Sequence[RecordLike]) -> tuple[RecordLike, ...]:
    """Keep only authoritative benign/malicious rows for supervised work."""

    return tuple(
        record for record in records if record.ground_truth_label is not GroundTruthLabel.UNKNOWN
    )


def _labels(records: Sequence[RecordLike]) -> list[bool]:
    return [record.ground_truth_label is GroundTruthLabel.MALICIOUS for record in records]


def make_model(model_name: str, *, class_weight: str | None, seed: int) -> Any:
    if model_name == "logistic_regression":
        return Pipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "classifier",
                    LogisticRegression(
                        class_weight=class_weight,
                        max_iter=1000,
                        random_state=seed,
                        solver="liblinear",
                    ),
                ),
            ]
        )
    if model_name == "random_forest":
        return RandomForestClassifier(
            class_weight=class_weight,
            max_depth=12,
            n_estimators=200,
            n_jobs=1,
            random_state=seed,
        )
    raise ValueError(f"unsupported model {model_name}")


def fit_scores(
    model_name: str,
    *,
    class_weight: str | None,
    train_records: Sequence[RecordLike],
    validation_records: Sequence[RecordLike],
    seed: int,
) -> tuple[Any, tuple[RecordLike, ...], list[float]]:
    train = known(train_records)
    validation = known(validation_records)
    if not train or not validation:
        raise ValueError("training and validation pools must contain known rows")
    if {record.ground_truth_label for record in train} != {
        GroundTruthLabel.BENIGN,
        GroundTruthLabel.MALICIOUS,
    }:
        raise ValueError("training pool must contain both known classes")
    model = make_model(model_name, class_weight=class_weight, seed=seed)
    model.fit([record.values for record in train], _labels(train))
    scores = [
        float(score[1]) for score in model.predict_proba([record.values for record in validation])
    ]
    return model, validation, scores


def threshold_metrics(
    *,
    model_name: str,
    split_name: str,
    validation: Sequence[RecordLike],
    scores: Sequence[float],
    threshold: float,
) -> BinaryMetrics:
    return compute_binary_metrics(
        _labels(validation),
        scores,
        model_name=model_name,
        split_name=split_name,
        threshold=threshold,
    )


def tune_threshold(
    *,
    model_name: str,
    split_name: str,
    validation: Sequence[RecordLike],
    scores: Sequence[float],
) -> tuple[BinaryMetrics, tuple[BinaryMetrics, ...]]:
    """Select the validation threshold by maximum F1, then recall, then precision."""

    tradeoff = tuple(
        threshold_metrics(
            model_name=model_name,
            split_name=split_name,
            validation=validation,
            scores=scores,
            threshold=threshold,
        )
        for threshold in THRESHOLD_GRID
    )
    selected = max(
        tradeoff,
        key=lambda metric: (
            metric.f1 if metric.f1 is not None else -1.0,
            metric.recall if metric.recall is not None else -1.0,
            metric.precision if metric.precision is not None else -1.0,
            -metric.threshold,
        ),
    )
    return selected, tradeoff


def error_summary(
    validation: Sequence[RecordLike],
    scores: Sequence[float],
    threshold: float,
    feature_names: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Summarize false negatives and true positives without exposing raw addresses."""

    labels = _labels(validation)
    false_negative_values: list[tuple[float, ...]] = []
    true_positive_values: list[tuple[float, ...]] = []
    for record, label, score in zip(validation, labels, scores, strict=True):
        if label and score < threshold:
            false_negative_values.append(record.values)
        elif label and score >= threshold:
            true_positive_values.append(record.values)

    def means(rows: Sequence[tuple[float, ...]]) -> dict[str, float | None]:
        names = feature_names or tuple(str(index) for index in range(len(rows[0]) if rows else 0))
        return {
            names[index]: (sum(row[index] for row in rows) / len(rows) if rows else None)
            for index in range(len(names))
        }

    return {
        "false_negative_count": len(false_negative_values),
        "true_positive_count": len(true_positive_values),
        "false_negative_feature_means": means(false_negative_values),
        "true_positive_feature_means": means(true_positive_values),
    }


def run_comparison(
    *,
    train_records: Sequence[RecordLike],
    validation_records: Sequence[RecordLike],
    feature_family: str,
    seed: int,
    feature_names: Sequence[str] | None = None,
    validation_groups: dict[str, Sequence[RecordLike]] | None = None,
) -> dict[str, Any]:
    """Run fixed-threshold and validation-tuned comparisons for both baselines."""

    output: dict[str, Any] = {}
    for model_name in ("logistic_regression", "random_forest"):
        for class_weight in (None, "balanced"):
            weight_name = "none" if class_weight is None else class_weight
            key = f"{model_name}__class_weight_{weight_name}"
            model, validation, scores = fit_scores(
                model_name,
                class_weight=class_weight,
                train_records=train_records,
                validation_records=validation_records,
                seed=seed,
            )
            fixed = threshold_metrics(
                model_name=f"{feature_family}:{key}",
                split_name="validation",
                validation=validation,
                scores=scores,
                threshold=BASELINE_THRESHOLD,
            )
            selected, tradeoff = tune_threshold(
                model_name=f"{feature_family}:{key}",
                split_name="validation",
                validation=validation,
                scores=scores,
            )
            group_metrics: dict[str, Any] = {}
            if validation_groups:
                for group_name, group_records in validation_groups.items():
                    group_known = known(group_records)
                    group_scores = [
                        float(score[1])
                        for score in model.predict_proba([record.values for record in group_known])
                    ]
                    group_metrics[group_name] = {
                        "fixed_threshold": threshold_metrics(
                            model_name=f"{feature_family}:{key}",
                            split_name=f"validation:{group_name}",
                            validation=group_known,
                            scores=group_scores,
                            threshold=BASELINE_THRESHOLD,
                        ).model_dump(mode="json"),
                        "selected_threshold": threshold_metrics(
                            model_name=f"{feature_family}:{key}",
                            split_name=f"validation:{group_name}",
                            validation=group_known,
                            scores=group_scores,
                            threshold=selected.threshold,
                        ).model_dump(mode="json"),
                    }
            output[key] = {
                "feature_family": feature_family,
                "class_weight": class_weight,
                "fixed_threshold": fixed.model_dump(mode="json"),
                "selected_threshold": selected.model_dump(mode="json"),
                "threshold_tradeoff": [metric.model_dump(mode="json") for metric in tradeoff],
                "error_summary_at_selected_threshold": error_summary(
                    validation, scores, selected.threshold, feature_names
                ),
                "validation_scenario_metrics": group_metrics,
            }
    return output
