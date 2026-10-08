"""The offline audit spine: one evidence bundle in, one open review subject out.

This module is the only place where the two independently built halves of the project are joined.
It wires an :class:`~aegistrace.schemas.findings.EvidenceBundle` through two independent assessors,
the agreement engine, tier classification, and a review history — and then it stops.

**The hard invariant.** The spine never appends a review, never decides anything, and never acts.
A record it produces ends with an *empty* review history awaiting a human. There is no autonomous
blocking model in this project; a component that reviewed its own output would violate the central
promise outright, so that rule is enforced in code by :func:`_assert_history_open`, which raises
:class:`RuntimeError` if any review is present on a record the spine is about to return.

The spine also performs no I/O. It calls the triage orchestrator once over the whole bundle set —
the run identity and the budget belong to the run, not to each bundle — and returns an immutable
:class:`SpineRecord` per bundle that reached a full assessment pair and a comparison.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from pydantic import field_validator

from aegistrace.review.history import new_history
from aegistrace.review.tiers import classify_tier
from aegistrace.schemas.common import FrozenSchema, SchemaVersion, Sha256, normalize_utc
from aegistrace.schemas.findings import EvidenceBundle
from aegistrace.schemas.review import ReviewHistory, TierAssignment
from aegistrace.schemas.triage import TriageAssessment, TriageComparison
from aegistrace.triage.provider import TriageProvider
from aegistrace.triage.run import TriageRun, run_independent_triage
from aegistrace.triage.snapshot import snapshot_digest

SPINE_SCHEMA_VERSION = "1.0.0"

_BASE = "https://github.com/Lakshmi-Sindhu-P/AegisTrace"
SPINE_ID_NAMESPACE = uuid5(NAMESPACE_URL, f"{_BASE}/spine-records/v1")


class SpineRecord(FrozenSchema):
    """One auditable path from evidence to an *unreviewed* tier assignment."""

    schema_version: SchemaVersion = SPINE_SCHEMA_VERSION
    spine_id: UUID
    created_at: datetime
    evidence_bundle_id: UUID
    finding_id: UUID
    snapshot_digest: Sha256
    triage_run: TriageRun
    comparison: TriageComparison
    tier: TierAssignment
    review_history: ReviewHistory
    synthetic: bool

    @field_validator("created_at")
    @classmethod
    def normalize_created_at(cls, value: datetime) -> datetime:
        return normalize_utc(value)


def spine_id_for(
    *, evidence_bundle_id: UUID, run_id: UUID, snapshot_digest: str
) -> UUID:
    """Derive a stable spine identity from the bundle, the run, and the snapshot digest."""

    return uuid5(
        SPINE_ID_NAMESPACE,
        f"{evidence_bundle_id}:{run_id}:{snapshot_digest}",
    )


def _assert_history_open(record: SpineRecord) -> None:
    """Refuse, loudly, any spine record that already carries a review.

    The spine ends at a human. This is executable code rather than a convention so the guarantee
    cannot be lost by a future caller forgetting it.
    """

    if record.review_history.reviews:
        raise RuntimeError(
            "the spine must never append a review: "
            f"record {record.spine_id} carries {len(record.review_history.reviews)} review(s); "
            "a spine record must end with an empty review history awaiting a human"
        )


def _assessment_pair(
    run: TriageRun, evidence_bundle_id: UUID
) -> tuple[TriageAssessment, ...]:
    """Return the two *real* assessments for one bundle, ordered by role for determinism.

    ``AssessmentOutcome`` is a union of an admitted assessment and a preserved failed attempt, so
    the outcomes are filtered to :class:`TriageAssessment` first. A failed side leaves no admissible
    pair, so the bundle produces no record rather than a fabricated one; the failure itself remains
    on the run.
    """

    admitted = tuple(
        outcome
        for outcome in run.assessments
        if isinstance(outcome, TriageAssessment)
        and outcome.evidence_bundle_id == evidence_bundle_id
    )
    return tuple(sorted(admitted, key=lambda item: item.role.value))


def run_spine(
    *,
    bundles: Sequence[EvidenceBundle],
    analyst_provider: TriageProvider,
    adjudicator_provider: TriageProvider,
    freeze: Mapping[str, Any],
    created_at: datetime,
) -> tuple[SpineRecord, ...]:
    """Run the full offline spine over ``bundles`` and return one open record per qualified bundle.

    The triage orchestrator is called exactly once for the whole bundle set. Bundles that did not
    reach both an assessment pair and a comparison — because the run aborted first — are skipped;
    no record is invented for them.
    """

    ordered_bundles = list(bundles)
    run = run_independent_triage(
        bundles=ordered_bundles,
        analyst_provider=analyst_provider,
        adjudicator_provider=adjudicator_provider,
        freeze=freeze,
        created_at=created_at,
    )

    comparisons_by_bundle: dict[UUID, TriageComparison] = {
        comparison.evidence_bundle_id: comparison for comparison in run.comparisons
    }

    records: list[SpineRecord] = []
    for bundle in ordered_bundles:
        comparison = comparisons_by_bundle.get(bundle.evidence_bundle_id)
        assessments = _assessment_pair(run, bundle.evidence_bundle_id)
        if comparison is None or len(assessments) != 2:
            continue

        digest = snapshot_digest(bundle)
        tier = classify_tier(bundle=bundle, comparison=comparison, assessments=assessments)
        record = SpineRecord(
            spine_id=spine_id_for(
                evidence_bundle_id=bundle.evidence_bundle_id,
                run_id=run.run_id,
                snapshot_digest=digest,
            ),
            created_at=created_at,
            evidence_bundle_id=bundle.evidence_bundle_id,
            finding_id=bundle.finding_id,
            snapshot_digest=digest,
            triage_run=run,
            comparison=comparison,
            tier=tier,
            review_history=new_history(comparison.comparison_id),
            synthetic=run.synthetic,
        )
        _assert_history_open(record)
        records.append(record)

    return tuple(records)


__all__ = [
    "SPINE_ID_NAMESPACE",
    "SPINE_SCHEMA_VERSION",
    "SpineRecord",
    "run_spine",
    "spine_id_for",
]
