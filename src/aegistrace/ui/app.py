"""The local AegisTrace UI: a read-only investigation instrument, served on 127.0.0.1 only.

This module builds the FastAPI application. It is deliberately thin. It does **no detection, no
scoring, no ranking and no tier classification** - those are library responsibilities performed
upstream, and in the case of tier assignment by :func:`aegistrace.review.tiers.classify_tier`. Every
route here reads an artifact the pipeline already wrote and renders it.

The one state-changing operation the finished UI will perform is appending a ``HumanReview``. That
is NOT wired yet, and the reason is concrete rather than an oversight: appending a review requires a
durable store to append to, and no persistence layer exists (see ``docs/ui_architecture.md``
section 7). The decision route therefore presents the form and returns an explicit
"not implemented" page rather than pretending to save anything. A form that silently discards a
human decision would be the worst possible failure for an evidence-custody tool.

Serving constraints, enforced in :mod:`scripts.run_local_ui` rather than here because they are
properties of the socket, not of the app: bind ``127.0.0.1`` only, no external requests, no
telemetry, all assets local.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from aegistrace.ui.artifacts import (
    DEFAULT_SPINE_ARTIFACT,
    ArtifactUnavailableError,
    SpineArtifactView,
    SpineRecordView,
    load_spine_artifact,
)

_HERE = Path(__file__).resolve().parent
TEMPLATES_DIR = _HERE / "templates"
STATIC_DIR = _HERE / "static"

#: The five approved views, in the owner's investigator order. The order is the workflow, and the
#: navigation renders it in that order because the sequence is part of the design.
NAV: tuple[tuple[str, str], ...] = (
    ("/findings", "Findings"),
    ("/provenance", "Evidence"),
    ("/comparison", "AI comparison"),
    ("/requirements", "Review requirements"),
    ("/decision", "Human decision"),
)


def _nav_items(current: str) -> list[dict[str, Any]]:
    return [
        {"href": href, "label": label, "current": href == current} for href, label in NAV
    ]


def _selected_record(
    artifact: SpineArtifactView | None, spine_id: str | None
) -> SpineRecordView | None:
    """Pick the record a single-record view should show.

    An unknown ``spine_id`` returns ``None`` rather than falling back to the first record: silently
    showing a *different* case than the one asked for is exactly the kind of substitution this
    project treats as a defect. The template renders an explicit "no such record" state.
    """

    if artifact is None or not artifact.records:
        return None
    if spine_id is None:
        return artifact.records[0]
    for record in artifact.records:
        if record.spine_id == spine_id:
            return record
    return None


def create_app(*, artifact_path: str | Path | None = None) -> FastAPI:
    """Build the application, reading from ``artifact_path``.

    ``artifact_path`` defaults to :data:`~aegistrace.ui.artifacts.DEFAULT_SPINE_ARTIFACT` relative
    to the repository root. A failure to read it is NOT raised out of the routes: it is captured
    and rendered as an explicit "artifact unavailable" panel, because a 500 tells an analyst
    nothing while a named reason tells them which script to run.
    """

    source = Path(artifact_path) if artifact_path is not None else Path(DEFAULT_SPINE_ARTIFACT)

    app = FastAPI(
        title="AegisTrace local UI",
        description="Read-only local investigation instrument. Synthetic data is labelled.",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
    if STATIC_DIR.is_dir():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    def _context(request: Request, page_title: str, current: str, **extra: Any) -> dict[str, Any]:
        """Assemble a page context, capturing a read failure instead of raising it."""

        artifact: SpineArtifactView | None = None
        error: str | None = None
        try:
            artifact = load_spine_artifact(source)
        except ArtifactUnavailableError as exc:
            error = str(exc)
        return {
            "request": request,
            "page_title": page_title,
            "artifact": artifact,
            "artifact_error": error,
            "nav_items": _nav_items(current),
            **extra,
        }

    @app.get("/", include_in_schema=False)
    def index() -> RedirectResponse:
        return RedirectResponse(url="/findings", status_code=307)

    @app.get("/findings", response_class=HTMLResponse)
    def findings(request: Request) -> HTMLResponse:
        context = _context(request, "Findings", "/findings")
        artifact = context["artifact"]
        context["records"] = artifact.records if artifact is not None else ()
        return templates.TemplateResponse(request, "findings.html", context)

    @app.get("/provenance", response_class=HTMLResponse)
    def provenance(request: Request, spine_id: str | None = None) -> HTMLResponse:
        context = _context(request, "Evidence", "/provenance")
        context["record"] = _selected_record(context["artifact"], spine_id)
        context["requested_spine_id"] = spine_id
        return templates.TemplateResponse(request, "provenance.html", context)

    @app.get("/comparison", response_class=HTMLResponse)
    def comparison(request: Request, spine_id: str | None = None) -> HTMLResponse:
        context = _context(request, "AI comparison", "/comparison")
        context["record"] = _selected_record(context["artifact"], spine_id)
        # Always False today, and that is the honest answer rather than a placeholder: the spine
        # summary this UI reads carries no assessment pair and no comparison record, and no real
        # (non-synthetic) assessment run exists - the provider freeze is BLOCKED_HUMAN. The template
        # renders an explicit "not available" state. It must never invent two assessors.
        context["comparison_available"] = False
        return templates.TemplateResponse(request, "comparison.html", context)

    @app.get("/requirements", response_class=HTMLResponse)
    def requirements(request: Request, spine_id: str | None = None) -> HTMLResponse:
        context = _context(request, "Review requirements", "/requirements")
        context["record"] = _selected_record(context["artifact"], spine_id)
        return templates.TemplateResponse(request, "requirements.html", context)

    @app.get("/decision", response_class=HTMLResponse)
    def decision(request: Request, spine_id: str | None = None) -> HTMLResponse:
        context = _context(request, "Human decision", "/decision")
        context["record"] = _selected_record(context["artifact"], spine_id)
        context["submitted"] = False
        return templates.TemplateResponse(request, "decision.html", context)

    @app.post("/decision", response_class=HTMLResponse)
    def submit_decision(
        request: Request,
        spine_id: str = Form(...),
        decision: str = Form(...),
        notes: str = Form(""),
    ) -> HTMLResponse:
        """Acknowledge the submission WITHOUT saving it, and say so plainly.

        This route exists so the write path is visible and testable rather than implied. It does not
        append a review, because there is nothing durable to append to. Returning a success page
        here would be a fabricated capability, so it returns the opposite: an explicit statement
        that the decision was NOT recorded.
        """

        context = _context(request, "Human decision", "/decision")
        context["record"] = _selected_record(context["artifact"], spine_id or None)
        context["submitted"] = True
        context["submitted_decision"] = decision
        context["submitted_notes"] = notes
        context["submitted_spine_id"] = spine_id
        return templates.TemplateResponse(request, "decision.html", context)

    return app
