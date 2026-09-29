"""Diagnose validation-case overlap changes between CTU-13 feature versions.

This is a read-only diagnostic over the corrected 1.1.0 stability artifact and
the 1.2.0 causal-representation artifact.  It does not fit a model, tune a
threshold, or load a scenario outside the four existing validation scenarios.
The malicious-case categories are derived from recorded RF/SVM predictions;
feature summaries are descriptive and never become a new model matrix.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from collections import Counter, defaultdict
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq

SEALED_SCENARIO_ID = "CTU-Malware-Capture-Botnet-48"
REFERENCE_VERSION = "1.1.0"
CAUSAL_VERSION = "1.2.0"
MODELS = ("random_forest", "svm")
GROUPS = ("causal_only", "reference_only", "both_residual", "both_union")
COMMON_FEATURES = (
    "duration_seconds",
    "log_total_bytes",
    "log_packet_count",
    "prior_source_connections_60s",
    "prior_unique_destinations_300s",
    "prior_unique_destination_ports_300s",
    "source_traffic_asymmetry",
    "prior_repeated_short_connections_300s",
)
CAUSAL_FEATURES = (
    "prior_source_connections_300s",
    "prior_unique_destinations_60s",
    "prior_unique_destination_ports_60s",
    "prior_unique_protocols_300s",
    "prior_destination_reuse_300s",
    "prior_destination_port_reuse_300s",
    "prior_short_connections_60s",
    "log_prior_total_bytes_300s",
    "log_prior_packet_count_300s",
    "log_seconds_since_prior_source_flow",
    "protocol_tcp",
    "protocol_udp",
    "protocol_icmp",
)
SUMMARY_FEATURES = COMMON_FEATURES + CAUSAL_FEATURES


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reference-artifact",
        type=Path,
        default=Path("data/evaluation/phase3_model_stability/stability_summary.json"),
    )
    parser.add_argument(
        "--causal-artifact",
        type=Path,
        default=Path("data/evaluation/phase3_causal_representation/causal_summary.json"),
    )
    parser.add_argument(
        "--reference-feature-dir",
        type=Path,
        default=Path("data/evaluation/phase3_model_stability"),
    )
    parser.add_argument(
        "--causal-feature-dir",
        type=Path,
        default=Path("data/evaluation/phase3_causal_representation"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/evaluation/phase3_causal_overlap/overlap_summary.json"),
    )
    parser.add_argument("--created-at", required=True)
    parser.add_argument("--seed", type=int, default=42)
    return parser


def _detectors(entry: dict[str, Any]) -> frozenset[str]:
    return frozenset(name for name in MODELS if name in entry["caught_by"])


def _model_overlap(detectors: frozenset[str]) -> str:
    if detectors == frozenset(MODELS):
        return "shared"
    if detectors == frozenset({"random_forest"}):
        return "rf_only"
    if detectors == frozenset({"svm"}):
        return "svm_only"
    return "none"


def _change_group(reference: dict[str, Any], causal: dict[str, Any]) -> str:
    reference_detectors = _detectors(reference)
    causal_detectors = _detectors(causal)
    if not reference_detectors and causal_detectors:
        return "causal_only"
    if reference_detectors and not causal_detectors:
        return "reference_only"
    if not reference_detectors and not causal_detectors:
        return "both_residual"
    return "both_union"


def _validate_artifact(
    artifact: dict[str, Any], *, expected_version: str, name: str
) -> list[dict[str, Any]]:
    if artifact.get("feature_version") != expected_version:
        raise ValueError(
            f"{name} feature_version must be {expected_version}, "
            f"got {artifact.get('feature_version')}"
        )
    scenarios = tuple(artifact.get("validation_scenarios", ()))
    if not scenarios or SEALED_SCENARIO_ID in scenarios:
        raise ValueError("Scenario 7 is sealed and cannot appear in this diagnostic")
    if artifact.get("training_scenarios") and SEALED_SCENARIO_ID in artifact["training_scenarios"]:
        raise ValueError("Scenario 7 is sealed and cannot appear in training metadata")
    disagreement = artifact["disagreement"]
    if "learned_models" in disagreement:
        disagreement = disagreement["learned_models"]
    cases = disagreement["cases"]
    if disagreement["malicious_case_count"] != len(cases):
        raise ValueError(f"{name} malicious case count does not match case records")
    return cases


def _case_maps(
    reference_cases: Iterable[dict[str, Any]], causal_cases: Iterable[dict[str, Any]]
) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    reference = {str(item["event_id"]): item for item in reference_cases}
    causal = {str(item["event_id"]): item for item in causal_cases}
    if set(reference) != set(causal):
        raise ValueError("reference and causal artifacts do not contain the same malicious cases")
    groups: dict[str, str] = {}
    for event_id in sorted(reference):
        if reference[event_id]["scenario_id"] != causal[event_id]["scenario_id"]:
            raise ValueError(f"scenario mismatch for event {event_id}")
        groups[event_id] = _change_group(reference[event_id], causal[event_id])
    return reference, groups


def _iter_feature_rows(
    path: Path, wanted: set[str], columns: tuple[str, ...]
) -> Iterable[dict[str, Any]]:
    if SEALED_SCENARIO_ID in path.name:
        raise ValueError("Scenario 7 is sealed and cannot be loaded")
    for batch in pq.ParquetFile(path).iter_batches(columns=["event_id", "scenario_id", *columns]):
        data = batch.to_pydict()
        for index, event_id in enumerate(data["event_id"]):
            event_id = str(event_id)
            if event_id not in wanted:
                continue
            yield {
                "event_id": event_id,
                "scenario_id": str(data["scenario_id"][index]),
                **{column: float(data[column][index]) for column in columns},
            }


def _quantiles(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"q25": None, "median": None, "q75": None, "mean": None}
    ordered = sorted(values)
    return {
        "q25": statistics.quantiles(ordered, n=4, method="inclusive")[0]
        if len(ordered) > 1
        else ordered[0],
        "median": statistics.median(ordered),
        "q75": statistics.quantiles(ordered, n=4, method="inclusive")[2]
        if len(ordered) > 1
        else ordered[0],
        "mean": statistics.fmean(ordered),
    }


def _feature_summary(
    rows: list[dict[str, Any]], groups: dict[str, str]
) -> dict[str, dict[str, dict[str, float | None]]]:
    values: dict[str, dict[str, list[float]]] = {
        group: {feature: [] for feature in SUMMARY_FEATURES} for group in GROUPS
    }
    for row in rows:
        group = groups[row["event_id"]]
        for feature in SUMMARY_FEATURES:
            values[group][feature].append(row[feature])
    return {
        group: {feature: _quantiles(values[group][feature]) for feature in SUMMARY_FEATURES}
        for group in GROUPS
    }


def _scenario_feature_summary(
    rows: list[dict[str, Any]], groups: dict[str, str]
) -> dict[str, dict[str, dict[str, dict[str, float | None]]]]:
    values: dict[str, dict[str, dict[str, list[float]]]] = defaultdict(
        lambda: {group: {feature: [] for feature in SUMMARY_FEATURES} for group in GROUPS}
    )
    for row in rows:
        group = groups[row["event_id"]]
        scenario = row["scenario_id"]
        for feature in SUMMARY_FEATURES:
            values[scenario][group][feature].append(row[feature])
    return {
        scenario: {
            group: {
                feature: _quantiles(values[scenario][group][feature])
                for feature in SUMMARY_FEATURES
            }
            for group in GROUPS
        }
        for scenario in sorted(values)
    }


def _ratio(
    summary: dict[str, dict[str, dict[str, float | None]]],
    numerator_group: str,
    denominator_group: str,
    feature: str,
) -> float | None:
    numerator = summary[numerator_group][feature]["median"]
    denominator = summary[denominator_group][feature]["median"]
    if numerator is None or denominator in (None, 0):
        return None
    return numerator / denominator


def _hypothesis(
    scenario_summary: dict[str, dict[str, dict[str, dict[str, float | None]]]],
    scenario_counts: dict[str, Counter[str]],
) -> dict[str, Any]:
    scenario = "CTU-Malware-Capture-Botnet-51"
    local = scenario_summary.get(scenario, {})
    required = ("causal_only", "both_residual")
    if any(group not in local for group in required):
        return {
            "statement": (
                "Within Scenario 10/51, candidate-only cases are burstier and no more "
                "destination-diverse than unchanged shared residuals."
            ),
            "status": "not_testable",
            "reason": "one required case group is absent",
        }
    rate_ratio = _ratio(local, "causal_only", "both_residual", "prior_source_connections_60s")
    destination_ratio = _ratio(
        local, "causal_only", "both_residual", "prior_unique_destinations_60s"
    )
    short_ratio = _ratio(local, "causal_only", "both_residual", "prior_short_connections_60s")
    supported = (
        rate_ratio is not None
        and short_ratio is not None
        and destination_ratio is not None
        and rate_ratio >= 1.5
        and short_ratio >= 1.5
        and destination_ratio <= 1.25
        and scenario_counts[scenario]["causal_only"] >= 100
    )
    return {
        "statement": (
            "Within Scenario 10/51, candidate-only cases are burstier and no more "
            "destination-diverse than unchanged shared residuals."
        ),
        "status": "supported_localized" if supported else "not_supported",
        "scope": scenario,
        "criteria": {
            "source_connections_60s_median_ratio_at_least": 1.5,
            "short_connections_60s_median_ratio_at_least": 1.5,
            "unique_destinations_60s_median_ratio_at_most": 1.25,
            "candidate_only_count_at_least": 100,
        },
        "observed": {
            "source_connections_60s_median_ratio": rate_ratio,
            "short_connections_60s_median_ratio": short_ratio,
            "unique_destinations_60s_median_ratio": destination_ratio,
            "candidate_only_count": scenario_counts[scenario]["causal_only"],
        },
        "interpretation": (
            "This supports a localized burst-density hypothesis for the overlap change, "
            "not a causal explanation for all residuals or a promotion decision."
            if supported
            else "The selected localized hypothesis is not supported by these summaries."
        ),
    }


def main() -> int:
    args = _parser().parse_args()
    reference_artifact = json.loads(args.reference_artifact.read_text(encoding="utf-8"))
    causal_artifact = json.loads(args.causal_artifact.read_text(encoding="utf-8"))
    reference_cases = _validate_artifact(
        reference_artifact, expected_version=REFERENCE_VERSION, name="reference"
    )
    causal_cases = _validate_artifact(
        causal_artifact, expected_version=CAUSAL_VERSION, name="causal"
    )
    if reference_artifact["validation_scenarios"] != causal_artifact["validation_scenarios"]:
        raise ValueError("reference and causal validation scenarios differ")
    reference, groups = _case_maps(reference_cases, causal_cases)
    causal_by_id = {str(item["event_id"]): item for item in causal_cases}
    wanted = set(reference)
    rows: list[dict[str, Any]] = []
    input_checksums = {
        "reference_artifact": _sha256(args.reference_artifact),
        "causal_artifact": _sha256(args.causal_artifact),
    }
    for scenario in reference_artifact["validation_scenarios"]:
        reference_path = args.reference_feature_dir / f"{scenario}_behavioral.parquet"
        causal_path = args.causal_feature_dir / f"{scenario}_causal.parquet"
        for path in (reference_path, causal_path):
            input_checksums[path.as_posix()] = _sha256(path)
        causal_rows = list(_iter_feature_rows(causal_path, wanted, SUMMARY_FEATURES))
        reference_rows = list(_iter_feature_rows(reference_path, wanted, COMMON_FEATURES))
        causal_feature_by_id = {row["event_id"]: row for row in causal_rows}
        reference_by_id = {row["event_id"]: row for row in reference_rows}
        expected = {
            event_id for event_id in wanted if reference[event_id]["scenario_id"] == scenario
        }
        if set(causal_feature_by_id) != expected or set(reference_by_id) != expected:
            raise ValueError(f"feature rows do not match malicious cases for {scenario}")
        for event_id in sorted(expected):
            causal_row = causal_feature_by_id[event_id]
            reference_row = reference_by_id[event_id]
            if causal_row["scenario_id"] != scenario or reference_row["scenario_id"] != scenario:
                raise ValueError(f"scenario mismatch in feature artifacts for {event_id}")
            for feature in COMMON_FEATURES:
                if causal_row[feature] != reference_row[feature]:
                    raise ValueError(
                        f"common feature changed between versions for {event_id}/{feature}"
                    )
            rows.append(causal_row)

    scenario_counts: dict[str, Counter[str]] = defaultdict(Counter)
    transition_counts: Counter[tuple[str, str]] = Counter()
    detector_changes: Counter[str] = Counter()
    for event_id, group in groups.items():
        scenario = reference[event_id]["scenario_id"]
        scenario_counts[scenario][group] += 1
        reference_overlap = _model_overlap(_detectors(reference[event_id]))
        causal_overlap = _model_overlap(_detectors(causal_by_id[event_id]))
        transition_counts[(reference_overlap, causal_overlap)] += 1
        reference_detectors = _detectors(reference[event_id])
        causal_entry = causal_by_id[event_id]
        causal_detectors = _detectors(causal_entry)
        for model in MODELS:
            if model in causal_detectors and model not in reference_detectors:
                detector_changes[f"{model}_gained"] += 1
            elif model in reference_detectors and model not in causal_detectors:
                detector_changes[f"{model}_lost"] += 1

    feature_summary = _feature_summary(rows, groups)
    scenario_feature_summary = _scenario_feature_summary(rows, groups)
    scenario_count_json = {
        scenario: {group: counts[group] for group in GROUPS}
        for scenario, counts in sorted(scenario_counts.items())
    }
    transition_json = {
        f"{reference_overlap}->{causal_overlap}": count
        for (reference_overlap, causal_overlap), count in sorted(transition_counts.items())
    }
    output: dict[str, Any] = {
        "schema_version": "1.0.0",
        "experiment_name": "phase3_causal_overlap_diagnosis",
        "created_at": args.created_at,
        "seed": args.seed,
        "feature_versions": {"reference": REFERENCE_VERSION, "causal": CAUSAL_VERSION},
        "training_scenarios": reference_artifact["training_scenarios"],
        "validation_scenarios": reference_artifact["validation_scenarios"],
        "scenario_7": {"status": "sealed", "loaded": False, "used_for_selection": False},
        "case_category_definition": {
            "causal_only": "RF/SVM union missed by 1.1.0 and caught by 1.2.0",
            "reference_only": "RF/SVM union caught by 1.1.0 and missed by 1.2.0",
            "both_residual": "RF/SVM union missed by both versions",
            "both_union": "RF/SVM union caught by both versions",
        },
        "malicious_case_count": len(groups),
        "case_category_counts": {
            group: sum(1 for value in groups.values() if value == group) for group in GROUPS
        },
        "case_category_counts_by_scenario": scenario_count_json,
        "rf_svm_overlap_transition_counts": transition_json,
        "detector_case_changes": dict(sorted(detector_changes.items())),
        "feature_lineage": {
            "common_features_verified_unchanged": list(COMMON_FEATURES),
            "causal_features_described": list(CAUSAL_FEATURES),
            "analysis_note": (
                "Summaries use authoritative malicious validation cases only; no analysis "
                "output is a model feature matrix."
            ),
        },
        "feature_summary": feature_summary,
        "feature_summary_by_scenario": scenario_feature_summary,
        "narrower_hypothesis": _hypothesis(scenario_feature_summary, scenario_counts),
        "limitations": [
            "The categories are conditional on frozen operating thresholds and cannot "
            "establish causality.",
            "Scenario 10/51 is a single validation scenario; the localized hypothesis "
            "requires a future held-out check before policy use.",
            "Pooled residual decrease is not evidence to promote 1.2.0 or justify fusion.",
            "Unknown Background and To-* rows are not treated as benign ground truth.",
        ],
        "source_checksums": input_checksums,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "output": args.output.as_posix(),
                "malicious_case_count": len(groups),
                "case_category_counts": output["case_category_counts"],
                "narrower_hypothesis": output["narrower_hypothesis"]["status"],
                "scenario_7": "sealed",
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
