"""Unit tests for the unexecuted-guard counting and ratchet logic.

These exercise the pure functions in
``scripts/report_unexecuted_guard_raises.py`` against SYNTHETIC source, so they do not
depend on real coverage data or on running the whole suite.
"""

from __future__ import annotations

from scripts.report_unexecuted_guard_raises import (
    exceed_count,
    unexecuted_guard_raises,
)

# --------------------------------------------------------------------------------------


def test_counts_an_unexecuted_raise() -> None:
    source = (
        "def f():\n"
        "    if x:\n"
        "        raise ValueError('bad')\n"
        "    return 1\n"
    )
    hits = unexecuted_guard_raises(source, executed_lines=set())
    assert len(hits) == 1
    assert hits[0]["lineno"] == 3
    assert hits[0]["function"] == "f"


def test_does_not_count_an_executed_raise() -> None:
    source = (
        "def f():\n"
        "    if x:\n"
        "        raise ValueError('bad')\n"
        "    return 1\n"
    )
    hits = unexecuted_guard_raises(source, executed_lines={3})
    assert hits == []


def test_excludes_main_block_raise() -> None:
    source = (
        "def f():\n"
        "    raise ValueError('guard')\n"
        "\n"
        "if __name__ == '__main__':\n"
        "    raise SystemExit(main())\n"
    )
    hits = unexecuted_guard_raises(source, executed_lines=set())
    assert len(hits) == 1
    # the guard, not the CLI entry point, is reported
    assert hits[0]["lineno"] == 2
    assert hits[0]["function"] == "f"


def test_main_block_guard_variants_are_excluded() -> None:
    source = (
        "if __name__ == '__main__':\n"
        "    raise SystemExit(main())\n"
        "\n"
        "if __name__ == \"__main__\":\n"
        "    raise SystemExit(main())\n"
    )
    assert unexecuted_guard_raises(source, executed_lines=set()) == []


def test_does_not_count_module_level_raise_in_main() -> None:
    source = "if __name__ == '__main__':\n    raise SystemExit(main())\n"
    assert unexecuted_guard_raises(source, executed_lines=set()) == []


def test_exceed_count_above_baseline_is_nonzero() -> None:
    assert exceed_count(3, 0) != 0


def test_exceed_count_at_or_below_baseline_is_zero() -> None:
    assert exceed_count(0, 0) == 0
    assert exceed_count(1, 1) == 0
    assert exceed_count(0, 2) == 0