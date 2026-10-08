"""Verify the committed artifact manifest against the experiment registry and local bytes.

Two classes of check are performed:

* Registry cross-checks, which never need artifact bytes and therefore always run.  A
  manifest entry whose digest disagrees with the registry, an entry the registry does not
  register, and a registered artifact missing from the manifest are all failures.  This is
  the check CI can perform on a fresh clone where none of the artifacts exist.
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

    seen: set[str] = set()
    for path in manifest_paths:
        if path in seen:
            violations.append(f"duplicate manifest entry for {path}")
        seen.add(path)

    for path in sorted(seen - set(registry_digests)):
        violations.append(f"manifest names unregistered artifact: {path}")
    for path in sorted(set(registry_digests) - seen):
        violations.append(f"registry artifact missing from manifest: {path}")

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
        actual_size = os.stat(artifact).st_size
        if entry.get("size_bytes") != actual_size:
            violations.append(
                f"size mismatch for {path}: manifest={entry.get('size_bytes')} actual={actual_size}"
            )

        actual_digest = sha256_file(artifact)
        if actual_digest != digest:
            violations.append(
                f"raw sha256 mismatch for {path}: manifest={digest} actual={actual_digest}"
            )

        keys, capture_count = _top_level_keys(artifact)
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
