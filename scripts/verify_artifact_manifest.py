"""Verify the committed artifact manifest against the experiment registry and local bytes.

Two classes of check are performed:

* Registry cross-checks, which never need artifact bytes and therefore always run.  A
  manifest entry whose digest disagrees with the registry, an entry the registry does not
  register, and a registered artifact missing from the manifest are all failures.  Each
  entry must also declare the reproducibility contract explicitly (``reproducible`` and
  ``reproducibility_note``), so a future entry cannot silently claim a reproducible digest
  that its producing script cannot actually emit (issue #21).  This is the check CI can
  perform on a fresh clone where none of the artifacts exist.
* Transitivity cross-check, added by issue #23 and repaired by issue #24.  ``reproducible``
  answers "can these exact bytes recur?", which is a property of the artifact's inputs as well
  as its own bytes.  Each entry commits the artifact paths it consumes in ``recorded_inputs``,
  so the closure is a pure function of the committed manifest and runs on a fresh clone where
  no artifact exists; the closure is followed transitively and cycles terminate because the set
  of non-reproducible paths only ever grows.  When an artifact is present and readable its own
  ``inputs`` array is loaded only if the entry stays below ``MAX_INPUT_SCAN_BYTES``, and the
  committed edges are cross-checked against it: a disagreement is a violation, because a stale
  dependency graph would silently under-check.
* Unverified inputs are reported, never silently dropped.  ``input_graph_checked`` names every
  entry whose edge list was established, while ``input_graph_unverified`` names every entry
  whose edges could not be established and why (absent / unreadable / unparseable / over the
  size ceiling), so "could not check" can never be mistaken for "checked clean".  An entry that
  declares an ``inputs`` top-level key or commits a non-empty ``recorded_inputs`` list whose
  artifact carries no readable ``inputs`` array is a violation.
* Byte-level checks, which run only for artifacts that are actually present on disk.  The
  recorded size, top-level keys, capture count and raw-bytes SHA-256 digest must all match.

Artifacts are deliberately untracked because of their size (about 196 MB in total, dominated
by ``stability_summary.json`` and ``causal_summary.json``).  An artifact that is absent from
disk is therefore reported, never failed.  Digests are computed over the raw bytes of the
file, exactly as the registry records them; canonical-JSON hashing is NOT used here.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = Path("docs/artifact_manifest.json")
DEFAULT_REGISTRY = Path("docs/experiment_registry.json")

# An artifact's recorded inputs are read from the artifact itself only as a cross-check
# against the committed ``recorded_inputs`` edges, which means loading the artifact.  This
# ceiling keeps the check from ever pulling the large summaries (the stability and causal
# artifacts are 139 MB and 65 MB) into memory.  Entries above the ceiling are reported,
# never read.
MAX_INPUT_SCAN_BYTES = 8 * 1024 * 1024

# Why an entry's committed edges could not be checked against the artifact's own bytes.
UNVERIFIED_ABSENT = "absent"
UNVERIFIED_UNREADABLE = "unreadable"
UNVERIFIED_UNPARSEABLE = "unparseable"
UNVERIFIED_OVER_CEILING = "over the size ceiling"


def sha256_file(path: Path) -> str:
    """Return the SHA-256 hex digest of the file's raw bytes."""

    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_registry_digests(registry: Any) -> tuple[dict[str, str], list[str]]:
    """Map each registered artifact path to its digest, reporting conflicting duplicates."""

    digests: dict[str, str] = {}
    violations: list[str] = []
    for run in registry.get("runs", []):
        for reference in run.get("artifact_refs", []):
            path = reference["path"]
            digest = reference["digest"]
            previous = digests.setdefault(path, digest)
            if previous != digest:
                violations.append(
                    f"registry records conflicting digests for {path}: {previous} vs {digest}"
                )
    return digests, violations


