"""Deterministic uncertainty summaries for aggregate confusion counts."""

from __future__ import annotations

from collections.abc import Mapping
from statistics import NormalDist
from typing import Any


def wilson_interval(
    successes: int, trials: int, *, confidence: float = 0.95
) -> tuple[float, float] | None:
    """Return a Wilson interval for a binomial proportion.

    This interval only describes a recorded aggregate count. It does not add
    uncertainty to PR-AUC or replace scenario-held-out evaluation.
    """

    if trials < 0 or successes < 0 or successes > trials:
        raise ValueError("successes must be between zero and trials")
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must be between zero and one")
    if trials == 0:
        return None
    z = NormalDist().inv_cdf(0.5 + confidence / 2.0)
    proportion = successes / trials
    denominator = 1.0 + z**2 / trials
    center = (proportion + z**2 / (2.0 * trials)) / denominator
    half_width = (
        z
        * ((proportion * (1.0 - proportion) / trials) + z**2 / (4.0 * trials**2)) ** 0.5
        / denominator
    )
    return (max(0.0, center - half_width), min(1.0, center + half_width))


def confusion_intervals(
    metrics: Mapping[str, Any], *, confidence: float = 0.95
) -> dict[str, tuple[float, float] | None]:
    """Summarize precision, recall, FPR, FNR, and alert-rate intervals."""

    true_positive = int(metrics["true_positive"])
    false_positive = int(metrics["false_positive"])
    true_negative = int(metrics["true_negative"])
    false_negative = int(metrics["false_negative"])
    return {
        "precision": wilson_interval(
            true_positive, true_positive + false_positive, confidence=confidence
        ),
        "recall": wilson_interval(
            true_positive, true_positive + false_negative, confidence=confidence
        ),
        "false_positive_rate": wilson_interval(
            false_positive, false_positive + true_negative, confidence=confidence
        ),
        "false_negative_rate": wilson_interval(
            false_negative, true_positive + false_negative, confidence=confidence
        ),
        "alert_rate": wilson_interval(
            true_positive + false_positive,
            true_positive + false_positive + true_negative + false_negative,
            confidence=confidence,
        ),
    }
