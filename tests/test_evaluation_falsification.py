"""Falsification of every remaining never-executed guard in ```aegistrace/evaluation``.

Each test runs one guard against the exact input it exists to reject. A guard that is never
observed refusing the input it claims to refuse is an unverified claim, so every guard here is
executed and required to raise with its precise message (matched via ``match`` so a pass cannot
come from an unrelated error). Unless a test's ``# FINDING:`` comment says otherwise, the guard
refused correctly.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

import numpy as np
import pytest

from aegistrace.evaluation.analyst_replay import (
    RoutingPolicy,
    _ranking_order,
    replay_capture,
    retrieval_curve,
)
from aegistrace.evaluation.baselines import evaluate_scenario_split
from aegistrace.evaluation.hardening import alert_volume, calibration_summary
from aegistrace.evaluation.improvement import RecordLike, fit_scores
from aegistrace.evaluation.metrics import compute_binary_metrics
from aegistrace.evaluation.model_family import (
    _balanced_sample_weights,
    select_operating_threshold,
)
from aegistrace.features.network import FEATURE_NAMES, FeatureDataset, FeatureRecord
from aegistrace.schemas.events import GroundTruthLabel

BENIGN = GroundTruthLabel.BENIGN
MALICIOUS = GroundTruthLabel.MALICIOUS
UNKNOWN = GroundTruthLabel.UNKNOWN


@dataclass(frozen=True, slots=True)
class _Record:
    """Minimal :class:`RecordLike` populated only with the fields the guards inspect."""

    event_id: UUID
    scenario_id: str
    source_event_id: str
    ground_truth_label: GroundTruthLabel
    values: tuple[float, ...]


def _records(labels: tuple[GroundTruthLabel, ...]) -> tuple[_Record, ...]:
    return tuple(
        _Record(
            event_id=uuid4(),
            scenario_id="s",
            source_event_id=f"src-{index}",
            ground_truth_label=label,
            values=(0.5 + index / 10, 0.0, 1.0, 0.0),
        )
        for index, label in enumerate(labels)
    )


def _dataset(labels: tuple[GroundTruthLabel, ...]) -> FeatureDataset:
    return FeatureDataset(
        records=tuple(
            FeatureRecord(
                event_id=uuid4(),
                scenario_id="s",
                source_event_id=f"src-{index}",
                ground_truth_label=label,
                values=tuple(float(index) for _ in range(len(FEATURE_NAMES))),
            )
            for index, label in enumerate(labels)
        )
    )


# --- metrics.compute_binary_metrics ------------------------------------------


def test_metrics_rejects_length_mismatch() -> None:
    with pytest.raises(ValueError, match="labels and scores must have equal length"):
        compute_binary_metrics(
            [False, True], [0.1, 0.2, 0.3], model_name="m", split_name="s"
        )


def test_metrics_rejects_threshold_outside_unit_interval() -> None:
    with pytest.raises(ValueError, match="threshold must be between 0 and 1"):
        compute_binary_metrics(
            [False, True], [0.1, 0.2], model_name="m", split_name="s", threshold=1.5
        )


# --- hardening.calibration_summary -------------------------------------------


def test_calibration_rejects_length_mismatch() -> None:
    with pytest.raises(ValueError, match="labels and scores must have equal length"):
        calibration_summary([True], [0.1, 0.5])


def test_calibration_rejects_scores_outside_unit_interval() -> None:
    with pytest.raises(ValueError, match="scores must be between 0 and 1"):
        calibration_summary([True, False], [0.5, 1.5])


# --- hardening.alert_volume --------------------------------------------------


def test_alert_volume_rejects_threshold_outside_unit_interval() -> None:
    with pytest.raises(ValueError, match="threshold must be between 0 and 1"):
        alert_volume([False, True], [0.1, 0.9], [0.9, 0.1], threshold=1.5)


# --- baselines.evaluate_scenario_split ---------------------------------------


def test_scenario_split_rejects_empty_train_split() -> None:
    with pytest.raises(
        ValueError, match="each scenario split needs known benign and malicious rows"
    ):
        evaluate_scenario_split(
            train_dataset=_dataset(()),
            validation_dataset=_dataset((BENIGN, MALICIOUS)),
            test_dataset=_dataset((BENIGN, MALICIOUS)),
        )


def test_scenario_split_rejects_single_class_train_split() -> None:
    with pytest.raises(
        ValueError, match="training scenario must contain both known classes"
    ):
        evaluate_scenario_split(
            train_dataset=_dataset((BENIGN, BENIGN, BENIGN)),
            validation_dataset=_dataset((BENIGN, MALICIOUS)),
            test_dataset=_dataset((BENIGN, MALICIOUS)),
        )


# --- improvement.fit_scores --------------------------------------------------


def test_fit_scores_rejects_empty_train_pool() -> None:
    empty_train: tuple[RecordLike, ...] = _records((UNKNOWN, UNKNOWN))
    with pytest.raises(
        ValueError, match="training and validation pools must contain known rows"
    ):
        fit_scores(
            "logistic_regression",
            class_weight=None,
            train_records=empty_train,
            validation_records=_records((BENIGN, MALICIOUS)),
            seed=42,
        )


def test_fit_scores_rejects_single_class_train_pool() -> None:
    with pytest.raises(
        ValueError, match="training pool must contain both known classes"
    ):
        fit_scores(
            "logistic_regression",
            class_weight=None,
            train_records=_records((BENIGN, BENIGN)),
            validation_records=_records((BENIGN, MALICIOUS)),
            seed=42,
        )


# --- model_family._balanced_sample_weights -----------------------------------


def test_balanced_sample_weights_rejects_single_class() -> None:
    with pytest.raises(
        ValueError, match="balanced sample weights require both known classes"
    ):
        _balanced_sample_weights(_records((BENIGN, BENIGN, BENIGN)))


# --- model_family.select_operating_threshold ---------------------------------


def test_select_operating_threshold_rejects_precision_floor_outside_unit() -> None:
    with pytest.raises(
        ValueError, match="precision_floor must be between 0 and 1"
    ):
        select_operating_threshold(
            detector_name="d",
            validation_records=_records((BENIGN, MALICIOUS)),
            scores={},
            precision_floor=1.5,
        )


# --- analyst_replay.retrieval_curve ------------------------------------------


def test_retrieval_curve_rejects_length_mismatch() -> None:
    with pytest.raises(ValueError, match="scores and labels must have equal length"):
        retrieval_curve(
            [0.1, 0.2],
            [True],
            policy=RoutingPolicy.MODEL_SCORE,
            threshold=0.5,
            event_ids=["a", "b"],
        )


# --- analyst_replay.replay_capture -------------------------------------------


def test_replay_capture_rejects_misaligned_lengths() -> None:
    with pytest.raises(ValueError, match="event_ids, scores, labels, and known must align"):
        replay_capture(
            scenario_id="s",
            event_ids=["a", "b", "c"],
            scores=[0.1, 0.2],
            labels=[True, False],
            known=[True, True],
            threshold=0.5,
            budgets=[],
        )


def test_replay_capture_rejects_nonfinite_scores() -> None:
    with pytest.raises(ValueError, match="scores must be finite"):
        replay_capture(
            scenario_id="s",
            event_ids=["a", "b", "c"],
            scores=[0.2, np.nan, 0.5],
            labels=[True, False, True],
            known=[True, True, True],
            threshold=0.5,
            budgets=[],
        )


# --- analyst_replay._ranking_order -------------------------------------------


def test_ranking_order_rejects_event_ids_length_mismatch() -> None:
    with pytest.raises(ValueError, match="event_ids must align with scores"):
        _ranking_order(
            np.array([0.1, 0.2], dtype=np.float64),
            np.array([True, False], dtype=bool),
            policy=RoutingPolicy.MODEL_SCORE,
            threshold=0.5,
            seed=42,
            event_ids=["a"],
        )