def _top_level_keys(path: Path) -> tuple[list[str], int | None]:
    """Load one artifact at a time and return its sorted keys and capture count."""

    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        return [], None
    keys = sorted(payload)
    captures = payload.get("captures")
    count = len(captures) if isinstance(captures, list) else None
    return keys, count


def _committed_input_paths(entry: dict[str, Any], violations: list[str]) -> list[str] | None:
    """Return the committed ``recorded_inputs`` paths, or ``None`` when the field is absent.

    Issue #24 commits the dependency edges as manifest data so the transitivity check needs no
    artifact bytes.  A present-but-malformed field is reported and treated as absent.
    """

    committed = entry.get("recorded_inputs")
    if committed is None:
        return None
    if not isinstance(committed, list) or not all(isinstance(item, str) for item in committed):
        violations.append(
            f"manifest entry {entry['path']} has malformed 'recorded_inputs': "
            "expected a list of artifact path strings"
        )
        return None
    return committed


def _artifact_input_paths(payload: Any, digest_to_path: dict[str, str]) -> list[str] | None:
    """Return an artifact's recorded input paths, or ``None`` if it has no readable list.

    Each input may name its ``path`` directly or record only a ``digest``; a digest is resolved
    through the manifest so the graph stays expressed in paths.
    """

    if not isinstance(payload, dict):
        return None
    inputs = payload.get("inputs")
    if not isinstance(inputs, list):
        return None
    paths: list[str] = []
    for item in inputs:
        if not isinstance(item, dict):
            continue
        path = item.get("path")
        if isinstance(path, str):
            paths.append(path)
        elif isinstance(item.get("digest"), str):
            mapped = digest_to_path.get(item["digest"])
            if mapped is not None:
                paths.append(mapped)
    return paths


def _input_graph(
    entries: list[dict[str, Any]], root: Path
) -> tuple[dict[str, list[str]], list[str], list[str], dict[str, str], list[str]]:
    """Return each entry's input edges plus the checked, skipped, unverified and violations.

    The result is ``(edges, checked, skipped_large, unverified, violations)``.  Committed
    ``recorded_inputs`` always supply the edges, so the transitivity check runs on a fresh
    clone; a present, readable artifact additionally cross-checks those edges (a disagreement is
    a violation) or supplies them for entries that predate the committed field.  Every entry
    whose edges could not be established is named in ``unverified`` with a reason, and an entry
    that declares inputs but yields no edge data is a violation rather than a silent pass.
    """

    edges: dict[str, list[str]] = {}
    checked: list[str] = []
    skipped_large: list[str] = []
    unverified: dict[str, str] = {}
    violations: list[str] = []

    digest_to_path: dict[str, str] = {}
    for entry in entries:
        digest = entry.get("digest")
        if isinstance(digest, str):
            digest_to_path.setdefault(digest, entry["path"])

    for entry in entries:
        path = entry["path"]
        declared = "inputs" in entry.get("top_level_keys", [])
        committed = _committed_input_paths(entry, violations)
        if not declared and not committed:
            continue

        reason: str | None = None
        resolved: list[str] | None = None
        size = entry.get("size_bytes")
        if isinstance(size, int) and size > MAX_INPUT_SCAN_BYTES:
            skipped_large.append(path)
            reason = UNVERIFIED_OVER_CEILING
        else:
            artifact = root / path
            if not artifact.is_file():
                reason = UNVERIFIED_ABSENT
            else:
                try:
                    text = artifact.read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError):
                    reason = UNVERIFIED_UNREADABLE
                else:
                    try:
                        payload = json.loads(text)
                    except json.JSONDecodeError:
                        reason = UNVERIFIED_UNPARSEABLE
                    else:
                        actual = _artifact_input_paths(payload, digest_to_path)
                        if actual is None:
                            if declared:
                                violations.append(
                                    f"manifest entry {path} declares an 'inputs' top-level key "
                                    "but its artifact payload has no readable 'inputs' list"
                                )
                        elif committed is not None:
                            if sorted(committed) != sorted(actual):
                                violations.append(
                                    f"manifest entry {path} committed 'recorded_inputs' disagree "
                                    f"with the artifact's inputs: manifest={sorted(committed)} "
                                    f"artifact={sorted(actual)}"
                                )
                            resolved = list(committed)
                        else:
                            resolved = list(actual)

        if resolved is None and committed:
            resolved = list(committed)
        if resolved:
            edges[path] = list(resolved)
            checked.append(path)
        elif declared and reason is not None:
            violations.append(
                f"manifest entry {path} declares 'inputs' but its input edges could not be "
                f"established ({reason}): no committed 'recorded_inputs' and no readable "
                "artifact 'inputs' list"
            )
        if reason is not None:
            unverified[path] = reason
    return edges, sorted(checked), sorted(skipped_large), unverified, violations


