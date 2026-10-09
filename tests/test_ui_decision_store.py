"""The human-decision route, once a durable store exists to append to.

`tests/test_ui_app.py` pins the honesty property that mattered while there was no store: the route
refuses rather than fabricating a saved review. This file pins the properties that matter now that
one can be supplied:

* with no store, the refusal is unchanged and nothing is created anywhere;
* with a store, a submission is **durably** appended - asserted by reopening the database
  independently, not by reading the response HTML;
* what the page shows is the persisted record, re-read and revalidated, not an echo of the form;
* a correction supersedes while leaving the superseded review byte-identical;
* every rejection (duplicate, unlinked correction, missing field, unknown enum, missing store
  directory) produces an explicit failure page naming the problem, never a 500 and never a
  silent success;
* the page emits no JavaScript at all.

The store is always a `tmp_path` database, so no test touches a real artifact or a real review.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from aegistrace.schemas.review import (
    EscalationState,
    ReviewDecision,
    ReviewTier,
    review_id_for,
)
from aegistrace.schemas.triage import AssessorRole
from aegistrace.storage.reviews import ReviewStore
from aegistrace.ui.app import create_app

SPINE_ID = "11111111-1111-5111-8111-111111111111"


def _payload() -> dict[str, Any]:
    """A valid minimal spine summary carrying exactly one record."""

    return {
        "warning": "SYNTHETIC DEMONSTRATION. Mechanical stubs, not models.",
        "providers_configured": False,
        "network_egress": "none",
        "created_at": "2026-10-08T13:00:00+00:00",
        "freeze_version": "1.0.0",
        "bundle_count": 1,
        "record_count": 1,
        "records": [
            {
                "spine_id": SPINE_ID,
                "evidence_bundle_id": "22222222-2222-5222-8222-222222222222",
                "finding_id": "33333333-3333-5333-8333-333333333333",
                "snapshot_digest": "a" * 64,
                "tier": "tier_d_insufficient_evidence",
                "machine_checks_passed": True,
                "review_count": 0,
            }
        ],
    }


@pytest.fixture
def artifact(tmp_path: Path) -> Path:
    path = tmp_path / "spine.json"
    path.write_text(json.dumps(_payload()), encoding="utf-8")
    return path


@pytest.fixture
def store_path(tmp_path: Path) -> Path:
    """A store path whose parent directory exists, as ``ReviewStore.open`` requires."""

    return tmp_path / "reviews.duckdb"


def _client(*, artifact: Path, store: Path | None) -> TestClient:
    return TestClient(create_app(artifact_path=artifact, store_path=store))


def _form(**overrides: str) -> dict[str, str]:
    """A complete, valid decision form. Callers vary one field at a time."""

    form = {
        "spine_id": SPINE_ID,
        "subject_role": "triage_analyst",
        "reviewer_ref": "analyst-1",
        "tier": "tier_b_guided_junior",
        "decision": "confirm",
        "notes": "looks benign",
        "escalation_state": "none",
        "final_disposition": "confirmed as benign",
        "supersedes_review_id": "",
    }
    form.update(overrides)
    return form


def _history(store_path: Path):
    """Read the durable history straight from the database, bypassing the app entirely."""

    with ReviewStore.open(store_path) as store:
        return store.load_history(UUID(SPINE_ID))


# --- the unwired state is unchanged ---------------------------------------------------------


def test_without_a_store_the_route_still_refuses_and_creates_nothing(
    tmp_path: Path, artifact: Path
) -> None:
    """No store configured must mean the old, honest refusal - not a quiet no-op that looks saved.

    The response is checked for the refusal statement AND for the absence of any success wording,
    because a page that said both would be worse than one that said neither.
    """

    client = _client(artifact=artifact, store=None)
    response = client.post(
        "/decision", data={"spine_id": SPINE_ID, "decision": "confirm", "notes": "n"}
    )
    assert response.status_code == 200
    lowered = response.text.lower()
    assert "not recorded" in lowered, "the unwired route must state the decision was not recorded"
    assert "successfully saved" not in lowered
    assert "review saved" not in lowered
    assert list(tmp_path.glob("*.duckdb")) == [], "no database may be created without a store path"


# --- a configured store actually persists ---------------------------------------------------


def test_a_submitted_decision_is_durably_appended(
    artifact: Path, store_path: Path
) -> None:
    """The most important test here: the review must exist in the DATABASE, not just the page.

    Asserted by reopening the store independently. A test that only inspected the response body
    would pass against a route that rendered a convincing page and wrote nothing.
    """

    client = _client(artifact=artifact, store=store_path)
    response = client.post("/decision", data=_form())
    assert response.status_code == 200

    with ReviewStore.open(store_path) as store:
        assert store.review_count() == 1, "the review must be durably stored"

    history = _history(store_path)
    assert len(history.reviews) == 1
    stored = history.reviews[0]
    assert stored.decision is ReviewDecision.CONFIRM
    assert stored.tier is ReviewTier.B_GUIDED_JUNIOR
    assert stored.subject_role is AssessorRole.TRIAGE_ANALYST
    assert stored.reviewer_ref == "analyst-1"
    assert stored.escalation_state is EscalationState.NONE
    assert stored.final_disposition == "confirmed as benign"
    assert stored.supersedes_review_id is None


def test_the_page_shows_the_persisted_review_not_the_form(
    artifact: Path, store_path: Path
) -> None:
    """What is rendered must be the stored record, including the id the store derived."""

    client = _client(artifact=artifact, store=store_path)
    response = client.post("/decision", data=_form())
    stored = _history(store_path).reviews[0]
    assert str(stored.review_id) in response.text
    assert "recorded" in response.text.lower()


def test_the_recorded_review_id_matches_the_identity_rule(
    artifact: Path, store_path: Path
) -> None:
    """The id must be content-derived, not random, or the schema's own check would have refused it.

    Recomputing it here from the submitted substance proves the route derived it the documented way
    rather than generating a uuid and hoping.
    """

    client = _client(artifact=artifact, store=store_path)
    client.post("/decision", data=_form())
    stored = _history(store_path).reviews[0]

    expected = review_id_for(
        subject_triage_id=UUID(SPINE_ID),
        subject_role=AssessorRole.TRIAGE_ANALYST,
        reviewer_ref="analyst-1",
        decision=ReviewDecision.CONFIRM,
        final_disposition="confirmed as benign",
        supersedes_review_id=None,
    )
    assert stored.review_id == expected


def test_an_empty_notes_box_is_recorded_as_a_visible_placeholder(
    artifact: Path, store_path: Path
) -> None:
    """The schema requires non-empty notes, so an empty box must not be silently dropped.

    The stored note is a visible placeholder rather than an empty string, and the page shows it, so
    a reader can tell that no note was written instead of seeing an unexplained blank.
    """

    client = _client(artifact=artifact, store=store_path)
    client.post("/decision", data=_form(notes=""))
    stored = _history(store_path).reviews[0]
    assert stored.notes.strip() != "", "notes must not be empty after a blank submission"


# --- corrections extend, never rewrite ------------------------------------------------------


def test_a_correction_supersedes_and_preserves_the_original(
    artifact: Path, store_path: Path
) -> None:
    """A revise must append a linked entry and leave the superseded review exactly as it was."""

    client = _client(artifact=artifact, store=store_path)
    client.post("/decision", data=_form())
    first = _history(store_path).reviews[0]

    response = client.post(
        "/decision",
        data=_form(
            decision="revise",
            reviewer_ref="analyst-2",
            final_disposition="corrected after review",
            supersedes_review_id=str(first.review_id),
        ),
    )
    assert response.status_code == 200

    history = _history(store_path)
    assert len(history.reviews) == 2
    assert history.reviews[0] == first, "the superseded review must be byte-identical"
    assert history.reviews[1].supersedes_review_id == first.review_id
    assert history.reviews[1].decision is ReviewDecision.REVISE


# --- every rejection is explicit, and writes nothing ----------------------------------------


def test_a_duplicate_submission_is_refused_without_writing(
    artifact: Path, store_path: Path
) -> None:
    """Posting the identical decision twice must be refused, and the store still holds one row."""

    client = _client(artifact=artifact, store=store_path)
    client.post("/decision", data=_form())
    second = client.post("/decision", data=_form())

    assert second.status_code == 200, "a refusal must be a page, not a 500"
    assert "nothing was written" in second.text.lower()
    with ReviewStore.open(store_path) as store:
        assert store.review_count() == 1


def test_an_unlinked_correction_is_refused_without_writing(
    artifact: Path, store_path: Path
) -> None:
    """A revise with no supersede reference violates the schema and must not reach the store."""

    client = _client(artifact=artifact, store=store_path)
    response = client.post("/decision", data=_form(decision="revise"))
    assert response.status_code == 200
    assert "nothing was written" in response.text.lower()
    with ReviewStore.open(store_path) as store:
        assert store.review_count() == 0


def test_a_non_superseding_second_review_is_refused(
    artifact: Path, store_path: Path
) -> None:
    """A second review must supersede the most recent one; the chain may not fork."""

    client = _client(artifact=artifact, store=store_path)
    client.post("/decision", data=_form())
    response = client.post("/decision", data=_form(reviewer_ref="analyst-2"))
    assert response.status_code == 200
    assert "nothing was written" in response.text.lower()
    with ReviewStore.open(store_path) as store:
        assert store.review_count() == 1


def test_an_escalation_without_an_escalation_state_is_refused(
    artifact: Path, store_path: Path
) -> None:
    """The coherence invariant belongs to the schema; the route must surface its refusal."""

    client = _client(artifact=artifact, store=store_path)
    response = client.post(
        "/decision", data=_form(decision="escalate", escalation_state="none")
    )
    assert response.status_code == 200
    assert "nothing was written" in response.text.lower()
    with ReviewStore.open(store_path) as store:
        assert store.review_count() == 0


def test_a_missing_required_field_is_named_in_the_failure(
    artifact: Path, store_path: Path
) -> None:
    """An empty required field must be reported by name, not as a generic error."""

    client = _client(artifact=artifact, store=store_path)
    response = client.post("/decision", data=_form(reviewer_ref=""))
    assert response.status_code == 200
    lowered = response.text.lower()
    assert "nothing was written" in lowered
    assert "reviewer_ref" in lowered, "the failure must name the field that was empty"
    with ReviewStore.open(store_path) as store:
        assert store.review_count() == 0


def test_an_unknown_enum_value_is_refused_not_crashed(
    artifact: Path, store_path: Path
) -> None:
    """An unrecognised decision value must be a reported failure rather than a 500."""

    client = _client(artifact=artifact, store=store_path)
    response = client.post("/decision", data=_form(decision="not_a_real_decision"))
    assert response.status_code == 200
    assert "nothing was written" in response.text.lower()
    with ReviewStore.open(store_path) as store:
        assert store.review_count() == 0


def test_a_missing_store_directory_is_refused_and_named(
    tmp_path: Path, artifact: Path
) -> None:
    """`ReviewStore.open` refuses a mistyped path; the route must surface that, not swallow it."""

    missing = tmp_path / "does_not_exist" / "reviews.duckdb"
    client = _client(artifact=artifact, store=missing)
    response = client.post("/decision", data=_form())
    assert response.status_code == 200
    lowered = response.text.lower()
    assert "nothing was written" in lowered
    assert "does not exist" in lowered, "the failure must name the missing directory"
    assert not missing.exists(), "no store may be created at a mistyped path"


# --- the standing UI constraints still hold on this page ------------------------------------


def test_the_decision_page_emits_no_javascript(
    artifact: Path, store_path: Path
) -> None:
    """No JavaScript at all is an approved constraint, checked on the form and both result pages."""

    client = _client(artifact=artifact, store=store_path)
    pages = [
        client.get("/decision").text,
        client.post("/decision", data=_form()).text,
        client.post("/decision", data=_form()).text,
    ]
    for page in pages:
        lowered = page.lower()
        assert "<script" not in lowered, "the UI must emit no script tags"
        for handler in ("onclick=", "onload=", "onsubmit=", "onchange="):
            assert handler not in lowered, f"no inline {handler} handler is permitted"


def test_synthetic_data_is_marked_on_the_recorded_page(
    artifact: Path, store_path: Path
) -> None:
    """A recorded decision must not make the page look like real experimental output."""

    client = _client(artifact=artifact, store=store_path)
    response = client.post("/decision", data=_form())
    lowered = response.text.lower()
    assert "synthetic" in lowered
    assert "not an experimental result" in lowered


# --- the write path must be reachable from the documented entry point ------------------------


def _runner_parser():
    """Load ``scripts/run_local_ui.py`` as a module without executing ``main``."""

    import importlib.util

    script = Path(__file__).resolve().parents[1] / "scripts" / "run_local_ui.py"
    spec = importlib.util.spec_from_file_location("run_local_ui_under_test_store", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_runner_exposes_a_store_option() -> None:
    """A write path unreachable from the documented entry point is not a usable capability."""

    parser = _runner_parser()._build_parser()
    option_strings = {opt for action in parser._actions for opt in action.option_strings}
    assert "--store" in option_strings


def test_the_runner_refuses_a_missing_store_directory_before_binding(
    tmp_path: Path, artifact: Path
) -> None:
    """The store refuses a mistyped path; the runner must refuse it before opening a socket.

    Otherwise the operator would see a working server and only discover the problem on the first
    submission, which is exactly the "looks fine until it matters" failure this project avoids.
    """

    import subprocess
    import sys

    script = Path(__file__).resolve().parents[1] / "scripts" / "run_local_ui.py"
    missing = tmp_path / "absent_store_dir" / "reviews.duckdb"
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--artifact",
            str(artifact),
            "--store",
            str(missing),
            "--port",
            "8798",
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode != 0, "a missing store directory must not start a server"
    assert "does not exist" in result.stderr
    assert "absent_store_dir" in result.stderr, "the error must name the missing directory"
    assert not missing.exists(), "no store may be created at a mistyped path"
