"""Tests for the committed artifact reproducibility manifest and its verifier.

The manifest records, for every artifact the experiment registry references, the size,
top-level keys, capture count and raw-bytes SHA-256 digest of the generated file.  Because
those artifacts are deliberately untracked, most byte-level assertions skip when a file is
absent; the checks that need no artifact bytes (manifest-to-registry digest agreement and
two-way path coverage) always run.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
from scripts.verify_artifact_manifest import main, verify_manifest

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "docs/artifact_manifest.json"
REGISTRY_PATH = REPO_ROOT / "docs/experiment_registry.json"
REL_PATH = "data/evaluation/phase3_synthetic/summary.json"


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _case(
    tmp_path: Path,
    artifact: dict[str, Any] | None,
    *,
    manifest_entry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a self-contained manifest/registry/artifact triple under ``tmp_path``."""

    if artifact is None:
        raw = b""
        digest = "0" * 64
    else:
        raw = (json.dumps(artifact, indent=2) + "\n").encode("utf-8")
        digest = hashlib.sha256(raw).hexdigest()
        target = tmp_path / REL_PATH
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)

    registry = {
        "schema_version": "1.0.0",
        "runs": [
            {
                "artifact_refs": [
                    {"path": REL_PATH, "digest": digest, "kind": "artifact", "tracked": False}
                ]
            }
        ],
    }
    entry: dict[str, Any] = {
        "path": REL_PATH,
        "digest": digest,
        "size_bytes": len(raw),
        "top_level_keys": sorted(artifact) if artifact is not None else ["captures"],
        "capture_count": None,
        "shape_note": "synthetic fixture",
        "reproducible": True,
        "reproducibility_note": "synthetic fixture digest is reproducible",
    }
    if artifact is not None and isinstance(artifact.get("captures"), list):
        entry["capture_count"] = len(artifact["captures"])
    if manifest_entry is not None:
        entry.update(manifest_entry)

    manifest = {"schema_version": "1.0", "generated_by": "test", "artifacts": [entry]}
    manifest_file = tmp_path / "manifest.json"
    registry_file = tmp_path / "registry.json"
    _write_json(manifest_file, manifest)
    _write_json(registry_file, registry)
    return {
        "manifest": manifest_file,
        "registry": registry_file,
        "base_dir": tmp_path,
        "entry": entry,
        "digest": digest,
    }


def test_committed_manifest_validates_against_registry() -> None:
    report, violations = verify_manifest(MANIFEST_PATH, REGISTRY_PATH, REPO_ROOT)

    assert violations == []
    assert report["entries"] == 9
    assert report["violations"] == []


def test_committed_manifest_matches_regeneration_fields() -> None:
    """Re-derive every registry-derived field the way regeneration would produce it."""

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    expected: dict[str, str] = {}
    for run in registry["runs"]:
        for reference in run["artifact_refs"]:
            expected[reference["path"]] = reference["digest"]

    entries = {entry["path"]: entry for entry in manifest["artifacts"]}
    assert set(entries) == set(expected)
    assert manifest["total_size_bytes"] == sum(
        entry["size_bytes"] for entry in manifest["artifacts"]
    )
    for path, digest in expected.items():
        assert entries[path]["digest"] == digest
        artifact = REPO_ROOT / path
        if not artifact.exists():
            continue
        assert entries[path]["size_bytes"] == artifact.stat().st_size
        payload = json.loads(artifact.read_text(encoding="utf-8"))
        assert entries[path]["top_level_keys"] == sorted(payload)
        captures = payload.get("captures")
        assert entries[path]["capture_count"] == (
            len(captures) if isinstance(captures, list) else None
        )
        raw_digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
        assert raw_digest == digest


def test_absent_artifacts_do_not_fail(tmp_path: Path) -> None:
    report, violations = verify_manifest(MANIFEST_PATH, REGISTRY_PATH, tmp_path)

    assert violations == []
    assert report["verified_on_disk"] == 0
    assert report["absent"] == report["entries"] == 9


def test_zero_entry_manifest_fails(tmp_path: Path) -> None:
    """Issue #19: an empty manifest plus an empty registry made both loops vacuous."""

    manifest_file = tmp_path / "manifest.json"
    registry_file = tmp_path / "registry.json"
    _write_json(manifest_file, {"schema_version": "1.0", "generated_by": "test", "artifacts": []})
    _write_json(registry_file, {"schema_version": "1.0.0", "runs": []})

    report, violations = verify_manifest(manifest_file, registry_file, tmp_path)

    assert any("manifest is empty" in violation for violation in violations)
    assert report["entries"] == 0
    assert report["verified_on_disk"] == 0


