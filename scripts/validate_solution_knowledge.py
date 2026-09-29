"""Validate the tracked, append-only solution-knowledge document."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from aegistrace.schemas.agent_trace import SolutionKnowledge


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="solution knowledge JSON file")
    args = parser.parse_args()
    try:
        payload: Any = json.loads(args.path.read_text(encoding="utf-8"))
        knowledge = SolutionKnowledge.model_validate(payload)
    except (json.JSONDecodeError, ValidationError, TypeError) as error:
        print(error)
        return 1
    print(
        json.dumps(
            {"path": str(args.path), "solution_count": len(knowledge.solutions)}, sort_keys=True
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
