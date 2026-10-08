"""Deterministic, label-free aggregation of detections into findings.

**Grouping rule.** Detections are grouped first by source host, then chained into bursts by
observed-time gap: a detection starts a new finding when it occurs more than ``window_seconds``
after the previous detection from the same host.

**Why a gap rule rather than fixed calendar buckets.** With fixed buckets, grouping is an artefact
of where the grid boundary happens to fall, so nudging the window silently reshapes findings. A gap
rule depends only on how far apart events actually are. The grouping is therefore identical for any
``window_seconds`` in the open interval (largest within-burst gap, smallest between-burst gap) —
which is exactly the stability the acceptance criteria demand, and it is directly testable.

**What this module may not read.** ``SecurityEvent.ground_truth_label``, any later-stage model
output, or any LLM conclusion. Grouping that consulted a research label would make the resulting
finding circular: the evidence for the grouping would be the answer we are trying to evaluate.
Grouping therefore uses operational fields only — source host, time, destination, and port.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from datetime import datetime
from uuid import UUID

from aegistrace.schemas.detections import DetectionResult, DetectionSeverity
from aegistrace.schemas.events import SecurityEvent
from aegistrace.schemas.findings import Finding, FindingStatus, finding_id_for

FINDING_AGGREGATION_VERSION = "1.0.0"
DEFAULT_WINDOW_SECONDS = 300.0
UNKNOWN_SOURCE_HOST = "unknown"
_AGGREGATION_NOTE = (
    "deterministic label-free aggregation; grouping uses source host, time, destination, and port"
)

_SEVERITY_RANK: dict[DetectionSeverity, int] = {
    DetectionSeverity.INFORMATIONAL: 0,
    DetectionSeverity.LOW: 1,
    DetectionSeverity.MEDIUM: 2,
    DetectionSeverity.HIGH: 3,
    DetectionSeverity.CRITICAL: 4,
}


def _source_host(event: SecurityEvent) -> str:
    """Extract the observed source host, without consulting any label."""

    details = event.details
    if details is not None:
        src_ip = getattr(details, "src_ip", None)
        if src_ip is not None:
            return str(src_ip)
        source_src = getattr(details, "source_src_address", None)
        if source_src is not None:
            return str(source_src)
    return UNKNOWN_SOURCE_HOST


def _destination(event: SecurityEvent) -> tuple[str | None, int | None]:
    """Extract the observed destination address and port."""

    details = event.details
    if details is None:
        return (None, None)
    dst_ip = getattr(details, "dst_ip", None)
    dst_port = getattr(details, "dst_port", None)
    return (str(dst_ip) if dst_ip is not None else None, dst_port)


def _highest_severity(detections: list[DetectionResult]) -> DetectionSeverity:
    """Propose one severity for a finding by a fixed rank, not by score comparison."""

    return max(
        (detection.severity for detection in detections),
        key=lambda severity: _SEVERITY_RANK[severity],
    )


def aggregate_findings(
    detections: Iterable[DetectionResult],
    events: Iterable[SecurityEvent],
    *,
    created_at: datetime,
    window_seconds: float = DEFAULT_WINDOW_SECONDS,
    aggregation_version: str = FINDING_AGGREGATION_VERSION,
) -> tuple[Finding, ...]:
    """Group detections into findings by source host and observed-time gap.

    The result is fully determined by its inputs: shuffling either input iterable yields the same
    findings, because every list is sorted before use and every identifier set is sorted before it
    is hashed into the finding identity.
    """

    if window_seconds <= 0:
        raise ValueError("window_seconds must be positive")

    events_by_id = {event.event_id: event for event in events}
    by_host: dict[str, list[DetectionResult]] = defaultdict(list)
    for detection in detections:
        event = events_by_id.get(detection.event_id)
        if event is None:
            continue
        by_host[_source_host(event)].append(detection)

    findings: list[Finding] = []
    for host in sorted(by_host):
        ordered = sorted(
            by_host[host],
            key=lambda detection: (
                events_by_id[detection.event_id].observed_at,
                str(detection.detection_id),
            ),
        )
        cluster: list[DetectionResult] = []
        previous: datetime | None = None
        for detection in ordered:
            observed_at = events_by_id[detection.event_id].observed_at
            if previous is not None and (observed_at - previous).total_seconds() > window_seconds:
                findings.append(
                    _build_finding(
                        cluster, events_by_id, host, created_at, aggregation_version
                    )
                )
                cluster = []
            cluster.append(detection)
            previous = observed_at
        if cluster:
            findings.append(
                _build_finding(cluster, events_by_id, host, created_at, aggregation_version)
            )

    return tuple(
        sorted(findings, key=lambda f: (f.source_host, f.window_start, str(f.finding_id)))
    )


def _build_finding(
    cluster: list[DetectionResult],
    events_by_id: dict[UUID, SecurityEvent],
    host: str,
    created_at: datetime,
    aggregation_version: str,
) -> Finding:
    """Assemble one finding from a single-host burst of detections."""

    times = sorted(events_by_id[detection.event_id].observed_at for detection in cluster)
    event_ids = tuple(sorted({detection.event_id for detection in cluster}, key=str))
    detection_ids = tuple(sorted({detection.detection_id for detection in cluster}, key=str))
    destinations: set[str] = set()
    ports: set[int] = set()
    for detection in cluster:
        destination, port = _destination(events_by_id[detection.event_id])
        if destination is not None:
            destinations.add(destination)
        if port is not None:
            ports.add(port)

    return Finding(
        finding_id=finding_id_for(
            aggregation_version=aggregation_version,
            source_host=host,
            window_start=times[0],
            event_ids=event_ids,
        ),
        aggregation_version=aggregation_version,
        event_ids=event_ids,
        detection_ids=detection_ids,
        source_host=host,
        window_start=times[0],
        window_end=times[-1],
        destinations=tuple(sorted(destinations)),
        destination_ports=tuple(sorted(ports)),
        proposed_severity=_highest_severity(cluster),
        status=FindingStatus.OPEN,
        created_at=created_at,
        note=_AGGREGATION_NOTE,
    )


__all__ = [
    "DEFAULT_WINDOW_SECONDS",
    "FINDING_AGGREGATION_VERSION",
    "UNKNOWN_SOURCE_HOST",
    "aggregate_findings",
]