def test_altered_digest_fails(tmp_path: Path) -> None:
    case = _case(tmp_path, {"schema_version": "1.0", "captures": []})
    manifest = json.loads(case["manifest"].read_text(encoding="utf-8"))
    manifest["artifacts"][0]["digest"] = "f" * 64
    _write_json(case["manifest"], manifest)

    _, violations = verify_manifest(case["manifest"], case["registry"], case["base_dir"])

    assert any("digest mismatch vs registry" in violation for violation in violations)


def test_manifest_entry_absent_from_registry_fails(tmp_path: Path) -> None:
    case = _case(tmp_path, {"schema_version": "1.0", "captures": []})
    manifest = json.loads(case["manifest"].read_text(encoding="utf-8"))
    extra = dict(manifest["artifacts"][0])
    extra["path"] = "data/evaluation/phase3_synthetic/other.json"
    manifest["artifacts"].append(extra)
    _write_json(case["manifest"], manifest)

    _, violations = verify_manifest(case["manifest"], case["registry"], case["base_dir"])

    assert any("unregistered artifact" in violation for violation in violations)


def test_registry_artifact_missing_from_manifest_fails(tmp_path: Path) -> None:
    case = _case(tmp_path, {"schema_version": "1.0", "captures": []})
    manifest = json.loads(case["manifest"].read_text(encoding="utf-8"))
    manifest["artifacts"] = []
    _write_json(case["manifest"], manifest)

    _, violations = verify_manifest(case["manifest"], case["registry"], case["base_dir"])

    assert any("missing from manifest" in violation for violation in violations)


def test_wrong_size_bytes_for_present_artifact_fails(tmp_path: Path) -> None:
    case = _case(tmp_path, {"schema_version": "1.0", "captures": []})
    manifest = json.loads(case["manifest"].read_text(encoding="utf-8"))
    manifest["artifacts"][0]["size_bytes"] += 1
    _write_json(case["manifest"], manifest)

    report, violations = verify_manifest(case["manifest"], case["registry"], case["base_dir"])

    assert report["verified_on_disk"] == 1
    assert any("size mismatch" in violation for violation in violations)


def test_absent_artifact_skips_byte_checks(tmp_path: Path) -> None:
    case = _case(tmp_path, None, manifest_entry={"size_bytes": 4242})
    assert not (case["base_dir"] / REL_PATH).exists()

    report, violations = verify_manifest(case["manifest"], case["registry"], case["base_dir"])

    assert violations == []
    assert report["absent"] == 1
    assert report["verified_on_disk"] == 0


def test_wrong_top_level_keys_fails(tmp_path: Path) -> None:
    case = _case(tmp_path, {"schema_version": "1.0", "captures": []})
    manifest = json.loads(case["manifest"].read_text(encoding="utf-8"))
    manifest["artifacts"][0]["top_level_keys"] = ["not_a_real_key"]
    _write_json(case["manifest"], manifest)

    _, violations = verify_manifest(case["manifest"], case["registry"], case["base_dir"])

    assert any("top_level_keys mismatch" in violation for violation in violations)


def test_wrong_capture_count_fails(tmp_path: Path) -> None:
    case = _case(tmp_path, {"schema_version": "1.0", "captures": [{"capture": 1}]})
    manifest = json.loads(case["manifest"].read_text(encoding="utf-8"))
    manifest["artifacts"][0]["capture_count"] = 99
    _write_json(case["manifest"], manifest)

    _, violations = verify_manifest(case["manifest"], case["registry"], case["base_dir"])

    assert any("capture_count mismatch" in violation for violation in violations)


def test_raw_bytes_hashing_rejects_canonical_json_digest(tmp_path: Path) -> None:
    artifact = {"schema_version": "1.0", "captures": []}
    case = _case(tmp_path, artifact)
    canonical = json.dumps(artifact, sort_keys=True, separators=(",", ":"))
    canonical_digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    assert canonical_digest != case["digest"]

    _, violations = verify_manifest(case["manifest"], case["registry"], case["base_dir"])

    assert violations == []


def test_cli_success_and_violation_exit_codes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    case = _case(tmp_path, {"schema_version": "1.0", "captures": []})
    assert (
        main(
            [
                str(case["manifest"]),
                "--registry",
                str(case["registry"]),
                "--base-dir",
                str(case["base_dir"]),
            ]
        )
        == 0
    )
    report = json.loads(capsys.readouterr().out)
    assert report["violations"] == []
    assert report["verified_on_disk"] == 1

    manifest = json.loads(case["manifest"].read_text(encoding="utf-8"))
    manifest["artifacts"][0]["digest"] = "0" * 64
    _write_json(case["manifest"], manifest)
    assert (
        main(
            [
                str(case["manifest"]),
                "--registry",
                str(case["registry"]),
                "--base-dir",
                str(case["base_dir"]),
            ]
        )
        == 1
    )
    captured = capsys.readouterr()
    assert "VIOLATION" in captured.err
    assert captured.out == ""


