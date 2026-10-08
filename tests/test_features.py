"""Tests for versioned, label-blind CTU-13 feature extraction."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pyarrow.parquet as pq

from aegistrace.features.behavioral import (
    BEHAVIORAL_FEATURE_NAMES,
    audit_prior_window_causality,
    build_ctu13_behavioral_features,
)
from aegistrace.features.causal import (
    CAUSAL_FEATURE_NAMES,
    audit_causal_prior_window,
    build_ctu13_causal_features,
    write_causal_feature_parquet,
)
from aegistrace.features.network import (
    FEATURE_NAMES,
    FeatureDataset,
    build_ctu13_features,
    write_feature_parquet,
)
from aegistrace.ingestion.ctu13 import parse_ctu13_binetflow

FIXTURE_PATH = Path("data/fixtures/ctu13/scenario_11.binetflow")


def test_features_preserve_metadata_but_keep_model_matrix_numeric() -> None:
    result = parse_ctu13_binetflow(FIXTURE_PATH, ingested_at=datetime(2026, 9, 21, 1, tzinfo=UTC))
    dataset = build_ctu13_features(result.events)

    assert len(dataset.records) == 4
    assert dataset.feature_names == FEATURE_NAMES
    assert len(dataset.matrix()) == 4
    assert all(len(row) == len(FEATURE_NAMES) for row in dataset.matrix())
    assert len(dataset.supervised_records()) == 2
    assert all(record.scenario_id == "CTU-Malware-Capture-Botnet-52" for record in dataset.records)
    assert all(isinstance(value, float) for value in dataset.records[0].values)


def test_feature_parquet_has_explicit_metadata_columns(tmp_path: Path) -> None:
    result = parse_ctu13_binetflow(FIXTURE_PATH, ingested_at=datetime(2026, 9, 21, 1, tzinfo=UTC))
    dataset = build_ctu13_features(result.events)
    output = tmp_path / "features.parquet"
    write_feature_parquet(dataset, output)

    table = pq.read_table(output)
    assert table.num_rows == 4
    assert table.column_names[:5] == [
        "event_id",
        "scenario_id",
        "source_event_id",
        "ground_truth_label",
        "feature_version",
    ]
    assert (
        table.schema.field("duration_missing").type
        == pq.read_schema(output).field("duration_missing").type
    )


def test_feature_dataset_rejects_noncanonical_feature_order() -> None:
    try:
        FeatureDataset(feature_names=("label",), records=())
    except ValueError as error:
        assert "canonical order" in str(error)
    else:
        raise AssertionError("noncanonical feature names should be rejected")


def test_behavioral_features_are_prior_only_and_scenario_local() -> None:
    result = parse_ctu13_binetflow(FIXTURE_PATH, ingested_at=datetime(2026, 9, 21, 1, tzinfo=UTC))
    dataset = build_ctu13_behavioral_features(result.events)

    assert dataset.feature_names == BEHAVIORAL_FEATURE_NAMES
    assert len(dataset.records) == 4
    assert dataset.records[0].values[-6:] == (0.0, 0.0, 0.0, 0.6, 0.0, 0.0)
    # Every fixture flow has a distinct source host, so no host history leaks across rows.
    assert all(record.values[26] == 0.0 for record in dataset.records)
    assert audit_prior_window_causality(result.events)


def test_behavioral_features_reject_mixed_scenarios() -> None:
    result = parse_ctu13_binetflow(FIXTURE_PATH, ingested_at=datetime(2026, 9, 21, 1, tzinfo=UTC))
    mixed = (
        *result.events,
        result.events[0].model_copy(
            update={"source": result.events[0].source.model_copy(update={"scenario_id": "other"})}
        ),
    )
    try:
        build_ctu13_behavioral_features(mixed)
    except ValueError as error:
        assert "one scenario" in str(error)
    else:
        raise AssertionError("mixed scenarios should be rejected")


def test_behavioral_aggregates_use_prior_host_window_and_write_parquet(tmp_path: Path) -> None:
    input_path = tmp_path / "repeated.binetflow"
    header = (
        "StartTime,Dur,Proto,SrcAddr,Sport,Dir,DstAddr,Dport,State,sTos,dTos,"
        "TotPkts,TotBytes,SrcBytes,Label"
    )
    rows = [
        [
            "2011/08/18 15:39:35.000000",
            "0.10",
            "tcp",
            "192.0.2.10",
            "1234",
            " ->",
            "198.51.100.10",
            "80",
            "PA",
            "0",
            "0",
            "2",
            "100",
            "50",
            "flow=From-Botnet-test",
        ],
        [
            "2011/08/18 15:39:45.000000",
            "0.20",
            "tcp",
            "192.0.2.10",
            "1234",
            " ->",
            "198.51.100.11",
            "443",
            "PA",
            "0",
            "0",
            "2",
            "200",
            "100",
            "flow=From-Botnet-test",
        ],
    ]
    input_path.write_text(
        header + "\n" + "\n".join(",".join(row) for row in rows) + "\n",
        encoding="utf-8",
    )
    result = parse_ctu13_binetflow(input_path, ingested_at=datetime(2026, 9, 21, 1, tzinfo=UTC))
    dataset = build_ctu13_behavioral_features(result.events)

    assert dataset.records[0].values[-6:] == (0.0, 0.0, 0.0, 0.5, 0.0, 0.0)
    assert dataset.records[1].values[-6:] == (1.0, 1.0, 1.0, 0.5, 0.0, 1.0)
    output = tmp_path / "behavioral.parquet"
    from aegistrace.features.behavioral import write_behavioral_feature_parquet

    write_behavioral_feature_parquet(dataset, output)
    assert pq.read_table(output).num_rows == 2


def test_behavioral_prior_connection_count_expires_at_sixty_seconds(tmp_path: Path) -> None:
    input_path = tmp_path / "window.binetflow"
    header = (
        "StartTime,Dur,Proto,SrcAddr,Sport,Dir,DstAddr,Dport,State,sTos,dTos,"
        "TotPkts,TotBytes,SrcBytes,Label"
    )
    stamps = [
        "2011/08/18 15:39:35.000000",
        "2011/08/18 15:40:05.000000",
        "2011/08/18 15:40:25.000000",
        "2011/08/18 15:41:15.000000",
    ]
    rows = [
        [
            stamp,
            "0.10",
            "tcp",
            "192.0.2.10",
            "1234",
            " ->",
            f"198.51.100.{10 + index}",
            "80",
            "PA",
            "0",
            "0",
            "2",
            "100",
            "50",
            "flow=From-Botnet-test",
        ]
        for index, stamp in enumerate(stamps)
    ]
    input_path.write_text(
        header + "\n" + "\n".join(",".join(row) for row in rows) + "\n", encoding="utf-8"
    )
    result = parse_ctu13_binetflow(input_path, ingested_at=datetime(2026, 9, 21, 1, tzinfo=UTC))
    dataset = build_ctu13_behavioral_features(result.events)

    connection_position = BEHAVIORAL_FEATURE_NAMES.index("prior_source_connections_60s")
    # One shared host: each flow counts only prior flows inside its own 60s window, so the oldest
    # entries must expire even though they remain inside the 300s window.
    assert [record.values[connection_position] for record in dataset.records] == [
        0.0,
        1.0,
        2.0,
        1.0,
    ]
    destination_position = BEHAVIORAL_FEATURE_NAMES.index("prior_unique_destinations_300s")
    assert dataset.records[3].values[destination_position] == 3.0


def test_causal_features_add_prior_reuse_recency_and_long_window(tmp_path: Path) -> None:
    input_path = tmp_path / "causal.binetflow"
    header = (
        "StartTime,Dur,Proto,SrcAddr,Sport,Dir,DstAddr,Dport,State,sTos,dTos,"
        "TotPkts,TotBytes,SrcBytes,Label"
    )
    rows = [
        [
            "2011/08/18 15:39:35.000000",
            "0.10",
            "tcp",
            "192.0.2.10",
            "1234",
            " ->",
            "198.51.100.10",
            "80",
            "PA",
            "0",
            "0",
            "2",
            "100",
            "50",
            "flow=From-Botnet-test",
        ],
        [
            "2011/08/18 15:39:45.000000",
            "0.20",
            "tcp",
            "192.0.2.10",
            "1234",
            " ->",
            "198.51.100.10",
            "80",
            "PA",
            "0",
            "0",
            "2",
            "200",
            "100",
            "flow=From-Botnet-test",
        ],
    ]
    input_path.write_text(
        header + "\n" + "\n".join(",".join(row) for row in rows) + "\n", encoding="utf-8"
    )
    result = parse_ctu13_binetflow(input_path, ingested_at=datetime(2026, 9, 21, 1, tzinfo=UTC))
    dataset = build_ctu13_causal_features(result.events)

    assert dataset.feature_names == CAUSAL_FEATURE_NAMES
    assert len(dataset.records[0].values) == len(CAUSAL_FEATURE_NAMES)
    index = {name: position for position, name in enumerate(CAUSAL_FEATURE_NAMES)}
    first, second = dataset.records
    assert first.values[index["prior_source_connections_300s"]] == 0.0
    assert first.values[index["seconds_since_prior_source_flow_missing"]] == 1.0
    assert second.values[index["prior_source_connections_300s"]] == 1.0
    assert second.values[index["prior_unique_destinations_60s"]] == 1.0
    assert second.values[index["prior_destination_reuse_300s"]] == 1.0
    assert second.values[index["prior_destination_port_reuse_300s"]] == 1.0
    assert second.values[index["prior_short_connections_60s"]] == 1.0
    assert second.values[index["seconds_since_prior_source_flow_missing"]] == 0.0
    assert audit_causal_prior_window(result.events)

    output = tmp_path / "causal.parquet"
    write_causal_feature_parquet(dataset, output)
    assert pq.read_table(output).num_rows == 2
