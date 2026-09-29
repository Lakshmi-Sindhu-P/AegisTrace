"""Tests for evidence-traceable deterministic rules."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from aegistrace.detection.rules import apply_ctu13_rules, rule_predictions, write_detection_json
from aegistrace.ingestion.ctu13 import parse_ctu13_binetflow

FIXTURE_PATH = Path("data/fixtures/ctu13/scenario_11.binetflow")
CREATED_AT = datetime(2026, 9, 21, 2, tzinfo=UTC)


def test_rules_emit_stable_evidence_and_do_not_consult_labels(tmp_path: Path) -> None:
    result = parse_ctu13_binetflow(FIXTURE_PATH, ingested_at=CREATED_AT)
    first = result.events[0]
    details = first.details
    assert details is not None
    updated = details.model_copy(
        update={
            "network_bytes": 20_000_000,
            "session_duration_seconds": 600.0,
            "packet_count": 200,
            "protocol": "icmp",
        }
    )
    event = first.model_copy(update={"details": updated})
    detections = apply_ctu13_rules((event,), created_at=CREATED_AT)

    assert {d.triggered_rules[0] for d in detections} == {
        "high_volume_flow",
        "long_lived_high_volume_flow",
        "icmp_packet_burst",
    }
    assert all(d.event_id == event.event_id for d in detections)
    assert all(d.note.endswith("not proof of compromise or an incident") for d in detections)
    assert all(d.supporting_evidence for d in detections)
    assert rule_predictions((event,), detections) == {event.event_id: True}

    output = tmp_path / "detections.json"
    write_detection_json(detections, output)
    assert "high_volume_flow" in output.read_text()


def test_rules_skip_non_ctu_details() -> None:
    result = parse_ctu13_binetflow(FIXTURE_PATH, ingested_at=CREATED_AT)
    assert apply_ctu13_rules((), created_at=CREATED_AT) == ()
    assert rule_predictions(result.events[:1], ()) == {result.events[0].event_id: False}
