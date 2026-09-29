"""Prior-only host and time-window features for CTU-13 residual analysis.

This module deliberately creates a new feature version instead of changing the
validated ``1.1.0`` behavioral contract.  Every aggregate is computed from
flows observed before the current flow within one scenario and one source host.
Raw addresses, labels, filenames, scenario identifiers, and source record
identifiers remain metadata and never enter the numeric model matrix.
"""

from __future__ import annotations

import math
from collections import Counter, deque
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID

import pyarrow as pa
import pyarrow.parquet as pq
from pydantic import Field, field_validator

from aegistrace.features.behavioral import BEHAVIORAL_FEATURE_NAMES
from aegistrace.features.network import base_feature_values
from aegistrace.schemas.common import FrozenSchema, NonEmptyText, SchemaVersion
from aegistrace.schemas.events import (
    Ctu13FlowDetails,
    GroundTruthLabel,
    SecurityEvent,
    event_id_for,
)

CAUSAL_FEATURE_VERSION = "1.2.0"
CAUSAL_FEATURE_NAMES: tuple[str, ...] = (
    *BEHAVIORAL_FEATURE_NAMES,
    "prior_source_connections_300s",
    "prior_unique_destinations_60s",
    "prior_unique_destination_ports_60s",
    "prior_unique_protocols_300s",
    "prior_destination_reuse_300s",
    "prior_destination_port_reuse_300s",
    "prior_short_connections_60s",
    "log_prior_total_bytes_300s",
    "prior_total_bytes_300s_missing",
    "log_prior_packet_count_300s",
    "prior_packet_count_300s_missing",
    "log_seconds_since_prior_source_flow",
    "seconds_since_prior_source_flow_missing",
)


class CausalFeatureRecord(FrozenSchema):
    """One versioned causal feature vector and audit metadata."""

    event_id: UUID
    scenario_id: NonEmptyText
    source_event_id: NonEmptyText
    observed_at: datetime
    ground_truth_label: GroundTruthLabel
    feature_version: SchemaVersion = CAUSAL_FEATURE_VERSION
    values: tuple[float, ...] = Field(
        min_length=len(CAUSAL_FEATURE_NAMES), max_length=len(CAUSAL_FEATURE_NAMES)
    )

    @field_validator("values")
    @classmethod
    def require_feature_count(cls, value: tuple[float, ...]) -> tuple[float, ...]:
        if len(value) != len(CAUSAL_FEATURE_NAMES):
            raise ValueError(f"expected {len(CAUSAL_FEATURE_NAMES)} feature values")
        return value


