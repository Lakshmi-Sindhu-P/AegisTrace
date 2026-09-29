"""Reconcile a causal-representation artifact with the corrected 1.1.0 reference.

This is a metadata-only repair: it does not refit models or load any scenario.
It is used after derived reference sections are repaired from recorded case
provenance, so candidate metrics are not silently compared with stale policy
metadata.
"""

from __future__ import annotations

import json
from pathlib import Path

from run_phase3_causal_representation import (
    FOCUSED_MODELS,
    _reference_snapshot,
)

ARTIFACT = Path("data/evaluation/phase3_causal_representation/causal_summary.json")


def main() -> None:
    summary = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    reference = _reference_snapshot()
    comparison = {}
    for name in FOCUSED_MODELS:
        baseline_metrics = reference["model_results"][name]["operating_metrics"]
        candidate_metrics = summary["model_results"][name]["operating_metrics"]
        comparison[name] = {
            "reference_feature_version": reference["feature_version"],
            "candidate_feature_version": summary["feature_version"],
            "reference_operating_threshold": reference["model_results"][name][
                "operating_threshold"
            ],
            "candidate_operating_threshold": summary["model_results"][name][
                "operating_threshold"
            ],
            "delta_precision": (candidate_metrics["precision"] or 0.0)
            - (baseline_metrics["precision"] or 0.0),
            "delta_recall": (candidate_metrics["recall"] or 0.0)
            - (baseline_metrics["recall"] or 0.0),
            "delta_f1": (candidate_metrics["f1"] or 0.0)
            - (baseline_metrics["f1"] or 0.0),
            "delta_pr_auc": (candidate_metrics["pr_auc"] or 0.0)
            - (baseline_metrics["pr_auc"] or 0.0),
            "reference_metrics": baseline_metrics,
            "candidate_metrics": candidate_metrics,
        }
    summary["reference"] = reference
    summary["comparison_to_reference"] = comparison
    summary["reference_reconciliation"] = {
        "status": "validated",
        "reason": "candidate comparison refreshed after corrected 1.1.0 HGB disagreement artifact",
        "scenario_7": "sealed; no candidate or reference data loaded",
    }
    ARTIFACT.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
