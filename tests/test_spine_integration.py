"""End-to-end integration tests for the offline audit spine.

These tests defend the property that matters most: the spine joins the triage layer to the review
layer and then *stops*, leaving an empty review history for a human. They also pin determinism and
the governance refusal that keeps the run offline.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from aegistrace import spine as spine_module
from aegistrace.detection.evidence import build_evidence_bundle
from aegistrace.detection.findings import aggregate_findings
from aegistrace.detection.ml import emit_ml_detections
from aegistrace.review.history import append_review, current_review, new_history
from aegistrace.schemas.events import (
    Ctu13FlowDetails,
    EventProvenance,
    SecurityEvent,
    SourceRecordRef,
    SourceType,
    event_id_for,
)
from aegistrace.schemas.findings import EvidenceBundle
from aegistrace.schemas.review import (
    EscalationState,
    HumanReview,
    ReviewDecision,
    ReviewHistory,
    ReviewTier,
    TierAssignment,
)
from aegistrace.schemas.triage import AssessorRole
from aegistrace.spine import run_spine
from aegistrace.triage.provider import (
    ProviderDescriptor,
    ProviderKind,
    ProviderRequest,
    StubTriageProvider,
)
from aegistrace.triage.snapshot import snapshot_digest

REPO_ROOT = Path(__file__).resolve().parents[1]
FREEZE = json.loads(
    (REPO_ROOT / "configs" / "triage_provider_freeze.json").read_text(encoding="utf-8")
)

BASE = datetime(2026, 10, 8, 12, 0, tzinfo=UTC)
CREATED_AT = datetime(2026, 10, 8, 13, 0, tzinfo=UTC)


def _event(offset_seconds: float, src_ip: str) -> SecurityEvent:
    observed_at = BASE + timedelta(seconds=offset_seconds)
    source = SourceRecordRef(
        source_type=SourceType.CTU13,
        source_dataset="CTU-13",
        scenario_id="11",
        dataset_version="1.0.0",
        source_event_id=f"{src_ip}@{offset_seconds}",
        raw_payload_reference="data/fixtures/ctu13/scenario_11.binetflow",
    )
    return SecurityEvent(
        event_id=event_id_for(source),
        source=source,
        observed_at=observed_at,
        ingested_at=observed_at,
        event_type="network_flow",
        provenance=EventProvenance(
            adapter_name="test_fixture",
            adapter_version="1.0.0",
            transformation_version="1.0.0",
            processed_at=observed_at,
        ),
        details=Ctu13FlowDetails(
            src_ip=src_ip,
            dst_ip="198.51.100.9",
            dst_port=80,
            protocol="tcp",
            source_label="flow=Background",
        ),
    )


def _bundle(src_ip: str = "10.0.0.1") -> EvidenceBundle:
    events = tuple(_event(offset, src_ip) for offset in (0.0, 10.0, 20.0))
    scores = {event.event_id: 0.95 for event in events}
    detections = emit_ml_detections(
        events,
        scores,
        detector_name="ctu13_phase3_random_forest",
        detector_version="1.0.0",
        model_name="random_forest",
        feature_version="1.1.0",
        threshold=0.2,
        created_at=CREATED_AT,
    )
    finding = aggregate_findings(detections, events, created_at=CREATED_AT)[0]
    return build_evidence_bundle(finding, detections, events, created_at=CREATED_AT)


def _stub(name: str, model_id: str, created_at: datetime = CREATED_AT) -> StubTriageProvider:
    descriptor = ProviderDescriptor(
        name=name,
        model_id=model_id,
        model_family="offline stub, not a model",
        kind=ProviderKind.OFFLINE_STUB,
        requires_egress=False,
    )
    return StubTriageProvider(descriptor, created_at)


def _run(bundles: tuple[EvidenceBundle, ...], created_at: datetime = CREATED_AT):
    return run_spine(
        bundles=bundles,
        analyst_provider=_stub("stub-triage-analyst", "stub-analyst-1"),
        adjudicator_provider=_stub("stub-expert-adjudicator", "stub-adjudicator-1"),
        freeze=FREEZE,
        created_at=created_at,
    )


class _RemoteProvider:
    """A structurally valid provider whose descriptor would require network egress."""

    def __init__(self) -> None:
        self._descriptor = ProviderDescriptor(
            name="remote-assessor",
            model_id="remote-model",
            model_family="remote",
            kind=ProviderKind.REMOTE,
            requires_egress=True,
        )

    @property
    def descriptor(self) -> ProviderDescriptor:
        return self._descriptor

    def complete(self, request: ProviderRequest) -> object:  # pragma: no cover
        raise AssertionError("a refused remote provider must never be called")


def test_spine_runs_end_to_end_with_one_record_per_bundle() -> None:
    bundles = (_bundle("10.0.0.1"), _bundle("10.0.0.2"))

    records = _run(bundles)

    assert len(records) == len(bundles)
    assert {record.evidence_bundle_id for record in records} == {
        bundle.evidence_bundle_id for bundle in bundles
    }
    finding_by_bundle = {record.evidence_bundle_id: record.finding_id for record in records}
    assert all(
        finding_by_bundle[bundle.evidence_bundle_id] == bundle.finding_id for bundle in bundles
    )

def test_spine_records_offline_run_without_claiming_independence() -> None:
    record = _run((_bundle(),))[0]
    run = record.triage_run

    assert run.analyst_descriptor != run.adjudicator_descriptor
    assert run.independence_established is False
    assert "synthetic offline providers" in run.independence_basis


def test_record_tier_is_a_valid_tier_assignment() -> None:
    record = _run((_bundle(),))[0]

    assert isinstance(record.tier, TierAssignment)
    assert record.tier.tier in set(ReviewTier)
    assert record.tier.reasons
    assert record.tier.machine_checks
    assert all(check.check_name for check in record.tier.machine_checks)


def test_review_history_is_empty_after_a_run() -> None:
    record = _run((_bundle(),))[0]

    assert record.review_history.reviews == ()
    assert current_review(record.review_history) is None


def test_no_spine_record_contains_a_populated_review() -> None:
    records = _run((_bundle("10.0.0.1"), _bundle("10.0.0.2")))

    assert all(record.review_history.reviews == () for record in records)


def test_two_runs_are_deterministic() -> None:
    bundles = (_bundle("10.0.0.1"), _bundle("10.0.0.2"))

    first = _run(bundles)
    second = _run(bundles)

    assert [record.spine_id for record in first] == [record.spine_id for record in second]
    assert [record.tier.tier for record in first] == [record.tier.tier for record in second]


def test_spine_raises_if_a_review_were_present(monkeypatch: pytest.MonkeyPatch) -> None:
    def _pre_reviewed_history(subject_triage_id: UUID) -> ReviewHistory:
        history = new_history(subject_triage_id)
        review = HumanReview(
            review_id=uuid4(),
            subject_triage_id=subject_triage_id,
            subject_role=AssessorRole.TRIAGE_ANALYST,
            reviewer_ref="integration-test",
            tier=ReviewTier.A_MACHINE_CHECK,
            decision=ReviewDecision.CONFIRM,
            notes="a review the spine must never hold",
            reviewed_at=CREATED_AT,
            escalation_state=EscalationState.NONE,
            final_disposition="confirmed",
        )
        return append_review(history, review)

    monkeypatch.setattr(spine_module, "new_history", _pre_reviewed_history)

    with pytest.raises(RuntimeError, match="never append a review"):
        _run((_bundle(),))


def test_snapshot_digest_matches_the_bundle() -> None:
    bundle = _bundle()
    record = _run((bundle,))[0]

    assert record.snapshot_digest == snapshot_digest(bundle)


def test_remote_descriptor_is_refused_under_the_repo_freeze() -> None:
    assert FREEZE["status"] == "BLOCKED_HUMAN"
    remote = _RemoteProvider()

    with pytest.raises(PermissionError, match="requires network egress"):
        run_spine(
            bundles=(_bundle(),),
            analyst_provider=remote,
            adjudicator_provider=remote,
            freeze=FREEZE,
            created_at=CREATED_AT,
        )


def _record_for(records, bundle: EvidenceBundle):
    return next(r for r in records if r.evidence_bundle_id == bundle.evidence_bundle_id)


def test_bundle_order_does_not_change_run_identity() -> None:
    """Issue #20: the same bundle set in any order must yield one run_id."""

    bundle_a = _bundle("10.0.0.1")
    bundle_b = _bundle("10.0.0.2")

    forward = _run((bundle_a, bundle_b))
    reverse = _run((bundle_b, bundle_a))

    assert forward[0].triage_run.run_id == reverse[0].triage_run.run_id


def test_unrelated_bundle_does_not_change_spine_id() -> None:
    """Issue #20: adding an unrelated bundle must not change an existing record's spine_id."""

    bundle_a = _bundle("10.0.0.1")
    bundle_b = _bundle("10.0.0.2")
    bundle_c = _bundle("10.0.0.3")

    under_ab = _record_for(_run((bundle_a, bundle_b)), bundle_a)
    under_abc = _record_for(_run((bundle_a, bundle_b, bundle_c)), bundle_a)
    under_ba = _record_for(_run((bundle_b, bundle_a)), bundle_a)

    assert under_ab.spine_id == under_abc.spine_id == under_ba.spine_id


def test_genuinely_different_bundles_get_different_spine_ids() -> None:
    records = _run((_bundle("10.0.0.1"), _bundle("10.0.0.2")))

    assert len({record.spine_id for record in records}) == len(records)


def test_run_id_is_still_present_on_every_record() -> None:
    records = _run((_bundle("10.0.0.1"), _bundle("10.0.0.2")))

    assert all(record.triage_run.run_id for record in records)
    assert len({record.triage_run.run_id for record in records}) == 1