def _unreproducible_paths(
    entries: list[dict[str, Any]], edges: dict[str, list[str]]
) -> set[str]:
    """Return the closure of manifest paths whose exact bytes cannot recur.

    A path is unreproducible when its entry is flagged so directly, or when any path it records
    as an input is unreproducible.  The closure is computed by monotone fixpoint: the set only
    grows, so a cyclic or malformed input graph cannot hang -- the loop stops as soon as a pass
    adds nothing.
    """

    unreproducible = {
        entry["path"]
        for entry in entries
        if entry.get("reproducible") is False and isinstance(entry.get("digest"), str)
    }
    changed = True
    while changed:
        changed = False
        for entry in entries:
            path = entry["path"]
            if path in unreproducible:
                continue
            if any(input_path in unreproducible for input_path in edges.get(path, [])):
                unreproducible.add(path)
                changed = True
    return unreproducible


def verify_manifest(
    manifest_path: Path | str = DEFAULT_MANIFEST,
    registry_path: Path | str = DEFAULT_REGISTRY,
    base_dir: Path | str = REPO_ROOT,
) -> tuple[dict[str, Any], list[str]]:
    """Return ``(report, violations)`` for a manifest, registry and artifact base directory."""

    manifest_file = Path(manifest_path)
    registry_file = Path(registry_path)
    root = Path(base_dir)

    manifest: Any = json.loads(manifest_file.read_text(encoding="utf-8"))
    registry: Any = json.loads(registry_file.read_text(encoding="utf-8"))

    registry_digests, violations = load_registry_digests(registry)
    entries: list[dict[str, Any]] = list(manifest.get("artifacts", []))
    manifest_paths = [entry["path"] for entry in entries]

    # Issue #19: a manifest with no entries and a registry with no artifact_refs made both
    # set-difference loops vacuous, so the script reported zero violations.  Absent artifacts
    # are still counted rather than failed; only the empty-manifest floor is added here.
    if not entries:
        violations.append("manifest is empty: expected at least one artifact entry")

    seen: set[str] = set()
    for path in manifest_paths:
        if path in seen:
            violations.append(f"duplicate manifest entry for {path}")
        seen.add(path)

    for path in sorted(seen - set(registry_digests)):
        violations.append(f"manifest names unregistered artifact: {path}")
    for path in sorted(set(registry_digests) - seen):
        violations.append(f"registry artifact missing from manifest: {path}")

    # Issue #21: a digest is only meaningful if the entry says whether it can be
    # reproduced.  The field is required for every entry and needs no artifact bytes.
    for entry in entries:
        path = entry["path"]
        if not isinstance(entry.get("reproducible"), bool):
            violations.append(
                f"manifest entry {path} is missing required boolean field 'reproducible'"
            )
        note = entry.get("reproducibility_note")
        if not isinstance(note, str) or not note.strip():
            violations.append(
                f"manifest entry {path} is missing required non-empty "
                "'reproducibility_note' field"
            )

    # Issue #23: ``reproducible`` is transitive; issue #24: the edges are committed manifest
    # data, so this runs on a fresh clone where no artifact exists.  A stored ``true`` whose
    # consumed artifacts cannot recur contradicts the committed graph.
    edges, checked, skipped_large, unverified, graph_violations = _input_graph(entries, root)
    violations.extend(graph_violations)
    unreproducible = _unreproducible_paths(entries, edges)
    manifest_path_set = set(manifest_paths)
    for entry in sorted(entries, key=lambda item: item["path"]):
        path = entry["path"]
        input_paths = edges.get(path, [])
        unknown = sorted({item for item in input_paths if item not in manifest_path_set})
        if entry.get("reproducible") is True and unknown:
            violations.append(
                f"manifest entry {path} is marked reproducible but records input path(s) that "
                f"are not manifest entries: {', '.join(unknown)}"
            )
        if entry.get("reproducible") is not True:
            continue
        offending = sorted({item for item in input_paths if item in unreproducible})
        if offending:
            violations.append(
                f"manifest entry {path} is marked reproducible but its recorded "
                f"inputs include unreproducible artifact(s): {', '.join(offending)}"
            )

    verified_on_disk = 0
    absent = 0
    for entry in sorted(entries, key=lambda item: item["path"]):
        path = entry["path"]
        digest = entry.get("digest")
        registered = registry_digests.get(path)
        if registered is not None and digest != registered:
            violations.append(
                f"digest mismatch vs registry for {path}: manifest={digest} registry={registered}"
            )

        artifact = root / path
        if not artifact.is_file():
            absent += 1
            continue

        verified_on_disk += 1
        try:
            actual_size = os.stat(artifact).st_size
            actual_digest = sha256_file(artifact)
            keys, capture_count = _top_level_keys(artifact)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            # A present artifact that cannot be read must not skip its byte checks silently.
            violations.append(
                f"artifact present but unreadable for byte checks: {path} ({error})"
            )
            continue

        if entry.get("size_bytes") != actual_size:
            violations.append(
                f"size mismatch for {path}: manifest={entry.get('size_bytes')} actual={actual_size}"
            )

        if actual_digest != digest:
            violations.append(
                f"raw sha256 mismatch for {path}: manifest={digest} actual={actual_digest}"
            )

        if sorted(entry.get("top_level_keys", [])) != keys:
            violations.append(f"top_level_keys mismatch for {path}")
        if entry.get("capture_count") != capture_count:
            violations.append(
                f"capture_count mismatch for {path}: "
                f"manifest={entry.get('capture_count')} actual={capture_count}"
            )

    report: dict[str, Any] = {
        "manifest": str(manifest_file),
        "entries": len(entries),
        "verified_on_disk": verified_on_disk,
        "absent": absent,
        "input_graph_checked": checked,
        "input_graph_skipped_large": skipped_large,
        "input_graph_unverified": dict(sorted(unverified.items())),
        "violations": violations,
    }
    return report, violations


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "manifest",
        nargs="?",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="committed artifact manifest JSON file",
    )
    parser.add_argument(
        "--registry",
        type=Path,
        default=DEFAULT_REGISTRY,
        help="experiment registry JSON file used for the always-on cross-checks",
    )
    parser.add_argument(
        "--base-dir",
        type=Path,
        default=REPO_ROOT,
        help="directory that artifact paths are resolved against",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        report, violations = verify_manifest(args.manifest, args.registry, args.base_dir)
    except (OSError, json.JSONDecodeError) as error:
        print(error, file=sys.stderr)
        return 1

    summary = (
        f"artifact manifest: {report['entries']} entries, "
        f"{report['verified_on_disk']} verified on disk, "
        f"{report['absent']} absent (deliberately untracked)"
    )
    if violations:
        for violation in violations:
            print(f"VIOLATION: {violation}", file=sys.stderr)
        print(summary, file=sys.stderr)
        print(f"{len(violations)} violation(s) found", file=sys.stderr)
        return 1
    print(json.dumps(report))
    print(summary, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
