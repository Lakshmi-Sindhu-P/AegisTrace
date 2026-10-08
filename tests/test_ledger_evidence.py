"""Tests for machine-checkable evidence assertions in the results ledger.

Issue #29: the ledger validator verified an artifact's existence and digest but never compared a
claim's stated value to the artifact's contents, so a claim could drift from its artifact while
validation stayed green. These tests pin the new enforcement: `path = value` evidence is audited
against the cited artifact, prose evidence stays allowed and unenforced, and the summary reports
how much of the ledger was actually checked.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.validate_results_ledger import build_summary, validate_data

ARTIFACT_REL = "data/eval/x.json"
EXPERIMENT_ID = "exp"


def _registry(digest: str) -> dict[str, object]:
    return {
        "schema_version": "1.0.0",
        "runs": [
            {
                "experiment_id": EXPERIMENT_ID,
                "artifact_refs": [
                    {
                        "path": ARTIFACT_REL,
                        "digest": digest,
                        "kind": "artifact",
                        "tracked": False,
                    }
                ],
            }
        ],
    }


def _write_artifact(tmp_path: Path, document: dict[str, object]) -> str:
    target = tmp_path / ARTIFACT_REL
    target.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(document).encode("utf-8")
    target.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def _claim(evidence: list[str]) -> dict[str, object]:
    return {
        "claim_id": "claim:fixture",
        "statement": "A fixture claim.",
        "claim_type": "DETERMINISTIC_DERIVATION",
        "status": "SUPPORTED",
        "experiment_ids": [EXPERIMENT_ID],
        "artifact_refs": [ARTIFACT_REL],
        "evidence": evidence,
        "scope_limit": "Fixture only.",
    }


def _validate(
    tmp_path: Path, document: dict[str, object], evidence: list[str]
) -> list[str]:
    digest = _write_artifact(tmp_path, document)
    ledger = {"schema_version": "1.0.0", "claims": [_claim(evidence)]}
    return validate_data(
        ledger, _registry(digest), base_dir=tmp_path, require_artifacts=True
    )


def test_correct_assertion_passes(tmp_path: Path) -> None:
    document = {"headline": {"best": True, "fallback": False}}
    violations = _validate(
        tmp_path, document, ["headline.best = true and headline.fallback = false"]
    )
    assert violations == []


def test_correct_float_with_sentence_period_passes(tmp_path: Path) -> None:
    """A float literal with a trailing sentence-period still parses and matches."""
    violations = _validate(tmp_path, {"ops": {"cap": 200.0}}, ["ops.cap = 200.0."])
    assert violations == []


def test_value_mismatch_is_a_violation(tmp_path: Path) -> None:
    violations = _validate(tmp_path, {"headline": {"n": 100}}, ["headline.n = 99"])
    assert any("mismatch" in violation for violation in violations)


def test_unresolvable_path_is_a_distinct_violation(tmp_path: Path) -> None:
    violations = _validate(
        tmp_path, {"headline": {"n": 100}}, ["headline.missing = 5"]
    )
    assert any("does not resolve" in violation for violation in violations)
    assert not any("mismatch" in violation for violation in violations)


def test_ambiguous_selector_is_a_violation(tmp_path: Path) -> None:
    document = {"items": [{"k": "a", "v": 1}, {"k": "a", "v": 2}]}
    violations = _validate(tmp_path, document, ["items[k=a].v = 1"])
    assert any("ambiguous" in violation for violation in violations)


def test_multi_assertion_mismatch_in_second_is_caught(tmp_path: Path) -> None:
    """Regression: `A = true and B = false` must parse as TWO assertions so a
    mismatch in the second is reported without fabricating one on the first."""
    document = {"headline": {"x": True, "y": True}}
    violations = _validate(
        tmp_path, document, ["headline.x = true and headline.y = false"]
    )
    mismatches = [v for v in violations if "mismatch" in v]
    assert len(mismatches) == 1
    assert "y" in mismatches[0]


def test_prose_evidence_is_allowed_and_unenforced(tmp_path: Path) -> None:
    digest = _write_artifact(tmp_path, {"headline": {"a": 1}})
    ledger = {
        "schema_version": "1.0.0",
        "claims": [
            _claim(["The model was evaluated on six captures."]),
        ],
    }
    violations = validate_data(
        ledger, _registry(digest), base_dir=tmp_path, require_artifacts=True
    )
    assert violations == []
    summary = build_summary("ledger.json", ledger)
    assert summary["evidence_strings_total"] == 1
    assert summary["evidence_strings_enforced"] == 0
    assert summary["assertions_checked"] == 0


def test_coverage_counts_in_summary_are_correct(tmp_path: Path) -> None:
    ledger = {
        "schema_version": "1.0.0",
        "claims": [
            _claim(["A prose-only statement."]),
            _claim(["headline.a = true and headline.b = false"]),
            _claim(["headline.c = 5"]),
        ],
    }
    summary = build_summary("ledger.json", ledger)
    assert summary["evidence_strings_total"] == 3
    assert summary["evidence_strings_enforced"] == 2
    assert summary["assertions_checked"] == 3