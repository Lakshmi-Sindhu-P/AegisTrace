"""Issue #21: wall-clock fit timing must never reach digest-covered artifact bytes.

``fit_seconds`` comes from ``time.perf_counter()`` in
``aegistrace.evaluation.model_family``.  The four phase-3 producer scripts used to
serialize it as ``fit_runtime_seconds`` and inside a ``runtime`` block, so their
recorded raw-bytes SHA-256 digests could never be reproduced.  They must now strip
the value before serialization while still reporting it on stderr for the operator.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from aegistrace.evaluation.model_family import artifact_fit_metadata

REPO_ROOT = Path(__file__).resolve().parents[1]
PRODUCER_SCRIPTS = (
    "scripts/run_phase3_model_family_benchmark.py",
    "scripts/run_phase3_model_stability.py",
    "scripts/run_phase3_model_stability_cached.py",
    "scripts/run_phase3_causal_representation.py",
)


def test_artifact_fit_metadata_strips_wall_clock_timing() -> None:
    runtime = {
        "fit_seconds": 12.5,
        "training_rows_known": 100,
        "validation_rows_scored": 40,
        "score_semantics": "ranking",
    }

    serialized = artifact_fit_metadata(runtime)

    assert "fit_seconds" not in serialized
    assert serialized == {
        "training_rows_known": 100,
        "validation_rows_scored": 40,
        "score_semantics": "ranking",
    }
    # The operator-facing input is left intact for reporting.
    assert runtime["fit_seconds"] == 12.5


@pytest.mark.parametrize("relative_path", PRODUCER_SCRIPTS)
def test_producer_script_does_not_serialize_fit_timing(relative_path: str) -> None:
    source = (REPO_ROOT / relative_path).read_text(encoding="utf-8")

    assert '"fit_runtime_seconds"' not in source
    assert '"runtime": runtime' not in source
    assert "artifact_fit_metadata(runtime)" in source
    for line in source.splitlines():
        if "fit_seconds" in line:
            # The only remaining use is the operator-facing stderr report.
            assert "file=sys.stderr" in line, line


def test_producer_script_payload_uses_sanitized_metadata() -> None:
    for relative_path in PRODUCER_SCRIPTS:
        source = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
        assert '"fit_metadata": artifact_fit_metadata(runtime)' in source

    # The benchmark also serializes the unsupervised Isolation Forest result.
    benchmark = (REPO_ROOT / PRODUCER_SCRIPTS[0]).read_text(encoding="utf-8")
    assert benchmark.count('"fit_metadata": artifact_fit_metadata(runtime)') == 2