def test_default_manifest_path_matches_registry() -> None:
    """The CLI defaults resolve to the committed files and pass on this checkout."""

    assert main([]) == 0


def test_manifest_entry_requires_reproducible_field(tmp_path: Path) -> None:
    """Issue #21: an entry may not silently omit its reproducibility contract."""

    case = _case(tmp_path, {"schema_version": "1.0", "captures": []})
    manifest = json.loads(case["manifest"].read_text(encoding="utf-8"))
    del manifest["artifacts"][0]["reproducible"]
    _write_json(case["manifest"], manifest)

    _, violations = verify_manifest(case["manifest"], case["registry"], case["base_dir"])

    assert any("missing required boolean field 'reproducible'" in v for v in violations)


def test_manifest_entry_requires_reproducibility_note(tmp_path: Path) -> None:
    case = _case(tmp_path, {"schema_version": "1.0", "captures": []})
    manifest = json.loads(case["manifest"].read_text(encoding="utf-8"))
    manifest["artifacts"][0]["reproducibility_note"] = "   "
    _write_json(case["manifest"], manifest)

    _, violations = verify_manifest(case["manifest"], case["registry"], case["base_dir"])

    assert any("'reproducibility_note' field" in v for v in violations)


def test_committed_manifest_marks_pre_fix_timing_entries_unreproducible() -> None:
    """The three artifacts whose bytes embedded a wall-clock fit time are flagged."""

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    entries = {entry["path"]: entry for entry in manifest["artifacts"]}
    timing_affected = {
        "data/evaluation/phase3_model_family/benchmark_summary.json",
        "data/evaluation/phase3_causal_representation/causal_summary.json",
        "data/evaluation/phase3_model_stability/stability_summary.json",
    }

    assert all(isinstance(entry["reproducible"], bool) for entry in entries.values())
    assert all(entry["reproducibility_note"].strip() for entry in entries.values())
    # Issue #23 adds a fourth, non-timing entry flagged because its inputs cannot recur.
    assert {path for path, entry in entries.items() if not entry["reproducible"]} == (
        timing_affected | {"data/evaluation/phase3_uncertainty/uncertainty_summary.json"}
    )
    for path in timing_affected:
        assert "time.perf_counter" in entries[path]["reproducibility_note"]


UNCERTAINTY_PATH = "data/evaluation/phase3_uncertainty/uncertainty_summary.json"
UNCERTAINTY_ARTIFACT = REPO_ROOT / UNCERTAINTY_PATH


