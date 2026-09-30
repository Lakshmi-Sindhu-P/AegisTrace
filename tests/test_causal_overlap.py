"""Tests for deterministic Issue #3 overlap categorization helpers."""

from __future__ import annotations

import pytest
from scripts.analyze_phase3_causal_overlap import (
    COMMON_FEATURES,
    SUMMARY_FEATURES,
    _case_maps,
    _change_group,
    _feature_summary,
    _validate_artifact,
)


def _case(event_id: str, caught_by: list[str], scenario: str = "scenario") -> dict[str, object]:
    return {
        "event_id": event_id,
        "scenario_id": scenario,
        "source_event_id": f"line-{event_id}",
        "caught_by": caught_by,
        "missed_by": [],
    }


def test_overlap_categories_reconcile_rf_svm_union() -> None:
    assert _change_group(_case("a", []), _case("a", ["random_forest"])) == "causal_only"
    assert _change_group(_case("b", ["svm"]), _case("b", [])) == "reference_only"
    assert _change_group(_case("c", []), _case("c", [])) == "both_residual"
    assert _change_group(_case("d", ["random_forest"]), _case("d", ["svm"])) == "both_union"


def test_case_maps_require_identical_event_ids_and_scenarios() -> None:
    reference, groups = _case_maps([_case("a", [])], [_case("a", ["svm"])])
    assert reference["a"]["scenario_id"] == "scenario"
    assert groups["a"] == "causal_only"
    with pytest.raises(ValueError, match="same malicious cases"):
        _case_maps([_case("a", [])], [_case("b", [])])
    with pytest.raises(ValueError, match="scenario mismatch"):
        _case_maps([_case("a", [], "one")], [_case("a", [], "two")])


def test_feature_summary_is_order_independent() -> None:
    rows = []
    for index, value in enumerate((2.0, 1.0, 3.0)):
        rows.append(
            {
                "event_id": str(index),
                "scenario_id": "scenario",
                **{feature: value for feature in SUMMARY_FEATURES},
            }
        )
    groups = {str(index): "both_residual" for index in range(3)}
    assert _feature_summary(rows, groups) == _feature_summary(list(reversed(rows)), groups)
    assert set(COMMON_FEATURES).issubset(SUMMARY_FEATURES)


def test_validate_artifact_rejects_sealed_scenario() -> None:
    artifact = {
        "feature_version": "1.1.0",
        "validation_scenarios": ["CTU-Malware-Capture-Botnet-48"],
        "training_scenarios": [],
        "disagreement": {"malicious_case_count": 0, "cases": []},
    }
    with pytest.raises(ValueError, match="Scenario 7"):
        _validate_artifact(artifact, expected_version="1.1.0", name="reference")
