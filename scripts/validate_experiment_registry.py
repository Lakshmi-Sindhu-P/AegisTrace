"""Validate tracked experiment declarations and optional local artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from aegistrace.schemas.experiments import ExperimentRegistry


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="tracked experiment registry JSON file")
    parser.add_argument(
        "--require-artifacts",
        action="store_true",
        help="fail when a referenced generated artifact is not available locally",
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        payload: Any = json.loads(args.path.read_text(encoding="utf-8"))
        registry = ExperimentRegistry.model_validate(payload)
    except (OSError, json.JSONDecodeError, ValidationError, TypeError) as error:
        print(error)
        return 1

    missing: list[str] = []
    mismatched: list[str] = []
    missing_docs: list[str] = []
    for run in registry.runs:
        for reference in run.artifact_refs:
            path = Path(reference.path)
            if not path.exists():
                missing.append(reference.path)
                continue
            if _sha256(path) != reference.digest:
                mismatched.append(reference.path)
        for reference in run.documentation_refs:
            if not Path(reference).exists():
                missing_docs.append(reference)

    if mismatched or missing_docs or (args.require_artifacts and missing):
        print(
            json.dumps(
                {
                    "mismatched_artifacts": sorted(set(mismatched)),
                    "missing_artifacts": sorted(set(missing)),
                    "missing_documentation": sorted(set(missing_docs)),
                },
                sort_keys=True,
            )
        )
        return 1
    print(
        json.dumps(
            {
                "path": str(args.path),
                "run_count": len(registry.runs),
                "missing_artifacts": sorted(set(missing)),
                "checked_artifacts": sum(len(run.artifact_refs) for run in registry.runs)
                - len(set(missing)),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
