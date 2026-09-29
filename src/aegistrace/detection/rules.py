"""Small evidence-traceable rules for CTU-13 network flows."""

from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from uuid import UUID

from aegistrace.schemas.detections import (
    DetectionEvidence,
    DetectionResult,
    DetectionSeverity,
    DetectorType,
    detection_id_for,
)
from aegistrace.schemas.events import Ctu13FlowDetails, SecurityEvent

CTU13_RULE_VERSION = "1.0.0"
HIGH_VOLUME_BYTES = 10_000_000
LONG_LIVED_SECONDS = 300.0
LONG_LIVED_BYTES = 1_000_000
ICMP_BURST_PACKETS = 100
_RULE_NOTE = "deterministic signal; not proof of compromise or an incident"


def _detection(
    event: SecurityEvent,
    *,
    rule_id: str,
    created_at: datetime,
    evidence: tuple[DetectionEvidence, ...],
    note: str,
) -> DetectionResult:
    detector_name = "ctu13_flow_rules"
    return DetectionResult(
        detection_id=detection_id_for(
            event_id=event.event_id,
            detector_name=detector_name,
            detector_version=CTU13_RULE_VERSION,
            rule_id=rule_id,
        ),
        event_id=event.event_id,
        detector_type=DetectorType.RULE,
        detector_name=detector_name,
        detector_version=CTU13_RULE_VERSION,
        severity=DetectionSeverity.MEDIUM,
        score=1.0,
        triggered_rules=(rule_id,),
        supporting_evidence=evidence,
        created_at=created_at,
        note=note,
    )


def apply_ctu13_rules(
    events: Iterable[SecurityEvent], *, created_at: datetime
) -> tuple[DetectionResult, ...]:
    """Apply fixed rules without consulting labels, scenario IDs, or filenames."""

    detections: list[DetectionResult] = []
    for event in events:
        details = event.details
        if not isinstance(details, Ctu13FlowDetails):
            continue
        if details.network_bytes is not None and details.network_bytes >= HIGH_VOLUME_BYTES:
            detections.append(
                _detection(
                    event,
                    rule_id="high_volume_flow",
                    created_at=created_at,
                    evidence=(
                        DetectionEvidence(
                            field="network_bytes",
                            observed_value=details.network_bytes,
                            predicate=f">={HIGH_VOLUME_BYTES}",
                        ),
                    ),
                    note=_RULE_NOTE,
                )
            )
        if (
            details.session_duration_seconds is not None
            and details.network_bytes is not None
            and details.session_duration_seconds >= LONG_LIVED_SECONDS
            and details.network_bytes >= LONG_LIVED_BYTES
        ):
            detections.append(
                _detection(
                    event,
                    rule_id="long_lived_high_volume_flow",
                    created_at=created_at,
                    evidence=(
                        DetectionEvidence(
                            field="session_duration_seconds",
                            observed_value=details.session_duration_seconds,
                            predicate=f">={LONG_LIVED_SECONDS}",
                        ),
                        DetectionEvidence(
                            field="network_bytes",
                            observed_value=details.network_bytes,
                            predicate=f">={LONG_LIVED_BYTES}",
                        ),
                    ),
                    note=_RULE_NOTE,
                )
            )
        if (
            details.protocol is not None
            and details.protocol.casefold() == "icmp"
            and details.packet_count is not None
            and details.packet_count >= ICMP_BURST_PACKETS
        ):
            detections.append(
                _detection(
                    event,
                    rule_id="icmp_packet_burst",
                    created_at=created_at,
                    evidence=(
                        DetectionEvidence(
                            field="packet_count",
                            observed_value=details.packet_count,
                            predicate=f">={ICMP_BURST_PACKETS}",
                        ),
                        DetectionEvidence(
                            field="protocol",
                            observed_value=details.protocol,
                            predicate="casefold == icmp",
                        ),
                    ),
                    note=_RULE_NOTE,
                )
            )
    return tuple(detections)


def rule_predictions(
    events: Iterable[SecurityEvent], detections: Iterable[DetectionResult]
) -> dict[UUID, bool]:
    """Create event-level positive predictions from one or more rule hits."""

    event_ids = {event.event_id for event in events}
    positive_ids = {detection.event_id for detection in detections}
    return {event_id: event_id in positive_ids for event_id in event_ids}


def write_detection_json(detections: Iterable[DetectionResult], output_path: str | Path) -> None:
    """Write stable, evidence-linked rule output for inspection and evaluation."""

    payload = [detection.model_dump(mode="json") for detection in detections]
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
