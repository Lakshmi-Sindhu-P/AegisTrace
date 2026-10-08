"""Small, interpretable network-flow features for CTU-13 experiments.

Feature extraction is deliberately source-aware and label-blind.  The output keeps
event/scenario metadata beside the numeric vector, but model callers receive only
the ordered numeric values.  Unknown-label rows remain available for rule scoring
and are excluded by the supervised-evaluation helpers.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any
from uuid import UUID

import pyarrow as pa
import pyarrow.parquet as pq
from pydantic import Field, field_validator

from aegistrace.schemas.common import FrozenSchema, NonEmptyText, SchemaVersion
from aegistrace.schemas.events import Ctu13FlowDetails, GroundTruthLabel, SecurityEvent

FEATURE_VERSION = "1.0.0"
FEATURE_NAMES: tuple[str, ...] = (
    "duration_seconds",
    "duration_missing",
    "log_total_bytes",
    "total_bytes_missing",
    "log_packet_count",
    "packet_count_missing",
    "log_source_bytes",
    "source_bytes_missing",
    "src_port_well_known",
    "src_port_missing",
    "dst_port_well_known",
    "dst_port_missing",
    "dst_port_http",
    "dst_port_dns",
    "protocol_tcp",
    "protocol_udp",
    "protocol_icmp",
    "protocol_other",
    "protocol_missing",
    "direction_forward",
    "direction_reverse",
    "direction_bidirectional",
    "direction_other",
    "direction_missing",
    "state_length",
    "state_missing",
)

FEATURE_PARQUET_SCHEMA = pa.schema(
    [
        pa.field("event_id", pa.string(), nullable=False),
        pa.field("scenario_id", pa.string(), nullable=False),
        pa.field("source_event_id", pa.string(), nullable=False),
        pa.field("ground_truth_label", pa.string(), nullable=False),
        pa.field("feature_version", pa.string(), nullable=False),
        *[pa.field(name, pa.float64(), nullable=False) for name in FEATURE_NAMES],
    ]
)


class FeatureRecord(FrozenSchema):
    """One versioned feature vector with non-feature provenance metadata."""

    event_id: UUID
    scenario_id: NonEmptyText
    source_event_id: NonEmptyText
    ground_truth_label: GroundTruthLabel
    feature_version: SchemaVersion = FEATURE_VERSION
    values: tuple[float, ...] = Field(min_length=len(FEATURE_NAMES), max_length=len(FEATURE_NAMES))

    @field_validator("values")
    @classmethod
    def require_feature_count(cls, value: tuple[float, ...]) -> tuple[float, ...]:
        if len(value) != len(FEATURE_NAMES):
            raise ValueError(f"expected {len(FEATURE_NAMES)} feature values")
        return value


class FeatureDataset(FrozenSchema):
    """Immutable feature collection with an explicit version and column order."""

    feature_version: SchemaVersion = FEATURE_VERSION
    feature_names: tuple[NonEmptyText, ...] = FEATURE_NAMES
    records: tuple[FeatureRecord, ...]

    @field_validator("feature_names")
    @classmethod
    def require_canonical_feature_names(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if value != FEATURE_NAMES:
            raise ValueError("feature_names must match the versioned canonical order")
        return value

    def supervised_records(self) -> tuple[FeatureRecord, ...]:
        """Return only authoritative benign/malicious rows for supervised work."""

        return tuple(
            record
            for record in self.records
            if record.ground_truth_label is not GroundTruthLabel.UNKNOWN
        )

    def matrix(self, records: Sequence[FeatureRecord] | None = None) -> list[list[float]]:
        """Return only numeric feature columns, never metadata or labels."""

        selected = self.records if records is None else records
        return [list(record.values) for record in selected]


def _log_value(value: int | None) -> tuple[float, float]:
    if value is None:
        return 0.0, 1.0
    return math.log1p(value), 0.0


def _port_flags(port: int | None) -> tuple[float, float]:
    if port is None:
        return 0.0, 1.0
    return float(port <= 1023), 0.0


def _protocol_flags(protocol: str | None) -> tuple[float, ...]:
    if protocol is None:
        return (0.0, 0.0, 0.0, 0.0, 1.0)
    normalized = protocol.casefold()
    return (
        float(normalized == "tcp"),
        float(normalized == "udp"),
        float(normalized == "icmp"),
        float(normalized not in {"tcp", "udp", "icmp"}),
        0.0,
    )


def _direction_flags(direction: str | None) -> tuple[float, ...]:
    if direction is None:
        return (0.0, 0.0, 0.0, 0.0, 1.0)
    normalized = direction.strip()
    return (
        float(normalized == "->"),
        float(normalized == "<-"),
        float(normalized == "<->"),
        float(normalized not in {"->", "<-", "<->"}),
        0.0,
    )


def _values(details: Ctu13FlowDetails) -> tuple[float, ...]:
    duration = (
        (details.session_duration_seconds, 0.0)
        if details.session_duration_seconds is not None
        else (0.0, 1.0)
    )
    total_bytes = _log_value(details.network_bytes)
    packet_count = _log_value(details.packet_count)
    source_bytes = _log_value(details.orig_bytes)
    src_well_known, src_missing = _port_flags(details.src_port)
    dst_well_known, dst_missing = _port_flags(details.dst_port)
    dst_http = float(details.dst_port in {80, 443, 8080}) if details.dst_port is not None else 0.0
    dst_dns = float(details.dst_port == 53) if details.dst_port is not None else 0.0
    state = details.connection_state
    state_length = float(len(state)) if state is not None else 0.0
    state_missing = float(state is None)
    return (
        duration[0],
        duration[1],
        total_bytes[0],
        total_bytes[1],
        packet_count[0],
        packet_count[1],
        source_bytes[0],
        source_bytes[1],
        src_well_known,
        src_missing,
        dst_well_known,
        dst_missing,
        dst_http,
        dst_dns,
        *_protocol_flags(details.protocol),
        *_direction_flags(details.flow_direction),
        state_length,
        state_missing,
    )


def base_feature_values(details: Ctu13FlowDetails) -> tuple[float, ...]:
    """Return the stable 1.0.0 per-flow vector for composed feature families."""

    return _values(details)


def build_ctu13_features(events: Iterable[SecurityEvent]) -> FeatureDataset:
    """Extract the versioned feature set from canonical CTU-13 flow events."""

    records: list[FeatureRecord] = []
    for event in events:
        details = event.details
        if not isinstance(details, Ctu13FlowDetails):
            continue
        scenario_id = event.source.scenario_id
        if scenario_id is None:
            raise ValueError("CTU-13 feature extraction requires scenario_id")
        records.append(
            FeatureRecord(
                event_id=event.event_id,
                scenario_id=scenario_id,
                source_event_id=event.source.source_event_id,
                ground_truth_label=event.ground_truth_label,
                values=_values(details),
            )
        )
    # Issue #22: values are order-invariant, but without canonicalising the emitted
    # sequence the caller's iteration order leaked into the artifact bytes. Sort by the
    # natural stable key so values and record order are both canonical.
    ordered = sorted(records, key=lambda record: str(record.event_id))
    return FeatureDataset(records=tuple(ordered))


def _row(record: FeatureRecord) -> dict[str, Any]:
    return {
        "event_id": str(record.event_id),
        "scenario_id": record.scenario_id,
        "source_event_id": record.source_event_id,
        "ground_truth_label": record.ground_truth_label.value,
        "feature_version": record.feature_version,
        **dict(zip(FEATURE_NAMES, record.values, strict=True)),
    }


def write_feature_parquet(dataset: FeatureDataset, output_path: str | Path) -> None:
    """Write a typed feature artifact with metadata kept separate from model columns."""

    rows = [_row(record) for record in dataset.records]
    table = pa.Table.from_pylist(rows, schema=FEATURE_PARQUET_SCHEMA)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, output, compression="zstd")
