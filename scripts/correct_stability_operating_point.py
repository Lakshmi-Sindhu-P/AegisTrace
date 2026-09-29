"""Repair the validation-only stability artifact after the HGB policy correction.

The original correction changed HGB's operating point to the zero-alert
fallback but left case-level disagreement and residual sections at the old
threshold. This command recomputes those derived sections from the recorded
malicious-case IDs and immutable non-sealed behavioral artifacts. It never
loads Scenario 7.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    from scripts.run_phase3_model_stability import (
        FOCUSED_MODELS,
        _residual_error_analysis,
        _unique_svm_analysis,
    )
    from scripts.run_phase3_model_stability_cached import _load_features
except ModuleNotFoundError:
    from run_phase3_model_stability import (
        FOCUSED_MODELS,
        _residual_error_analysis,
        _unique_svm_analysis,
    )
    from run_phase3_model_stability_cached import _load_features

from aegistrace.evaluation.model_family import disagreement_report

ARTIFACT = Path("data/evaluation/phase3_model_stability/stability_summary.json")
FEATURE_ROOT = Path("data/evaluation/phase3_model_stability")
VALIDATION_SCENARIOS = (
    "CTU-Malware-Capture-Botnet-46",
    "CTU-Malware-Capture-Botnet-53",
    "CTU-Malware-Capture-Botnet-45",
    "CTU-Malware-Capture-Botnet-51",
)
SEALED_SCENARIO_ID = "CTU-Malware-Capture-Botnet-48"


def _remove_hgb(report: dict[str, Any]) -> dict[str, Any]:
    """Return case records with HGB removed from the old operating point."""

    cases = []
    detector_names = tuple(report["detector_malicious_catch_counts"])
    for case in report["cases"]:
        caught_by = tuple(name for name in case["caught_by"] if name != "hist_gradient_boosting")
        missed_by = tuple(name for name in detector_names if name not in caught_by)
        cases.append({**case, "caught_by": caught_by, "missed_by": missed_by})
    return {**report, "cases": cases}


def _predictions_from_cases(
    cases: list[dict[str, Any]], names: tuple[str, ...]
) -> dict[str, dict[str, bool]]:
    return {
        name: {
            str(case["event_id"]): name in case["caught_by"]
            for case in cases
        }
        for name in names
    }


def _load_validation_records() -> tuple[Any, ...]:
    records = []
    for scenario_id in VALIDATION_SCENARIOS:
        if scenario_id == SEALED_SCENARIO_ID:
            raise ValueError("Scenario 7 is sealed and cannot be repaired or loaded")
        path = FEATURE_ROOT / f"{scenario_id}_behavioral.parquet"
        scenario_records, _ = _load_features(path, scenario_id)
        records.extend(scenario_records)
    return tuple(records)


def main() -> None:
    summary = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    result = summary["model_results"]["hist_gradient_boosting"]
    candidate = next(item for item in result["threshold_tradeoff"] if item["threshold"] == 1.0)
    result["operating_threshold"] = 1.0
    result["operating_metrics"] = candidate["metrics"]
    unknown_rows = sum(item["unknown_rows"] for item in summary["scenario_metadata"]["validation"])
    result["alert_volume_at_operating_point"] = {
        "threshold": 1.0,
        "known_alerts": 0,
        "labeled_rows_scored": candidate["metrics"]["support"],
        "alerts_per_1000_labeled_flows": 0.0,
        "unknown_rows": unknown_rows,
        "unknown_alerts": None,
        "all_validation_alerts": None,
        "unknown_scoring": "not performed; unknown rows remain unknown",
    }
    result["operating_policy"]["selection_status"] = (
        "no_grid_point_satisfied_constraints; workload-first fallback selected zero-alert threshold"
    )
    result["operating_policy"]["fallback_policy"] = (
        "when no candidate satisfies both constraints, minimize workload-cap violation first, "
        "then precision-floor violation, then maximize recall"
    )
    zero_alert_scenario_metrics = {}
    for scenario_id, old_metrics in result[
        "validation_scenario_metrics_at_operating_point"
    ].items():
        negatives = old_metrics["negative_count"]
        positives = old_metrics["positive_count"]
        zero_alert_scenario_metrics[scenario_id] = {
            **old_metrics,
            "threshold": 1.0,
            "true_positive": 0,
            "false_positive": 0,
            "true_negative": negatives,
            "false_negative": positives,
            "confusion_matrix": ((negatives, 0), (positives, 0)),
            "precision": None,
            "recall": 0.0,
            "f1": None,
            "false_positive_rate": 0.0,
            "false_negative_rate": 1.0,
        }
    result["validation_scenario_metrics_at_operating_point"] = zero_alert_scenario_metrics
    for model_name in FOCUSED_MODELS:
        model_result = summary["model_results"][model_name]
        model_result["validation_scenario_alert_volume_at_operating_point"] = {
            scenario_id: {
                "known_alerts": metrics["true_positive"] + metrics["false_positive"],
                "labeled_rows": metrics["support"],
                "alerts_per_1000_labeled_flows": (
                    (metrics["true_positive"] + metrics["false_positive"])
                    / metrics["support"]
                    * 1000
                    if metrics["support"]
                    else None
                ),
            }
            for scenario_id, metrics in model_result[
                "validation_scenario_metrics_at_operating_point"
            ].items()
        }

    learned_old = summary["disagreement"]["learned_models"]
    including_old = summary["disagreement"]["including_rules"]
    learned_cases = _remove_hgb(learned_old)["cases"]
    including_cases = _remove_hgb(including_old)["cases"]
    validation_records = _load_validation_records()
    learned_predictions = _predictions_from_cases(learned_cases, FOCUSED_MODELS)
    including_predictions = _predictions_from_cases(
        including_cases, ("rules", *FOCUSED_MODELS)
    )
    summary["disagreement"] = {
        "learned_models": disagreement_report(
            validation_records=validation_records,
            detector_predictions=learned_predictions,
        ),
        "including_rules": disagreement_report(
            validation_records=validation_records,
            detector_predictions=including_predictions,
        ),
    }
    summary["svm_unique_coverage"] = _unique_svm_analysis(
        validation_records=validation_records,
        predictions=including_predictions,
    )
    summary["residual_error_analysis"] = _residual_error_analysis(
        validation_records=validation_records,
        predictions=including_predictions,
    )
    summary["artifact_repair"] = {
        "status": "validated",
        "reason": (
            "HGB zero-alert operating-point correction required derived disagreement and "
            "residual sections to be recomputed from recorded case IDs"
        ),
        "source": (
            "existing stability_summary.json case-level disagreement plus immutable behavioral "
            "Parquet artifacts"
        ),
        "scenario_7": "sealed; not loaded",
    }
    ARTIFACT.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
