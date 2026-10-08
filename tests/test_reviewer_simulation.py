"""Tests for the deterministic reviewer simulation (stage 2).

These assert the stated reviewer policy is implemented literally: the shift budget bounds work done,
escalation is ``score >= strictness``, missed detections are counted over the whole labeled capture,
every rate is guarded against a zero denominator, ``ORACLE`` is refused, and the queue order is the
same order stage 1 ranked.
"""

from __future__ import annotations

import numpy as np
import pytest

from aegistrace.evaluation.analyst_replay import (
    RoutingPolicy,
    retrieval_curve,
    true_positives_at_budget,
)
from aegistrace.evaluation.reviewer_simulation import (
    ReviewerOutcome,
    ReviewerPolicy,
    routing_order,
    simulate_capture,
)

SCENARIO = "CTU-Malware-Capture-Botnet-00"
THRESHOLD = 0.5


def _flat_fixture() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Five known rows: scores descending, two malicious, one unknown row."""

    scores = np.array([0.9, 0.8, 0.7, 0.6, 0.4, 0.99], dtype=np.float64)
    labels = np.array([True, False, True, False, False, False], dtype=bool)
    known = np.array([True, True, True, True, True, False], dtype=bool)
    return scores, labels, known


def _outcome(
    simulation_outcomes: tuple[ReviewerOutcome, ...],
    policy: RoutingPolicy,
    strictness: float,
    shift_budget: int,
) -> ReviewerOutcome:
    for outcome in simulation_outcomes:
        candidate = outcome.policy
        if (
            candidate.routing_policy is policy
            and candidate.strictness == strictness
            and candidate.shift_budget == shift_budget
        ):
            return outcome
    raise AssertionError("reviewer policy not found in outcomes")


def test_shift_budget_bounds_reviewer_load_and_clamps_to_rows() -> None:
    scores, labels, known = _flat_fixture()
    simulation = simulate_capture(
        scenario_id=SCENARIO,
        scores=scores,
        labels=labels,
        known=known,
        threshold=THRESHOLD,
        strictness_values=(0.5,),
        shift_budgets=(2, 50),
        policies=(RoutingPolicy.MODEL_SCORE,),
        seed=1,
    )

    assert simulation.labeled_rows == 5
    assert simulation.malicious_rows == 2
    assert simulation.unknown_rows == 1
    assert _outcome(simulation.outcomes, RoutingPolicy.MODEL_SCORE, 0.5, 2).reviewer_load == 2
    assert _outcome(simulation.outcomes, RoutingPolicy.MODEL_SCORE, 0.5, 50).reviewer_load == 5


def test_model_score_escalation_is_strictness_threshold() -> None:
    scores, labels, known = _flat_fixture()
    simulation = simulate_capture(
        scenario_id=SCENARIO,
        scores=scores,
        labels=labels,
        known=known,
        threshold=THRESHOLD,
        strictness_values=(0.5, 0.85),
        shift_budgets=(5,),
        policies=(RoutingPolicy.MODEL_SCORE,),
        seed=1,
    )

    low = _outcome(simulation.outcomes, RoutingPolicy.MODEL_SCORE, 0.5, 5)
    # Known rows in descending score order: 0.9 (malicious), 0.8, 0.7 (malicious), 0.6, 0.4.
    assert low.escalations == 4
    assert low.true_escalations == 2
    assert low.false_escalations == 2
    assert low.escalation_rate == pytest.approx(4 / 5)
    assert low.false_escalation_rate == pytest.approx(2 / 4)
    assert low.missed_detections == 0
    assert low.missed_detection_rate == pytest.approx(0.0)

    high = _outcome(simulation.outcomes, RoutingPolicy.MODEL_SCORE, 0.85, 5)
    assert high.escalations == 1
    assert high.true_escalations == 1
    assert high.missed_detections == 1
    assert high.missed_detection_rate == pytest.approx(0.5)


def test_missed_detections_use_whole_labeled_capture_not_just_worked_rows() -> None:
    scores, labels, known = _flat_fixture()
    simulation = simulate_capture(
        scenario_id=SCENARIO,
        scores=scores,
        labels=labels,
        known=known,
        threshold=THRESHOLD,
        strictness_values=(0.5,),
        shift_budgets=(1,),
        policies=(RoutingPolicy.MODEL_SCORE,),
        seed=1,
    )

    outcome = _outcome(simulation.outcomes, RoutingPolicy.MODEL_SCORE, 0.5, 1)
    assert outcome.reviewer_load == 1
    assert outcome.true_escalations == 1
    assert outcome.missed_detections == 1
    assert outcome.missed_detection_rate == pytest.approx(0.5)


def test_zero_denominators_are_guarded() -> None:
    scores = np.array([0.9, 0.8], dtype=np.float64)
    labels = np.array([False, False], dtype=bool)
    known = np.array([True, True], dtype=bool)
    simulation = simulate_capture(
        scenario_id=SCENARIO,
        scores=scores,
        labels=labels,
        known=known,
        threshold=THRESHOLD,
        strictness_values=(0.5,),
        shift_budgets=(0, 10),
        policies=(RoutingPolicy.MODEL_SCORE,),
        seed=1,
    )
    empty = _outcome(simulation.outcomes, RoutingPolicy.MODEL_SCORE, 0.5, 0)
    assert (empty.reviewer_load, empty.escalations) == (0, 0)
    assert (empty.escalation_rate, empty.false_escalation_rate) == (0.0, 0.0)
    assert empty.missed_detections == 0
    assert empty.missed_detection_rate == 0.0

    no_rows = simulate_capture(
        scenario_id=SCENARIO,
        scores=np.empty(0, dtype=np.float64),
        labels=np.empty(0, dtype=bool),
        known=np.empty(0, dtype=bool),
        threshold=THRESHOLD,
        strictness_values=(0.5,),
        shift_budgets=(10,),
        policies=(RoutingPolicy.RANDOM,),
        seed=1,
    )
    assert no_rows.labeled_rows == 0
    assert no_rows.malicious_rows == 0
    assert no_rows.outcomes[0].missed_detection_rate == 0.0


def test_uncertainty_beats_model_score_on_a_crafted_queue() -> None:
    # Benign rows carry the highest scores; malicious rows sit on the decision boundary.
    scores = np.array([0.95, 0.94, 0.93, 0.5, 0.5, 0.5], dtype=np.float64)
    labels = np.array([False, False, False, True, True, True], dtype=bool)
    known = np.ones(6, dtype=bool)
    simulation = simulate_capture(
        scenario_id=SCENARIO,
        scores=scores,
        labels=labels,
        known=known,
        threshold=THRESHOLD,
        strictness_values=(0.5,),
        shift_budgets=(3,),
        policies=(RoutingPolicy.MODEL_SCORE, RoutingPolicy.UNCERTAINTY),
        seed=1,
    )

    model_score = _outcome(simulation.outcomes, RoutingPolicy.MODEL_SCORE, 0.5, 3)
    uncertainty = _outcome(simulation.outcomes, RoutingPolicy.UNCERTAINTY, 0.5, 3)
    assert model_score.true_escalations == 0
    assert uncertainty.true_escalations == 3


def test_random_policy_is_reproducible_and_policy_is_carried() -> None:
    scores, labels, known = _flat_fixture()
    kwargs = dict(
        scenario_id=SCENARIO,
        scores=scores,
        labels=labels,
        known=known,
        threshold=THRESHOLD,
        strictness_values=(0.5, 0.9),
        shift_budgets=(2, 4),
        policies=(RoutingPolicy.RANDOM,),
    )
    first = simulate_capture(**kwargs, seed=7)
    second = simulate_capture(**kwargs, seed=7)

    assert first == second
    assert len(first.outcomes) == 4
    for outcome in first.outcomes:
        assert isinstance(outcome.policy, ReviewerPolicy)
        assert outcome.policy.routing_policy is RoutingPolicy.RANDOM


def test_oracle_is_rejected() -> None:
    scores, labels, known = _flat_fixture()
    with pytest.raises(ValueError, match="ORACLE"):
        simulate_capture(
            scenario_id=SCENARIO,
            scores=scores,
            labels=labels,
            known=known,
            threshold=THRESHOLD,
            strictness_values=(0.5,),
            shift_budgets=(1,),
            policies=(RoutingPolicy.ORACLE,),
            seed=1,
        )


def test_misaligned_inputs_are_rejected() -> None:
    with pytest.raises(ValueError, match="align"):
        simulate_capture(
            scenario_id=SCENARIO,
            scores=np.zeros(2, dtype=np.float64),
            labels=np.zeros(3, dtype=bool),
            known=np.zeros(2, dtype=bool),
            threshold=THRESHOLD,
            strictness_values=(0.5,),
            shift_budgets=(1,),
            policies=(RoutingPolicy.MODEL_SCORE,),
            seed=1,
        )


def test_routing_order_matches_retrieval_curve_for_every_policy() -> None:
    rng = np.random.default_rng(3)
    scores = rng.random(60)
    labels = rng.random(60) < 0.3
    for policy in (RoutingPolicy.MODEL_SCORE, RoutingPolicy.UNCERTAINTY, RoutingPolicy.RANDOM):
        order = routing_order(scores, labels, policy=policy, threshold=THRESHOLD, seed=11)
        curve = retrieval_curve(scores, labels, policy=policy, threshold=THRESHOLD, seed=11)
        for budget in (1, 5, 17, 60):
            expected = int(np.count_nonzero(labels[order[:budget]]))
            assert true_positives_at_budget(curve, budget) == expected
