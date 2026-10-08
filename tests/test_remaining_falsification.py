"""Falsify the last guards, and correct the metric that counted two non-guards.

Every guard here is executed against the input it exists to reject, because a guard never
observed failing is an untested claim. Same method as the four sibling suites.

This file also closes a defect in the metric used to find these guards. That metric is
"raise statements the test suite never executes", computed by walking the AST. It is a
useful proxy but an imprecise one, and two of the nine remaining hits were not guards at
all:

    ingestion/ctu13.py:677   raise SystemExit(main())
    ingestion/iot23.py:545   raise SystemExit(main())

Both sit under ``if __name__ == "__main__":``. They are CLI entry points and cannot be
"executed by the test suite" by design, because importing a module does not run its
``__main__`` block. Counting them inflates the number and, worse, invites someone to write
a test that imports the module as a script purely to make a metric go down. They are
excluded from the count, and the exclusion is stated rather than silent.

Three of the guards here are reachable only by passing a value the type system does not
permit - a raw string where an enum is expected, or an unknown model name. They are marked
below. They are not dead code: they are the boundary that stops an unvalidated string from
being accepted as a routing policy or a model family, which is exactly the kind of value
that arrives from a config file or a CLI argument.
"""

from __future__ import annotations

import numpy as np
import pytest

from aegistrace.evaluation.analyst_replay import _ranking_order
from aegistrace.evaluation.model_family import make_model, select_operating_threshold
from aegistrace.evaluation.reviewer_simulation import RoutingPolicy, simulate_capture
from aegistrace.ingestion.iot23 import _separator_from_header
from aegistrace.schemas.manifests import DatasetManifest

# --------------------------------------------------------------------------------------
# Guards reachable only by passing a value outside the declared type.
#
# These are the boundary against an unvalidated string arriving from a config file or a
# CLI argument. The type annotations say ``RoutingPolicy`` and ``str`` for the model name
# respectively, but nothing at runtime enforces that, which is precisely why the guard
# exists.
# --------------------------------------------------------------------------------------


def test_ranking_order_rejects_unsupported_routing_policy() -> None:
    """A raw string must not be accepted where a RoutingPolicy is required."""

    with pytest.raises(ValueError, match="unsupported routing policy"):
        _ranking_order(
            np.array([0.1, 0.9]),
            np.array([False, True]),
            policy="model_score",  # type: ignore[arg-type]
            threshold=0.5,
            seed=42,
            event_ids=None,
        )


def test_make_model_rejects_unsupported_family() -> None:
    """An unknown model name must refuse rather than return nothing.

    This matters beyond hygiene: ``make_model`` constructs the detectors, so a family name
    that silently produced no estimator would surface later as an empty model rather than
    as a configuration error.
    """

    with pytest.raises(ValueError, match="unsupported model family"):
        make_model("gradient_boosted_trees_typo", seed=42)


def test_iot23_rejects_unsupported_zeek_separator() -> None:
    """A separator that is neither tab, a \\x escape, nor one character must refuse."""

    with pytest.raises(ValueError, match="unsupported Zeek separator"):
        _separator_from_header("#separator MULTI_CHAR_SEPARATOR")


# --------------------------------------------------------------------------------------
# Guards on the ordinary public path.
# --------------------------------------------------------------------------------------


def test_manifest_rejects_negative_label_count() -> None:
    """An impossible negative class count must refuse.

    A negative count cannot arise from counting rows, so accepting one would mean the count
    came from arithmetic on records rather than from the records themselves - and would
    make any downstream total quietly wrong.
    """

    payload = {
        "dataset_id": "ctu13",
        "name": "CTU-13",
        "version": "1.0.0",
        "source_url": "https://example.invalid/ctu13",
        "license": "CC-BY-4.0",
        "row_count": 10,
        "label_distribution": {"malicious": -1, "benign": 11},
        "content_digest": "0" * 64,
    }
    try:
        DatasetManifest(**payload)
    except Exception as exc:  # pydantic wraps the ValueError
        assert "label counts must be non-negative" in str(exc)
    else:  # pragma: no cover - only on regression
        pytest.fail("negative label count was accepted")


def test_operating_threshold_rejects_negative_alert_cap() -> None:
    """A negative alerts-per-1000 cap is not a permissive cap, it is a typo."""

    with pytest.raises(ValueError, match="must be non-negative"):
        select_operating_threshold(
            detector_name="rf",
            validation_records=(),
            scores={},
            alerts_per_1000_cap=-1.0,
        )


# --------------------------------------------------------------------------------------
# Reviewer-simulation guards. These were verified interactively earlier in the round and
# are committed here so the guarantee is enforced by the suite rather than by a one-off
# script that no longer exists.
# --------------------------------------------------------------------------------------

_SIM_KWARGS = dict(
    scenario_id="CAP",
    scores=np.array([0.2, 0.9]),
    labels=np.array([False, True]),
    known=np.array([True, True]),
    threshold=0.5,
    strictness_values=(0.1,),
    shift_budgets=(1,),
    policies=(RoutingPolicy.MODEL_SCORE,),
    seed=42,
    event_ids=("e0", "e1"),
)


def test_reviewer_simulation_rejects_non_finite_scores() -> None:
    """A NaN score compares false against every threshold.

    Left unchecked it would be treated as "never alerts" and counted as an ordinary miss,
    hiding a defect in the scores behind a plausible-looking metric.
    """

    with pytest.raises(ValueError, match="scores must be finite"):
        simulate_capture(**{**_SIM_KWARGS, "scores": np.array([0.2, np.nan])})


def test_reviewer_simulation_rejects_misaligned_event_ids() -> None:
    with pytest.raises(ValueError, match="event_ids must align with scores"):
        simulate_capture(**{**_SIM_KWARGS, "event_ids": ("e0",)})


def test_reviewer_simulation_rejects_misaligned_arrays() -> None:
    with pytest.raises(ValueError, match="scores, labels, and known must align"):
        simulate_capture(
            **{
                **_SIM_KWARGS,
                "scores": np.array([0.2, 0.9, 0.1]),
                "labels": np.array([False, True]),
                "known": np.array([True, True]),
            }
        )


def test_reviewer_simulation_still_rejects_oracle() -> None:
    """ORACLE reads ground truth and is not an achievable reviewer policy.

    Asserted here as well as in the pipeline suite because this single guard is what keeps
    an oracle baseline out of the reviewer simulation, which would make every routing policy
    look worse than a reviewer who can see the answers.
    """

    with pytest.raises(ValueError, match="ORACLE is not an achievable reviewer policy"):
        simulate_capture(**{**_SIM_KWARGS, "policies": (RoutingPolicy.ORACLE,)})


def test_the_metric_excludes_cli_entry_points() -> None:
    """Record why two former "guards" are not guards.

    ``raise SystemExit(main())`` under ``if __name__ == "__main__":`` is a CLI entry point.
    Importing the module cannot execute it, so a test suite can never cover it and should
    not try. This test exists so the exclusion is documented in code rather than only in a
    commit message.
    """

    for module in ("src/aegistrace/ingestion/ctu13.py", "src/aegistrace/ingestion/iot23.py"):
        with open(module, encoding="utf-8") as handle:
            source = handle.read()
        idx = source.index('if __name__ == "__main__":')
        block = source[idx:]
        assert "raise SystemExit(main())" in block, module
        # the entry point is the ONLY raise in that block, and it is not a guard
        assert block.count("raise ") == 1, module
