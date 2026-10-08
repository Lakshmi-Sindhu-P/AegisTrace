"""Leakage-reviewed, scenario-local behavioral aggregates for CTU-13 flows.

The aggregate state is built independently for each scenario and uses only flows
observed before the current flow. This makes the feature family suitable for a
streaming-style detector and prevents future rows or labels from contributing to
the current vector. Unknown-label flows still contribute context, but never enter
supervised fitting or metric denominators.
"""

from __future__ import annotations

from collections import Counter, deque
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID, uuid5

import pyarrow as pa
import pyarrow.parquet as pq
from pydantic import Field, field_validator

from aegistrace.features.network import FEATURE_NAMES, base_feature_values
from aegistrace.schemas.common import FrozenSchema, NonEmptyText, SchemaVersion
from aegistrace.schemas.events import Ctu13FlowDetails, GroundTruthLabel, SecurityEvent

BEHAVIORAL_FEATURE_VERSION = "1.1.0"
BEHAVIORAL_FEATURE_NAMES: tuple[str, ...] = (
    *FEATURE_NAMES,
    "prior_source_connections_60s",
    "prior_unique_destinations_300s",
    "prior_unique_destination_ports_300s",
    "source_traffic_asymmetry",
    "source_traffic_asymmetry_missing",
    "prior_repeated_short_connections_300s",
)
BEHAVIORAL_BASE_FEATURE_COUNT = len(FEATURE_NAMES)


class BehavioralFeatureRecord(FrozenSchema):
    """One behavioral vector plus provenance metadata kept outside the matrix."""

    event_id: UUID
    scenario_id: NonEmptyText
    source_event_id: NonEmptyText
    observed_at: datetime
    ground_truth_label: GroundTruthLabel
    feature_version: SchemaVersion = BEHAVIORAL_FEATURE_VERSION
    values: tuple[float, ...] = Field(
        min_length=len(BEHAVIORAL_FEATURE_NAMES), max_length=len(BEHAVIORAL_FEATURE_NAMES)
    )

    @field_validator("values")
    @classmethod
    def require_feature_count(cls, value: tuple[float, ...]) -> tuple[float, ...]:
        if len(value) != len(BEHAVIORAL_FEATURE_NAMES):
            raise ValueError(f"expected {len(BEHAVIORAL_FEATURE_NAMES)} feature values")
        return value


