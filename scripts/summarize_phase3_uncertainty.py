"""Add aggregate Wilson intervals to existing Phase 3 validation artifacts.

This command does not refit models, select thresholds, or estimate PR-AUC
uncertainty. It summarizes uncertainty for metrics recoverable from recorded
confusion counts and explicitly keeps Scenario 7 sealed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from aegistrace.evaluation.uncertainty import confusion_intervals

SEALED_SCENARIO_ID = "CTU-Malware-Capture-Botnet-48"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        action="append",
        type=Path,
        dest="inputs",
        default=[],
        help="validation summary JSON; may be repeated",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/evaluation/phase3_uncertainty/uncertainty_summary.json"),
    )
    parser.add_argument("--created-at", required=True)
    parser.add_argument("--confidence", type=float, default=0.95)
    return parser


def _summary_intervals(summary: dict[str, Any], confidence: float) -> dict[str, Any]:
    validation_scenarios = tuple(summary.get("validation_scenarios", ()))
    if SEALED_SCENARIO_ID in validation_scenarios:
        raise ValueError("Scenario 7 is sealed and cannot be summarized")
    scenario_7 = summary.get("scenario_7")
    if isinstance(scenario_7, dict) and scenario_7.get("loaded"):
        raise ValueError("Scenario 7 artifact metadata indicates it was loaded")
    if isinstance(scenario_7, str) and "not loaded" not in scenario_7.lower():
        raise ValueError("Scenario 7 metadata does not prove it remained sealed")

    models: dict[str, Any] = {}
    for model_name, result in summary["model_results"].items():
        if model_name == "rules":
            continue
        models[model_name] = {
            "operating_threshold": result.get("operating_threshold"),
            "pooled": confusion_intervals(result["operating_metrics"], confidence=confidence),
            "per_scenario": {
                scenario: confusion_intervals(metrics, confidence=confidence)
                for scenario, metrics in result.get(
                    "validation_scenario_metrics_at_operating_point", {}
                ).items()
            },
        }
    return models


def main() -> int:
    args = _parser().parse_args()
    inputs = args.inputs or [
        Path("data/evaluation/phase3_model_stability/stability_summary.json"),
        Path("data/evaluation/phase3_causal_representation/causal_summary.json"),
    ]
    if not 0.0 < args.confidence < 1.0:
        raise ValueError("confidence must be between zero and one")
    summaries = [json.loads(path.read_text(encoding="utf-8")) for path in inputs]
    output: dict[str, Any] = {
        "schema_version": "1.0.0",
        "experiment_name": "phase3_aggregate_uncertainty",
        "created_at": args.created_at,
        "confidence_level": args.confidence,
        "interval_method": "Wilson score interval over recorded confusion counts",
        "scenario_7": {"status": "sealed", "loaded": False, "used_for_selection": False},
        "inputs": [],
        "runs": [],
        "limitations": [
            "Intervals describe aggregate confusion-count proportions, not independent "
            "event samples.",
            "PR-AUC uncertainty is not estimated because only aggregate confusion counts are used.",
            "This summary does not change model selection, thresholds, or final-policy status.",
            "Unknown Background and To-* rows remain outside supervised denominators.",
        ],
    }
    for path, summary in zip(inputs, summaries, strict=True):
        output["inputs"].append({"path": path.as_posix(), "digest": _sha256(path)})
        output["runs"].append(
            {
                "experiment_name": summary["experiment_name"],
                "feature_version": summary.get("feature_version"),
                "validation_scenarios": summary.get("validation_scenarios", []),
                "models": _summary_intervals(summary, args.confidence),
            }
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "output": args.output.as_posix(),
                "input_count": len(inputs),
                "confidence_level": args.confidence,
                "scenario_7": "sealed",
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