def _multi_case(tmp_path: Path, specs: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a multi-entry manifest/registry/artifact set under ``tmp_path``.

    Each spec is ``{"path", "artifact", "reproducible"}`` with optional ``note``,
    ``digest_override`` and ``top_level_keys``.  ``artifact`` may be a dict or a callable
    that receives the digests computed so far and returns the dict to serialize, which is
    how an entry records the digest of an input.
    """

    entries: list[dict[str, Any]] = []
    refs: list[dict[str, Any]] = []
    digests: dict[str, str] = {}
    for spec in specs:
        rel = spec["path"]
        artifact = spec["artifact"]
        if callable(artifact):
            artifact = artifact(digests)
        raw = (json.dumps(artifact, indent=2) + "\n").encode("utf-8")
        actual_digest = hashlib.sha256(raw).hexdigest()
        digests[rel] = actual_digest
        stored_digest = spec.get("digest_override", actual_digest)
        target = tmp_path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        entries.append(
            {
                "path": rel,
                "digest": stored_digest,
                "size_bytes": len(raw),
                "top_level_keys": spec.get("top_level_keys", sorted(artifact)),
                "capture_count": None,
                "shape_note": "synthetic fixture",
                "reproducible": spec["reproducible"],
                "reproducibility_note": spec.get("note", "synthetic fixture note"),
            }
        )
        refs.append({"path": rel, "digest": stored_digest, "kind": "artifact", "tracked": False})

    registry = {"schema_version": "1.0.0", "runs": [{"artifact_refs": refs}]}
    manifest = {"schema_version": "1.0", "generated_by": "test", "artifacts": entries}
    manifest_file = tmp_path / "manifest.json"
    registry_file = tmp_path / "registry.json"
    _write_json(manifest_file, manifest)
    _write_json(registry_file, registry)
    return {
        "manifest": manifest_file,
        "registry": registry_file,
        "base_dir": tmp_path,
        "digests": digests,
        "entries": {entry["path"]: entry for entry in entries},
    }


def _marked_reproducible_with_bad_input(violations: list[str]) -> list[str]:
    return [v for v in violations if "recorded inputs include unreproducible" in v]


def test_entry_with_unreproducible_input_cannot_be_marked_reproducible(tmp_path: Path) -> None:
    """Issue #23: a stored ``true`` contradicts a recorded non-reproducible input digest."""

    producer = "data/evaluation/phase3_synthetic/producer.json"
    consumer = "data/evaluation/phase3_synthetic/consumer.json"
    case = _multi_case(
        tmp_path,
        [
            {
                "path": producer,
                "artifact": {"schema_version": "1.0"},
                "reproducible": False,
                "note": "timing-affected bytes",
            },
            {
                "path": consumer,
                "artifact": lambda digests: {
                    "schema_version": "1.0",
                    "inputs": [{"path": producer, "digest": digests[producer]}],
                },
                "reproducible": True,
            },
        ],
    )

    _, violations = verify_manifest(case["manifest"], case["registry"], case["base_dir"])

    assert any(consumer in v for v in _marked_reproducible_with_bad_input(violations))


def test_reproducibility_is_transitive_across_an_input_chain(tmp_path: Path) -> None:
    """A true-flagged consumer of a true-flagged consumer is still tainted transitively."""

    root = "data/evaluation/phase3_synthetic/"
    a, b, c = root + "a.json", root + "b.json", root + "c.json"
    case = _multi_case(
        tmp_path,
        [
            {"path": a, "artifact": {"schema_version": "1.0"}, "reproducible": False},
            {
                "path": b,
                "artifact": lambda digests: {"inputs": [{"path": a, "digest": digests[a]}]},
                "reproducible": True,
            },
            {
                "path": c,
                "artifact": lambda digests: {"inputs": [{"path": b, "digest": digests[b]}]},
                "reproducible": True,
            },
        ],
    )

    _, violations = verify_manifest(case["manifest"], case["registry"], case["base_dir"])
    flagged = " ".join(_marked_reproducible_with_bad_input(violations))

    assert f"manifest entry {b}" in flagged
    assert f"manifest entry {c}" in flagged


def test_verifier_rejects_deliberately_inconsistent_committed_fixture(tmp_path: Path) -> None:
    """Flipping the committed uncertainty entry back to true must fail the input check."""

    if not UNCERTAINTY_ARTIFACT.is_file():
        pytest.skip("uncertainty artifact is not present on this checkout")

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    for entry in manifest["artifacts"]:
        if entry["path"] == UNCERTAINTY_PATH:
            entry["reproducible"] = True
    manifest_file = tmp_path / "manifest.json"
    _write_json(manifest_file, manifest)

    report, violations = verify_manifest(manifest_file, REGISTRY_PATH, REPO_ROOT)

    assert report["input_graph_checked"] == [UNCERTAINTY_PATH]
    assert any(
        UNCERTAINTY_PATH in v for v in _marked_reproducible_with_bad_input(violations)
    )


@pytest.mark.skipif(not UNCERTAINTY_ARTIFACT.is_file(), reason="artifact not regenerated here")
def test_uncertainty_summary_is_false_with_an_inputs_based_note() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    entries = {entry["path"]: entry for entry in manifest["artifacts"]}
    entry = entries[UNCERTAINTY_PATH]

    assert entry["reproducible"] is False
    note = entry["reproducibility_note"]
    assert "stability_summary.json" in note
    assert "causal_summary.json" in note
    # The note blames the recorded inputs, not the issue #21 timing wording.
    assert "time.perf_counter" not in note


@pytest.mark.skipif(not UNCERTAINTY_ARTIFACT.is_file(), reason="artifact not regenerated here")
def test_committed_input_graph_is_consistent_and_skips_large_artifacts() -> None:
    report, violations = verify_manifest(MANIFEST_PATH, REGISTRY_PATH, REPO_ROOT)

    assert violations == []
    assert report["input_graph_checked"] == [UNCERTAINTY_PATH]
    # No large artifact declares an "inputs" key, so none was loaded for this check.
    assert report["input_graph_skipped_large"] == []


def test_verifier_handles_cyclic_input_graph_without_hanging(tmp_path: Path) -> None:
    """A malformed cyclic graph must terminate; propagation still reaches the cycle."""

    left = "data/evaluation/phase3_synthetic/cycle_left.json"
    right = "data/evaluation/phase3_synthetic/cycle_right.json"
    case = _multi_case(
        tmp_path,
        [
            {
                "path": left,
                "artifact": {"inputs": [{"path": right, "digest": "b" * 64}]},
                "reproducible": False,
                "digest_override": "a" * 64,
            },
            {
                "path": right,
                "artifact": {"inputs": [{"path": left, "digest": "a" * 64}]},
                "reproducible": True,
                "digest_override": "b" * 64,
            },
        ],
    )

    report, violations = verify_manifest(case["manifest"], case["registry"], case["base_dir"])

    assert report["entries"] == 2
    assert any(right in v for v in _marked_reproducible_with_bad_input(violations))

