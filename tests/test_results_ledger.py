"""Tests for the consolidated results ledger, its validator, and its renderer."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from scripts.render_results_ledger import main, render
from scripts.validate_results_ledger import (
    REPO_ROOT,
    build_summary,
    validate_data,
)

REGISTRY = {
    "schema_version": "1.0.0",
    "runs": [
        {
            "experiment_id": "exp-a",
            "artifact_refs": [
                {
                    "path": "data/evaluation/a.json",
                    "digest": "0" * 64,
                    "kind": "artifact",
                    "tracked": False,
                }
            ],
        }
    ],
}


def make_claim(**overrides: object) -> dict[str, object]:
    claim: dict[str, object] = {
        "claim_id": "claim:example",
        "statement": "An example claim.",
        "claim_type": "DETERMINISTIC_DERIVATION",
        "status": "SUPPORTED",
        "experiment_ids": ["exp-a"],
        "artifact_refs": ["data/evaluation/a.json"],
        "evidence": ["a literal number 1"],
        "scope_limit": "Only for the example fixture.",
    }
    claim.update(overrides)
    return claim


def make_ledger(claims: list[dict[str, object]]) -> dict[str, object]:
    return {"schema_version": "1.0.0", "claims": claims}


def check(claims: list[dict[str, object]], *, require_artifacts: bool = False) -> list[str]:
    return validate_data(
        make_ledger(claims), REGISTRY, base_dir=REPO_ROOT, require_artifacts=require_artifacts
    )


def test_real_ledger_validates_cleanly() -> None:
    ledger = json.loads((REPO_ROOT / "docs/results_ledger.json").read_text(encoding="utf-8"))
    registry = json.loads((REPO_ROOT / "docs/experiment_registry.json").read_text(encoding="utf-8"))
    violations = validate_data(ledger, registry, base_dir=REPO_ROOT, require_artifacts=True)
    assert violations == []


def test_empty_ledger_fails() -> None:
    """Issue #16: an empty ledger must not pass vacuously."""

    violations = check([])
    assert any("empty" in violation for violation in violations)


def test_real_ledger_passes_the_empty_floor() -> None:
    """The non-empty floor must not reject the real, populated ledger."""

    ledger = json.loads((REPO_ROOT / "docs/results_ledger.json").read_text(encoding="utf-8"))
    registry = json.loads((REPO_ROOT / "docs/experiment_registry.json").read_text(encoding="utf-8"))
    assert ledger["claims"]
    assert validate_data(ledger, registry, base_dir=REPO_ROOT, require_artifacts=True) == []


def test_bad_claim_type_fails() -> None:
    violations = check([make_claim(claim_type="MADE_UP_TYPE")])
    assert any("unknown claim_type" in v for v in violations)


def test_unknown_status_fails() -> None:
    violations = check([make_claim(status="PROBABLY_TRUE")])
    assert any("unknown status" in v for v in violations)


def test_unknown_experiment_id_fails() -> None:
    violations = check([make_claim(experiment_ids=["no-such-experiment"])])
    assert any("not in the registry" in v for v in violations)


def test_artifact_ref_not_in_registry_fails() -> None:
    violations = check([make_claim(artifact_refs=["data/evaluation/not-registered.json"])])
    assert any("not registered to any referenced experiment" in v for v in violations)


def test_artifacts_without_experiment_ids_fail() -> None:
    """An artifact-backed claim must name its registered run.

    Without this rule an empty experiment_ids skips the membership check entirely, so a
    claim citing a real-looking artifact validates cleanly while nothing was checked.
    """

    violations = check([make_claim(experiment_ids=[], artifact_refs=["data/evaluation/a.json"])])
    assert any("names no experiment_id" in v for v in violations)


def test_reference_only_claim_may_omit_experiment_ids() -> None:
    """A literature claim has no artifact and therefore no experiment, which is legitimate."""

    violations = check(
        [
            make_claim(
                claim_type="REFERENCE_BACKED_FACT",
                experiment_ids=[],
                artifact_refs=[],
                evidence=["Smith 2024, Table 2, median 13.44 s versus 18.76 s"],
            )
        ]
    )
    assert violations == []


def test_supported_without_evidence_fails() -> None:
    violations = check([make_claim(status="SUPPORTED", evidence=[])])
    assert any("SUPPORTED claim has empty evidence" in v for v in violations)


def test_refuted_without_evidence_fails() -> None:
    violations = check([make_claim(status="REFUTED", evidence=[])])
    assert any("REFUTED claim has empty evidence" in v for v in violations)


