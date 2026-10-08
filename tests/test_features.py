"""Tests for versioned, label-blind CTU-13 feature extraction."""

from __future__ import annotations

import hashlib
import json
import random
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

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
from aegistrace.schemas.events import event_id_for

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
    # The source is changed AND the id re-derived from it. Changing the source alone produces an
    # event whose id no longer matches its own source, which SecurityEvent forbids - it used to slip
    # through because `model_copy` skipped validation (issue #42).
    other_source = result.events[0].source.model_copy(update={"scenario_id": "other"})
    mixed = (
        *result.events,
        result.events[0].model_copy(
            update={"source": other_source, "event_id": event_id_for(other_source)}
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


def test_behavioral_leakage_audit_does_not_pass_empty_baseline() -> None:
    """An empty baseline is unmeasurable, so it must not report a passing audit (issue #18)."""

    assert not audit_prior_window_causality(())


def test_causal_leakage_audit_does_not_pass_empty_baseline() -> None:
    """An empty baseline is unmeasurable, so it must not report a passing audit (issue #18)."""

    assert not audit_causal_prior_window(())


def test_leakage_audits_pass_clean_non_empty_baseline() -> None:
    result = parse_ctu13_binetflow(FIXTURE_PATH, ingested_at=datetime(2026, 9, 21, 1, tzinfo=UTC))

    assert audit_prior_window_causality(result.events)
    assert audit_causal_prior_window(result.events)


# --- Issue #22: feature records must be emitted in a canonical order -------------------------
#
# Values were always order-invariant (computed over a sorted view), but the records tuple was
# rebuilt over the raw input, so the caller's iteration order leaked into the artifact bytes.
# These tests pin the canonical sequence and, crucially, the per-``event_id`` values so the
# ordering fix cannot silently change any feature value.

_ISSUE_22_BUILDERS: tuple[tuple[str, Any], ...] = (
    ("network", build_ctu13_features),
    ("behavioral", build_ctu13_behavioral_features),
    ("causal", build_ctu13_causal_features),
)

# Captured before the #22 fix: per-``event_id`` value maps for the fixture. The fix must not
# change these — only the emitted sequence.
#
# Re-captured for the issue #38 identity rule (`docs/identity_rule.md`), which changed `event_id`
# so that a line number is qualified by the file it was read from. This digest covers
# ``(event_id, values)`` pairs, so it moves with the id scheme as well as with the values.
#
# Both properties were verified when re-capturing, and the check below now separates them:
#   * with ``event_id_v1_for`` patched into BOTH the parser and the validator, all
#     three previous digests reproduce EXACTLY (48435f1e4ad4 / 7411b8bf8cb3 / 7c8a256bc0af);
#   * the id-free value multisets are byte-identical between v1 and v2.
# So only the identifiers changed; no feature value did.
_ISSUE_22_EXPECTED_VALUE_DIGESTS = {
    "network": "8a46d175c407",
    "behavioral": "eda6a708b920",
    "causal": "8343e2991cad",
}


def _id_free_value_digest(dataset: Any) -> str:
    """Digest the feature VALUES without the identifiers, so an identity change cannot move it."""

    values = sorted(json.dumps(list(record.values), default=str) for record in dataset.records)
    return hashlib.sha256(json.dumps(values).encode("utf-8")).hexdigest()[:12]


def _issue_22_events() -> list[Any]:
    result = parse_ctu13_binetflow(
        FIXTURE_PATH, ingested_at=datetime(2026, 9, 21, 1, tzinfo=UTC)
    )
    return list(result.events)


def _issue_22_orders() -> tuple[list[Any], list[Any], list[Any]]:
    events = _issue_22_events()
    reversed_events = list(reversed(events))
    shuffled_events = list(events)
    random.Random(22).shuffle(shuffled_events)
    assert tuple(shuffled_events) != tuple(events)
    return events, reversed_events, shuffled_events


def _event_id_sequence(dataset: Any) -> tuple[str, ...]:
    return tuple(str(record.event_id) for record in dataset.records)


def _value_map_digest(dataset: Any) -> str:
    mapping = sorted((str(record.event_id), list(record.values)) for record in dataset.records)
    payload = json.dumps(mapping, default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:12]


def test_issue_22_input_order_yields_byte_identical_serialized_output(tmp_path: Path) -> None:
    from aegistrace.features.behavioral import write_behavioral_feature_parquet

    events, reversed_events, shuffled_events = _issue_22_orders()
    writers = {
        "network": write_feature_parquet,
        "behavioral": write_behavioral_feature_parquet,
        "causal": write_causal_feature_parquet,
    }
    for name, build in _ISSUE_22_BUILDERS:
        payloads = []
        sequences = []
        for label, order in (
            ("original", events),
            ("reversed", reversed_events),
            ("shuffled", shuffled_events),
        ):
            dataset = build(order)
            path = tmp_path / f"{name}-{label}.parquet"
            writers[name](dataset, path)
            payloads.append(path.read_bytes())
            sequences.append(_event_id_sequence(dataset))
        assert payloads[0] == payloads[1] == payloads[2], name
        assert sequences[0] == sequences[1] == sequences[2], name


def test_issue_22_feature_values_are_unchanged_by_the_ordering_fix() -> None:
    events, reversed_events, shuffled_events = _issue_22_orders()
    for name, build in _ISSUE_22_BUILDERS:
        digests = {
            _value_map_digest(build(order))
            for order in (events, reversed_events, shuffled_events)
        }
        assert digests == {_ISSUE_22_EXPECTED_VALUE_DIGESTS[name]}, name
        # The property this test is NAMED for - that the values do not depend on input order -
        # asserted without reference to any identifier, so a future identity-version change cannot
        # make this test move for the wrong reason.
        value_digests = {_id_free_value_digest(build(order)) for order in (events, reversed_events,
            shuffled_events)}
        assert len(value_digests) == 1, name


def test_issue_22_ordering_is_deterministic_within_a_process() -> None:
    events = _issue_22_events()
    for name, build in _ISSUE_22_BUILDERS:
        baseline_sequence = _event_id_sequence(build(events))
        baseline_matrix = build(events).matrix()
        for seed in range(8):
            order = list(events)
            random.Random(seed).shuffle(order)
            dataset = build(order)
            assert _event_id_sequence(dataset) == baseline_sequence, name
            assert dataset.matrix() == baseline_matrix, name
