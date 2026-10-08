"""Report ``raise`` statements in ``src/aegistrace`` that the test suite never executes.

Coverage tells you a function ran; it never says the rejection path ran. This script walks
every ``raise`` in the package and reports the ones the suite never executed, so a guard
observed only by reading it is surfaced rather than silently trusted.

Method note: ``raise SystemExit(main())`` under ``if __name__ == "__main__":`` is a CLI
entry point, not a guard. Importing a module cannot execute its ``__main__`` block, so a
test suite can never cover it and should not try. These are excluded from the count.

The report is descriptive; the *ratchet* is on the count. The count is compared against a
recorded baseline (``configs/guard_falsification_baseline.json``) and the command exits
non-zero only when the count *exceeds* the baseline. A count below the baseline is an
improvement and prints a note to tighten it, so the baseline cannot silently drift above
reality. Forcing a hard zero is rejected by the governing issue: some raises are genuinely
unreachable defensive boundaries, and demanding zero would invite deleting real guards to
satisfy a metric.

The counting and comparison logic are pure functions (taking source text + executed lines,
and count + baseline) so they can be tested on synthetic input without real coverage data.
"""

from __future__ import annotations

import argparse
import ast
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src" / "aegistrace"
DEFAULT_BASELINE = REPO_ROOT / "configs" / "guard_falsification_baseline.json"
DEFAULT_COVERAGE = Path("/tmp/cov.json")


def _is_main_guard(test: ast.expr) -> bool:
    """True when ``test`` tests whether ``__name__ == "__main__"``."""
    if not isinstance(test, ast.Compare) or len(test.ops) != 1:
        return False
    if not isinstance(test.ops[0], ast.Eq):
        return False
    left = test.left
    if not (isinstance(left, ast.Name) and left.id == "__name__"):
        return False
    comparators = test.comparators
    if len(comparators) != 1:
        return False
    comparator = comparators[0]
    return isinstance(comparator, ast.Constant) and comparator.value == "__main__"


def _main_block_ranges(tree: ast.Module) -> list[tuple[int, int]]:
    """Line ranges (inclusive) occupied by ``if __name__ == "__main__":`` blocks."""
    ranges: list[tuple[int, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.If) and _is_main_guard(node.test):
            end = node.end_lineno if node.end_lineno is not None else node.lineno
            ranges.append((node.lineno, end))
    return ranges


def _build_parents(tree: ast.Module) -> dict[ast.AST, ast.AST]:
    parents: dict[ast.AST, ast.AST] = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parents[child] = parent
    return parents


def _enclosing_function(node: ast.AST, parents: dict[ast.AST, ast.AST]) -> str:
    current: ast.AST | None = node
    while current is not None:
        current = parents.get(current)
        if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return current.name
    return "<module>"


def unexecuted_guard_raises(
    source_text: str, executed_lines: set[int]
) -> list[dict[str, Any]]:
    """List every ``raise`` in ``source_text`` not covered by ``executed_lines``.

    A ``raise`` inside an ``if __name__ == "__main__":`` block is excluded (CLI entry
    point, not a guard). Each result carries ``file``-independent ``lineno`` and the
    enclosing function name so a reader can judge whether the guard is reachable.
    """
    tree = ast.parse(source_text)
    main_ranges = _main_block_ranges(tree)
    parents = _build_parents(tree)

    hits: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Raise) or node.lineno is None:
            continue
        if node.lineno in executed_lines:
            continue
        if any(lo <= node.lineno <= hi for lo, hi in main_ranges):
            continue
        hits.append(
            {
                "lineno": node.lineno,
                "function": _enclosing_function(node, parents),
            }
        )
    hits.sort(key=lambda hit: hit["lineno"])
    return hits


def exceed_count(count: int, baseline: int) -> int:
    """Return a non-zero exit code when ``count`` exceeds ``baseline``, else 0."""
    if count > baseline:
        return 1
    return 0


def _run_coverage(coverage_path: Path) -> None:
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "--cov=aegistrace",
        f"--cov-report=json:{coverage_path}",
    ]
    subprocess.run(cmd, cwd=REPO_ROOT, check=True)


def _load_executed_lines(coverage_path: Path) -> dict[str, set[int]]:
    """Map each measured file, keyed by an absolute path, to its executed lines.

    Coverage JSON keys may be absolute or relative to the repo root; normalize them so a
    caller can look up by the absolute path it already holds.
    """
    payload: dict[str, Any] = json.loads(
        coverage_path.read_text(encoding="utf-8")
    )
    files = payload.get("files", {})
    executed: dict[str, set[int]] = {}
    for path, entry in files.items():
        if not (isinstance(entry, dict) and path.endswith(".py")):
            continue
        absolute = path if Path(path).is_absolute() else str(REPO_ROOT / path)
        executed[absolute] = set(entry.get("executed_lines", []))
    return executed


def _load_baseline(path: Path) -> int:
    payload: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return int(payload["baseline"])


def _src_files() -> list[Path]:
    return sorted(SRC_ROOT.rglob("*.py"))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--coverage-file",
        type=Path,
        default=DEFAULT_COVERAGE,
        help="coverage JSON to read or write (default: /tmp/cov.json)",
    )
    parser.add_argument(
        "--no-cov-run",
        action="store_true",
        help="reuse an existing coverage file instead of running pytest",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=DEFAULT_BASELINE,
        help="baseline JSON file (default: configs/guard_falsification_baseline.json)",
    )
    parser.add_argument(
        "--json", action="store_true", help="emit machine-readable JSON"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if not args.no_cov_run:
        _run_coverage(args.coverage_file)
    if not args.coverage_file.exists():
        print(
            f"coverage file not found: {args.coverage_file} (need --no-cov-run)",
            file=sys.stderr,
        )
        return 2

    executed_by_file = _load_executed_lines(args.coverage_file)
    baseline = _load_baseline(args.baseline)
    results: list[dict[str, Any]] = []
    for source_file in _src_files():
        unexecuted = unexecuted_guard_raises(
            source_file.read_text(encoding="utf-8"),
            executed_by_file.get(str(source_file), set()),
        )
        for hit in unexecuted:
            results.append(
                {"file": str(source_file.relative_to(REPO_ROOT)), **hit}
            )
    results.sort(key=lambda hit: (hit["file"], hit["lineno"]))
    count = len(results)
    exit_code = exceed_count(count, baseline)

    if args.json:
        print(
            json.dumps(
                {
                    "count": count,
                    "baseline": baseline,
                    "exceeds_baseline": exit_code != 0,
                    "unexecuted_raises": results,
                },
                sort_keys=True,
                indent=2,
            )
        )
    else:
        print(f"unexecuted guard raises: {count} (baseline {baseline})")
        for hit in results:
            print(f"  {hit['file']}:{hit['lineno']}  in {hit['function']}()")
        if count < baseline:
            print(
                "note: count is below the baseline; consider tightening the baseline so "
                "it does not silently drift above reality."
            )
        elif count > baseline:
            print("FAIL: unexecuted guard raises exceed the recorded baseline.")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())