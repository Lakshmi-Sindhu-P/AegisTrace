"""Deterministic reviewer simulation over the frozen Phase-3 policy (stage 2).

Stage 1 established that routing by decision-boundary uncertainty lost to routing by model score on
every one of the six captures.  This module asks whether that negative result is an artifact of one
routing rule by sweeping an *explicit* reviewer policy instead of a single retrieval budget.

Reviewer model (a POLICY, not a person)
---------------------------------------

This is a stated assumption set, **not** observed analyst behaviour:

* A reviewer works alerts from a queue ordered by the routing policy, up to a shift budget ``B``.
* For each alert worked, the reviewer escalates iff ``score >= strictness S``.
* Alerts beyond ``B`` are never worked.

Nothing here observes or estimates how a human analyst behaves.  It is a system-level sensitivity
analysis under stated reviewer assumptions and is not evidence about analyst decision quality,
over-reliance, trust calibration, or automation bias.

Definitions
-----------

* ``reviewer_load`` - alerts actually worked, ``min(B, labeled_rows)``.
* ``escalation_rate`` - ``escalations / reviewer_load`` (0.0 when the load is 0).
* ``false_escalation_rate`` - ``false_escalations / escalations``: the share of escalations that
  were not malicious (0.0 when no alert was escalated).
* ``missed_detection_rate`` - ``missed_detections / total_malicious`` over the whole labeled
  capture, including malicious rows that were never worked (0.0 when there are no malicious rows).

``model_score`` is the incumbent baseline established by stage 1.  A swept reviewer policy is only
interesting where it beats ``model_score`` at the same strictness and shift budget.  ``ORACLE`` is
omitted because it reads ground-truth labels and is not an achievable reviewer policy.

The review order delegates to the ranking rules used by
:func:`aegistrace.evaluation.analyst_replay.retrieval_curve`, so the simulated queue is exactly the
queue stage 1 ranked.  Known-label rows only; ``UNKNOWN`` rows are excluded and reported separately.
Each capture is evaluated separately and is never pooled with another capture.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from numpy.typing import ArrayLike, NDArray

from aegistrace.evaluation.analyst_replay import (
    DEFAULT_SEED,
    RoutingPolicy,
    _ranking_order,
)
from aegistrace.schemas.common import FrozenSchema

__all__ = [
    "DEFAULT_POLICIES",
    "DEFAULT_SHIFT_BUDGETS",
    "DEFAULT_STRICTNESS_VALUES",
    "CaptureSimulation",
    "ReviewerOutcome",
    "ReviewerPolicy",
    "routing_order",
    "simulate_capture",
]

DEFAULT_STRICTNESS_VALUES: tuple[float, ...] = (0.1, 0.2, 0.3, 0.5, 0.7)
DEFAULT_SHIFT_BUDGETS: tuple[int, ...] = (10, 25, 50, 100, 200)
DEFAULT_POLICIES: tuple[RoutingPolicy, ...] = (
    RoutingPolicy.MODEL_SCORE,
    RoutingPolicy.UNCERTAINTY,
    RoutingPolicy.RANDOM,
)


class ReviewerPolicy(FrozenSchema):
    """One simulated reviewer: escalation strictness, shift budget, queue order."""

    strictness: float
    shift_budget: int
    routing_policy: RoutingPolicy


class ReviewerOutcome(FrozenSchema):
    """Simulated reviewer outcome for one capture under one reviewer policy."""

    policy: ReviewerPolicy
    reviewer_load: int
    escalations: int
    escalation_rate: float
    false_escalations: int
    false_escalation_rate: float
    true_escalations: int
    missed_detections: int
    missed_detection_rate: float


class CaptureSimulation(FrozenSchema):
    """Per-capture simulation result; captures are never pooled here."""

    scenario_id: str
    labeled_rows: int
    malicious_rows: int
    unknown_rows: int
    threshold: float
    outcomes: tuple[ReviewerOutcome, ...]


def routing_order(
    scores: ArrayLike,
    labels: ArrayLike,
    *,
    policy: RoutingPolicy,
    threshold: float,
    seed: int = DEFAULT_SEED,
    event_ids: Sequence[str] | None = None,
) -> NDArray[np.intp]:
    """Review order of row indices for one routing policy.

    Delegates to the ranking rules behind
    :func:`aegistrace.evaluation.analyst_replay.retrieval_curve`; the ranking rules themselves are
    not reimplemented here.  ``scores`` and ``labels`` must describe known-label rows only.
    """

    return _ranking_order(
        np.asarray(scores, dtype=np.float64),
        np.asarray(labels, dtype=np.bool_),
        policy=policy,
        threshold=threshold,
        seed=seed,
        event_ids=event_ids,
    )


def _simulate_reviewer(
    *,
    policy: ReviewerPolicy,
    order: NDArray[np.intp],
    scores: NDArray[np.float64],
    labels: NDArray[np.bool_],
    malicious_rows: int,
    labeled_rows: int,
) -> ReviewerOutcome:
    """Run the stated reviewer policy over one ordered queue."""

    load = min(max(int(policy.shift_budget), 0), labeled_rows)
    worked = order[:load]
    worked_scores = scores[worked]
    worked_labels = labels[worked]
    escalated = worked_scores >= float(policy.strictness)
    escalations = int(np.count_nonzero(escalated))
    true_escalations = int(np.count_nonzero(escalated & worked_labels))
    false_escalations = escalations - true_escalations
    missed_detections = malicious_rows - true_escalations
    return ReviewerOutcome(
        policy=policy,
        reviewer_load=load,
        escalations=escalations,
        escalation_rate=escalations / load if load else 0.0,
        false_escalations=false_escalations,
        false_escalation_rate=(false_escalations / escalations if escalations else 0.0),
        true_escalations=true_escalations,
        missed_detections=missed_detections,
        missed_detection_rate=(
            missed_detections / malicious_rows if malicious_rows else 0.0
        ),
    )


def simulate_capture(
    *,
    scenario_id: str,
    scores: ArrayLike,
    labels: ArrayLike,
    known: ArrayLike,
    threshold: float,
    strictness_values: Sequence[float],
    shift_budgets: Sequence[int],
    policies: Sequence[RoutingPolicy],
    seed: int = DEFAULT_SEED,
    event_ids: Sequence[str] | None = None,
) -> CaptureSimulation:
    """Sweep the stated reviewer policy over the known-label rows of one capture.

    ``scores``, ``labels``, and ``known`` are full-capture arrays in row order; ``labels`` is a
    boolean malicious indicator and ``known`` is a boolean mask that is true for authoritative
    benign/malicious rows.  Unknown rows are excluded from every queue and counted only in
    ``unknown_rows``.  ``ORACLE`` is rejected because it reads ground-truth labels.
    """

    score_array = np.asarray(scores, dtype=np.float64)
    label_array = np.asarray(labels, dtype=np.bool_)
    known_array = np.asarray(known, dtype=np.bool_)
    if not (score_array.shape[0] == label_array.shape[0] == known_array.shape[0]):
        raise ValueError("scores, labels, and known must align")
    if not np.all(np.isfinite(score_array)):
        raise ValueError("scores must be finite")
    if any(policy is RoutingPolicy.ORACLE for policy in policies):
        raise ValueError("ORACLE is not an achievable reviewer policy")

    known_scores = score_array[known_array]
    known_labels = label_array[known_array]
    known_ids: list[str] | None = None
    if event_ids is not None:
        if len(event_ids) != score_array.shape[0]:
            raise ValueError("event_ids must align with scores")
        raw_ids = [str(value) for value in np.asarray(event_ids, dtype=object)[known_array]]
        id_order = np.argsort(np.asarray(raw_ids, dtype=np.str_), kind="stable")
        known_scores = known_scores[id_order]
        known_labels = known_labels[id_order]
        known_ids = [raw_ids[int(index)] for index in id_order]

    labeled_rows = int(known_labels.shape[0])
    malicious_rows = int(np.count_nonzero(known_labels))
    unknown_rows = int(np.count_nonzero(~known_array))

    outcomes: list[ReviewerOutcome] = []
    for routing_policy in policies:
        order = routing_order(
            known_scores,
            known_labels,
            policy=routing_policy,
            threshold=threshold,
            seed=seed,
            event_ids=known_ids,
        )
        for strictness in strictness_values:
            for shift_budget in shift_budgets:
                policy = ReviewerPolicy(
                    strictness=float(strictness),
                    shift_budget=int(shift_budget),
                    routing_policy=routing_policy,
                )
                outcomes.append(
                    _simulate_reviewer(
                        policy=policy,
                        order=order,
                        scores=known_scores,
                        labels=known_labels,
                        malicious_rows=malicious_rows,
                        labeled_rows=labeled_rows,
                    )
                )

    return CaptureSimulation(
        scenario_id=scenario_id,
        labeled_rows=labeled_rows,
        malicious_rows=malicious_rows,
        unknown_rows=unknown_rows,
        threshold=threshold,
        outcomes=tuple(outcomes),
    )
