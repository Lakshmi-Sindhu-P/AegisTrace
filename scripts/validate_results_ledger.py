"""Validate the consolidated results ledger against the experiment registry.

The ledger is only trustworthy if its citations are real. This validator enforces
three kinds of rule:

* vocabulary -- ``claim_type`` and ``status`` must come from the project taxonomy;
* structure  -- unique ``claim_id``, non-empty ``scope_limit``, evidence where the
  status demands it;
* provenance -- every ``experiment_id`` must exist in the registry, every
  ``artifact_ref`` of a claim that cites experiments must be a registered artifact
  of one of those experiments, and (with ``--require-artifacts``) must exist on
  disk with a matching canonical digest;
* evidence    -- with ``--require-artifacts``, evidence strings in the machine
  checkable ``path = value`` form are enforced against the cited artifacts: a
  value mismatch, an unresolvable path, or an ambiguous list selector is a
  violation. Prose evidence stays allowed and unenforced. ``build_summary`` also
  reports how much of the ledger was actually audited (``evidence_strings_total``,
  ``evidence_strings_enforced``, ``assertions_checked``) so a clean run cannot be
  read as "all evidence verified".

Run ``python scripts/validate_results_ledger.py docs/results_ledger.json
--require-artifacts`` for the full check.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from aegistrace.verification.evidence_assertions import parse_assertions, validate_evidence

CLAIM_TYPES = frozenset(
    {
        "OBSERVED_FACT",
        "DETERMINISTIC_DERIVATION",
        "REFERENCE_BACKED_FACT",
        "MODEL_INFERENCE",
        "AI_INTERPRETATION",
        "UNKNOWN_INSUFFICIENT_EVIDENCE",
    }
)
STATUSES = frozenset({"SUPPORTED", "REFUTED", "NOT_CLAIMABLE", "UNKNOWN"})

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LEDGER = "docs/results_ledger.json"
DEFAULT_REGISTRY = "docs/experiment_registry.json"


def canonical_digest(path: Path) -> str:
    """Return the registry's digest: sha256 of the artifact's raw file bytes."""

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _registry_index(registry: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    index: dict[str, list[dict[str, Any]]] = {}
    for run in registry.get("runs", []):
        index[str(run.get("experiment_id", ""))] = list(run.get("artifact_refs", []))
    return index


def validate_data(
    ledger: dict[str, Any],
    registry: dict[str, Any],
    *,
    base_dir: Path,
    require_artifacts: bool = False,
) -> list[str]:
    """Return every violation found in ``ledger``; an empty list means valid."""

    violations: list[str] = []
    index = _registry_index(registry)
    claims = ledger.get("claims", [])
    artifact_cache: dict[str, Any] = {}

    def load_document(ref: str) -> Any | None:
        """Load a referenced artifact's JSON once, keeping a per-run cache."""
        if ref in artifact_cache:
            return artifact_cache[ref]
        try:
            document = _load(base_dir / ref)
        except (OSError, json.JSONDecodeError):
            document = None
        artifact_cache[ref] = document
        return document

    # Deliberate non-empty floor (issue #16): a ledger with zero claims satisfies every
    # per-claim rule vacuously, so an empty ledger must be reported as a violation
    # rather than a clean pass.
    if not claims:
        violations.append("ledger is empty: expected at least one claim")

    seen_ids: set[str] = set()
    for position, claim in enumerate(claims):
        raw_id = claim.get("claim_id")
        claim_id = raw_id if isinstance(raw_id, str) and raw_id else f"<claims[{position}]>"
        claim_type = str(claim.get("claim_type", "")).upper()
        status = str(claim.get("status", "")).upper()

        if claim_type not in CLAIM_TYPES:
            violations.append(f"{claim_id}: unknown claim_type {claim.get('claim_type')!r}")
        if status not in STATUSES:
            violations.append(f"{claim_id}: unknown status {claim.get('status')!r}")
        if raw_id in seen_ids:
            violations.append(f"{claim_id}: duplicate claim_id")
        elif isinstance(raw_id, str):
            seen_ids.add(raw_id)

        scope_limit = claim.get("scope_limit")
        if not isinstance(scope_limit, str) or not scope_limit.strip():
            violations.append(f"{claim_id}: missing or empty scope_limit")

        evidence = claim.get("evidence")
        evidence_empty = not isinstance(evidence, list) or not evidence
        if status == "SUPPORTED" and evidence_empty:
            violations.append(f"{claim_id}: SUPPORTED claim has empty evidence")
        if status in {"REFUTED", "NOT_CLAIMABLE"} and evidence_empty:
            violations.append(f"{claim_id}: {status} claim has empty evidence")

        experiment_ids = claim.get("experiment_ids") or []
        allowed_paths: set[str] = set()
        known_experiments = True
        for experiment_id in experiment_ids:
            if experiment_id not in index:
                violations.append(
                    f"{claim_id}: experiment_id {experiment_id!r} is not in the registry"
                )
                known_experiments = False
                continue
            allowed_paths.update(str(ref.get("path")) for ref in index[experiment_id])

        artifact_refs = claim.get("artifact_refs") or []

        # An artifact-backed claim must name the registered experiment that produced the
        # artifact. Without this, an empty experiment_ids silently skips the membership
        # check below and the claim looks verified while nothing was actually checked.
        if artifact_refs and not experiment_ids:
            violations.append(
                f"{claim_id}: cites {len(artifact_refs)} artifact(s) but names no experiment_id, "
                "so nothing ties those artifacts to a registered run"
            )

        for artifact_ref in artifact_refs:
            ref = str(artifact_ref)
            if experiment_ids and known_experiments and ref not in allowed_paths:
                violations.append(
                    f"{claim_id}: artifact_ref {ref!r} is not registered to any referenced "
                    "experiment"
                )
            if require_artifacts:
                target = base_dir / ref
                if not target.is_file():
                    violations.append(f"{claim_id}: artifact {ref!r} does not exist on disk")
                    continue
                digest = next(
                    (
                        str(item.get("digest"))
                        for run in registry.get("runs", [])
                        for item in run.get("artifact_refs", [])
                        if str(item.get("path")) == ref and item.get("digest")
                    ),
                    None,
                )
                if digest is not None and canonical_digest(target) != digest:
                    violations.append(
                        f"{claim_id}: artifact {ref!r} digest does not match registry"
                    )

        if require_artifacts:
            documents = [
                document
                for ref in artifact_refs
                if (document := load_document(str(ref))) is not None
            ]
            evidence_violations, _, _ = validate_evidence(claim.get("evidence") or [], documents)
            violations.extend(evidence_violations)

    return violations


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _evidence_coverage(ledger: dict[str, Any]) -> dict[str, int]:
    """Count how much of the ledger's evidence is machine-checkable and audited.

    Machine-checkable strings are those in the enforced ``path = value`` form; each yields one or
    more assertions. Prose evidence is counted in the total but not in enforced/checked, so a clean
    summary always shows the gap between what the ledger says and what was actually audited.
    """
    total = enforced = assertions = 0
    for claim in ledger.get("claims", []):
        for entry in claim.get("evidence") or []:
            if not isinstance(entry, str):
                continue
            total += 1
            parsed = parse_assertions(entry)
            if parsed is not None:
                enforced += 1
                assertions += len(parsed)
    return {
        "evidence_strings_total": total,
        "evidence_strings_enforced": enforced,
        "assertions_checked": assertions,
    }