class CausalFeatureDataset(FrozenSchema):
    """Immutable scenario-local causal feature collection."""

    feature_version: SchemaVersion = CAUSAL_FEATURE_VERSION
    feature_names: tuple[NonEmptyText, ...] = CAUSAL_FEATURE_NAMES
    records: tuple[CausalFeatureRecord, ...]

    @field_validator("feature_names")
    @classmethod
    def require_canonical_feature_names(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if value != CAUSAL_FEATURE_NAMES:
            raise ValueError("feature_names must match the versioned causal order")
        return value

    def supervised_records(self) -> tuple[CausalFeatureRecord, ...]:
        return tuple(
            record
            for record in self.records
            if record.ground_truth_label is not GroundTruthLabel.UNKNOWN
        )

    def matrix(self, records: Sequence[CausalFeatureRecord] | None = None) -> list[list[float]]:
        selected = self.records if records is None else records
        return [list(record.values) for record in selected]


@dataclass(slots=True)
class _PriorFlow:
    observed_at: datetime
    destination: str
    destination_port: int | None
    protocol: str
    short: bool
    total_bytes: int | None
    packet_count: int | None


@dataclass(slots=True)
class _WindowState:
    flows: deque[_PriorFlow] = field(default_factory=deque)
    destinations: Counter[str] = field(default_factory=Counter)
    destination_ports: Counter[int] = field(default_factory=Counter)
    protocols: Counter[str] = field(default_factory=Counter)
    short_count: int = 0
    total_bytes: int = 0
    observed_bytes: int = 0
    packet_count: int = 0
    observed_packets: int = 0


@dataclass(slots=True)
class _HostState:
    long: _WindowState = field(default_factory=_WindowState)
    short: _WindowState = field(default_factory=_WindowState)
    last_observed_at: datetime | None = None


def _host_key(details: Ctu13FlowDetails, event_id: UUID) -> str:
    value = details.source_src_address or (str(details.src_ip) if details.src_ip else None)
    return value if value else f"__missing_source__:{event_id}"


def _destination_key(details: Ctu13FlowDetails) -> str:
    return details.source_dst_address or (str(details.dst_ip) if details.dst_ip else "__missing__")


def _protocol_key(details: Ctu13FlowDetails) -> str:
    return details.protocol.casefold() if details.protocol else "__missing__"


def _prune(window: _WindowState, cutoff: datetime) -> None:
    while window.flows and window.flows[0].observed_at <= cutoff:
        old = window.flows.popleft()
        window.destinations[old.destination] -= 1
        if window.destinations[old.destination] <= 0:
            del window.destinations[old.destination]
        if old.destination_port is not None:
            window.destination_ports[old.destination_port] -= 1
            if window.destination_ports[old.destination_port] <= 0:
                del window.destination_ports[old.destination_port]
        window.protocols[old.protocol] -= 1
        if window.protocols[old.protocol] <= 0:
            del window.protocols[old.protocol]
        if old.short:
            window.short_count -= 1
        if old.total_bytes is not None:
            window.total_bytes -= old.total_bytes
            window.observed_bytes -= 1
        if old.packet_count is not None:
            window.packet_count -= old.packet_count
            window.observed_packets -= 1


def _add(window: _WindowState, flow: _PriorFlow) -> None:
    window.flows.append(flow)
    window.destinations[flow.destination] += 1
    if flow.destination_port is not None:
        window.destination_ports[flow.destination_port] += 1
    window.protocols[flow.protocol] += 1
    if flow.short:
        window.short_count += 1
    if flow.total_bytes is not None:
        window.total_bytes += flow.total_bytes
        window.observed_bytes += 1
    if flow.packet_count is not None:
        window.packet_count += flow.packet_count
        window.observed_packets += 1


def build_ctu13_causal_features(events: Iterable[SecurityEvent]) -> CausalFeatureDataset:
    """Build causal ``1.2.0`` features from one CTU-13 scenario.

    The existing ``1.1.0`` vectors are composed unchanged.  New values are
    derived only from prior flows in 60- and 300-second windows.  Unknown rows
    are allowed to contribute context, but their labels are never copied into
    a numeric feature.
    """

    selected = [
        event
        for event in events
        if isinstance(event.details, Ctu13FlowDetails) and event.source.scenario_id is not None
    ]
    if not selected:
        return CausalFeatureDataset(records=())
    scenario_ids = {event.source.scenario_id for event in selected}
    if len(scenario_ids) != 1:
        raise ValueError("causal features require one scenario per dataset")

    states: dict[str, _HostState] = {}
    vectors: dict[UUID, tuple[float, ...]] = {}
    ordered = sorted(selected, key=lambda event: (event.observed_at, str(event.event_id)))
    for event in ordered:
        details = event.details
        assert isinstance(details, Ctu13FlowDetails)
        host = _host_key(details, event.event_id)
        state = states.setdefault(host, _HostState())
        _prune(state.long, event.observed_at - timedelta(seconds=300))
        _prune(state.short, event.observed_at - timedelta(seconds=60))

        destination = _destination_key(details)
        destination_port = details.dst_port
        protocol = _protocol_key(details)
        prior = _PriorFlow(
            observed_at=event.observed_at,
            destination=destination,
            destination_port=destination_port,
            protocol=protocol,
            short=(
                details.session_duration_seconds is not None
                and details.session_duration_seconds <= 1.0
            ),
            total_bytes=details.network_bytes,
            packet_count=details.packet_count,
        )
        if state.last_observed_at is None:
            seconds_since_prior = 0.0
            seconds_since_prior_missing = 1.0
        else:
            seconds_since_prior = max(
                0.0, (event.observed_at - state.last_observed_at).total_seconds()
            )
            seconds_since_prior_missing = 0.0
        total_bytes = details.network_bytes
        source_bytes = details.orig_bytes
        asymmetry_missing = float(total_bytes is None or total_bytes <= 0 or source_bytes is None)
        asymmetry = (
            float(source_bytes) / float(total_bytes)
            if total_bytes is not None and total_bytes > 0 and source_bytes is not None
            else 0.0
        )
        values = (
            *base_feature_values(details),
            float(len(state.short.flows)),
            float(len(state.long.destinations)),
            float(len(state.long.destination_ports)),
            asymmetry,
            asymmetry_missing,
            float(state.long.short_count),
            float(len(state.long.flows)),
            float(len(state.short.destinations)),
            float(len(state.short.destination_ports)),
            float(len(state.long.protocols)),
            float(state.long.destinations.get(destination, 0)),
            float(
                state.long.destination_ports.get(destination_port, 0)
                if destination_port is not None
                else 0
            ),
            float(state.short.short_count),
            math.log1p(state.long.total_bytes),
            float(state.long.observed_bytes == 0),
            math.log1p(state.long.packet_count),
            float(state.long.observed_packets == 0),
            math.log1p(seconds_since_prior),
            seconds_since_prior_missing,
        )
        vectors[event.event_id] = values
        _add(state.long, prior)
        _add(state.short, prior)
        state.last_observed_at = event.observed_at

    records: list[CausalFeatureRecord] = []
    for event in selected:
        scenario_id = event.source.scenario_id
        assert scenario_id is not None
        records.append(
            CausalFeatureRecord(
                event_id=event.event_id,
                scenario_id=scenario_id,
                source_event_id=event.source.source_event_id,
                observed_at=event.observed_at,
                ground_truth_label=event.ground_truth_label,
                values=vectors[event.event_id],
            )
        )
    return CausalFeatureDataset(records=tuple(records))


def audit_causal_prior_window(events: Iterable[SecurityEvent]) -> bool:
    """Verify a future flow cannot change any earlier causal vector."""

    original = tuple(events)
    baseline = build_ctu13_causal_features(original)
    if not baseline.records:
        return True
    last = max(original, key=lambda event: event.observed_at)
    future_source = last.source.model_copy(
        update={"source_event_id": f"{last.source.source_event_id}-causal-future-audit"}
    )
    future_event = last.model_copy(
        update={
            "event_id": event_id_for(future_source),
            "source": future_source,
            "observed_at": last.observed_at + timedelta(seconds=1),
        }
    )
    augmented = build_ctu13_causal_features((*original, future_event))
    baseline_values = {record.event_id: record.values for record in baseline.records}
    augmented_values = {record.event_id: record.values for record in augmented.records}
    return all(
        augmented_values.get(event_id) == values
        for event_id, values in baseline_values.items()
    )


def _row(record: CausalFeatureRecord) -> dict[str, Any]:
    return {
        "event_id": str(record.event_id),
        "scenario_id": record.scenario_id,
        "source_event_id": record.source_event_id,
        "ground_truth_label": record.ground_truth_label.value,
        "feature_version": record.feature_version,
        "observed_at": record.observed_at,
        **dict(zip(CAUSAL_FEATURE_NAMES, record.values, strict=True)),
    }


def write_causal_feature_parquet(
    dataset: CausalFeatureDataset, output_path: str | Path
) -> None:
    """Write causal vectors with metadata kept outside the model matrix."""

    schema = pa.schema(
        [
            pa.field("event_id", pa.string(), nullable=False),
            pa.field("scenario_id", pa.string(), nullable=False),
            pa.field("source_event_id", pa.string(), nullable=False),
            pa.field("ground_truth_label", pa.string(), nullable=False),
            pa.field("feature_version", pa.string(), nullable=False),
            pa.field("observed_at", pa.timestamp("us", tz="UTC"), nullable=False),
            *[pa.field(name, pa.float64(), nullable=False) for name in CAUSAL_FEATURE_NAMES],
        ]
    )
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pylist([_row(record) for record in dataset.records], schema=schema)
    pq.write_table(table, output, compression="zstd")


__all__ = [
    "CAUSAL_FEATURE_NAMES",
    "CAUSAL_FEATURE_VERSION",
    "CausalFeatureDataset",
    "CausalFeatureRecord",
    "audit_causal_prior_window",
    "build_ctu13_causal_features",
    "write_causal_feature_parquet",
]
