"""Tests for the deterministic, label-free triage corpus.

The corpus is the frozen input set for a triage run, so the properties that matter are determinism
(same bundles, same digest, any order) and label isolation (a research label cannot reach it).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest

from aegistrace.detection.evidence import build_evidence_bundle
from aegistrace.detection.findings import aggregate_findings
from aegistrace.detection.ml import emit_ml_detections
from aegistrace.schemas.events import (
    Ctu13FlowDetails,
    EventProvenance,
    GroundTruthLabel,
    SecurityEvent,
    SourceRecordRef,
    SourceType,
    event_id_for,
)
from aegistrace.schemas.findings import EvidenceBundle
from aegistrace.triage.corpus import CorpusEntry, build_corpus, write_corpus

BASE = datetime(2026, 10, 8, 12, 0, tzinfo=UTC)
CREATED_AT = datetime(2026, 10, 8, 13, 0, tzinfo=UTC)


def _event(
    offset_seconds: float, src_ip: str, label: GroundTruthLabel = GroundTruthLabel.UNKNOWN
) -> SecurityEvent:
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
        ground_truth_label=label,
        label_source=None if label is GroundTruthLabel.UNKNOWN else "CTU-13 scenario label",
    )


def _bundle(src_ip: str, label: GroundTruthLabel = GroundTruthLabel.UNKNOWN) -> EvidenceBundle:
    events = tuple(_event(offset, src_ip, label) for offset in (0.0, 10.0, 20.0))
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


def test_corpus_digest_is_order_independent() -> None:
    bundles = (_bundle("10.0.0.1"), _bundle("10.0.0.2"), _bundle("10.0.0.3"))

    forward = build_corpus(bundles, created_at=CREATED_AT)
    backward = build_corpus(tuple(reversed(bundles)), created_at=CREATED_AT)

    assert forward.corpus_digest == backward.corpus_digest
    assert len(forward.entries) == 3
    assert [str(entry.evidence_bundle_id) for entry in forward.entries] == [
        str(entry.evidence_bundle_id) for entry in backward.entries
    ]


def test_corpus_digest_ignores_created_at() -> None:
    bundles = (_bundle("10.0.0.1"),)
    earlier = build_corpus(bundles, created_at=CREATED_AT)
    later = build_corpus(bundles, created_at=CREATED_AT + timedelta(days=1))

    assert earlier.corpus_digest == later.corpus_digest


def test_corpus_digest_changes_with_version() -> None:
    bundles = (_bundle("10.0.0.1"),)
    first = build_corpus(bundles, created_at=CREATED_AT, corpus_version="1.0.0")
    second = build_corpus(bundles, created_at=CREATED_AT, corpus_version="1.0.1")

    assert first.corpus_digest != second.corpus_digest


def test_corpus_rejects_empty_input() -> None:
    with pytest.raises(ValueError, match="empty bundle sequence"):
        build_corpus([], created_at=CREATED_AT)
    with pytest.raises(ValueError, match="empty bundle sequence"):
        build_corpus(iter(()), created_at=CREATED_AT)


def test_corpus_ignores_research_labels() -> None:
    benign = build_corpus((_bundle("10.0.0.1", GroundTruthLabel.BENIGN),), created_at=CREATED_AT)
    malicious = build_corpus(
        (_bundle("10.0.0.1", GroundTruthLabel.MALICIOUS),), created_at=CREATED_AT
    )

    assert benign.corpus_digest == malicious.corpus_digest


def test_corpus_entries_expose_no_label_or_model_field() -> None:
    assert set(CorpusEntry.model_fields) == {
        "evidence_bundle_id",
        "finding_id",
        "snapshot_digest",
        "event_count",
        "detection_count",
    }


def test_write_corpus_round_trips_canonical_json(tmp_path) -> None:
    corpus = build_corpus((_bundle("10.0.0.1"),), created_at=CREATED_AT)
    destination = write_corpus(corpus, tmp_path / "nested" / "corpus.json")

    payload = json.loads(destination.read_text(encoding="utf-8"))
    assert payload["corpus_digest"] == corpus.corpus_digest
    assert payload["corpus_version"] == "1.0.0"
    assert len(payload["entries"]) == 1
    assert destination.read_text(encoding="utf-8").endswith("\n")