def build_summary(ledger_path: str, ledger: dict[str, Any]) -> dict[str, Any]:
    """Summarize claim counts by status and by type, plus evidence coverage."""

    by_status: dict[str, int] = {}
    by_type: dict[str, int] = {}
    claims = ledger.get("claims", [])
    for claim in claims:
        status = str(claim.get("status", ""))
        claim_type = str(claim.get("claim_type", ""))
        by_status[status] = by_status.get(status, 0) + 1
        by_type[claim_type] = by_type.get(claim_type, 0) + 1
    summary = {
        "ledger": ledger_path,
        "claim_count": len(claims),
        "by_status": by_status,
        "by_type": by_type,
    }
    summary.update(_evidence_coverage(ledger))
    return summary


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point: validate the ledger and report a machine-readable summary."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "ledger", nargs="?", default=DEFAULT_LEDGER, help="path to results_ledger.json"
    )
    parser.add_argument(
        "--registry", default=DEFAULT_REGISTRY, help="path to experiment_registry.json"
    )
    parser.add_argument(
        "--require-artifacts",
        action="store_true",
        help="also require each artifact_ref to exist on disk with a matching digest",
    )
    args = parser.parse_args(argv)

    ledger_path = Path(args.ledger)
    registry_path = Path(args.registry)
    try:
        ledger = _load(ledger_path)
    except (OSError, json.JSONDecodeError, ValidationError, TypeError) as error:
        print(f"cannot load ledger {ledger_path}: {error}", file=sys.stderr)
        return 1

    try:
        registry = _load(registry_path)
    except (OSError, json.JSONDecodeError, ValidationError, TypeError) as error:
        print(f"cannot load registry {registry_path}: {error}", file=sys.stderr)
        return 1

    violations = validate_data(
        ledger,
        registry,
        base_dir=Path.cwd(),
        require_artifacts=args.require_artifacts,
    )
    if violations:
        for violation in violations:
            print(f"VIOLATION: {violation}", file=sys.stderr)
        return 1

    print(json.dumps(build_summary(args.ledger, ledger), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
