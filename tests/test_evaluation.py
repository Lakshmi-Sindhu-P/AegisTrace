"""Tests for explicit metrics and scenario-aware supervised baselines."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from aegistrace.evaluation.baselines import evaluate_scenario_split
from aegistrace.evaluation.hardening import alert_volume, calibration_summary
from aegistrace.evaluation.improvement import (
    error_summary,
    fit_scores,
    make_model,
    run_comparison,
    tune_threshold,
)
from aegistrace.evaluation.metrics import compute_binary_metrics
from aegistrace.evaluation.model_family import (
    MODEL_FAMILY_NAMES,
    _normalize_anomaly_scores,
    alert_volume_for_scores,
    disagreement_report,
    fit_isolation_forest_scores,
    fit_supervised_scores,
    metrics_for_scores,
    scenario_metrics,
    select_operating_threshold,
    select_validation_threshold,
)
from aegistrace.features.network import FEATURE_NAMES, FeatureDataset, FeatureRecord
from aegistrace.schemas.events import GroundTruthLabel


@dataclass(frozen=True, slots=True)
class _ImprovementRecord:
    event_id: UUID
    scenario_id: str
    source_event_id: str
    ground_truth_label: GroundTruthLabel
    values: tuple[float, ...]


def _dataset(scenario: str, offset: float) -> FeatureDataset:
    records = []
    for index, label in enumerate((GroundTruthLabel.BENIGN, GroundTruthLabel.MALICIOUS) * 4):
        values = tuple(offset + float(index + column) / 10 for column in range(len(FEATURE_NAMES)))
        records.append(
            FeatureRecord(
                event_id=uuid4(),
                scenario_id=scenario,
                source_event_id=f"line-{index}",
                ground_truth_label=label,
                values=values,
            )
        )
    return FeatureDataset(records=tuple(records))


def test_metrics_report_confusion_and_error_rates() -> None:
    metrics = compute_binary_metrics(
        [False, False, True, True],
        [0.1, 0.8, 0.2, 0.9],
        model_name="test",
        split_name="test",
    )

    assert metrics.confusion_matrix == ((1, 1), (1, 1))
    assert metrics.precision == 0.5
    assert metrics.recall == 0.5
    assert metrics.false_positive_rate == 0.5
    assert metrics.false_negative_rate == 0.5
    assert metrics.pr_auc is not None


def test_scenario_aware_models_fit_only_on_train_dataset() -> None:
    metrics, predictions = evaluate_scenario_split(
        train_dataset=_dataset("train", 0.0),
        validation_dataset=_dataset("validation", 0.1),
        test_dataset=_dataset("test", 0.2),
        seed=42,
    )

    assert set(metrics) == {"logistic_regression", "random_forest"}
    assert all(len(model_metrics) == 2 for model_metrics in metrics.values())
    assert {row["scenario_id"] for row in predictions} == {"validation", "test"}
    assert all("ground_truth_label" in row for row in predictions)


def _improvement_records(scenario: str, offset: float) -> tuple[_ImprovementRecord, ...]:
    rows: list[_ImprovementRecord] = []
    for index in range(12):
        malicious = index % 2 == 1
        value = offset + (2.0 if malicious else 0.0) + index / 100
        rows.append(
            _ImprovementRecord(
                event_id=uuid4(),
                scenario_id=scenario,
                source_event_id=f"line-{index}",
                ground_truth_label=GroundTruthLabel.MALICIOUS
                if malicious
                else GroundTruthLabel.BENIGN,
                values=(value, 0.0, 1.0, 0.0),
            )
        )
    rows.append(
        _ImprovementRecord(
            event_id=uuid4(),
            scenario_id=scenario,
            source_event_id="unknown",
            ground_truth_label=GroundTruthLabel.UNKNOWN,
            values=(0.0, 0.0, 0.0, 0.0),
        )
    )
    return tuple(rows)


def test_validation_only_improvement_comparison_and_error_summary() -> None:
    train = _improvement_records("train", 0.0) + _improvement_records("train2", 0.2)
    validation = _improvement_records("validation", 0.1)
    comparison = run_comparison(
        train_records=train,
        validation_records=validation,
        feature_family="test",
        feature_names=("a", "b", "c", "d"),
        seed=42,
        validation_groups={"validation": validation},
    )
    assert len(comparison) == 4
    assert all(item["threshold_tradeoff"] for item in comparison.values())
    assert all("validation" in item["validation_scenario_metrics"] for item in comparison.values())
    assert all(
        "false_negative_count" in item["error_summary_at_selected_threshold"]
        for item in comparison.values()
    )


def test_improvement_helpers_validate_model_and_threshold_inputs() -> None:
    train = _improvement_records("train", 0.0)
    validation = _improvement_records("validation", 0.1)
    model, known_validation, scores = fit_scores(
        "logistic_regression",
        class_weight="balanced",
        train_records=train,
        validation_records=validation,
        seed=42,
    )
    assert model is not None
    selected, tradeoff = tune_threshold(
        model_name="test", split_name="validation", validation=known_validation, scores=scores
    )
    assert selected.threshold in {metric.threshold for metric in tradeoff}
    assert error_summary(known_validation, scores, selected.threshold, ("a", "b", "c", "d"))
    assert make_model("random_forest", class_weight=None, seed=42) is not None
    try:
        make_model("unknown", class_weight=None, seed=42)
    except ValueError as error:
        assert "unsupported" in str(error)
    else:
        raise AssertionError("unsupported model should fail")


def test_hardening_calibration_and_alert_volume_metrics() -> None:
    labels = [False, False, True, True]
    scores = [0.1, 0.2, 0.7, 0.9]
    calibration = calibration_summary(labels, scores, bin_count=2)
    assert calibration["brier_score"] is not None
    assert calibration["expected_calibration_error"] is not None
    assert calibration["bins"]
    volume = alert_volume(labels, scores, [*scores, 0.8], threshold=0.5)
    assert volume["known_alerts"] == 2
    assert volume["all_validation_alerts"] == 3
    assert volume["alerts_per_1000_labeled_flows"] == 500.0
    assert calibration_summary([], [], bin_count=2)["bins"] == []
    try:
        calibration_summary(labels, scores, bin_count=1)
    except ValueError as error:
        assert "at least" in str(error)
    else:
        raise AssertionError("invalid bin count should fail")


def test_model_family_scores_are_validation_only_and_unknown_safe() -> None:
    train = _improvement_records("train", 0.0) + _improvement_records("train2", 0.2)
    validation = _improvement_records("validation", 0.1)
    for family in MODEL_FAMILY_NAMES:
        scores, metadata = fit_supervised_scores(
            family,
            train_records=train,
            validation_records=validation,
            seed=42,
        )
        assert len(scores) == len(validation)
        assert metadata["validation_rows_scored"] == len(validation)
    anomaly_scores, anomaly_metadata = fit_isolation_forest_scores(
        train_records=train,
        validation_records=validation,
        seed=42,
    )
    assert len(anomaly_scores) == len(validation)
    assert anomaly_metadata["training_rows_unknown"] == 0


def test_disagreement_report_exposes_unique_catches_and_misses() -> None:
    validation = _improvement_records("validation", 0.1)
    malicious = [
        record for record in validation if record.ground_truth_label is GroundTruthLabel.MALICIOUS
    ]
    first, second = malicious[:2]
    detector_predictions = {
        "rules": {str(first.event_id): True, str(second.event_id): False},
        "random_forest": {str(first.event_id): False, str(second.event_id): True},
        "isolation_forest": {str(first.event_id): False, str(second.event_id): False},
    }
    report = disagreement_report(
        validation_records=validation,
        detector_predictions=detector_predictions,
    )
    assert report["malicious_case_count"] == 6
    assert len(report["unique_catches"]["rules"]) == 1
    assert len(report["unique_catches"]["random_forest"]) == 1
    assert report["unique_misses"]["isolation_forest"] == []


def test_model_family_operating_policy_and_score_helpers() -> None:
    validation = _improvement_records("validation", 0.1)
    scores = {
        str(record.event_id): (
            0.9
            if record.ground_truth_label in {GroundTruthLabel.MALICIOUS, GroundTruthLabel.UNKNOWN}
            else 0.1
        )
        for record in validation
    }
    no_pr_auc = metrics_for_scores(
        detector_name="test",
        validation_records=validation,
        scores=scores,
        threshold=0.5,
        include_pr_auc=False,
    )
    assert no_pr_auc.pr_auc is None
    selected, tradeoff = select_validation_threshold(
        detector_name="test", validation_records=validation, scores=scores
    )
    assert selected.threshold in {item.threshold for item in tradeoff}
    operating, operating_tradeoff, policy = select_operating_threshold(
        detector_name="test",
        validation_records=validation,
        scores=scores,
        precision_floor=0.9,
        alerts_per_1000_cap=500.0,
    )
    assert operating.threshold == 0.11
    assert policy["selection_status"] == "constraint_satisfied"
    assert any(item["eligible"] for item in operating_tradeoff)
    fallback, _, fallback_policy = select_operating_threshold(
        detector_name="test",
        validation_records=validation,
        scores=scores,
        precision_floor=1.0,
        alerts_per_1000_cap=0.0,
    )
    assert fallback.threshold == 0.91
    assert fallback_policy["selection_status"] == "no_grid_point_satisfied_constraints"
    volume = alert_volume_for_scores(
        validation_records=validation, scores=scores, threshold=0.5
    )
    assert volume["known_alerts"] == 6
    assert volume["unknown_alerts"] == 1
    per_scenario = scenario_metrics(
        detector_name="test", validation_records=validation, scores=scores, threshold=0.5
    )
    assert set(per_scenario) == {"validation"}
    assert _normalize_anomaly_scores([1.0, 1.0], [0.0, 2.0])[0] == [0.0, 0.0]
    assert _normalize_anomaly_scores([0.0, 1.0], [-1.0, 2.0])[0] == [0.0, 1.0]


def test_model_family_rejects_invalid_pools_and_policy() -> None:
    unknown_only = _improvement_records("validation", 0.1)[-1:]
    known_only = tuple(
        record
        for record in _improvement_records("validation", 0.1)
        if record.ground_truth_label is GroundTruthLabel.BENIGN
    )
    try:
        fit_supervised_scores(
            "random_forest",
            train_records=unknown_only,
            validation_records=known_only,
            seed=42,
        )
    except ValueError as error:
        assert "known rows" in str(error)
    else:
        raise AssertionError("unknown-only training should fail")
    try:
        fit_supervised_scores(
            "random_forest",
            train_records=known_only,
            validation_records=known_only,
            seed=42,
        )
    except ValueError as error:
        assert "both known classes" in str(error)
    else:
        raise AssertionError("single-class training should fail")
    try:
        fit_isolation_forest_scores(train_records=(), validation_records=known_only, seed=42)
    except ValueError as error:
        assert "must not be empty" in str(error)
    else:
        raise AssertionError("empty anomaly training should fail")
    scores = {str(record.event_id): 0.5 for record in known_only}
    try:
        select_operating_threshold(
            detector_name="test",
            validation_records=known_only,
            scores=scores,
            precision_floor=1.1,
        )
    except ValueError as error:
        assert "precision_floor" in str(error)
    else:
        raise AssertionError("invalid precision floor should fail")
