"""Validation-only model-family and disagreement evaluation helpers.

This module deliberately accepts training and validation records only. It keeps
unknown rows out of supervised fitting and labeled metrics, while allowing the
separate Isolation Forest experiment to score all rows as an unsupervised
prioritization signal. No function accepts a final-test dataset.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from time import perf_counter
from typing import Any, Protocol

from sklearn.ensemble import (
    ExtraTreesClassifier,
    HistGradientBoostingClassifier,
    IsolationForest,
    RandomForestClassifier,
)
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC
from sklearn.tree import DecisionTreeClassifier

from aegistrace.evaluation.metrics import BinaryMetrics, compute_binary_metrics
from aegistrace.schemas.events import GroundTruthLabel

MODEL_FAMILY_VERSION = "1.0.0"
FIXED_POLICY_THRESHOLD = 0.20
THRESHOLD_GRID: tuple[float, ...] = tuple(index / 20 for index in range(1, 20))
# Operating-point selection is deliberately a policy constraint, not a score
# calibration claim.  Each model's score is evaluated on its own [0, 1] scale.
OPERATING_THRESHOLD_GRID: tuple[float, ...] = tuple(index / 100 for index in range(0, 101))
OPERATING_PRECISION_FLOOR = 0.95
OPERATING_ALERTS_PER_1000_CAP = 200.0
MODEL_FAMILY_NAMES: tuple[str, ...] = (
    "logistic_regression",
    "decision_tree",
    "random_forest",
    "extra_trees",
    "hist_gradient_boosting",
    "svm",
)


class RecordLike(Protocol):
    """Minimal feature-record contract shared by behavioral and test records."""

    event_id: Any
    scenario_id: str
    source_event_id: str
    ground_truth_label: GroundTruthLabel
    values: tuple[float, ...]


def known(records: Sequence[RecordLike]) -> tuple[RecordLike, ...]:
    """Keep only authoritative benign/malicious rows for supervised metrics."""

    return tuple(
        record for record in records if record.ground_truth_label is not GroundTruthLabel.UNKNOWN
    )


def _labels(records: Sequence[RecordLike]) -> list[bool]:
    return [record.ground_truth_label is GroundTruthLabel.MALICIOUS for record in records]


def _balanced_sample_weights(records: Sequence[RecordLike]) -> list[float]:
    labels = _labels(records)
    positives = sum(labels)
    negatives = len(labels) - positives
    if positives == 0 or negatives == 0:
        raise ValueError("balanced sample weights require both known classes")
    positive_weight = len(labels) / (2 * positives)
    negative_weight = len(labels) / (2 * negatives)
    return [positive_weight if label else negative_weight for label in labels]


def make_model(model_name: str, *, seed: int) -> Any:
    """Build one fixed, reproducible candidate without looking at validation data."""

    if model_name == "logistic_regression":
        from sklearn.linear_model import LogisticRegression
        from sklearn.preprocessing import StandardScaler

        return Pipeline(
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
        )
    if model_name == "decision_tree":
        return DecisionTreeClassifier(
            class_weight="balanced",
            max_depth=6,
            min_samples_leaf=20,
            random_state=seed,
        )
    if model_name == "random_forest":
        return RandomForestClassifier(
            class_weight="balanced",
            max_depth=12,
            n_estimators=200,
            n_jobs=1,
            random_state=seed,
        )
    if model_name == "extra_trees":
        return ExtraTreesClassifier(
            class_weight="balanced",
            max_depth=12,
            n_estimators=200,
            n_jobs=1,
            random_state=seed,
        )
    if model_name == "hist_gradient_boosting":
        return HistGradientBoostingClassifier(
            learning_rate=0.1,
            l2_regularization=1.0,
            max_iter=200,
            max_leaf_nodes=31,
            random_state=seed,
        )
    if model_name == "svm":
        from sklearn.preprocessing import StandardScaler

        return Pipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "classifier",
                    LinearSVC(
                        C=1.0,
                        class_weight="balanced",
                        dual="auto",
                        max_iter=5000,
                        random_state=seed,
                    ),
                ),
            ]
        )
    raise ValueError(f"unsupported model family {model_name}")


def _fit_supervised(
    model_name: str,
    train_records: Sequence[RecordLike],
    *,
    seed: int,
) -> tuple[Any, float]:
    train = known(train_records)
    if not train:
        raise ValueError("training pool must contain known rows")
    if {record.ground_truth_label for record in train} != {
        GroundTruthLabel.BENIGN,
        GroundTruthLabel.MALICIOUS,
    }:
        raise ValueError("training pool must contain both known classes")
    model = make_model(model_name, seed=seed)
    matrix = [record.values for record in train]
    labels = _labels(train)
    started = perf_counter()
    if model_name == "hist_gradient_boosting":
        model.fit(matrix, labels, sample_weight=_balanced_sample_weights(train))
    else:
        model.fit(matrix, labels)
    return model, perf_counter() - started


def fit_supervised_scores(
    model_name: str,
    *,
    train_records: Sequence[RecordLike],
    validation_records: Sequence[RecordLike],
    seed: int,
) -> tuple[dict[str, float], dict[str, Any]]:
    """Fit on known training rows and score every validation row."""

    model, fit_seconds = _fit_supervised(model_name, train_records, seed=seed)
    train_matrix = [record.values for record in known(train_records)]
    validation_matrix = [record.values for record in validation_records]
    scores, score_metadata = _model_scores(
        model,
        train_matrix=train_matrix,
        validation_matrix=validation_matrix,
    )
    return (
        {
            str(record.event_id): score
            for record, score in zip(validation_records, scores, strict=True)
        },
        {
            "fit_seconds": fit_seconds,
            "training_rows_known": len(known(train_records)),
            "validation_rows_scored": len(validation_records),
            **score_metadata,
        },
    )


def _normalize_anomaly_scores(
    train_scores: Sequence[float], validation_scores: Sequence[float]
) -> tuple[list[float], dict[str, float]]:
    lower = min(train_scores)
    upper = max(train_scores)
    span = upper - lower
    if span <= 0:
        return [0.0 for _ in validation_scores], {"training_min": lower, "training_max": upper}
    normalized = [max(0.0, min(1.0, (score - lower) / span)) for score in validation_scores]
    return normalized, {"training_min": lower, "training_max": upper}


def _model_scores(
    model: Any,
    *,
    train_matrix: Sequence[tuple[float, ...]],
    validation_matrix: Sequence[tuple[float, ...]],
    chunk_size: int = 50_000,
) -> tuple[list[float], dict[str, Any]]:
    """Score in bounded batches, using probabilities or normalized margins."""

    if hasattr(model, "predict_proba"):
        scores: list[float] = []
        for start in range(0, len(validation_matrix), chunk_size):
            batch = validation_matrix[start : start + chunk_size]
            scores.extend(float(row[1]) for row in model.predict_proba(batch))
        return scores, {
            "score_semantics": "raw classifier score interpreted as ranking/probability-like output"
        }
    train_margin = [float(value) for value in model.decision_function(train_matrix)]
    validation_margin = [float(value) for value in model.decision_function(validation_matrix)]
    scores, normalization = _normalize_anomaly_scores(train_margin, validation_margin)
    return scores, {
        "score_semantics": "training-range-normalized linear SVM margin; not a probability",
        "score_normalization": normalization,
    }


def fit_isolation_forest_scores(
    *,
    train_records: Sequence[RecordLike],
    validation_records: Sequence[RecordLike],
    seed: int,
) -> tuple[dict[str, float], dict[str, Any]]:
    """Fit Isolation Forest without labels and return normalized anomaly scores.

    The practical baseline fits on known feature rows without passing labels to the
    estimator. Unknown validation rows remain unknown and are scored only for
    separate workload analysis; no ground-truth label is changed.
    """

    if not train_records or not validation_records:
        raise ValueError("training and validation pools must not be empty")
    train_known = known(train_records)
    model = IsolationForest(
        contamination="auto",
        n_estimators=100,
        n_jobs=1,
        random_state=seed,
    )
    train_matrix = [record.values for record in train_known]
    validation_matrix = [record.values for record in validation_records]
    started = perf_counter()
    model.fit(train_matrix)
    fit_seconds = perf_counter() - started
    raw_train = [-float(value) for value in model.decision_function(train_matrix)]
    raw_validation = [-float(value) for value in model.decision_function(validation_matrix)]
    scores, normalization = _normalize_anomaly_scores(raw_train, raw_validation)
    return (
        {
            str(record.event_id): score
            for record, score in zip(validation_records, scores, strict=True)
        },
        {
            "fit_seconds": fit_seconds,
            "training_rows_all_labels": len(train_known),
            "training_rows_known": len(train_known),
            "training_rows_unknown": 0,
            "score_semantics": "training-range-normalized anomaly ranking; not a probability",
            "contamination": "auto",
            "training_selection": "known rows only; labels not passed to Isolation Forest",
            "normalization": normalization,
        },
    )


def artifact_fit_metadata(runtime: Mapping[str, Any]) -> dict[str, Any]:
    """Return fit-scoring metadata with the wall-clock ``fit_seconds`` value removed.

    ``fit_seconds`` is measured with :func:`time.perf_counter` purely as operator
    telemetry.  Serializing it would place a non-reproducible value inside artifact
    bytes whose SHA-256 digest the committed manifest records as reproducible
    evidence (issue #21), so every producing script excludes it from the artifact
    payload.  The measurement is kept for the operator by reporting it on the
    script's stderr log instead.
    """

    return {key: value for key, value in runtime.items() if key != "fit_seconds"}


def metrics_for_scores(
    *,
    detector_name: str,
    validation_records: Sequence[RecordLike],
    scores: dict[str, float],
    threshold: float,
    include_pr_auc: bool = True,
) -> BinaryMetrics:
    labeled = known(validation_records)
    return compute_binary_metrics(
        _labels(labeled),
        [scores[str(record.event_id)] for record in labeled],
        model_name=detector_name,
        split_name="validation",
        threshold=threshold,
        include_pr_auc=include_pr_auc,
    )


def select_validation_threshold(
    *,
    detector_name: str,
    validation_records: Sequence[RecordLike],
    scores: dict[str, float],
) -> tuple[BinaryMetrics, tuple[BinaryMetrics, ...]]:
    """Select a threshold on validation only using the established tie-breaks."""

    tradeoff = tuple(
        metrics_for_scores(
            detector_name=detector_name,
            validation_records=validation_records,
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


def select_operating_threshold(
    *,
    detector_name: str,
    validation_records: Sequence[RecordLike],
    scores: dict[str, float],
    precision_floor: float = OPERATING_PRECISION_FLOOR,
    alerts_per_1000_cap: float = OPERATING_ALERTS_PER_1000_CAP,
) -> tuple[BinaryMetrics, tuple[dict[str, Any], ...], dict[str, Any]]:
    """Choose a validation-only operating point under explicit workload policy.

    The policy maximizes recall subject to precision and labeled-alert workload
    constraints.  Unknown rows never enter the precision denominator or the
    constraint; their alert count is reported separately by the workload helper.
    Thresholds are candidates on each detector's own score scale and therefore
    are not comparable numeric probabilities across model families.
    """

    if not 0 <= precision_floor <= 1:
        raise ValueError("precision_floor must be between 0 and 1")
    if alerts_per_1000_cap < 0:
        raise ValueError("alerts_per_1000_cap must be non-negative")
    labeled = known(validation_records)
    known_scores = [scores[str(record.event_id)] for record in labeled]
    support = len(labeled)
    pr_auc = metrics_for_scores(
        detector_name=detector_name,
        validation_records=labeled,
        scores=scores,
        threshold=0.5,
    ).pr_auc
    tradeoff: list[dict[str, Any]] = []
    for threshold in OPERATING_THRESHOLD_GRID:
        metrics = metrics_for_scores(
            detector_name=detector_name,
            validation_records=validation_records,
            scores=scores,
            threshold=threshold,
            include_pr_auc=False,
        )
        # Unknown rows are intentionally not rescanned for every candidate:
        # they cannot affect precision or the labeled-workload constraint.
        known_alerts = sum(score >= threshold for score in known_scores)
        volume: dict[str, float | int | None] = {
            "threshold": threshold,
            "known_alerts": known_alerts,
            "unknown_rows": len(validation_records) - support,
            "unknown_alerts": None,
            "all_validation_alerts": None,
            "alerts_per_1000_labeled_flows": known_alerts / support * 1000 if support else None,
        }
        precision = metrics.precision if metrics.precision is not None else 0.0
        alerts_per_1000 = volume["alerts_per_1000_labeled_flows"]
        candidate_eligible = (
            precision >= precision_floor
            and alerts_per_1000 is not None
            and alerts_per_1000 <= alerts_per_1000_cap
        )
        metric_payload = metrics.model_dump(mode="json")
        metric_payload["pr_auc"] = pr_auc
        tradeoff.append(
            {
                "threshold": threshold,
                "metrics": metric_payload,
                "alert_volume": volume,
                "eligible": candidate_eligible,
            }
        )
    eligible_candidates = [item for item in tradeoff if item["eligible"]]
    if eligible_candidates:
        selected_item = max(
            eligible_candidates,
            key=lambda item: (
                item["metrics"]["recall"] if item["metrics"]["recall"] is not None else -1.0,
                item["metrics"]["precision"] if item["metrics"]["precision"] is not None else -1.0,
                -item["threshold"],
            ),
        )
        selection_status = "constraint_satisfied"
    else:
        # Preserve a truthful artifact when no grid point satisfies policy. The
        # fallback minimizes constraint violation, then prefers recall.
        selected_item = min(
            tradeoff,
            key=lambda item: (
                max(
                    0.0,
                    (item["alert_volume"]["alerts_per_1000_labeled_flows"] or 0.0)
                    - alerts_per_1000_cap,
                ),
                max(0.0, precision_floor - (item["metrics"]["precision"] or 0.0)),
                -(item["metrics"]["recall"] or 0.0),
                item["threshold"],
            ),
        )
        selection_status = "no_grid_point_satisfied_constraints"
    selected = metrics_for_scores(
        detector_name=detector_name,
        validation_records=validation_records,
        scores=scores,
        threshold=float(selected_item["threshold"]),
    )
    policy = {
        "selection_status": selection_status,
        "objective": "maximize recall",
        "precision_floor": precision_floor,
        "alerts_per_1000_labeled_flows_cap": alerts_per_1000_cap,
        "threshold_candidates": "0.01 increments on each model's own normalized/score scale",
        "unknown_rows_in_constraints": "excluded; reported separately as workload context",
    }
    return selected, tuple(tradeoff), policy


def alert_volume_for_scores(
    *,
    validation_records: Sequence[RecordLike],
    scores: dict[str, float],
    threshold: float,
) -> dict[str, float | int | None]:
    labeled = known(validation_records)
    known_scores = [scores[str(record.event_id)] for record in labeled]
    all_scores = [scores[str(record.event_id)] for record in validation_records]
    metrics = compute_binary_metrics(
        _labels(labeled),
        known_scores,
        model_name="model_family_benchmark",
        split_name="validation",
        threshold=threshold,
    )
    known_alerts = sum(score >= threshold for score in known_scores)
    all_alerts = sum(score >= threshold for score in all_scores)
    unknown_count = len(validation_records) - len(labeled)
    return {
        "threshold": threshold,
        "known_alerts": known_alerts,
        "unknown_rows": unknown_count,
        "unknown_alerts": all_alerts - known_alerts,
        "all_validation_alerts": all_alerts,
        "alerts_per_1000_labeled_flows": known_alerts / metrics.support * 1000
        if metrics.support
        else None,
    }


def scenario_metrics(
    *,
    detector_name: str,
    validation_records: Sequence[RecordLike],
    scores: dict[str, float],
    threshold: float,
) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for scenario_id in sorted({record.scenario_id for record in validation_records}):
        records = tuple(
            record for record in validation_records if record.scenario_id == scenario_id
        )
        metrics = metrics_for_scores(
            detector_name=detector_name,
            validation_records=records,
            scores=scores,
            threshold=threshold,
        )
        output[scenario_id] = metrics.model_dump(mode="json")
    return output


def disagreement_report(
    *,
    validation_records: Sequence[RecordLike],
    detector_predictions: dict[str, dict[str, bool]],
) -> dict[str, Any]:
    """Report per-case overlap, unique catches, and unique misses on known malicious rows."""

    malicious = tuple(
        record
        for record in validation_records
        if record.ground_truth_label is GroundTruthLabel.MALICIOUS
    )
    detector_names = tuple(detector_predictions)
    cases: list[dict[str, Any]] = []
    for record in malicious:
        event_id = str(record.event_id)
        caught_by = tuple(
            name for name in detector_names if detector_predictions[name].get(event_id, False)
        )
        cases.append(
            {
                "event_id": event_id,
                "scenario_id": record.scenario_id,
                "source_event_id": record.source_event_id,
                "caught_by": caught_by,
                "missed_by": tuple(name for name in detector_names if name not in caught_by),
            }
        )
    unique_catches: dict[str, list[dict[str, str]]] = {name: [] for name in detector_names}
    unique_misses: dict[str, list[dict[str, str]]] = {name: [] for name in detector_names}
    for case in cases:
        caught_by = tuple(case["caught_by"])
        missed_by = tuple(case["missed_by"])
        if len(caught_by) == 1:
            unique_catches[caught_by[0]].append(
                {key: str(case[key]) for key in ("event_id", "scenario_id", "source_event_id")}
            )
        if len(missed_by) == 1:
            unique_misses[missed_by[0]].append(
                {key: str(case[key]) for key in ("event_id", "scenario_id", "source_event_id")}
            )
    pairwise_overlap: dict[str, dict[str, int]] = {}
    for left in detector_names:
        pairwise_overlap[left] = {}
        for right in detector_names:
            pairwise_overlap[left][right] = sum(
                detector_predictions[left].get(str(record.event_id), False)
                and detector_predictions[right].get(str(record.event_id), False)
                for record in malicious
            )
    return {
        "malicious_case_count": len(malicious),
        "case_coverage_histogram": dict(
            sorted(Counter(len(case["caught_by"]) for case in cases).items())
        ),
        "detector_malicious_catch_counts": {
            name: sum(
                detector_predictions[name].get(str(record.event_id), False) for record in malicious
            )
            for name in detector_names
        },
        "unique_catches": unique_catches,
        "unique_misses": unique_misses,
        "all_detector_cases": [
            case for case in cases if len(case["caught_by"]) == len(detector_names)
        ],
        "no_detector_cases": [case for case in cases if not case["caught_by"]],
        "pairwise_catch_overlap_counts": pairwise_overlap,
        "cases": cases,
    }
