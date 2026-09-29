"""Metrics that make class imbalance and error trade-offs explicit."""

from __future__ import annotations

from collections.abc import Sequence

from pydantic import Field
from sklearn.metrics import average_precision_score

from aegistrace.schemas.common import FrozenSchema, NonEmptyText, SchemaVersion


class BinaryMetrics(FrozenSchema):
    """Binary classification metrics at a fixed, documented score threshold."""

    schema_version: SchemaVersion = "1.0.0"
    model_name: NonEmptyText
    split_name: NonEmptyText
    threshold: float = Field(ge=0, le=1)
    support: int = Field(ge=0)
    positive_count: int = Field(ge=0)
    negative_count: int = Field(ge=0)
    true_positive: int = Field(ge=0)
    false_positive: int = Field(ge=0)
    true_negative: int = Field(ge=0)
    false_negative: int = Field(ge=0)
    confusion_matrix: tuple[tuple[int, int], tuple[int, int]]
    precision: float | None = Field(default=None, ge=0, le=1)
    recall: float | None = Field(default=None, ge=0, le=1)
    f1: float | None = Field(default=None, ge=0, le=1)
    false_positive_rate: float | None = Field(default=None, ge=0, le=1)
    false_negative_rate: float | None = Field(default=None, ge=0, le=1)
    pr_auc: float | None = Field(default=None, ge=0, le=1)


def compute_binary_metrics(
    labels: Sequence[bool],
    scores: Sequence[float],
    *,
    model_name: str,
    split_name: str,
    threshold: float = 0.5,
    include_pr_auc: bool = True,
) -> BinaryMetrics:
    """Compute threshold metrics and PR-AUC without evaluating unknown labels."""

    if len(labels) != len(scores):
        raise ValueError("labels and scores must have equal length")
    if not 0 <= threshold <= 1:
        raise ValueError("threshold must be between 0 and 1")
    predictions = [score >= threshold for score in scores]
    true_positive = sum(
        label and prediction for label, prediction in zip(labels, predictions, strict=True)
    )
    false_positive = sum(
        not label and prediction for label, prediction in zip(labels, predictions, strict=True)
    )
    true_negative = sum(
        not label and not prediction for label, prediction in zip(labels, predictions, strict=True)
    )
    false_negative = sum(
        label and not prediction for label, prediction in zip(labels, predictions, strict=True)
    )
    positive_count = sum(labels)
    negative_count = len(labels) - positive_count
    precision = (
        true_positive / (true_positive + false_positive) if true_positive + false_positive else None
    )
    recall = true_positive / positive_count if positive_count else None
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision is not None and recall is not None and precision + recall
        else None
    )
    false_positive_rate = (
        false_positive / (false_positive + true_negative)
        if false_positive + true_negative
        else None
    )
    false_negative_rate = (
        false_negative / (false_negative + true_positive)
        if false_negative + true_positive
        else None
    )
    pr_auc = (
        float(average_precision_score(labels, scores))
        if include_pr_auc and positive_count and negative_count
        else None
    )
    return BinaryMetrics(
        model_name=model_name,
        split_name=split_name,
        threshold=threshold,
        support=len(labels),
        positive_count=positive_count,
        negative_count=negative_count,
        true_positive=true_positive,
        false_positive=false_positive,
        true_negative=true_negative,
        false_negative=false_negative,
        confusion_matrix=((true_negative, false_positive), (false_negative, true_positive)),
        precision=precision,
        recall=recall,
        f1=f1,
        false_positive_rate=false_positive_rate,
        false_negative_rate=false_negative_rate,
        pr_auc=pr_auc,
    )
