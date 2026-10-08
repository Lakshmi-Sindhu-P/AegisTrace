"""Permanent non-leakage invariant for the provider snapshot.

The egress audit was originally performed by hand, once. A hand audit is a claim about one
afternoon, not a property of the code. These tests convert it into a property of the code.

The sentinel construction is deliberate. Asserting that the string "Background" is absent would
pass merely because no fixture happened to use it. Instead the fixture writes unique sentinel tokens
into the *raw input events*, and the tests assert that those exact tokens survive into neither the
evidence bundle nor the snapshot. The first version of this file asserted absence directly and was
caught being vacuous: the label was already dropped before the bundle, so absence proved nothing.
The tests below therefore assert the whole chain, raw input included.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta

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
from aegistrace.triage import (
    SNAPSHOT_FIELDS,
    canonical_snapshot_json,
    input_snapshot,
    snapshot_digest,
)

BASE = datetime(2026, 10, 8, 12, 0, tzinfo=UTC)
CREATED_AT = datetime(2026, 10, 8, 13, 0, tzinfo=UTC)

# Values that must never survive into the snapshot. Each is unique to this fixture so that an
# accidental match elsewhere in the payload cannot mask a real leak.
LABEL_SENTINEL = "SENTINEL-LABEL-BOTNET-C2"
PATH_SENTINEL = "data/fixtures/SENTINEL-PATH/scenario_11.binetflow"
SCENARIO_SENTINEL = "SENTINEL-SCENARIO-99"


def _event(offset_seconds: float, src_ip: str) -> SecurityEvent:
    observed_at = BASE + timedelta(seconds=offset_seconds)
    source = SourceRecordRef(
        source_type=SourceType.CTU13,
        source_dataset="CTU-13",
        scenario_id=SCENARIO_SENTINEL,
        dataset_version="1.0.0",
        source_event_id=f"{src_ip}@{offset_seconds}",
        raw_payload_reference=PATH_SENTINEL,
    )
    return SecurityEvent(
        event_id=event_id_for(source),
        source=source,
        observed_at=observed_at,
        ingested_at=observed_at,
        event_type="network_flow",
        provenance=EventProvenance(
            adapter_name="snapshot_leakage_test",
            adapter_version="1.0.0",
            transformation_version="1.0.0",
            processed_at=observed_at,
        ),
        details=Ctu13FlowDetails(
            src_ip=src_ip,
            dst_ip="198.51.100.9",
            dst_port=80,
            protocol="tcp",
            source_label=LABEL_SENTINEL,
        ),
    )


def _events(src_ip: str = "10.0.0.1") -> tuple[SecurityEvent, ...]:
    return tuple(_event(offset, src_ip) for offset in (0.0, 10.0, 20.0))


def _bundle(src_ip: str = "10.0.0.1") -> EvidenceBundle:
    events = _events(src_ip)
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


def test_fixture_really_places_a_label_in_the_raw_input() -> None:
    """Guard against a vacuous suite: the raw events must actually carry label material.

    Without this, every absence assertion below could pass simply because nothing was ever there.
    """

    raw = "".join(event.model_dump_json() for event in _events())

    assert LABEL_SENTINEL in raw
    assert PATH_SENTINEL in raw
    assert SCENARIO_SENTINEL in raw


def test_snapshot_keys_are_exactly_the_evidence_bundle_fields() -> None:
    """An assessor may receive the bundle and nothing else - no added convenience fields."""

    snapshot = input_snapshot(_bundle())

    assert set(snapshot) == set(SNAPSHOT_FIELDS)
    assert set(snapshot) == set(EvidenceBundle.model_fields)


def test_ground_truth_label_stops_at_the_bundle_boundary() -> None:
    """The label is present in the raw input and absent from both the bundle and the snapshot."""

    bundle = _bundle()

    assert LABEL_SENTINEL not in bundle.model_dump_json()
    assert LABEL_SENTINEL not in canonical_snapshot_json(bundle)


def test_raw_payload_reference_and_paths_cannot_travel_through_the_snapshot() -> None:
    """A provider must not learn where the data lives on disk."""

    text = canonical_snapshot_json(_bundle())

    assert PATH_SENTINEL not in text
    assert "SENTINEL-PATH" not in text
    assert ".binetflow" not in text
    assert "raw_payload_reference" not in text


def test_scenario_identity_and_label_field_names_do_not_survive() -> None:
    """The snapshot carries observations, not the curator's bookkeeping about them."""

    text = canonical_snapshot_json(_bundle())

    assert SCENARIO_SENTINEL not in text
    assert "scenario_id" not in text
    assert "source_label" not in text


def test_network_identity_does_survive_and_that_is_intentional() -> None:
    """Host identity is the grouping key, so it must survive. Pinned so removal is a decision.

    If a future change starts stripping addresses, this test fails on purpose: the audit recorded
    addresses as reaching the provider, and that is a governance fact the project must not lose
    silently.
    """

    text = canonical_snapshot_json(_bundle(src_ip="203.0.113.7"))

    assert "203.0.113.7" in text
    assert input_snapshot(_bundle(src_ip="203.0.113.7"))["event_summaries"]


def test_snapshot_is_deterministic_for_identical_input() -> None:
    first = _bundle()
    second = _bundle()
    expected = hashlib.sha256(canonical_snapshot_json(first).encode()).hexdigest()

    assert canonical_snapshot_json(first) == canonical_snapshot_json(second)
    assert snapshot_digest(first) == snapshot_digest(second)
    assert snapshot_digest(first) == expected


def test_snapshot_digest_changes_when_a_snapshot_field_changes() -> None:
    """The digest must be a real content address, not a constant."""

    bundle = _bundle()
    limitations = (*bundle.limitations, "an added limitation")
    mutated = bundle.model_copy(update={"limitations": limitations})

    assert snapshot_digest(bundle) != snapshot_digest(mutated)


def test_snapshot_is_json_round_trippable() -> None:
    snapshot = input_snapshot(_bundle())

    assert json.loads(json.dumps(snapshot, sort_keys=True)) == snapshot