def test_not_claimable_without_evidence_fails() -> None:
    violations = check([make_claim(status="NOT_CLAIMABLE", evidence=[])])
    assert any("NOT_CLAIMABLE claim has empty evidence" in v for v in violations)


def test_missing_scope_limit_fails() -> None:
    claim = make_claim()
    del claim["scope_limit"]
    violations = check([claim])
    assert any("scope_limit" in v for v in violations)


def test_duplicate_claim_id_fails() -> None:
    violations = check([make_claim(), make_claim()])
    assert any("duplicate claim_id" in v for v in violations)


def test_missing_artifact_on_disk_fails(tmp_path: Path) -> None:
    violations = validate_data(
        make_ledger([make_claim()]), REGISTRY, base_dir=tmp_path, require_artifacts=True
    )
    assert any("does not exist on disk" in v for v in violations)


def test_digest_mismatch_fails(tmp_path: Path) -> None:
    (tmp_path / "data/evaluation").mkdir(parents=True)
    (tmp_path / "data/evaluation/a.json").write_text('{"x": 1}', encoding="utf-8")
    violations = validate_data(
        make_ledger([make_claim()]), REGISTRY, base_dir=tmp_path, require_artifacts=True
    )
    assert any("digest does not match" in v for v in violations)


def test_clean_fixture_has_no_violations(tmp_path: Path) -> None:
    (tmp_path / "data/evaluation").mkdir(parents=True)
    (tmp_path / "data/evaluation/a.json").write_text("{}", encoding="utf-8")
    violations = validate_data(
        make_ledger([make_claim()]), REGISTRY, base_dir=tmp_path, require_artifacts=False
    )
    assert violations == []


def test_render_is_idempotent() -> None:
    ledger = json.loads((REPO_ROOT / "docs/results_ledger.json").read_text(encoding="utf-8"))
    assert render(ledger) == render(ledger)


def test_committed_results_md_is_in_sync_with_the_ledger() -> None:
    """The rendered doc must not drift from the ledger it is generated from.

    Idempotence only proves the renderer is stable; it does not prove the committed file
    is current. Without this, editing the ledger and forgetting to re-render would leave
    the human-readable results quietly disagreeing with the machine-checked ones.
    """

    ledger = json.loads((REPO_ROOT / "docs/results_ledger.json").read_text(encoding="utf-8"))
    on_disk = (REPO_ROOT / "docs/results.md").read_text(encoding="utf-8")
    assert on_disk == render(ledger), "run scripts/render_results_ledger.py to regenerate"


def test_check_mode_passes_when_in_sync(tmp_path: Path) -> None:
    ledger_path = tmp_path / "ledger.json"
    out = tmp_path / "out.md"
    ledger_path.write_text(
        json.dumps(make_ledger([make_claim()])), encoding="utf-8"
    )
    assert main([str(ledger_path), "--output", str(out)]) == 0
    assert main([str(ledger_path), "--output", str(out), "--check"]) == 0


def test_check_mode_fails_when_out_of_date(tmp_path: Path) -> None:
    ledger_path = tmp_path / "ledger.json"
    out = tmp_path / "out.md"
    ledger_path.write_text(json.dumps(make_ledger([make_claim()])), encoding="utf-8")
    out.write_text("stale content that no longer matches the ledger", encoding="utf-8")
    assert main([str(ledger_path), "--output", str(out), "--check"]) == 1
    # --check must never rewrite the file it is judging.
    assert out.read_text(encoding="utf-8") == "stale content that no longer matches the ledger"


def test_check_mode_fails_when_output_is_missing(tmp_path: Path) -> None:
    ledger_path = tmp_path / "ledger.json"
    ledger_path.write_text(json.dumps(make_ledger([make_claim()])), encoding="utf-8")
    assert main([str(ledger_path), "--output", str(tmp_path / "absent.md"), "--check"]) == 1


def test_render_writes_byte_identical_output_twice(tmp_path: Path) -> None:
    ledger = json.loads((REPO_ROOT / "docs/results_ledger.json").read_text(encoding="utf-8"))
    first = tmp_path / "first.md"
    second = tmp_path / "second.md"
    first.write_text(render(ledger), encoding="utf-8")
    second.write_text(render(ledger), encoding="utf-8")
    assert first.read_bytes() == second.read_bytes()


def test_summary_counts_by_status_and_type() -> None:
    ledger = make_ledger(
        [
            make_claim(claim_id="claim:a", status="SUPPORTED"),
            make_claim(claim_id="claim:b", status="REFUTED"),
        ]
    )
    summary = build_summary("ledger.json", ledger)
    assert summary["claim_count"] == 2
    assert summary["by_status"] == {"SUPPORTED": 1, "REFUTED": 1}


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__]))
