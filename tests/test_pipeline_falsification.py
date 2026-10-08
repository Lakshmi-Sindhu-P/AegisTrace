"""Falsification of never-executed pipeline guards.

Each test here executes a guard against the exact input it exists to reject. A ``raise`` that the
suite has never observed firing is an untested claim: it asserts that bad input is refused, but no
run has ever demonstrated the refusal. These tests force the worst case through the guard and
require the guard's own message, so a pass cannot be borrowed from an unrelated error.

Pure helpers (``_parse_timestamp``, ``_event_from_record``, ``_event_to_row`` and the pydantic
``require_feature_count`` classmethods) are called directly, because their public wrappers either
validate before the guard runs or do not expose the condition.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from aegistrace.detection.evidence import build_evidence_bundle
from aegistrace.detection.ml import emit_ml_detections
from aegistrace.features.behavioral import (
    BEHAVIORAL_FEATURE_NAMES,
    BehavioralFeatureDataset,
    BehavioralFeatureRecord,
)
from aegistrace.features.causal import (
    CAUSAL_FEATURE_NAMES,
    CausalFeatureDataset,
    CausalFeatureRecord,
    build_ctu13_causal_features,
)
from aegistrace.features.network import FEATURE_NAMES, FeatureRecord, build_ctu13_features
from aegistrace.ingestion.ctu13 import _event_to_row as ctu13_event_to_row
from aegistrace.ingestion.ctu13 import _parse_timestamp, parse_ctu13_binetflow
from aegistrace.ingestion.iot23 import _event_from_record as iot23_event_from_record
from aegistrace.ingestion.iot23 import _event_to_row as iot23_event_to_row
from aegistrace.schemas.detections import DetectionSeverity
from aegistrace.schemas.findings import Finding

FIXTURE_PATH = "data/fixtures/ctu13/scenario_11.binetflow"
BASE = datetime(2026, 10, 8, 12, 0, tzinfo=UTC)
CREATED_AT = datetime(2026, 10, 8, 13, 0, tzinfo=UTC)


def _fixture_events():
    return parse_ctu13_binetflow(FIXTURE_PATH, ingested_at=BASE).events


def test_ml_emit_rejects_threshold_outside_unit_interval() -> None:
    with pytest.raises(ValueError, match=r"threshold must be within \[0, 1\]"):
        emit_ml_detections(
            (),
            {},
            detector_name="detector",
            detector_version="1.0.0",
            model_name="model",
            feature_version="1.0.0",
            threshold=1.5,
            created_at=CREATED_AT,
        )


def test_evidence_bundle_reaches_missing_events_guard_when_detections_match() -> None:
    events = _fixture_events()
    detections = emit_ml_detections(
        events,
        {event.event_id: 0.95 for event in events},
        detector_name="detector",
        detector_version="1.0.0",
        model_name="model",
        feature_version="1.0.0",
        threshold=0.5,
        created_at=CREATED_AT,
    )
    assert detections
    finding = Finding(
        finding_id=uuid4(),
        aggregation_version="1.0.0",
        # A different event identity: detection ids match, event ids match none of ``events``.
        event_ids=(uuid4(),),
        detection_ids=tuple(detection.detection_id for detection in detections),
        source_host="198.51.100.10",
        window_start=BASE,
        window_end=CREATED_AT,
        proposed_severity=DetectionSeverity.CRITICAL,
        created_at=CREATED_AT,
        note="falsification fixture",
    )

    with pytest.raises(ValueError, match="finding has no matching events to bundle"):
        build_evidence_bundle(finding, detections, events, created_at=CREATED_AT)


def test_network_feature_record_rejects_wrong_value_count() -> None:
    with pytest.raises(ValueError, match=f"expected {len(FEATURE_NAMES)} feature values"):
        FeatureRecord.require_feature_count((1.0,))


def test_network_features_reject_missing_scenario_id() -> None:
    events = _fixture_events()
    orphaned = events[0].model_copy(
        update={"source": events[0].source.model_copy(update={"scenario_id": None})}
    )
    with pytest.raises(ValueError, match="CTU-13 feature extraction requires scenario_id"):
        build_ctu13_features((orphaned,))


def test_behavioral_feature_record_rejects_wrong_value_count() -> None:
    message = f"expected {len(BEHAVIORAL_FEATURE_NAMES)} feature values"
    with pytest.raises(ValueError, match=message):
        BehavioralFeatureRecord.require_feature_count((1.0,))


def test_behavioral_dataset_rejects_noncanonical_feature_order() -> None:
    with pytest.raises(ValueError, match="feature_names must match the versioned canonical order"):
        BehavioralFeatureDataset(feature_names=("label",), records=())


def test_causal_feature_record_rejects_wrong_value_count() -> None:
    message = f"expected {len(CAUSAL_FEATURE_NAMES)} feature values"
    with pytest.raises(ValueError, match=message):
        CausalFeatureRecord.require_feature_count((1.0,))


def test_causal_dataset_rejects_noncanonical_feature_order() -> None:
    with pytest.raises(ValueError, match="feature_names must match the versioned causal order"):
        CausalFeatureDataset(feature_names=("label",), records=())


def test_causal_features_reject_mixed_scenarios() -> None:
    events = _fixture_events()
    mixed = (
        *events,
        events[0].model_copy(
            update={"source": events[0].source.model_copy(update={"scenario_id": "other"})}
        ),
    )
    with pytest.raises(ValueError, match="causal features require one scenario per dataset"):
        build_ctu13_causal_features(mixed)


def test_ctu13_parse_timestamp_rejects_missing_start_time() -> None:
    with pytest.raises(ValueError, match="missing StartTime"):
        _parse_timestamp(None, UTC)


def test_ctu13_normalized_row_rejects_non_ctu13_details() -> None:
    event = _fixture_events()[0].model_copy(update={"details": None})
    with pytest.raises(TypeError, match="CTU-13 normalized output requires CTU-13 flow details"):
        ctu13_event_to_row(event)


def test_iot23_event_from_record_rejects_missing_ts() -> None:
    with pytest.raises(ValueError, match="missing ts"):
        iot23_event_from_record(
            {"uid": "no-timestamp"},
            line_number=1,
            raw_reference="conn.log",
            raw_checksum="0" * 64,
            dataset_version="1.0.0",
            ingested_at=BASE,
        )


def test_iot23_normalized_row_rejects_non_network_details() -> None:
    event = _fixture_events()[0]
    with pytest.raises(TypeError, match="IoT-23 normalized output requires network details"):
        iot23_event_to_row(event)
