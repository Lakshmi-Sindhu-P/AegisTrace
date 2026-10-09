"""Contract tests for the local UI application.

These tests are about the *honesty* properties of the UI rather than its layout:

* every route renders without a server error, including when the artifact cannot be read;
* a failure to read the artifact renders a named reason, never an empty page that would read as
  "there is no evidence";
* synthetic data is marked on every page;
* the AI-comparison view does not invent assessors when no comparison exists;
* the human-decision route does not claim to have saved anything, because nothing durable exists to
  save to;
* an unknown record id does not silently show a different case.

The application is built with an explicit artifact path, so no test touches the real artifact.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from aegistrace.ui.app import NAV, create_app

PAGES = [href for href, _ in NAV]

SPINE_ID = "11111111-1111-5111-8111-111111111111"


def _payload(**overrides: Any) -> dict[str, Any]:
    """A valid minimal spine summary. Callers vary one thing at a time."""

    record = {
        "spine_id": SPINE_ID,
        "evidence_bundle_id": "22222222-2222-5222-8222-222222222222",
        "finding_id": "33333333-3333-5333-8333-333333333333",
        "snapshot_digest": "a" * 64,
        "tier": "tier_d_insufficient_evidence",
        "machine_checks_passed": True,
        "review_count": 0,
    }
    payload: dict[str, Any] = {
        "warning": "SYNTHETIC DEMONSTRATION. Mechanical stubs, not models.",
        "providers_configured": False,
        "network_egress": "none",
        "created_at": "2026-10-08T13:00:00+00:00",
        "freeze_version": "1.0.0",
        "bundle_count": 1,
        "record_count": 1,
        "records": [record],
    }
    payload.update(overrides)
    return payload


def _write(tmp_path: Path, payload: dict[str, Any]) -> Path:
    path = tmp_path / "spine.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _client(tmp_path: Path, payload: dict[str, Any] | None = None) -> TestClient:
    path = _write(tmp_path, payload if payload is not None else _payload())
    return TestClient(create_app(artifact_path=path))


# --- routes render -------------------------------------------------------------------------


@pytest.mark.parametrize("page", PAGES)
def test_every_approved_view_renders(tmp_path: Path, page: str) -> None:
    response = _client(tmp_path).get(page)
    assert response.status_code == 200
    assert response.text.strip(), "a rendered page must not be empty"


def test_the_root_redirects_to_findings(tmp_path: Path) -> None:
    response = _client(tmp_path).get("/", follow_redirects=False)
    assert response.status_code in (307, 308)
    assert response.headers["location"] == "/findings"


def test_the_navigation_lists_all_five_views_in_workflow_order(tmp_path: Path) -> None:
    """The order is the investigator workflow, so it is a contract, not a layout detail."""

    text = _client(tmp_path).get("/findings").text
    positions = [text.index(label) for _, label in NAV]
    assert positions == sorted(positions), "navigation must preserve the approved workflow order"


# --- the artifact-unavailable state --------------------------------------------------------


@pytest.mark.parametrize("page", PAGES)
def test_a_missing_artifact_renders_a_named_reason_not_an_empty_page(
    tmp_path: Path, page: str
) -> None:
    """A broken read must not be indistinguishable from "there is no evidence"."""

    client = TestClient(create_app(artifact_path=tmp_path / "absent.json"))
    response = client.get(page)

    assert response.status_code == 200, "a missing artifact must not be a server error"
    lowered = response.text.lower()
    assert "unavailable" in lowered or "could not" in lowered, (
        "the page must say the artifact could not be read"
    )
    assert "absent.json" in response.text, "the reason must name the path that failed"
    # The distinction that matters: it must NOT read as though the evidence were merely empty.
    assert "no findings" not in lowered or "unavailable" in lowered


def test_a_malformed_artifact_also_renders_the_unavailable_state(tmp_path: Path) -> None:
    path = tmp_path / "broken.json"
    path.write_text("{not json", encoding="utf-8")
    response = TestClient(create_app(artifact_path=path)).get("/findings")
    assert response.status_code == 200
    assert "unavailable" in response.text.lower() or "could not" in response.text.lower()


def test_an_empty_but_valid_artifact_is_NOT_the_unavailable_state(tmp_path: Path) -> None:
    """The boundary: zero records is a fact about the evidence, not about the plumbing."""

    payload = _payload(records=[], record_count=0, bundle_count=0)
    response = _client(tmp_path, payload).get("/findings")
    assert response.status_code == 200
    assert "absent.json" not in response.text
    assert "artifact not found" not in response.text.lower()


# --- synthetic marking ---------------------------------------------------------------------


@pytest.mark.parametrize("page", PAGES)
def test_synthetic_data_is_marked_on_every_page(tmp_path: Path, page: str) -> None:
    """Synthetic must be unmissable on every page, and must say what it is NOT.

    The assertion is deliberately on a substring that does not depend on singular/plural wording -
    an earlier version of this test demanded "not experimental results" and failed against a
    template that correctly rendered "NOT an experimental result". The test was wrong, not the
    template.
    """

    response = _client(tmp_path).get(page)
    lowered = response.text.lower()
    assert "synthetic" in lowered, f"{page} must mark synthetic data"
    assert "not an experimental result" in lowered, (
        f"{page} must state that synthetic data is not an experimental result"
    )
    # And the artifact's own warning must be surfaced, not paraphrased away.
    assert "mechanical stubs" in lowered, f"{page} must surface the artifact's own warning verbatim"


@pytest.mark.parametrize("page", PAGES)
def test_a_non_synthetic_artifact_is_not_mislabelled(tmp_path: Path, page: str) -> None:
    """The other direction: the banner must be driven by the flag, not always on."""

    payload = _payload(providers_configured=True, warning=None)
    response = _client(tmp_path, payload).get(page)
    assert response.status_code == 200
    assert "SYNTHETIC DEMONSTRATION" not in response.text


# --- the comparison view does not invent assessors -----------------------------------------


def test_the_comparison_view_states_that_no_assessment_is_available(tmp_path: Path) -> None:
    """No real assessment data exists in this repository, and the page must say so."""

    text = _client(tmp_path).get("/comparison").text.lower()
    assert "not available" in text, "the comparison view must state its own absence"
    for invented in ("triage analyst", "expert adjudicator"):
        assert invented not in text, "no assessor may be invented where none exists"


# --- the write path is visible and honest --------------------------------------------------


def test_the_decision_form_is_present(tmp_path: Path) -> None:
    text = _client(tmp_path).get("/decision").text
    assert "<form" in text.lower(), "the human-decision surface must present a form"
    assert "append-only" in text.lower() or "append only" in text.lower()


def test_submitting_a_decision_does_NOT_claim_to_have_saved_it(tmp_path: Path) -> None:
    """The single most important honesty test here.

    There is no durable store, so the route must refuse rather than fabricate a saved review. A form
    that silently discards a human decision would be the worst failure an evidence-custody tool can
    have.
    """

    response = _client(tmp_path).post(
        "/decision",
        data={"spine_id": SPINE_ID, "decision": "confirm", "notes": "looks benign"},
    )
    assert response.status_code == 200
    lowered = response.text.lower()
    refused = any(
        phrase in lowered for phrase in ("not recorded", "was not saved", "not implemented")
    )
    assert refused, "the response must state that the decision was NOT recorded"
    assert "successfully saved" not in lowered
    assert "review saved" not in lowered


# --- no silent substitution ----------------------------------------------------------------


def test_an_unknown_record_id_does_not_silently_show_a_different_case(tmp_path: Path) -> None:
    """Showing case B when case A was asked for is a substitution, not a fallback."""

    response = _client(tmp_path).get("/provenance?spine_id=99999999-9999-5999-8999-999999999999")
    assert response.status_code == 200
    assert SPINE_ID not in response.text, "a different record must not be shown in its place"


def test_a_known_record_id_is_shown(tmp_path: Path) -> None:
    """The control for the test above: a real id must actually resolve."""

    response = _client(tmp_path).get(f"/provenance?spine_id={SPINE_ID}")
    assert response.status_code == 200
    assert SPINE_ID in response.text


# --- local-only serving --------------------------------------------------------------------


def test_the_ui_extra_is_optional_so_the_library_never_needs_a_server() -> None:
    """The research library must import and run without the UI dependencies present.

    Checked structurally against the declared dependency groups rather than by uninstalling
    anything: `fastapi` must appear ONLY under the optional `ui` extra, never under `dependencies`.
    """

    pyproject = (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text(encoding="utf-8")
    core = pyproject.split("dependencies = [", 1)[1].split("]", 1)[0]
    assert "fastapi" not in core.lower(), "fastapi must not be a core dependency"
    assert "uvicorn" not in core.lower(), "uvicorn must not be a core dependency"
    assert "[project.optional-dependencies]" in pyproject
    ui_extra = pyproject.split("ui = [", 1)[1].split("]", 1)[0]
    assert "fastapi" in ui_extra.lower()


# --- the loopback-only constraint, made structural rather than documented -------------------


def test_the_server_cannot_be_told_to_bind_a_public_interface() -> None:
    """Loopback-only is an approved security constraint, not a default a caller may override.

    Verified structurally so it holds without opening a socket: the runner exposes no `--host`
    argument at all, and its single bind address constant is the loopback address. A documented-only
    constraint is enforced by whoever reads the documentation; this one is enforced by the absence
    of the flag.

    The live behaviour was also verified by hand: with the server running,
    `http://127.0.0.1:<port>/findings` returned 200 while the machine's LAN address was refused.
    """

    import importlib.util

    script = Path(__file__).resolve().parents[1] / "scripts" / "run_local_ui.py"
    spec = importlib.util.spec_from_file_location("run_local_ui_under_test", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.LOOPBACK == "127.0.0.1"

    parser = module._build_parser()
    option_strings = {opt for action in parser._actions for opt in action.option_strings}
    assert "--host" not in option_strings, "the bind host must not be caller-configurable"
    assert not any("host" in opt for opt in option_strings), (
        "no option may let a caller change the bind address"
    )


def test_the_runner_refuses_a_missing_artifact_before_binding(tmp_path: Path) -> None:
    """A server that starts and then shows "unavailable" is worse than one that never starts.

    The operator would believe it is working. So a missing artifact must be a refusal with a
    non-zero exit code and a hint at how to produce the artifact.
    """

    import subprocess
    import sys

    script = Path(__file__).resolve().parents[1] / "scripts" / "run_local_ui.py"
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--artifact",
            str(tmp_path / "absent.json"),
            "--port",
            "8799",
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode != 0, "a missing artifact must not start a server"
    assert "not found" in result.stderr
    assert "run_offline_spine_demo" in result.stderr, "the error must say how to produce it"
