"""Evaluation helpers for scenario-aware Phase 3 baselines."""

from aegistrace.evaluation.metrics import BinaryMetrics, compute_binary_metrics
from aegistrace.evaluation.uncertainty import confusion_intervals, wilson_interval

__all__ = [
    "BinaryMetrics",
    "compute_binary_metrics",
    "confusion_intervals",
    "wilson_interval",
]
