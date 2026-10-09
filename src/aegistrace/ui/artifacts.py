"""Read-only access to already-computed AegisTrace artifacts.

The local UI performs **no detection, no scoring, no ranking and no tier classification**. It reads
artifacts the pipeline already wrote and renders them. This module is the only place the UI touches
the filesystem, and every function here is read-only.

Two honesty rules are encoded here rather than left to the templates, because a template is the
wrong place to enforce them:

1. **A missing or malformed artifact raises; it never becomes an empty view.** An empty screen and
   a broken screen must not look the same. If the file is absent, unreadable, or does not have the
   expected shape, the caller gets an exception naming the problem - not a page showing "no
   findings", which would be a claim about the evidence rather than about the plumbing.

2. **The synthetic flag is read, never inferred from the data.** This artifact declares its own
   provenance through ``providers_configured`` and carries a ``warning`` string. Both are surfaced
   verbatim so no template can soften, truncate or hide them.

Scope note, stated because it would otherwise be easy to overread: the artifact this module reads
today is the offline spine demonstration. Its assessors were mechanical stubs, so it is a
plumbing demonstration and **not a triage result**. ``SpineRecord.synthetic`` is the authoritative
per-record flag in the library, but this summary does not carry it, so ``synthetic`` here is
derived from the artifact's own ``providers_configured`` declaration and is documented as such.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import Field

from aegistrace.schemas.common import FrozenSchema, NonEmptyText

#: Default location of the offline spine demonstration summary, relative to the repository root.
DEFAULT_SPINE_ARTIFACT = "data/evaluation/triage_spine/offline_spine_demo.json"


class ArtifactUnavailableError(RuntimeError):
    """The artifact a view needs is absent, unreadable or malformed.

    Deliberately distinct from "the artifact exists and is empty". A view that cannot read its
    source must say so; it must not render as though the evidence were simply absent.
    """


class SpineRecordView(FrozenSchema):
    """One spine record, reduced to the fields the UI renders.

    Every field is copied from the artifact unchanged. No value is recomputed, and in particular
    ``tier`` is the tier the pipeline assigned - the UI never classifies one.
    """

    spine_id: NonEmptyText
    evidence_bundle_id: NonEmptyText
    finding_id: NonEmptyText
    snapshot_digest: NonEmptyText
    #: The tier the deterministic classifier assigned. "Who is qualified to decide", not a severity.
    tier: NonEmptyText
    machine_checks_passed: bool
    review_count: int = Field(ge=0)

    @property
    def tier_label(self) -> str:
        """A human-readable tier label derived from the stored enum value.

        Presentation only. It maps the stored string to a display label and never re-derives the
        tier itself, so a tier the UI does not recognise is shown as-is rather than guessed at.
        """

        labels = {
            "tier_a_machine_check": "Tier A - machine check",
            "tier_b_guided_junior": "Tier B - guided junior review",
            "tier_c_expert_judgment": "Tier C - expert judgement",
            "tier_d_insufficient_evidence": "Tier D - insufficient evidence",
        }
        return labels.get(self.tier, self.tier)


class SpineArtifactView(FrozenSchema):
    """The whole offline spine summary, as the UI reads it.

    ``synthetic`` is derived from the artifact's own ``providers_configured`` declaration. It is
    ``True`` when the artifact does not declare configured providers, which is the case for the
    offline stub demonstration. ``warning`` is the artifact's own text and is surfaced verbatim.
    """

    source_path: NonEmptyText
    created_at: NonEmptyText
    freeze_version: NonEmptyText
    network_egress: NonEmptyText
    providers_configured: bool
    warning: NonEmptyText | None = None
    bundle_count: int = Field(ge=0)
    record_count: int = Field(ge=0)
    records: tuple[SpineRecordView, ...] = ()

    @property
    def synthetic(self) -> bool:
        """Whether the artifact declares that no real provider produced these assessments."""

        return not self.providers_configured


def _read_json(path: Path) -> dict[str, Any]:
    """Read a JSON object, converting every failure into a named, actionable error."""

    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError as error:
        raise ArtifactUnavailableError(
            f"artifact not found: {path}. The UI reads artifacts the pipeline has already written; "
            f"run the producing script first (see docs/ui_architecture.md section 7)."
        ) from error
    except OSError as error:
        raise ArtifactUnavailableError(f"artifact could not be read: {path}: {error}") from error

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ArtifactUnavailableError(f"artifact is not valid JSON: {path}: {error}") from error

    if not isinstance(parsed, dict):
        raise ArtifactUnavailableError(
            f"artifact must be a JSON object, found {type(parsed).__name__}: {path}"
        )
    return parsed


def load_spine_artifact(path: str | Path) -> SpineArtifactView:
    """Load the offline spine summary from ``path``.

    Raises :class:`ArtifactUnavailableError` if the file is missing, unreadable, not JSON, not an
    object, or missing a field the views need. It never returns a partially-populated view, because
    a view that renders half an artifact as though it were whole is the defect this project keeps
    finding in other guises.
    """

    resolved = Path(path)
    payload = _read_json(resolved)

    raw_records = payload.get("records", [])
    if not isinstance(raw_records, list):
        raise ArtifactUnavailableError(
            f"artifact field 'records' must be a list, "
            f"found {type(raw_records).__name__}: {resolved}"
        )

    records: list[SpineRecordView] = []
    for index, row in enumerate(raw_records):
        if not isinstance(row, dict):
            raise ArtifactUnavailableError(
                f"artifact record {index} must be an object, "
                f"found {type(row).__name__}: {resolved}"
            )
        try:
            records.append(SpineRecordView.model_validate(row))
        except ValueError as error:
            raise ArtifactUnavailableError(
                f"artifact record {index} is not a usable spine record: {error}"
            ) from error

    try:
        return SpineArtifactView(
            source_path=str(resolved),
            created_at=str(payload["created_at"]),
            freeze_version=str(payload["freeze_version"]),
            network_egress=str(payload["network_egress"]),
            providers_configured=bool(payload["providers_configured"]),
            warning=payload.get("warning"),
            bundle_count=int(payload["bundle_count"]),
            record_count=int(payload["record_count"]),
            records=tuple(records),
        )
    except KeyError as error:
        raise ArtifactUnavailableError(
            f"artifact is missing required field {error.args[0]!r}: {resolved}"
        ) from error
    except ValueError as error:
        raise ArtifactUnavailableError(
            f"artifact has an unusable field: {resolved}: {error}"
        ) from error
