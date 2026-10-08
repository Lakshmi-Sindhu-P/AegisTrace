"""Tests for the deterministic analyst-decision-theoretic replay.

These assert the properties the research claim rests on: ranking orders are what they claim to be,
the random control is genuinely reproducible, unknown-label rows never enter a curve, and the
normalized coverage AUC is bounded so that oracle is 1.0 and random sits near 0.5.
"""

from __future__ import annotations

import numpy as np
import pytest

from aegistrace.evaluation.analyst_replay import (
    BudgetSpec,
    RoutingPolicy,
    alerts_to_reach_recall,
    coverage_auc,
    replay_capture,
    retrieval_curve,
    true_positives_at_budget,
)

COUNT = 100
POSITIVES = 10


def _fixture() -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Labels interleaved so no policy wins by accident of row order."""

    labels = np.zeros(COUNT, dtype=bool)
    labels[:: COUNT // POSITIVES] = True
    scores = np.where(labels, 0.8, 0.1)
    ids = [f"e{index:05d}" for index in range(COUNT)]
    return scores, labels, ids


def test_oracle_retrieves_every_positive_first() -> None:
    scores, labels, ids = _fixture()

    curve = retrieval_curve(
        scores, labels, policy=RoutingPolicy.ORACLE, threshold=0.2, event_ids=ids
    )

    assert curve[POSITIVES - 1] == POSITIVES
    assert coverage_auc(curve, POSITIVES) == 1.0


def test_model_score_ranks_by_descending_score() -> None:
    _, labels, ids = _fixture()
    scores = np.linspace(0.0, 1.0, COUNT)
    top = np.argsort(-scores)[:POSITIVES]
    labels = np.zeros(COUNT, dtype=bool)
    labels[top] = True

    curve = retrieval_curve(
        scores, labels, policy=RoutingPolicy.MODEL_SCORE, threshold=0.2, event_ids=ids
    )

    assert curve[POSITIVES - 1] == POSITIVES
    assert coverage_auc(curve, POSITIVES) == 1.0


def test_uncertainty_ranks_by_distance_from_the_threshold() -> None:
    _, labels, ids = _fixture()
    # Put positives exactly on the boundary and benign rows far from it.
    scores = np.where(labels, 0.2, 0.99)

    curve = retrieval_curve(
        scores, labels, policy=RoutingPolicy.UNCERTAINTY, threshold=0.2, event_ids=ids
    )

    assert curve[POSITIVES - 1] == POSITIVES
    assert coverage_auc(curve, POSITIVES) == 1.0


def test_random_control_is_reproducible_and_near_half() -> None:
    _, labels, ids = _fixture()

    first = retrieval_curve(
        np.zeros(COUNT), labels, policy=RoutingPolicy.RANDOM, threshold=0.2, event_ids=ids, seed=42
    )
    second = retrieval_curve(
        np.zeros(COUNT), labels, policy=RoutingPolicy.RANDOM, threshold=0.2, event_ids=ids, seed=42
    )
    other_seed = retrieval_curve(
        np.zeros(COUNT), labels, policy=RoutingPolicy.RANDOM, threshold=0.2, event_ids=ids, seed=7
    )

    assert first == second
    assert first != other_seed
    auc = coverage_auc(first, POSITIVES)
    assert 0.3 < auc < 0.7, auc


def test_deterministic_policies_ignore_physical_row_order() -> None:
    scores, labels, ids = _fixture()
    order = np.arange(COUNT)[::-1]

    for policy in (RoutingPolicy.MODEL_SCORE, RoutingPolicy.UNCERTAINTY, RoutingPolicy.ORACLE):
        forward = retrieval_curve(
            scores, labels, policy=policy, threshold=0.2, event_ids=ids
        )
        reversed_ = retrieval_curve(
            scores[order],
            labels[order],
            policy=policy,
            threshold=0.2,
            event_ids=[ids[i] for i in order],
        )
        assert forward == reversed_, policy


def test_true_positives_at_budget_clamps_and_handles_zero() -> None:
    curve = [1, 2, 3]

    assert true_positives_at_budget(curve, 0) == 0
    assert true_positives_at_budget(curve, -5) == 0
    assert true_positives_at_budget(curve, 2) == 2
    assert true_positives_at_budget(curve, 999) == 3


def test_alerts_to_reach_recall_finds_the_smallest_budget() -> None:
    curve = [0, 1, 2, 3, 4]

    assert alerts_to_reach_recall(curve, 4, 0.5) == 3
    assert alerts_to_reach_recall(curve, 4, 1.0) == 5
    assert alerts_to_reach_recall(curve, 0, 0.5) is None
    assert alerts_to_reach_recall([], 4, 0.5) is None
    with pytest.raises(ValueError, match="target must be in"):
        alerts_to_reach_recall(curve, 4, 0.0)
    with pytest.raises(ValueError, match="target must be in"):
        alerts_to_reach_recall(curve, 4, 1.5)


def test_coverage_auc_is_zero_without_positives_or_rows() -> None:
    assert coverage_auc([], 0) == 0.0
    assert coverage_auc([0, 0, 0], 0) == 0.0


def test_replay_capture_excludes_unknown_rows_from_the_labeled_evaluation() -> None:
    scores, labels, ids = _fixture()
    known = np.ones(COUNT, dtype=bool)
    known[::3] = False  # every third row is unknown-labeled
    unknown_count = int(np.count_nonzero(~known))

    result = replay_capture(
        scenario_id="CTU-Malware-Capture-Botnet-48",
        event_ids=ids,
        scores=np.where(known, scores, 0.99),
        labels=labels,
        known=known,
        threshold=0.2,
        budgets=(BudgetSpec(label="k50", kind="absolute", value=50),),
    )

    assert result.unknown_rows == unknown_count
    assert result.labeled_rows == COUNT - unknown_count
    assert result.labeled_rows + result.unknown_rows == COUNT
    assert result.malicious_rows + result.benign_rows == result.labeled_rows
    for policy in result.policies:
        assert policy.curve_length == result.labeled_rows


def test_replay_capture_reports_the_oracle_bound_and_the_random_control() -> None:
    scores, labels, ids = _fixture()

    result = replay_capture(
        scenario_id="CTU-Malware-Capture-Botnet-48",
        event_ids=ids,
        scores=scores,
        labels=labels,
        known=np.ones(COUNT, dtype=bool),
        threshold=0.2,
        budgets=(BudgetSpec(label="k10", kind="absolute", value=10),),
        recall_targets=(0.5, 1.0),
    )

    by_policy = {item.policy: item for item in result.policies}
    assert by_policy[RoutingPolicy.ORACLE].coverage_auc == 1.0
    assert by_policy[RoutingPolicy.ORACLE].budgets[0].true_positives == POSITIVES
    assert by_policy[RoutingPolicy.RANDOM].coverage_auc < 1.0
    assert by_policy[RoutingPolicy.ORACLE].recall_targets[1].alerts == POSITIVES


def test_replay_capture_resolves_fraction_budgets_and_validates_alignment() -> None:
    scores, labels, ids = _fixture()
    known = np.ones(COUNT, dtype=bool)

    result = replay_capture(
        scenario_id="capture",
        event_ids=ids,
        scores=scores,
        labels=labels,
        known=known,
        threshold=0.2,
        budgets=(BudgetSpec(label="one_percent", kind="fraction", value=0.01),),
    )

    assert result.policies[0].budgets[0].budget == 1

    with pytest.raises(ValueError, match="must align"):
        replay_capture(
            scenario_id="capture",
            event_ids=ids[:-1],
            scores=scores,
            labels=labels,
            known=known,
            threshold=0.2,
            budgets=(),
        )
