"""Tests for the solution-knowledge validator and its non-empty floor (issue #16)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from scripts.validate_solution_knowledge import main

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_empty_solution_store_fails(tmp_path: Path, monkeypatch, capsys) -> None:
    """Issue #16: a store with zero solutions must not pass vacuously."""

    store = tmp_path / "solutions_empty.json"
    store.write_text(
        json.dumps({"schema_version": "1.0.0", "solutions": []}), encoding="utf-8"
    )
    monkeypatch.setattr(sys, "argv", ["validate_solution_knowledge.py", str(store)])

    assert main() == 1
    assert "empty" in capsys.readouterr().out


def test_real_solution_store_passes(monkeypatch, capsys) -> None:
    """The non-empty floor must not reject the real, populated store."""

    store = REPO_ROOT / "docs/solution_knowledge.json"
    monkeypatch.setattr(sys, "argv", ["validate_solution_knowledge.py", str(store)])

    assert main() == 0
    assert json.loads(capsys.readouterr().out)["solution_count"] > 0
