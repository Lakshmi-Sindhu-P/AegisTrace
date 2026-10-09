"""Contract and output tests for the IoT-23 Zeek adapter."""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import pyarrow.parquet as pq
import pytest

from aegistrace.ingestion import iot23
from aegistrace.ingestion.iot23 import (
    IOT23_DATASET_NAME,
    parse_iot23_conn_log,
    write_ingestion_outputs,
)
from aegistrace.schemas.events import GroundTruthLabel, NetworkEventDetails

FIXTURE_PATH = Path("data/fixtures/iot23/conn.log.labeled")
INGESTED_AT = datetime(2026, 9, 20, 1, 0, tzinfo=UTC)


def test_parse_zeek_fixture_and_report_quality() -> None:
    result = parse_iot23_conn_log(
        FIXTURE_PATH, ingested_at=INGESTED_AT, report_generated_at=INGESTED_AT
    )

    assert len(result.events) == 3
    assert result.report.dataset_name == IOT23_DATASET_NAME
    assert result.report.rows_seen == 3
    assert result.report.accepted_rows == 3
    assert result.report.rejected_rows == 0
    assert result.report.label_distribution == {"benign": 1, "malicious": 1, "unknown": 1}
    assert result.report.missing_counts["service"] == 1
    assert result.report.missing_counts["duration"] == 1
    assert result.report.observed_start is not None
    assert result.report.observed_end is not None

    first = result.events[0]
    assert first.ground_truth_label is GroundTruthLabel.BENIGN
    assert isinstance(first.details, NetworkEventDetails)
    assert first.details.network_bytes == 300
    assert first.details.packet_count == 5


def test_malformed_rows_are_rejected_without_copying_raw_values(tmp_path: Path) -> None:
    malformed = tmp_path / "malformed.log"
    malformed.write_text(
        "#separator \\x09\n"
        "#fields ts\tuid\tid.orig_h\tid.orig_p\tid.resp_h\tid.resp_p\tproto\tservice\t"
        "duration\torig_bytes\tresp_bytes\tconn_state\tlocal_orig\tlocal_resp\tmissed_bytes\t"
        "history\torig_pkts\torig_ip_bytes\tresp_pkts\tresp_ip_bytes\ttunnel_parents\tlabel\t"
        "detailed-label\n"
        "not-a-time\tBAD\t192.0.2.1\t1\t198.51.100.1\t2\ttcp\t-\t1\t1\t1\tSF\tT\tF\t0\tS\t1\t1\t1\t1\t-\t-\t-\n"
    )

    result = parse_iot23_conn_log(
        malformed, ingested_at=INGESTED_AT, report_generated_at=INGESTED_AT
    )

    assert result.events == ()
    assert result.report.rejected_rows == 1
    assert result.report.issues[0].issue_type == "invalid_record"
    assert "not-a-time" not in result.report.model_dump_json()


def test_duplicate_source_records_are_counted(tmp_path: Path) -> None:
    duplicate = tmp_path / "duplicate.log"
    lines = FIXTURE_PATH.read_text().splitlines()
    data_line = next(line for line in lines if line and not line.startswith("#"))
    duplicate.write_text("\n".join([*lines[:8], data_line, data_line, *lines[9:]]) + "\n")

    result = parse_iot23_conn_log(
        duplicate, ingested_at=INGESTED_AT, report_generated_at=INGESTED_AT
    )

    assert result.report.duplicate_event_ids == 1
    assert result.report.accepted_rows == 3
    assert result.report.rejected_rows == 1
    assert result.report.issues[0].issue_type == "duplicate_event"


