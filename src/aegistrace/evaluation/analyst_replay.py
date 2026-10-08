"""Deterministic analyst-decision-theoretic replay of alert routing policies.

This module measures one narrow, fully deterministic quantity: given a fixed
reviewer budget of ``K`` alerts over the *known-label* rows of a single capture,
how many true positives does each ranking policy retrieve?  It compares four
policies on identical scores, labels, threshold, and data:

* ``MODEL_SCORE`` - descending model score (what a score-sorted queue gives).
* ``UNCERTAINTY`` - ascending ``abs(score - threshold)``; alerts closest to the
  frozen decision boundary are reviewed first.
* ``RANDOM`` - a fixed seeded permutation; the negative control.
* ``ORACLE`` - every malicious row first; the upper bound that uses labels.

Every ordering is deterministic: ties are broken on ``event_id`` (or, when no
ids are supplied, on the caller's input order via a stable sort), and the random
policy uses a fixed seed.

Interpretation guardrails
-------------------------

* A policy "beating" ``MODEL_SCORE`` is only meaningful if it *also* beats
  ``RANDOM``.  ``RANDOM`` is the negative control; ``ORACLE`` is the upper bound
  and is not achievable in deployment because it reads ground-truth labels.
* What this measures is the value of the ROUTING of already-computed scores.
  It says nothing about human cognition.  Nothing here is a claim about analyst
  behaviour, over-reliance, trust calibration, or automation bias.
* ``GroundTruthLabel.UNKNOWN`` rows are excluded from the labeled evaluation and
  reported separately as ``unknown_rows``.  Unknown rows are never counted as
  false positives and never appear in a retrieval curve.
* Each capture is evaluated separately; capture identity is never pooled away.
"""

from __future__ import annotations

from collections.abc import Sequence
from enum import StrEnum
from typing import Literal

import numpy as np
from numpy.typing import ArrayLike, NDArray

from aegistrace.schemas.common import FrozenSchema

__all__ = [
    "BudgetPoint",
    "BudgetSpec",
    "CaptureReplay",
    "PolicyResult",
    "RecallPoint",
    "RoutingPolicy",
    "alerts_to_reach_recall",
    "coverage_auc",
    "replay_capture",
    "retrieval_curve",
    "true_positives_at_budget",
]

DEFAULT_SEED = 42
DEFAULT_RECALL_TARGETS: tuple[float, ...] = (0.5, 0.9, 0.95)


class RoutingPolicy(StrEnum):
    """The four alert-routing policies compared by the replay."""

    MODEL_SCORE = "model_score"
    UNCERTAINTY = "uncertainty"
    RANDOM = "random"
    ORACLE = "oracle"


class BudgetSpec(FrozenSchema):
    """One requested reviewer budget, absolute or a fraction of labeled rows."""

    label: str
    kind: Literal["absolute", "fraction"]
    value: float


class BudgetPoint(FrozenSchema):
    """True positives retrieved at one realized budget for one policy."""

    label: str
    budget: int
    true_positives: int
    precision: float
    recall: float


class RecallPoint(FrozenSchema):
    """Smallest budget reaching a recall target, or ``None`` if unreachable."""

    target: float
    alerts: int | None


class PolicyResult(FrozenSchema):
    """Per-policy retrieval summary for one capture."""

    policy: RoutingPolicy
    coverage_auc: float
    curve_length: int
    budgets: tuple[BudgetPoint, ...]
    recall_targets: tuple[RecallPoint, ...]


class CaptureReplay(FrozenSchema):
    """Frozen per-capture replay result; captures are never pooled here."""

    scenario_id: str
    labeled_rows: int
    malicious_rows: int
    benign_rows: int
    unknown_rows: int
    threshold: float
    policies: tuple[PolicyResult, ...]


