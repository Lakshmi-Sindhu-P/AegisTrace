"""Render docs/results.md from the consolidated results ledger.

The ledger is the machine-checked source of truth; this renderer is a pure function of
it. Running it twice produces byte-identical output.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

LEDGER = "docs/results_ledger.json"
OUTPUT = "docs/results.md"

FRAMING = (
    "This ledger states what the AegisTrace project claims, at what evidence tier, and backed "
    "by which registered experiment artifact; every number is extracted from an artifact on "
    "disk. It is generated from `docs/results_ledger.json` by "
    "`scripts/render_results_ledger.py` and is validated against `docs/experiment_registry.json` "
    "by `scripts/validate_results_ledger.py`, so a claim cannot drift from its citation without "
    "the validator failing."
)


def render(ledger: dict[str, Any]) -> str:
    """Return the full Markdown document for ``ledger``."""

    lines: list[str] = ["# AegisTrace results ledger", "", FRAMING, ""]

    lines.extend(
        [
            "## Claim index",
            "",
            "| Claim | Type | Status |",
            "| --- | --- | --- |",
        ]
    )
    for claim in ledger["claims"]:
        lines.append(
            f"| `{claim['claim_id']}` | {claim['claim_type']} | {claim['status']} |"
        )
    lines.append("")

    for claim in ledger["claims"]:
        lines.extend(
            [
                f"## `{claim['claim_id']}`",
                "",
                f"**Statement.** {claim['statement']}",
                "",
                "**Evidence.**",
                "",
            ]
        )
        for item in claim["evidence"]:
            lines.append(f"- {item}")
        lines.extend(
            [
                "",
                f"**Scope limit.** {claim['scope_limit']}",
                "",
                "**Experiments.** "
                + (", ".join(f"`{e}`" for e in claim["experiment_ids"]) or "_(none cited)_"),
                "",
                "**Artifacts.** "
                + (", ".join(f"`{a}`" for a in claim["artifact_refs"]) or "_(none cited)_"),
                "",
            ]
        )

    lines.extend(["## Non-claims", ""])
    lines.extend(f"- {item}" for item in ledger.get("non_claims", []))
    lines.extend(["", "## Evidence gaps", ""])
    lines.extend(f"- {item}" for item in ledger.get("evidence_gaps", []))
    lines.append("")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point: read the ledger and write, or drift-check, the rendered Markdown."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ledger", nargs="?", default=LEDGER, help="path to results_ledger.json")
    parser.add_argument("--output", default=OUTPUT, help="path to write results.md")
    parser.add_argument(
        "--check",
        action="store_true",
        help="do not write; exit 1 if the file on disk differs from the rendered output",
    )
    args = parser.parse_args(argv)

    ledger = json.loads(Path(args.ledger).read_text(encoding="utf-8"))
    rendered = render(ledger)
    target = Path(args.output)

    if args.check:
        if not target.is_file():
            print(f"{args.output} does not exist; run this script to generate it", file=sys.stderr)
            return 1
        if target.read_text(encoding="utf-8") != rendered:
            print(
                f"{args.output} is out of date with {args.ledger}; "
                "run this script to regenerate it",
                file=sys.stderr,
            )
            return 1
        print(f"{args.output} is in sync with {args.ledger}")
        return 0

    target.write_text(rendered, encoding="utf-8")
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
