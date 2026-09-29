"""Contract tests for canonical security events."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

from aegistrace.schemas.events import (
    GroundTruthLabel,
    NetworkEventDetails,
    SecurityEvent,
    SourceRecordRef,
    event_id_for,
)

FIXTURE_PATH = Path("data/fixtures/events/synthetic_network_event.json")


def fixture_payload() -> dict[str, object]:
    return json.loads(FIXTURE_PATH.read_text())


def test_synthetic_fixture_parses_and_generates_stable_event_id() -> None:
    event = SecurityEvent.model_validate(fixture_payload())

    assert event.event_id == event_id_for(event.source)
    assert event.ground_truth_label is GroundTruthLabel.BENIGN
    assert isinstance(event.details, NetworkEventDetails)
    assert str(event.details.src_ip) == "192.0.2.10"
    assert event.observed_at.tzinfo is UTC


def test_event_id_is_repeatable_for_the_same_source_identity() -> None:
    source = SourceRecordRef.model_validate(fixture_payload()["source"])

    assert event_id_for(source) == event_id_for(source.model_copy())


def test_mismatched_event_id_is_rejected() -> None:
    payload = fixture_payload()
    payload["event_id"] = str(uuid4())

    with pytest.raises(ValidationError, match="stable source identity"):
        SecurityEvent.model_validate(payload)


def test_naive_timestamp_is_rejected() -> None:
    payload = fixture_payload()
    payload["observed_at"] = datetime(2026, 9, 20, 12, 0, 0).isoformat()

    with pytest.raises(ValidationError, match="timezone"):
        SecurityEvent.model_validate(payload)


def test_invalid_port_is_rejected() -> None:
    payload = fixture_payload()
    details = payload["details"]
    assert isinstance(details, dict)
    details["dst_port"] = 70000

    with pytest.raises(ValidationError, match="dst_port"):
        SecurityEvent.model_validate(payload)


def test_known_label_requires_label_source() -> None:
    payload = fixture_payload()
    payload["label_source"] = None

    with pytest.raises(ValidationError, match="label_source"):
        SecurityEvent.model_validate(payload)


def test_unknown_label_cannot_have_attack_category() -> None:
    payload = fixture_payload()
    payload["ground_truth_label"] = "unknown"
    payload["label_source"] = None
    payload["attack_category"] = "c2"

    with pytest.raises(ValidationError, match="attack_category"):
        SecurityEvent.model_validate(payload)


def test_extra_fields_are_rejected() -> None:
    payload = fixture_payload()
    payload["unsupported_conclusion"] = "compromised"

    with pytest.raises(ValidationError, match="unsupported_conclusion"):
        SecurityEvent.model_validate(payload)


def test_missing_source_identity_is_rejected() -> None:
    payload = fixture_payload()
    source = payload["source"]
    assert isinstance(source, dict)
    del source["source_event_id"]

    with pytest.raises(ValidationError, match="source_event_id"):
        SecurityEvent.model_validate(payload)
