"""Apply the workload-first no-feasible-point correction to the stability artifact."""

from __future__ import annotations

import json
from pathlib import Path


def main() -> None:
    path = Path("data/evaluation/phase3_model_stability/stability_summary.json")
    summary = json.loads(path.read_text())
    result = summary["model_results"]["hist_gradient_boosting"]
    candidate = next(
        item for item in result["threshold_tradeoff"] if item["threshold"] == 1.0
    )
    result["operating_threshold"] = 1.0
    result["operating_metrics"] = candidate["metrics"]
    unknown_rows = sum(
        item["unknown_rows"] for item in summary["scenario_metadata"]["validation"]
    )
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
    old_scenario_metrics = result["validation_scenario_metrics_at_operating_point"]
    zero_alert_scenario_metrics = {}
    for scenario_id, old_metrics in old_scenario_metrics.items():
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
    for model_name in ("random_forest", "hist_gradient_boosting", "svm"):
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
    path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