def test_outputs_are_typed_parquet_json_and_manifest(tmp_path: Path) -> None:
    result = parse_iot23_conn_log(
        FIXTURE_PATH, ingested_at=INGESTED_AT, report_generated_at=INGESTED_AT
    )
    parquet_path = tmp_path / "events.parquet"
    report_path = tmp_path / "quality_report.json"
    manifest_path = tmp_path / "dataset_manifest.json"

    manifest = write_ingestion_outputs(
        result,
        input_path=FIXTURE_PATH,
        parquet_path=parquet_path,
        report_path=report_path,
        manifest_path=manifest_path,
    )

    table = pq.read_table(parquet_path)
    assert table.num_rows == 3
    assert table.schema.field("observed_at").type.tz == "UTC"
    assert json.loads(report_path.read_text())["accepted_rows"] == 3
    assert json.loads(manifest_path.read_text())["manifest_id"] == str(manifest.manifest_id)
    assert manifest.record_count == 3


def test_cli_main_writes_the_three_phase2_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    output_dir = tmp_path / "cli-output"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "ingest_iot23",
            "--input",
            str(FIXTURE_PATH),
            "--output-dir",
            str(output_dir),
            "--ingested-at",
            INGESTED_AT.isoformat(),
            "--raw-reference",
            "data/raw/iot23/CTU-IoT-Malware-Capture-34-1/bro/conn.log.labeled",
        ],
    )

    assert iot23.main() == 0
    assert (output_dir / "events.parquet").exists()
    assert (output_dir / "quality_report.json").exists()
    assert (output_dir / "dataset_manifest.json").exists()
    assert "accepted_rows" in capsys.readouterr().out


def test_missing_fields_header_is_rejected(tmp_path: Path) -> None:
    invalid = tmp_path / "no-fields.log"
    invalid.write_text("#separator \\x09\n1\tvalue\n")

    result = parse_iot23_conn_log(invalid, ingested_at=INGESTED_AT, report_generated_at=INGESTED_AT)

    assert result.events == ()
    assert result.report.rejected_rows == 2
    assert all(issue.issue_type == "malformed_row" for issue in result.report.issues)


@pytest.mark.parametrize("bad_value", ["", "-", "(empty)"])
def test_missing_values_are_normalized(bad_value: str, tmp_path: Path) -> None:
    source = FIXTURE_PATH.read_text().replace("ssl", bad_value, 1)
    path = tmp_path / "missing.log"
    path.write_text(source)

    result = parse_iot23_conn_log(path, ingested_at=INGESTED_AT, report_generated_at=INGESTED_AT)

    assert len(result.events) == 3
    assert result.report.missing_counts["service"] >= 1


# --- Issue #37: a zero-accept ingest must not report success --------------------------------


def test_issue_37_empty_but_valid_source_exits_non_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Same rule as the CTU-13 adapter, reached through a different parser.

    Both CLIs share one definition of the rule (`ingestion.ingestion_exit_reason`), so this test
    exists to prove the IoT-23 path actually calls it rather than to re-specify the rule.
    """

    header_only = tmp_path / "conn-header-only.log"
    header_only.write_text("#separator \\x09\n#fields\ta\tb\n")

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "ingest_iot23",
            "--input",
            str(header_only),
            "--output-dir",
            str(tmp_path / "out"),
            "--ingested-at",
            INGESTED_AT.isoformat(),
            "--raw-reference",
            "data/raw/iot23/CTU-IoT-Malware-Capture-34-1/bro/conn.log.labeled",
        ],
    )
    exit_code = iot23.main()

    captured = capsys.readouterr()
    assert exit_code != 0, "a zero-row ingest must not exit 0"
    assert "accepted_rows" in captured.out
    assert "no accepted rows" in captured.err
    assert (tmp_path / "out" / "quality_report.json").exists()


def test_issue_37_a_successful_ingest_still_exits_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The control, without which the test above would pass for an always-failing CLI."""

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "ingest_iot23",
            "--input",
            str(FIXTURE_PATH),
            "--output-dir",
            str(tmp_path / "out"),
            "--ingested-at",
            INGESTED_AT.isoformat(),
            "--raw-reference",
            "data/raw/iot23/CTU-IoT-Malware-Capture-34-1/bro/conn.log.labeled",
        ],
    )
    assert iot23.main() == 0
