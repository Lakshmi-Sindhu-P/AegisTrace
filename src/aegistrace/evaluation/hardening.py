"""Metrics for the pre-final validation-only detector hardening pass."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from aegistrace.evaluation.metrics import BinaryMetrics, compute_binary_metrics

BEHAVIORAL_FEATURE_GROUPS: dict[str, tuple[str, ...]] = {
    "connection_rate": ("prior_source_connections_60s",),
    "destination_diversity": ("prior_unique_destinations_300s",),
    "destination_port_diversity": ("prior_unique_destination_ports_300s",),
    "traffic_asymmetry": (
        "source_traffic_asymmetry",
        "source_traffic_asymmetry_missing",
    ),
    "repeated_short_connections": ("prior_repeated_short_connections_300s",),
}


def calibration_summary(
    labels: Sequence[bool], scores: Sequence[float], *, bin_count: int = 10
) -> dict[str, Any]:
    """Return Brier score, expected calibration error, and reliability bins."""

    if len(labels) != len(scores):
        raise ValueError("labels and scores must have equal length")
    if bin_count < 2:
        raise ValueError("bin_count must be at least 2")
    if not labels:
        return {"brier_score": None, "expected_calibration_error": None, "bins": []}
    if any(score < 0 or score > 1 for score in scores):
        raise ValueError("scores must be between 0 and 1")
    buckets: list[list[tuple[bool, float]]] = [[] for _ in range(bin_count)]
    for label, score in zip(labels, scores, strict=True):
        index = min(int(score * bin_count), bin_count - 1)
        buckets[index].append((label, score))
    bins: list[dict[str, float | int]] = []
    weighted_gap = 0.0
    total = len(labels)
    for index, values in enumerate(buckets):
        if not values:
            continue
        mean_score = sum(score for _, score in values) / len(values)
        observed_rate = sum(label for label, _ in values) / len(values)
        weighted_gap += len(values) / total * abs(mean_score - observed_rate)
        bins.append(
            {
                "lower_bound": index / bin_count,
                "upper_bound": (index + 1) / bin_count,
                "count": len(values),
                "mean_score": mean_score,
                "observed_positive_rate": observed_rate,
            }
        )
    brier = sum((score - float(label)) ** 2 for label, score in zip(labels, scores, strict=True))
    return {
        "brier_score": brier / total,
        "expected_calibration_error": weighted_gap,
        "bins": bins,
    }


def alert_volume(
    labels: Sequence[bool],
    known_scores: Sequence[float],
    all_scores: Sequence[float],
    *,
    threshold: float,
) -> dict[str, float | int | None]:
    """Report labeled confusion counts and alert workload at one threshold."""

    # The threshold range is checked by `compute_binary_metrics` below, which is called
    # unconditionally and raises the identical ValueError. A duplicate check here produced the
    # identical message from two places, which made the falsification test for THIS guard vacuous:
    # deleting it left the test green because the delegated call raised instead. One guard, one
    # place, and the test that names it now covers it.
    metrics: BinaryMetrics = compute_binary_metrics(
        labels,
        known_scores,
        model_name="behavioral_random_forest",
        split_name="validation",
        threshold=threshold,
    )
    known_alerts = sum(score >= threshold for score in known_scores)
    all_alerts = sum(score >= threshold for score in all_scores)
    return {
        "threshold": threshold,
        "precision": metrics.precision,
        "recall": metrics.recall,
        "f1": metrics.f1,
        "false_positive": metrics.false_positive,
        "false_negative": metrics.false_negative,
        "false_positive_rate": metrics.false_positive_rate,
        "false_negative_rate": metrics.false_negative_rate,
        "known_alerts": known_alerts,
        "all_validation_alerts": all_alerts,
        "alerts_per_1000_labeled_flows": known_alerts / metrics.support * 1000
        if metrics.support
        else None,
    }