def _ranking_order(
    scores: NDArray[np.float64],
    labels: NDArray[np.bool_],
    *,
    policy: RoutingPolicy,
    threshold: float,
    seed: int,
    event_ids: Sequence[str] | None,
) -> NDArray[np.intp]:
    """Return the retrieval order of row indices for one policy.

    ``MODEL_SCORE``, ``UNCERTAINTY``, and ``ORACLE`` break ties on ``event_id``
    (falling back to a stable sort on input order).  ``RANDOM`` is a seeded
    permutation of the rows as given.
    """

    count = int(scores.shape[0])
    if count == 0:
        return np.empty(0, dtype=np.intp)
    if policy is RoutingPolicy.RANDOM:
        permutation = np.random.default_rng(seed).permutation(count)
        return np.asarray(permutation, dtype=np.intp)
    if policy is RoutingPolicy.MODEL_SCORE:
        primary = -scores
    elif policy is RoutingPolicy.UNCERTAINTY:
        primary = np.abs(scores - threshold)
    elif policy is RoutingPolicy.ORACLE:
        primary = np.where(labels, 0.0, 1.0)
    else:
        raise ValueError(f"unsupported routing policy {policy!r}")
    if event_ids is None:
        tie: NDArray[np.str_] = np.arange(count).astype(np.str_)
    else:
        if len(event_ids) != count:
            raise ValueError("event_ids must align with scores")
        tie = np.asarray(event_ids, dtype=np.str_)
    # lexsort: the last key is the primary sort key, so ties fall through to event_id.
    return np.asarray(np.lexsort((tie, primary)), dtype=np.intp)


def retrieval_curve(
    scores: ArrayLike,
    labels: ArrayLike,
    *,
    policy: RoutingPolicy,
    threshold: float,
    seed: int = DEFAULT_SEED,
    event_ids: Sequence[str] | None = None,
) -> list[int]:
    """Cumulative true positives at every budget ``K = 1..N``.

    ``scores`` and ``labels`` must already describe KNOWN-label rows only; the
    caller is responsible for excluding unknown-label rows.  The returned list
    has one entry per row, so ``curve[K - 1]`` is the true-positive count after
    reviewing the first ``K`` alerts in the policy's order.
    """

    score_array = np.asarray(scores, dtype=np.float64)
    label_array = np.asarray(labels, dtype=np.bool_)
    if score_array.shape[0] != label_array.shape[0]:
        raise ValueError("scores and labels must have equal length")
    order = _ranking_order(
        score_array,
        label_array,
        policy=policy,
        threshold=threshold,
        seed=seed,
        event_ids=event_ids,
    )
    return [int(value) for value in np.cumsum(label_array[order])]


def true_positives_at_budget(curve: Sequence[int], k: int) -> int:
    """True positives retrieved after ``k`` alerts; ``k`` is clamped to ``[0, N]``."""

    usable = min(max(int(k), 0), len(curve))
    if usable <= 0:
        return 0
    return int(curve[usable - 1])


def alerts_to_reach_recall(
    curve: Sequence[int], total_positives: int, target: float
) -> int | None:
    """Smallest budget ``K`` reaching ``target`` of all positives, else ``None``.

    ``target`` is a fraction in ``(0, 1]``.  ``None`` is returned when the target
    is unreachable because the curve never retrieves enough positives (for
    example when the capture contains no positives at all).
    """

    if not 0.0 < target <= 1.0:
        raise ValueError("target must be in (0, 1]")
    if total_positives <= 0 or not curve:
        return None
    required = int(np.ceil(target * total_positives))
    required = max(required, 1)
    for index, positives in enumerate(curve):
        if int(positives) >= required:
            return index + 1
    return None


def _trapezoid_area(values: NDArray[np.float64]) -> float:
    """Unit-spaced trapezoid integral of ``values`` sampled at ``0..N``."""

    if values.shape[0] < 2:
        return 0.0
    interior = float(np.sum(values[1:-1])) if values.shape[0] > 2 else 0.0
    return float((values[0] + values[-1]) / 2.0 + interior)


def coverage_auc(curve: Sequence[int], total_positives: int) -> float:
    """Normalized area under the coverage-vs-budget curve, via the trapezoid rule.

    Coverage at budget ``K`` is ``curve[K - 1] / total_positives`` and the curve
    starts at coverage ``0`` for budget ``0``.  The area is normalized by the
    area of the ideal (oracle) ordering, so the result is in ``[0, 1]`` and
    ``1.0`` means every positive was retrieved first.  A random ordering scores
    about ``0.5`` under this normalization.  ``0.0`` is returned when there are
    no positives or no rows, where coverage is undefined.
    """

    count = len(curve)
    if count == 0 or total_positives <= 0:
        return 0.0
    counts = np.asarray(curve, dtype=np.float64)
    if int(counts[-1]) <= 0:
        return 0.0
    coverage = np.concatenate(([0.0], counts / float(total_positives)))
    observed = _trapezoid_area(coverage)
    steps = np.arange(0, count + 1, dtype=np.float64)
    ideal = np.minimum(steps, float(total_positives)) / float(total_positives)
    ideal_area = _trapezoid_area(ideal)
    if ideal_area <= 0.0:
        return 0.0
    return float(min(1.0, max(0.0, observed / ideal_area)))


