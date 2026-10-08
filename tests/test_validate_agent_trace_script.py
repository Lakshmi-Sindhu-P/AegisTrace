"""Tests for the agent-trace JSONL validation script's non-degenerate floors.

Issue #19: a trace file with zero non-blank lines produced no errors and exited 0, so a
missing or emptied trace looked identical to a valid one at the gate.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from scripts.validate_agent_trace import main

REPO_ROOT = Path(__file__).resolve().parents[1]
TRACES_DIR = REPO_ROOT / ".context/traces"


def _run(monkeypatch: pytest.MonkeyPatch, path: Path) -> int:
    monkeypatch.setattr(sys, "argv", ["validate_agent_trace.py", str(path)])
    return main()


def test_empty_trace_file_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    trace = tmp_path / "empty.jsonl"
    trace.write_text("", encoding="utf-8")

    assert _run(monkeypatch, trace) == 1


def test_blank_only_trace_file_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    trace = tmp_path / "blank.jsonl"
    trace.write_text("\n   \n", encoding="utf-8")

    assert _run(monkeypatch, trace) == 1
    assert "no records found" in capsys.readouterr().err


def test_real_traces_still_validate(monkeypatch: pytest.MonkeyPatch) -> None:
    traces = sorted(TRACES_DIR.glob("*.jsonl"))
    assert traces, "expected committed traces under .context/traces"

    for trace in traces:
        assert _run(monkeypatch, trace) == 0, trace
