"""Contract and output tests for the CTU-13 Argus-flow adapter."""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import pyarrow.parquet as pq
import pytest

from aegistrace.ingestion import ctu13
from aegistrace.ingestion.ctu13 import (
    CTU13_DATASET_NAME,
    CTU13_SCENARIO_ID,
    parse_ctu13_binetflow,
    write_ctu13_ingestion_outputs,
)
from aegistrace.schemas.events import Ctu13FlowDetails, GroundTruthLabel

FIXTURE_PATH = Path("data/fixtures/ctu13/scenario_11.binetflow")
INGESTED_AT = datetime(2026, 9, 21, 1, 0, tzinfo=UTC)


def test_parse_ctu13_fixture_preserves_labels_scenario_and_argus_fields() -> None:
    result = parse_ctu13_binetflow(
        FIXTURE_PATH,
        ingested_at=INGESTED_AT,
        report_generated_at=INGESTED_AT,
    )

    assert len(result.events) == 4
    assert result.report.dataset_name == CTU13_DATASET_NAME
    assert result.report.rows_seen == 4
    assert result.report.accepted_rows == 4
    assert result.report.rejected_rows == 0
    assert result.report.label_distribution == {"malicious": 1, "benign": 1, "unknown": 2}
    assert result.report.source_label_distribution["flow=Background"] == 1
    assert result.report.missing_counts["dTos"] == 2
    assert result.report.flow_distributions["protocol"] == {"tcp": 2, "udp": 1, "icmp": 1}

    first = result.events[0]
    assert first.source.scenario_id == CTU13_SCENARIO_ID
    assert first.source.source_event_id == "line-2"
    assert first.observed_at.isoformat() == "2011-08-18T13:39:35.087798+00:00"
    assert first.ground_truth_label is GroundTruthLabel.MALICIOUS
    assert first.attack_category == "flow=From-Botnet-V52-1-TCP"
    assert isinstance(first.details, Ctu13FlowDetails)
    assert first.details.network_bytes == 1000
    assert first.details.source_tos == 0
    assert first.details.source_label == "flow=From-Botnet-V52-1-TCP"
    assert "source_timestamp_timezone_assumed:Europe/Prague" in first.provenance.quality_flags

    background = result.events[2]
    assert background.ground_truth_label is GroundTruthLabel.UNKNOWN
    assert background.attack_category is None
    assert background.label_source == "ctu13_stratosphere_label"


def test_reingestion_is_deterministic() -> None:
    first = parse_ctu13_binetflow(FIXTURE_PATH, ingested_at=INGESTED_AT)
    second = parse_ctu13_binetflow(FIXTURE_PATH, ingested_at=INGESTED_AT)

    assert [event.event_id for event in first.events] == [event.event_id for event in second.events]
    assert first.report.raw_checksum == second.report.raw_checksum


def test_outputs_are_typed_parquet_json_and_manifest(tmp_path: Path) -> None:
    result = parse_ctu13_binetflow(
        FIXTURE_PATH, ingested_at=INGESTED_AT, report_generated_at=INGESTED_AT
    )
    parquet_path = tmp_path / "events.parquet"
    report_path = tmp_path / "quality_report.json"
    manifest_path = tmp_path / "dataset_manifest.json"

    manifest = write_ctu13_ingestion_outputs(
        result,
        input_path=FIXTURE_PATH,
        parquet_path=parquet_path,
        report_path=report_path,
        manifest_path=manifest_path,
    )

    table = pq.read_table(parquet_path)
    assert table.num_rows == 4
    assert table.schema.field("observed_at").type.tz == "UTC"
    assert table.schema.field("source_label").nullable is False
    assert json.loads(report_path.read_text())["accepted_rows"] == 4
    assert json.loads(manifest_path.read_text())["manifest_id"] == str(manifest.manifest_id)
    assert manifest.selected_scenarios == (CTU13_SCENARIO_ID,)