def _resolve_budget(spec: BudgetSpec, labeled_rows: int) -> int:
    """Resolve one budget spec against the capture's labeled-row count."""

    if labeled_rows <= 0:
        return 0
    requested = round(spec.value) if spec.kind == "absolute" else round(spec.value * labeled_rows)
    return min(max(requested, 1), labeled_rows)


def replay_capture(
    *,
    scenario_id: str,
    event_ids: Sequence[str],
    scores: ArrayLike,
    labels: ArrayLike,
    known: ArrayLike,
    threshold: float,
    budgets: Sequence[BudgetSpec],
    recall_targets: Sequence[float] = DEFAULT_RECALL_TARGETS,
    seed: int = DEFAULT_SEED,
) -> CaptureReplay:
    """Replay all routing policies on the known-label rows of one capture.

    ``scores``, ``labels``, and ``known`` are full-capture arrays in row order;
    ``labels`` is a boolean malicious indicator and ``known`` is a boolean mask
    that is true for authoritative benign/malicious rows.  Unknown rows are
    excluded from every curve and counted only in ``unknown_rows``.
    """

    score_array = np.asarray(scores, dtype=np.float64)
    label_array = np.asarray(labels, dtype=np.bool_)
    known_array = np.asarray(known, dtype=np.bool_)
    if not (
        score_array.shape[0] == label_array.shape[0] == known_array.shape[0] == len(event_ids)
    ):
        raise ValueError("event_ids, scores, labels, and known must align")
    if not np.all(np.isfinite(score_array)):
        raise ValueError("scores must be finite")

    known_scores = score_array[known_array]
    known_labels = label_array[known_array]
    known_ids = [str(value) for value in np.asarray(event_ids, dtype=object)[known_array]]
    # Sort known rows by event_id so even the seeded permutation is reproducible
    # regardless of physical parquet row order.
    id_order = np.argsort(np.asarray(known_ids, dtype=np.str_), kind="stable")
    known_scores = known_scores[id_order]
    known_labels = known_labels[id_order]
    known_ids = [known_ids[int(index)] for index in id_order]

    labeled_rows = int(known_labels.shape[0])
    malicious_rows = int(np.count_nonzero(known_labels))
    unknown_rows = int(np.count_nonzero(~known_array))
    resolved = [(spec, _resolve_budget(spec, labeled_rows)) for spec in budgets]

    policies: list[PolicyResult] = []
    for policy in RoutingPolicy:
        curve = retrieval_curve(
            known_scores,
            known_labels,
            policy=policy,
            threshold=threshold,
            seed=seed,
            event_ids=known_ids,
        )
        points: list[BudgetPoint] = []
        for spec, budget in resolved:
            positives = true_positives_at_budget(curve, budget)
            points.append(
                BudgetPoint(
                    label=spec.label,
                    budget=budget,
                    true_positives=positives,
                    precision=positives / budget if budget else 0.0,
                    recall=positives / malicious_rows if malicious_rows else 0.0,
                )
            )
        recall_points = tuple(
            RecallPoint(
                target=target,
                alerts=alerts_to_reach_recall(curve, malicious_rows, target),
            )
            for target in recall_targets
        )
        policies.append(
            PolicyResult(
                policy=policy,
                coverage_auc=coverage_auc(curve, malicious_rows),
                curve_length=len(curve),
                budgets=tuple(points),
                recall_targets=recall_points,
            )
        )

    return CaptureReplay(
        scenario_id=scenario_id,
        labeled_rows=labeled_rows,
        malicious_rows=malicious_rows,
        benign_rows=labeled_rows - malicious_rows,
        unknown_rows=unknown_rows,
        threshold=threshold,
        policies=tuple(policies),
    )
