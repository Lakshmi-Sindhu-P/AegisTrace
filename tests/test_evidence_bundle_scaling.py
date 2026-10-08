"""Regression and scaling tests for the evidence bundle batch path.

These tests lock in the fix for the quadratic bundle stage. ``build_evidence_bundles`` builds the
``EvidenceIndex`` once for a whole batch, so the events index is iterated a constant number of times
regardless of how many findings are bundled; the per-finding ``build_evidence_bundle`` shares that
index when one is supplied. This is a performance/contract fix, not a behaviour change, so the tests
also pin down that the on-demand and shared-index paths yield byte-identical bundles.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import pytest

from aegistrace.detection.evidence import (
    EvidenceIndex,
    build_evidence_bundle,
    build_evidence_bundles,
)
from aegistrace.detection.findings import aggregate_findings
from aegistrace.detection.ml import emit_ml_detections
from aegistrace.schemas.detections import DetectionSeverity
from aegistrace.schemas.events import (
    Ctu13FlowDetails,
    EventProvenance,
    GroundTruthLabel,
    SecurityEvent,
    SourceRecordRef,
    SourceType,
    event_id_for,
)
from aegistrace.schemas.findings import Finding

BASE = datetime(2026, 10, 8, 12, 0, tzinfo=UTC)
CREATED_AT = datetime(2026, 10, 8, 13, 0, tzinfo=UTC)
FEATURE_VERSION = "1.1.0"


def _event(*, src_ip: str, offset_seconds: float) -> SecurityEvent:
    """Build one CTU-13-shaped event; each (host, offset) yields a unique identity."""
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
        ground_truth_label=GroundTruthLabel.UNKNOWN,
    )


def _detections(events: Sequence[SecurityEvent]) -> tuple[Any, ...]:
    """Emit an ML detection for every event at a high fixed score."""
    scores = {event.event_id: 0.95 for event in events}
    return emit_ml_detections(
        events,
        scores,
        detector_name="ctu13_phase3_random_forest",
        detector_version="1.0.0",
        model_name="random_forest",
        feature_version=FEATURE_VERSION,
        threshold=0.2,
        created_at=CREATED_AT,
    )


def _multi_host_events() -> tuple[SecurityEvent, ...]:
    """Events across several source hosts, producing several findings."""
    hosts = ("10.0.0.1", "10.0.0.2", "10.0.0.3")
    offsets = (0.0, 10.0, 20.0)
    return tuple(_event(src_ip=host, offset_seconds=o) for host in hosts for o in offsets)


class _CountingSequence(Sequence[Any]):
    """A Sequence that counts how many times it is re-iterated."""

    def __init__(self, items: Sequence[Any]) -> None:
        self._items = tuple(items)
        self.iterations = 0

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self):
        self.iterations += 1
        return iter(self._items)

    def __getitem__(self, index):
        return self._items[index]


def _message(finding: Finding, detections: Any, events: Any) -> str:
    """Capture the exact ValueError message raised for these inputs."""
    with pytest.raises(ValueError) as exc_info:
        build_evidence_bundle(finding, detections, events, created_at=CREATED_AT)
    return str(exc_info.value)


def _dump(bundle: Any) -> str:
    return json.dumps(bundle.model_dump(mode="json"), sort_keys=True)


def test_shared_generator_batch_matches_tuple_batch() -> None:
    """A single-shot generator input must yield the same bundles as materialized tuples."""
    events = _multi_host_events()
    detections = _detections(events)
    findings = aggregate_findings(detections, events, created_at=CREATED_AT)
    assert len(findings) > 1

    from_tuples = build_evidence_bundles(
        findings, detections, events, created_at=CREATED_AT
    )
    from_generators = build_evidence_bundles(
        findings, (d for d in detections), (e for e in events), created_at=CREATED_AT
    )
    assert [_dump(b) for b in from_generators] == [_dump(b) for b in from_tuples]


def test_absent_input_distinct_from_general_no_match() -> None:
    """The empty-input message must not be conflated with a genuine no-match finding."""
    events = _multi_host_events()
    detections = _detections(events)
    finding = aggregate_findings(detections, events, created_at=CREATED_AT)[0]

    # Absent detections input (empty iterable) -> the input itself was empty.
    with pytest.raises(ValueError, match="detections input yielded no detections"):
        build_evidence_bundle(finding, (), events, created_at=CREATED_AT)

    empty_msg = _message(finding, (), events)
    # Genuine no-match: detections exist but none belongs to this finding.
    unrelated = _detections((_event(src_ip="198.51.100.7", offset_seconds=0.0),))
    orphan = Finding(
        finding_id=uuid4(),
        aggregation_version="1.0.0",
        event_ids=(detections[0].event_id,),
        detection_ids=(uuid4(),),
        source_host="198.51.100.99",
        window_start=BASE,
        window_end=CREATED_AT,
        proposed_severity=DetectionSeverity.CRITICAL,
        created_at=CREATED_AT,
        note="no match fixture",
    )
    general_msg = _message(orphan, unrelated, events)
    assert general_msg != empty_msg
    assert "detections input yielded no detections" in empty_msg
    assert general_msg == "finding has no matching detections to bundle"

    # Absent events input is likewise distinct from a genuine event no-match.
    ev_empty = _message(finding, detections, ())
    assert "events input yielded no events" in ev_empty
    mismatched = finding.model_copy(update={"event_ids": (uuid4(),)})
    ev_general = _message(mismatched, detections, events)
    assert ev_general != ev_empty
    assert ev_general == "finding has no matching events to bundle"


def test_events_index_built_once_regardless_of_finding_count() -> None:
    """The regression guard: events iteration is O(1) in the number of findings."""
    events = _multi_host_events()
    detections = _detections(events)
    findings = aggregate_findings(detections, events, created_at=CREATED_AT)
    assert len(findings) >= 3

    for group in (findings[:1], findings):
        counted = _CountingSequence(events)
        build_evidence_bundles(group, detections, counted, created_at=CREATED_AT)
        assert counted.iterations == 1, (
            "events index must be constructed once regardless of finding count; "
            f"got {counted.iterations} iterations for {len(group)} finding(s)"
        )


def test_index_is_shared_across_single_and_batch_paths() -> None:
    """A single finding via the batch index is byte-identical to the on-demand path."""
    events = _multi_host_events()
    detections = _detections(events)
    finding = aggregate_findings(detections, events, created_at=CREATED_AT)[0]

    index = EvidenceIndex.from_inputs(detections, events)
    on_demand = build_evidence_bundle(finding, detections, events, created_at=CREATED_AT)
    shared = build_evidence_bundle(finding, (), (), created_at=CREATED_AT, index=index)
    batched = build_evidence_bundles(
        (finding,), (), (), created_at=CREATED_AT, index=index
    )[0]

    assert _dump(shared) == _dump(on_demand)
    assert _dump(batched) == _dump(on_demand)
    assert shared.evidence_bundle_id == on_demand.evidence_bundle_id
    assert shared.detection_ids == on_demand.detection_ids
    assert shared.event_summaries == on_demand.event_summaries


def test_single_finding_bundle_fields_are_stable() -> None:
    """A single finding still yields identical, well-ordered bundle fields."""
    events = _multi_host_events()
    detections = _detections(events)
    finding = aggregate_findings(detections, events, created_at=CREATED_AT)[0]
    bundle = build_evidence_bundle(finding, detections, events, created_at=CREATED_AT)

    assert set(bundle.detection_ids) == set(finding.detection_ids)
    assert tuple(sorted(bundle.detection_ids, key=str)) == bundle.detection_ids
    assert {s.event_id for s in bundle.event_summaries} == set(finding.event_ids)
    assert bundle.observed_values
    assert bundle.score_references
    assert all(ref.feature_version == FEATURE_VERSION for ref in bundle.score_references)