def test_duplicate_rows_are_rejected_and_reported(tmp_path: Path) -> None:
    lines = FIXTURE_PATH.read_text().splitlines()
    duplicate = tmp_path / "duplicate.binetflow"
    duplicate.write_text("\n".join([lines[0], lines[1], lines[1], *lines[2:]]) + "\n")

    result = parse_ctu13_binetflow(
        duplicate, ingested_at=INGESTED_AT, report_generated_at=INGESTED_AT
    )

    assert result.report.accepted_rows == 4
    assert result.report.rejected_rows == 1
    assert result.report.duplicate_source_records == 1
    assert result.report.issues[0].issue_type == "duplicate_source_record"


def test_malformed_and_invalid_rows_are_safe(tmp_path: Path) -> None:
    malformed = tmp_path / "malformed.binetflow"
    lines = FIXTURE_PATH.read_text().splitlines()
    malformed.write_text(
        "\n".join(
            [
                lines[0],
                "bad,csv",
                (
                    "2011/08/18 15:39:35.0,1,tcp,192.0.2.1,1,->,198.51.100.1,2,SF,"
                    "0,0,1,10,5,flow=Background"
                ),
                (
                    '2011/08/18 15:39:35.0,1,tcp,"unterminated,1,->,198.51.100.1,2,SF,'
                    "0,0,1,10,5,flow=Background"
                ),
            ]
        )
        + "\n"
    )

    result = parse_ctu13_binetflow(
        malformed, ingested_at=INGESTED_AT, report_generated_at=INGESTED_AT
    )

    assert len(result.events) == 1
    assert result.report.rejected_rows == 2
    assert {issue.issue_type for issue in result.report.issues} == {"malformed_row"}
    assert "unterminated" not in result.report.model_dump_json()


def test_invalid_header_and_missing_label_are_rejected(tmp_path: Path) -> None:
    invalid_header = tmp_path / "invalid-header.binetflow"
    invalid_header.write_text("not,a,ctu,header\n1,2,3,4\n")
    result = parse_ctu13_binetflow(
        invalid_header, ingested_at=INGESTED_AT, report_generated_at=INGESTED_AT
    )
    assert result.events == ()
    assert result.report.rejected_rows == 2

    missing_label = tmp_path / "missing-label.binetflow"
    line = FIXTURE_PATH.read_text().splitlines()[1].rsplit(",", maxsplit=1)[0]
    missing_label.write_text(f"{FIXTURE_PATH.read_text().splitlines()[0]}\n{line},-\n")
    result = parse_ctu13_binetflow(
        missing_label, ingested_at=INGESTED_AT, report_generated_at=INGESTED_AT
    )
    assert result.events == ()
    assert result.report.issues[0].issue_type == "invalid_record"


def test_cli_main_writes_three_artifacts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output_dir = tmp_path / "cli-output"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "ingest_ctu13",
            "--input",
            str(FIXTURE_PATH),
            "--output-dir",
            str(output_dir),
            "--ingested-at",
            INGESTED_AT.isoformat(),
            "--report-generated-at",
            INGESTED_AT.isoformat(),
            "--raw-reference",
            "data/raw/ctu13/CTU-Malware-Capture-Botnet-52/capture20110818-2.binetflow",
        ],
    )

    assert ctu13.main() == 0
    assert (output_dir / "events.parquet").exists()
    assert (output_dir / "quality_report.json").exists()
    assert (output_dir / "dataset_manifest.json").exists()


def test_direct_normal_and_botnet_labels_and_timezone_argument(tmp_path: Path) -> None:
    source = FIXTURE_PATH.read_text().replace("flow=From-Botnet-V52-1-TCP", "Botnet", 1)
    source = source.replace("flow=From-Normal-V52-Grill", "Normal", 1)
    path = tmp_path / "direct-labels.binetflow"
    path.write_text(source)
    result = parse_ctu13_binetflow(
        path,
        ingested_at=INGESTED_AT,
        source_timezone="UTC",
        report_generated_at=INGESTED_AT,
    )

    assert result.events[0].ground_truth_label is GroundTruthLabel.MALICIOUS
    assert result.events[1].ground_truth_label is GroundTruthLabel.BENIGN
    assert result.events[0].observed_at.isoformat() == "2011-08-18T15:39:35.087798+00:00"
