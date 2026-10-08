"""Validate that the LLM A/B triage preregistration is frozen before the data exists.

This checks the properties that make a preregistration real rather than a story written after the
fact:

* the status is ``FROZEN_PRE_DATA``;
* exactly one primary metric is declared, so the result metric cannot be chosen post hoc;
* a refutation condition is present, so the experiment can lose;
* every secondary metric is marked ``exploratory: true``, so it cannot be presented as the primary
  result;
* the pre-data attestation still agrees with the live provider freeze file; and
* **ordering**: the preregistration's ``frozen_at`` is strictly earlier than the ``created_at`` of
  every registry run that references a provider or triage run. A protocol written after a run that
  consumed the provider would be fitted to that run's output.

Exit 0 and print a JSON summary when there are no violations; exit 1 and list every violation
otherwise.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

DEFAULT_PREREGISTRATION = "configs/llm_ab_preregistration.json"
DEFAULT_FREEZE = "configs/triage_provider_freeze.json"
DEFAULT_REGISTRY = "docs/experiment_registry.json"

REQUIRED_STATUS = "FROZEN_PRE_DATA"

#: A registry run is treated as provider-consuming when its command or configuration mentions a
#: provider, a triage run, an assessor, or an LLM. Matched as plain case-insensitive substrings, not
#: whole words: identifiers such as ``run_independent_triage`` or ``provider_freeze`` embed these
#: terms next to underscores, where a word-boundary pattern would silently miss them. A false
#: positive only forces us to prove the preregistration is older than the run, which is the safe
#: direction.
PROVIDER_RUN_MARKERS = re.compile(r"(provider|triage|assessor|llm)", re.IGNORECASE)

_MISSING = object()


def _load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def parse_timestamp(value: Any) -> datetime | None:
    """Parse an ISO 8601 timestamp, returning ``None`` unless it carries an explicit UTC offset."""

    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed


def _freeze_spend(freeze: Mapping[str, Any]) -> Any:
    """Return the freeze's recorded spend, wherever the freeze places it.

    The committed freeze records it at ``budget.measured_spend``. The other locations are accepted
    so this check keeps working if the freeze is ever reorganised, since the property under test is
    agreement with the observed value, not the nesting.
    """

    for key in ("budget", "egress_policy"):
        block = freeze.get(key)
        if isinstance(block, Mapping) and "measured_spend" in block:
            return block["measured_spend"]
    return freeze.get("measured_spend", _MISSING)


def _references_provider(run: Mapping[str, Any]) -> bool:
    command = str(run.get("command", ""))
    if PROVIDER_RUN_MARKERS.search(command):
        return True
    configuration = json.dumps(run.get("configuration", {}), sort_keys=True, default=str)
    return bool(PROVIDER_RUN_MARKERS.search(configuration))


def _ordering_violations(frozen_at: datetime | None, registry_path: str | Path) -> list[str]:
    if frozen_at is None:
        return []  # the unparseable frozen_at is already reported
    try:
        registry = _load_json(registry_path)
    except (OSError, json.JSONDecodeError) as exc:
        return [f"cannot read registry {registry_path}: {exc}"]
    runs = registry.get("runs") if isinstance(registry, Mapping) else None
    if not isinstance(runs, list):
        return [f"registry {registry_path} must contain a 'runs' list"]

    violations: list[str] = []
    for index, run in enumerate(runs):
        if not isinstance(run, Mapping) or not _references_provider(run):
            continue
        run_id = run.get("experiment_id") or f"runs[{index}]"
        created_at = parse_timestamp(run.get("created_at"))
        if created_at is None:
            violations.append(
                f"ordering check: run {run_id!r} references a provider or triage run but has no "
                f"parseable created_at with a UTC offset, so the preregistration cannot be proven "
                f"to predate it"
            )
            continue
        if not frozen_at < created_at:
            violations.append(
                f"ordering violation: run {run_id!r} references a provider or triage run and was "
                f"created at {created_at.isoformat()}, but the preregistration was frozen at "
                f"{frozen_at.isoformat()}. The preregistration MUST be frozen strictly before any "
                f"run that consumes the provider; a protocol written after model output exists is "
                f"fitted to that output and is not a preregistration"
            )
    return violations


def collect_violations(
    preregistration_path: str | Path = DEFAULT_PREREGISTRATION,
    freeze_path: str | Path = DEFAULT_FREEZE,
    registry_path: str | Path = DEFAULT_REGISTRY,
) -> list[str]:
    """Return every preregistration violation; an empty list means the artifact is valid."""

    try:
        prereg = _load_json(preregistration_path)
    except (OSError, json.JSONDecodeError) as exc:
        return [f"cannot read preregistration {preregistration_path}: {exc}"]
    if not isinstance(prereg, Mapping):
        return [f"preregistration {preregistration_path} must be a JSON object"]

    violations: list[str] = []

    status = prereg.get("status")
    if status != REQUIRED_STATUS:
        violations.append(
            f"status must be {REQUIRED_STATUS!r}, observed {status!r}; a preregistration that is "
            f"not frozen pre-data cannot fix the protocol"
        )

    primary = prereg.get("primary_metric")
    if not isinstance(primary, list) or len(primary) != 1:
        observed = len(primary) if isinstance(primary, list) else type(primary).__name__
        violations.append(
            f"primary_metric must be a list with exactly one metric, observed {observed}; more "
            f"than one primary metric leaves the deciding result open to post-hoc selection"
        )
    elif not isinstance(primary[0], Mapping) or not str(primary[0].get("name", "")).strip():
        violations.append("primary_metric[0] must be an object with a non-empty 'name'")

    refutation = prereg.get("refutation_condition")
    if not isinstance(refutation, str) or not refutation.strip():
        violations.append(
            "refutation_condition must be a non-empty string; without it the experiment cannot "
            "lose"
        )

    secondary = prereg.get("secondary_metrics")
    if not isinstance(secondary, list):
        violations.append("secondary_metrics must be a list")
    else:
        for index, metric in enumerate(secondary):
            if not isinstance(metric, Mapping) or metric.get("exploratory") is not True:
                name = metric.get("name") if isinstance(metric, Mapping) else metric
                violations.append(
                    f"secondary_metrics[{index}] ({name!r}) must be marked exploratory: true; a "
                    f"secondary metric must never be presentable as the primary result"
                )

    frozen_at = parse_timestamp(prereg.get("frozen_at"))
    if frozen_at is None:
        violations.append(
            "frozen_at must be an ISO 8601 timestamp with an explicit UTC offset, e.g. "
            "2026-10-09T00:00:00Z"
        )

    attestation = prereg.get("pre_data_attestation")
    freeze: Mapping[str, Any] = {}
    try:
        loaded = _load_json(freeze_path)
        freeze = loaded if isinstance(loaded, Mapping) else {}
    except (OSError, json.JSONDecodeError) as exc:
        violations.append(f"cannot read freeze {freeze_path}: {exc}")

    if not isinstance(attestation, Mapping):
        violations.append("pre_data_attestation must be an object describing the observed state")
    elif freeze:
        freeze_status = str(freeze.get("status", ""))
        attested_status = str(attestation.get("provider_freeze_status", ""))
        if attested_status != freeze_status:
            violations.append(
                f"pre_data_attestation.provider_freeze_status {attested_status!r} disagrees with "
                f"the freeze file {freeze_path} status {freeze_status!r}"
            )
        freeze_spend = _freeze_spend(freeze)
        attested_spend = str(attestation.get("measured_spend", "")).strip()
        expected_spend = "" if freeze_spend is _MISSING else str(freeze_spend).strip()
        if attested_spend != expected_spend:
            violations.append(
                f"pre_data_attestation.measured_spend {attested_spend!r} disagrees with the freeze "
                f"file {freeze_path} measured_spend {expected_spend!r}"
            )

    violations.extend(_ordering_violations(frozen_at, registry_path))
    return violations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("preregistration", nargs="?", default=DEFAULT_PREREGISTRATION)
    parser.add_argument("--freeze", default=DEFAULT_FREEZE)
    parser.add_argument("--registry", default=DEFAULT_REGISTRY)
    args = parser.parse_args(argv)

    violations = collect_violations(args.preregistration, args.freeze, args.registry)
    if violations:
        for violation in violations:
            print(f"VIOLATION: {violation}", file=sys.stderr)
        print(
            json.dumps(
                {"preregistration": args.preregistration, "violations": violations}, indent=2
            ),
            file=sys.stderr,
        )
        return 1

    prereg = _load_json(args.preregistration)
    metric = prereg["primary_metric"][0]["name"]
    print(
        json.dumps(
            {
                "preregistration": args.preregistration,
                "status": prereg["status"],
                "primary_metric": metric,
                "frozen_at": prereg["frozen_at"],
                "violations": [],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
