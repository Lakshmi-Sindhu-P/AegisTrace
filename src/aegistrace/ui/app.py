"""The local AegisTrace UI: a read-only investigation instrument, served on 127.0.0.1 only.

This module builds the FastAPI application. It is deliberately thin. It does **no detection, no
scoring, no ranking and no tier classification** - those are library responsibilities performed
upstream, and in the case of tier assignment by :func:`aegistrace.review.tiers.classify_tier`. Every
route here reads an artifact the pipeline already wrote and renders it.

The one state-changing operation the UI performs is appending a ``HumanReview``. It is deliberately
conditional: when ``create_app`` is given a ``store_path`` it appends to that durable append-only
store; when no store is supplied it keeps the old, honest behaviour of refusing to record at all
rather than pretending to save anything. The decision form therefore either records durably or
returns an explicit "not recorded" page - it never fabricates a saved review. A form that silently
discarded a human decision would be the worst possible failure for an evidence-custody tool.

Serving constraints, enforced in :mod:`scripts.run_local_ui` rather than here because they are
properties of the socket, not of the app: bind ``127.0.0.1`` only, no external requests, no
telemetry, all assets local.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from aegistrace.schemas.review import (
    EscalationState,
    HumanReview,
    ReviewDecision,
    ReviewTier,
    review_id_for,
)
from aegistrace.schemas.triage import AssessorRole
from aegistrace.storage.reviews import ReviewStore, ReviewStoreError
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

#: The write of this instrument is appending a ``HumanReview`` and nothing else. ``reviewed_at`` is
#: not a field the human fills in: it is the recording time, set to the moment of submission and
#: stated on the page rather than hidden. The id is content-derived via
#: :func:`~aegistrace.schemas.review.review_id_for`, never a random uuid, so the schema's identity
#: validator (which recomputes the id and refuses a mismatch) accepts what we write.
_REVIEWED_AT_NOTE = (
    "reviewed_at is set to the server's submission time in UTC; it is the recording time, "
    "not a field the human fills in."
)

#: Notes are ``NonEmptyText`` in the schema. An empty notes box is recorded as an explicit, visible
#: placeholder rather than rejected - so every review carries an honest note value.
_EMPTY_NOTES = "(no notes provided)"

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


def _build_review(
    *,
    subject_triage_id: str,
    subject_role: str,
    reviewer_ref: str,
    tier: str,
    decision: str,
    notes: str,
    escalation_state: str,
    final_disposition: str,
    supersedes_review_id: str,
    reviewed_at: datetime,
) -> HumanReview:
    """Build a ``HumanReview`` from submitted form strings.

    The subject triage id is the spine record id, which this form submits as ``spine_id``. ``tier``
    is the tier the human actually conducted - the UI performs no tier classification. ``notes`` is
    coerced to a visible placeholder when left empty because the schema requires non-empty notes.

    The enum-valued fields are coerced through their own enum constructors rather than handed to the
    model as raw strings. That keeps mypy honest about the types, and it turns an unrecognised value
    into a plain ``ValueError`` naming the field, which the route already reports as an explicit
    failure instead of a 500.

    Raises ``ValueError`` if any field is unusable - a malformed ``UUID``, an unknown enum member,
    or a pydantic ``ValidationError`` (which subclasses ``ValueError``), including a
    ``review_id_for`` mismatch.
    """

    subject = UUID(subject_triage_id.strip())
    supersedes: UUID | None = (
        UUID(supersedes_review_id.strip()) if supersedes_review_id.strip() else None
    )

    role = AssessorRole(subject_role.strip())
    conducted_tier = ReviewTier(tier.strip())
    disposition = ReviewDecision(decision.strip())
    escalation = EscalationState(escalation_state.strip())

    # The id is derived from the substance of the judgment, never random. The schema validator
    # recomputes this exact value and refuses a mismatch, so our derivation must use the same
    # strings the model will coerce. ``StrEnum`` members are ``str``, so they serialize identically.
    review_id = review_id_for(
        subject_triage_id=subject,
        subject_role=role,
        reviewer_ref=reviewer_ref.strip(),
        decision=disposition,
        final_disposition=final_disposition.strip(),
        supersedes_review_id=supersedes,
    )
    return HumanReview(
        review_id=review_id,
        subject_triage_id=subject,
        subject_role=role,
        reviewer_ref=reviewer_ref.strip(),
        tier=conducted_tier,
        decision=disposition,
        notes=notes.strip() or _EMPTY_NOTES,
        reviewed_at=reviewed_at,
        escalation_state=escalation,
        final_disposition=final_disposition.strip(),
        supersedes_review_id=supersedes,
    )


def create_app(
    *, artifact_path: str | Path | None = None, store_path: str | Path | None = None
) -> FastAPI:
    """Build the application, reading evidence from ``artifact_path`` and writing to ``store_path``.

    ``artifact_path`` defaults to :data:`~aegistrace.ui.artifacts.DEFAULT_SPINE_ARTIFACT` relative
    to the repository root. A failure to read it is NOT raised out of the routes: it is captured
    and rendered as an explicit "artifact unavailable" panel, because a 500 tells an analyst
    nothing while a named reason tells them which script to run.

    ``store_path`` is the durable, append-only ``HumanReview`` store (see
    :class:`aegistrace.storage.reviews.ReviewStore`). When supplied, ``POST /decision`` records a
    review there and renders the persisted result. When ``None`` (the default), the route keeps its
    deliberate "not recorded" behaviour: it never pretends to have saved a decision it did not save.
    The evidence artifact is always read-only; the only write anywhere is appending a review, and a
    missing ``store_path`` parent directory is surfaced as an explicit failure rather than a 500.
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
        context["recorded"] = False
        context["recorded_review"] = None
        context["recorded_history"] = None
        context["store_error"] = None
        context["can_record"] = store_path is not None
        context["reviewed_at_note"] = _REVIEWED_AT_NOTE
        return templates.TemplateResponse(request, "decision.html", context)

    @app.post("/decision", response_class=HTMLResponse)
    def submit_decision(
        request: Request,
        spine_id: str = Form(...),
        decision: str = Form(...),
        notes: str = Form(""),
        subject_role: str = Form(""),
        reviewer_ref: str = Form(""),
        tier: str = Form(""),
        escalation_state: str = Form("none"),
        final_disposition: str = Form(""),
        supersedes_review_id: str = Form(""),
    ) -> HTMLResponse:
        """Record the submission durably, or refuse visibly - never claim a save that did not occur.

        With a ``store_path`` configured this appends a ``HumanReview`` and then re-reads the
        history from the store, so the page shows durable state rather than an echo of the form.
        Without one it keeps the original behaviour: acknowledge the submission and state that
        nothing was saved.

        The failure messages distinguish two genuinely different situations, because collapsing them
        would be the dishonest move: an append that failed (nothing was written, the transaction
        rolled back) versus an append that succeeded but whose read-back failed (something WAS
        written and the instrument cannot confirm its shape). Telling a reviewer "nothing was saved"
        in the second case would be false.
        """

        context = _context(request, "Human decision", "/decision")
        context["record"] = _selected_record(context["artifact"], spine_id or None)
        context["submitted"] = True
        context["submitted_decision"] = decision
        context["submitted_notes"] = notes
        context["submitted_spine_id"] = spine_id
        context["recorded"] = False
        context["recorded_review"] = None
        context["recorded_history"] = None
        context["store_error"] = None
        context["can_record"] = store_path is not None
        context["reviewed_at_note"] = _REVIEWED_AT_NOTE

        if store_path is None:
            # Unchanged, honest refusal: there is no durable store to append to.
            return templates.TemplateResponse(request, "decision.html", context)

        empty = [
            name
            for name, value in (
                ("reviewer_ref", reviewer_ref),
                ("tier", tier),
                ("final_disposition", final_disposition),
            )
            if not value.strip()
        ]
        if empty:
            context["store_error"] = (
                "Nothing was written. These fields are required to record a review and were "
                "empty: " + ", ".join(empty) + "."
            )
            return templates.TemplateResponse(request, "decision.html", context)

        try:
            review = _build_review(
                subject_triage_id=spine_id,
                subject_role=subject_role.strip() or "triage_analyst",
                reviewer_ref=reviewer_ref,
                tier=tier,
                decision=decision,
                notes=notes,
                escalation_state=escalation_state,
                final_disposition=final_disposition,
                supersedes_review_id=supersedes_review_id,
                reviewed_at=datetime.now(UTC),
            )
        except ValueError as error:
            # ``ValueError`` covers both a malformed UUID and a pydantic ``ValidationError``, which
            # subclasses it. Nothing has touched the store yet, so the claim is safe.
            context["store_error"] = (
                f"Nothing was written. The submitted review is not valid: {error}"
            )
            return templates.TemplateResponse(request, "decision.html", context)

        try:
            store = ReviewStore.open(store_path)
        except ReviewStoreError as error:
            context["store_error"] = f"Nothing was written. {error}"
            return templates.TemplateResponse(request, "decision.html", context)

        with store:
            try:
                store.append_review(review)
            except ReviewStoreError as error:
                context["store_error"] = (
                    f"Nothing was written. The review was refused by the store: {error}"
                )
                return templates.TemplateResponse(request, "decision.html", context)

            try:
                history = store.load_history(review.subject_triage_id)
            except ReviewStoreError as error:
                # The append committed. Saying "nothing was written" here would be false.
                context["recorded"] = True
                context["store_error"] = (
                    "The review WAS appended, but the store could not read the history back to "
                    f"confirm it: {error} Re-open the store to inspect the durable state before "
                    "relying on this record."
                )
                return templates.TemplateResponse(request, "decision.html", context)

        context["recorded"] = True
        context["recorded_review"] = history.reviews[-1]
        context["recorded_history"] = history
        return templates.TemplateResponse(request, "decision.html", context)

    return app
