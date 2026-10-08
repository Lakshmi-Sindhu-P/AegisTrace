"""Validate one redacted AegisTrace agent JSONL provenance file."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from aegistrace.schemas.agent_trace import AgentTraceRecord


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="JSONL trace file to validate")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    valid = 0
    errors: list[str] = []
    with args.path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                payload: Any = json.loads(line)
                AgentTraceRecord.model_validate(payload)
            except (json.JSONDecodeError, ValidationError, TypeError) as error:
                errors.append(f"line {line_number}: {error}")
            else:
                valid += 1
    if errors:
        for error in errors:
            print(error)
        return 1
    # Issue #19: an empty or blank-only trace previously produced no errors and exited 0,
    # making a missing trace indistinguishable from a valid one at the gate.
    if valid == 0:
        print(f"{args.path}: no records found", file=sys.stderr)
        return 1
    print(json.dumps({"path": str(args.path), "valid_records": valid}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
