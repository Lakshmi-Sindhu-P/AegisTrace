"""Emit classifier scores as versioned, evidence-linked ``DetectionResult`` records.

**Score semantics (the important part).** A model score is only meaningful relative to the model
that produced it. A Random Forest probability of ``0.73`` and a gradient-boosted probability of
``0.73`` are different quantities on different scales, and ranking them against each other is
meaningless. This module therefore never compares, combines, or re-scales scores across models.
Each emitted record keeps its own ``detector_name``, ``detector_version``, and ``model_name``, and
the supporting evidence says which feature contract produced the number. Downstream code that wants
to rank alerts must rank *within* one model, or use a documented cross-model policy that is not
this module's job to invent.

Severity is derived from the score by fixed bands so that severity is a presentation label, not a
second, hidden ranking across models.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import datetime
from uuid import UUID

from aegistrace.schemas.detections import (
    DetectionEvidence,
    DetectionResult,
    DetectionSeverity,
    DetectorType,
    detection_id_for,
)
from aegistrace.schemas.events import SecurityEvent

ML_SEVERITY_BANDS: tuple[tuple[float, DetectionSeverity], ...] = (
    (0.90, DetectionSeverity.CRITICAL),
    (0.75, DetectionSeverity.HIGH),
    (0.50, DetectionSeverity.MEDIUM),
    (0.25, DetectionSeverity.LOW),
)
_ML_NOTE = "model signal; not proof of compromise or an incident"
_SCALE_NOTE = "score is model-specific and not comparable across models"


def severity_for_score(score: float) -> DetectionSeverity:
    """Map a model score to a severity band using fixed, documented thresholds."""

    if not 0.0 <= score <= 1.0:
        raise ValueError("score must be within [0, 1]")
    for lower_bound, severity in ML_SEVERITY_BANDS:
        if score >= lower_bound:
            return severity
    return DetectionSeverity.INFORMATIONAL


def emit_ml_detections(
    events: Iterable[SecurityEvent],
    scores: Mapping[UUID, float],
    *,
    detector_name: str,
    detector_version: str,
    model_name: str,
    feature_version: str,
    threshold: float,
    created_at: datetime,
) -> tuple[DetectionResult, ...]:
    """Emit one detection per event whose model score reaches ``threshold``.

    Events without a score, or below the threshold, produce no record: the threshold is a frozen
    policy input, so this function must not choose one.
    """

    if not 0.0 <= threshold <= 1.0:
        raise ValueError("threshold must be within [0, 1]")

    ordered = sorted(events, key=lambda event: (event.observed_at, str(event.event_id)))
    detections: list[DetectionResult] = []
    for event in ordered:
        score = scores.get(event.event_id)
        if score is None or score < threshold:
            continue
        detections.append(
            DetectionResult(
                detection_id=detection_id_for(
                    event_id=event.event_id,
                    detector_name=detector_name,
                    detector_version=detector_version,
                    rule_id=f"ml:{model_name}",
                ),
                event_id=event.event_id,
                detector_type=DetectorType.ML,
                detector_name=detector_name,
                detector_version=detector_version,
                severity=severity_for_score(score),
                score=score,
                triggered_rules=(f"model:{model_name}", f"ml_threshold:{threshold:g}"),
                supporting_evidence=(
                    DetectionEvidence(
                        field="model_score",
                        observed_value=score,
                        predicate=f"model_score >= {threshold:g}",
                    ),
                    DetectionEvidence(
                        field="feature_version",
                        observed_value=feature_version,
                        predicate="feature contract used at inference time",
                    ),
                    DetectionEvidence(
                        field="model_name",
                        observed_value=model_name,
                        predicate="identifies the score scale; do not compare across models",
                    ),
                ),
                created_at=created_at,
                note=f"{_ML_NOTE}; {_SCALE_NOTE}",
            )
        )
    return tuple(detections)


__all__ = ["ML_SEVERITY_BANDS", "emit_ml_detections", "severity_for_score"]