class BehavioralFeatureDataset(FrozenSchema):
    """Immutable scenario-local behavioral feature collection."""

    feature_version: SchemaVersion = BEHAVIORAL_FEATURE_VERSION
    feature_names: tuple[NonEmptyText, ...] = BEHAVIORAL_FEATURE_NAMES
    records: tuple[BehavioralFeatureRecord, ...]

    @field_validator("feature_names")
    @classmethod
    def require_canonical_feature_names(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if value != BEHAVIORAL_FEATURE_NAMES:
            raise ValueError("feature_names must match the versioned canonical order")
        return value

    def supervised_records(self) -> tuple[BehavioralFeatureRecord, ...]:
        return tuple(
            record
            for record in self.records
            if record.ground_truth_label is not GroundTruthLabel.UNKNOWN
        )

    def matrix(self, records: Sequence[BehavioralFeatureRecord] | None = None) -> list[list[float]]:
        selected = self.records if records is None else records
        return [list(record.values) for record in selected]


@dataclass(slots=True)
class _PriorFlow:
    observed_at: datetime
    destination: str
    destination_port: int | None
    short: bool


@dataclass(slots=True)
class _HostState:
    flows: deque[_PriorFlow]
    destinations: Counter[str]
    destination_ports: Counter[int]
    recent: deque[datetime]
    short_count: int = 0


def _host_key(details: Ctu13FlowDetails, event_id: UUID) -> str:
    value = details.source_src_address or (str(details.src_ip) if details.src_ip else None)
    # Missing source identity must not merge unrelated flows into one synthetic host.
    return value if value else f"__missing_source__:{event_id}"


def _destination_key(details: Ctu13FlowDetails) -> str:
    return details.source_dst_address or (str(details.dst_ip) if details.dst_ip else "__missing__")


def _prune(state: _HostState, cutoff: datetime) -> None:
    while state.flows and state.flows[0].observed_at <= cutoff:
        old = state.flows.popleft()
        state.destinations[old.destination] -= 1
        if state.destinations[old.destination] <= 0:
            del state.destinations[old.destination]
        if old.destination_port is not None:
            state.destination_ports[old.destination_port] -= 1
            if state.destination_ports[old.destination_port] <= 0:
                del state.destination_ports[old.destination_port]
        if old.short:
            state.short_count -= 1


def build_ctu13_behavioral_features(events: Iterable[SecurityEvent]) -> BehavioralFeatureDataset:
    """Build 1.1.0 per-flow plus prior host/window features within one scenario."""

    selected = [
        event
        for event in events
        if isinstance(event.details, Ctu13FlowDetails) and event.source.scenario_id is not None
    ]
    if not selected:
        return BehavioralFeatureDataset(records=())
    scenario_ids = {event.source.scenario_id for event in selected}
    if len(scenario_ids) != 1:
        raise ValueError("behavioral features require one scenario per dataset")

    states: dict[str, _HostState] = {}
    vectors: dict[UUID, tuple[float, ...]] = {}
    ordered = sorted(selected, key=lambda event: (event.observed_at, str(event.event_id)))
    for event in ordered:
        details = event.details
        assert isinstance(details, Ctu13FlowDetails)
        host = _host_key(details, event.event_id)
        state = states.setdefault(
            host,
            _HostState(
                flows=deque(),
                destinations=Counter(),
                destination_ports=Counter(),
                recent=deque(),
            ),
        )
        _prune(state, event.observed_at - timedelta(seconds=300))
        connection_cutoff = event.observed_at - timedelta(seconds=60)
        # `recent` mirrors the prior-flow 60s window in insertion order, so the count is O(1)
        # instead of a per-event scan of the host's whole 300s window.
        while state.recent and state.recent[0] <= connection_cutoff:
            state.recent.popleft()
        prior_connections = len(state.recent)
        total_bytes = details.network_bytes
        source_bytes = details.orig_bytes
        asymmetry_missing = float(total_bytes is None or total_bytes <= 0 or source_bytes is None)
        asymmetry = (
            float(source_bytes) / float(total_bytes)
            if total_bytes is not None and total_bytes > 0 and source_bytes is not None
            else 0.0
        )
        vectors[event.event_id] = (
            *base_feature_values(details),
            float(prior_connections),
            float(len(state.destinations)),
            float(len(state.destination_ports)),
            asymmetry,
            asymmetry_missing,
            float(state.short_count),
        )
        short = (
            details.session_duration_seconds is not None and details.session_duration_seconds <= 1.0
        )
        prior = _PriorFlow(
            observed_at=event.observed_at,
            destination=_destination_key(details),
            destination_port=details.dst_port,
            short=short,
        )
        state.flows.append(prior)
        state.recent.append(event.observed_at)
        state.destinations[prior.destination] += 1
        if prior.destination_port is not None:
            state.destination_ports[prior.destination_port] += 1
        if short:
            state.short_count += 1

    records = []
    # Issue #22: reuse the same (observed_at, event_id) key used for value computation so the
    # emitted sequence is canonical and cannot drift from the values.
    for event in ordered:
        scenario_id = event.source.scenario_id
        assert scenario_id is not None
        records.append(
            BehavioralFeatureRecord(
                event_id=event.event_id,
                scenario_id=scenario_id,
                source_event_id=event.source.source_event_id,
                observed_at=event.observed_at,
                ground_truth_label=event.ground_truth_label,
                values=vectors[event.event_id],
            )
        )
    return BehavioralFeatureDataset(records=tuple(records))


def audit_prior_window_causality(events: Iterable[SecurityEvent]) -> bool:
    """Verify that appending a future flow cannot change earlier feature vectors.

    This is a small executable leakage check used by the hardening experiment and
    unit tests. It is deliberately separate from supervised labels and uses a
    deterministic synthetic future event identity.
    """

    original = tuple(events)
    baseline = build_ctu13_behavioral_features(original)
    if not baseline.records:
        # An empty baseline means there was nothing to measure, not that the prior-window
        # invariant held. Returning True here reported a PASSED leakage audit having examined
        # nothing (issue #18); conservatively report non-passing instead.
        return False
    last = max(original, key=lambda event: event.observed_at)
    future_source = last.source.model_copy(
        update={"source_event_id": f"{last.source.source_event_id}-future-audit"}
    )
    future_event = last.model_copy(
        update={
            "event_id": uuid5(last.event_id, "future-audit"),
            "source": future_source,
            "observed_at": last.observed_at + timedelta(seconds=1),
        }
    )
    augmented = build_ctu13_behavioral_features((*original, future_event))
    baseline_values = {record.event_id: record.values for record in baseline.records}
    augmented_values = {record.event_id: record.values for record in augmented.records}
    return all(
        augmented_values.get(event_id) == values for event_id, values in baseline_values.items()
    )


def _row(record: BehavioralFeatureRecord) -> dict[str, Any]:
    return {
        "event_id": str(record.event_id),
        "scenario_id": record.scenario_id,
        "source_event_id": record.source_event_id,
        "ground_truth_label": record.ground_truth_label.value,
        "feature_version": record.feature_version,
        "observed_at": record.observed_at,
        **dict(zip(BEHAVIORAL_FEATURE_NAMES, record.values, strict=True)),
    }


def write_behavioral_feature_parquet(
    dataset: BehavioralFeatureDataset, output_path: str | Path
) -> None:
    """Write behavioral features for audit; model callers use ``matrix`` only."""

    schema = pa.schema(
        [
            pa.field("event_id", pa.string(), nullable=False),
            pa.field("scenario_id", pa.string(), nullable=False),
            pa.field("source_event_id", pa.string(), nullable=False),
            pa.field("ground_truth_label", pa.string(), nullable=False),
            pa.field("feature_version", pa.string(), nullable=False),
            pa.field("observed_at", pa.timestamp("us", tz="UTC"), nullable=False),
            *[pa.field(name, pa.float64(), nullable=False) for name in BEHAVIORAL_FEATURE_NAMES],
        ]
    )
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pylist([_row(record) for record in dataset.records], schema=schema)
    pq.write_table(table, output, compression="zstd")
