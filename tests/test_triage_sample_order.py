"""Regression tests for Issue #32: the run's bundle sample must not depend on caller order.

The freeze's primary metric is defined over the first ``max_bundles_per_run`` bundles of a
complete run *set*, while ``build_corpus`` sorts by ``(evidence_bundle_id, finding_id)`` before
sliding. Before the fix the orchestrator sliced in caller order, so two runs over a byte-identical
corpus could dissolve into disjoint samples (measured 0/20 overlap). These tests pin the invariant
that the selected set is a function of the bundle *set* alone, matching the corpus entry order.
"""

from __future__ import annotations

import json
import random
from datetime import UTC, datetime, timedelta
from pathlib import Path

from aegistrace.detection.evidence import build_evidence_bundle
from aegistrace.detection.findings import aggregate_findings
from aegistrace.detection.ml import emit_ml_detections
from aegistrace.schemas.events import (
    Ctu13FlowDetails,
    EventProvenance,
    SecurityEvent,
    SourceRecordRef,
    SourceType,
    event_id_for,
)
from aegistrace.schemas.findings import EvidenceBundle
from aegistrace.spine import run_spine
from aegistrace.triage.corpus import build_corpus
from aegistrace.triage.provider import ProviderDescriptor, ProviderKind, StubTriageProvider
from aegistrace.triage.run import run_independent_triage

BASE = datetime(2026, 10, 8, 12, 0, tzinfo=UTC)
CREATED_AT = datetime(2026, 10, 8, 13, 0, tzinfo=UTC)
FREEZE = json.loads(
    (Path(__file__).resolve().parents[1] / "configs" / "triage_provider_freeze.json").read_text(
        encoding="utf-8"
    )
)


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


def _bundle(src_ip: str) -> EvidenceBundle:
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


def _bundles(count: int) -> list[EvidenceBundle]:
    return [_bundle(f"10.0.{i // 250}.{i % 250}") for i in range(count)]


def _stub(name: str, model_id: str) -> StubTriageProvider:
    descriptor = ProviderDescriptor(
        name=name,
        model_id=model_id,
        model_family="offline stub, not a model",
        kind=ProviderKind.OFFLINE_STUB,
        requires_egress=False,
    )
    return StubTriageProvider(descriptor, CREATED_AT)


def _stub_pair():
    return _stub("stub-triage-analyst", "stub-analyst-1"), _stub(
        "stub-expert-adjudicator", "stub-adjudicator-1"
    )


def _selected_ids(bundles: list[EvidenceBundle], budget: int) -> list[str]:
    analyst, adjudicator = _stub_pair()
    freeze = {**FREEZE, "budget": {**FREEZE["budget"], "max_bundles_per_run": budget}}
    run = run_independent_triage(
        bundles=bundles,
        analyst_provider=analyst,
        adjudicator_provider=adjudicator,
        freeze=freeze,
        created_at=CREATED_AT,
    )
    return sorted({str(item.evidence_bundle_id) for item in run.assessments})


def _shuffles(bundles: list[EvidenceBundle], seeds: list[int]) -> list[list[EvidenceBundle]]:
    out: list[list[EvidenceBundle]] = []
    state = random.Random(seeds[0])
    for seed in seeds:
        state.seed(seed)
        perm = list(bundles)
        state.shuffle(perm)
        out.append(perm)
    return out


def test_shuffling_the_bundle_argument_does_not_change_the_selected_set() -> None:
    bundles = _bundles(30)
    original = _selected_ids(bundles, 20)
    shuffled = [*_shuffles(bundles, [7])[0]]

    assert original == _selected_ids(shuffled, 20)
    assert len(original) == 20


def test_selected_set_matches_corpus_entries_prefix_when_bundle_set_matches() -> None:
    bundles = _bundles(30)
    corpus = build_corpus(bundles, created_at=CREATED_AT)
    expected = {str(entry.evidence_bundle_id) for entry in corpus.entries[:20]}

    assert _selected_ids(bundles, 20) == sorted(expected)


def test_selected_set_is_stable_across_several_shuffles() -> None:
    bundles = _bundles(30)
    baseline = _selected_ids(bundles, 20)

    for perm in _shuffles(bundles, [1, 2, 3, 4, 5]):
        assert _selected_ids(perm, 20) == baseline


def test_more_bundles_than_budget_selects_exactly_max_bundles() -> None:
    assert len(_selected_ids(_bundles(25), 10)) == 10


def test_fewer_bundles_than_budget_selects_all() -> None:
    assert _selected_ids(_bundles(5), 10) == sorted(
        str(bundle.evidence_bundle_id) for bundle in _bundles(5)
    )


def test_comparison_and_record_ordering_is_unchanged_by_input_shuffling() -> None:
    bundles = _bundles(30)
    canonical = sorted(
        bundles,
        key=lambda bundle: (str(bundle.evidence_bundle_id), str(bundle.finding_id)),
    )

    def _comparison_ids(bundle_list: list[EvidenceBundle]) -> list[str]:
        analyst, adjudicator = _stub_pair()
        run = run_independent_triage(
            bundles=bundle_list,
            analyst_provider=analyst,
            adjudicator_provider=adjudicator,
            freeze=FREEZE,
            created_at=CREATED_AT,
        )
        return [str(item.evidence_bundle_id) for item in run.comparisons]

    def _record_ids(bundle_list: list[EvidenceBundle]) -> list[str]:
        analyst, adjudicator = _stub_pair()
        records = run_spine(
            bundles=bundle_list,
            analyst_provider=analyst,
            adjudicator_provider=adjudicator,
            freeze=FREEZE,
            created_at=CREATED_AT,
        )
        return [str(record.evidence_bundle_id) for record in records]

    expected_comp = [str(b.evidence_bundle_id) for b in canonical[:20]]
    expected_records = [str(b.evidence_bundle_id) for b in canonical[:20]]

    for perm in _shuffles(bundles, [11, 22, 33]):
        assert _comparison_ids(perm) == expected_comp
        assert _record_ids(perm) == expected_records


def test_corpus_digest_is_stable_across_input_orders() -> None:
    bundles = _bundles(30)
    digests = [
        build_corpus(perm, created_at=CREATED_AT).corpus_digest
        for perm in _shuffles(bundles, [13, 17, 19])
    ]

    assert len(set(digests)) == 1