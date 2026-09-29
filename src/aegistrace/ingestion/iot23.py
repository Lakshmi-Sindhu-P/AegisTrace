"""Parser and normalized-output writer for IoT-23 Zeek connection logs."""

from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
from collections import Counter
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
from pydantic import ValidationError

from aegistrace.ingestion.report import IngestionReport, ParseIssue, ParseResult
from aegistrace.schemas.events import (
    EventProvenance,
    GroundTruthLabel,
    NetworkEventDetails,
    SecurityEvent,
    SourceRecordRef,
    SourceType,
    event_id_for,
)
from aegistrace.schemas.manifests import DatasetManifest, ManifestFile, manifest_id_for

IOT23_DATASET_NAME = "CTU-IoT-Malware-Capture-34-1"
IOT23_DATASET_VERSION = "1.0.0"
IOT23_ADAPTER_VERSION = "1.0.0"
IOT23_TRANSFORMATION_VERSION = "1.0.0"
IOT23_SOURCE_URL = (
    "https://mcfp.felk.cvut.cz/publicDatasets/IoT-23-Dataset/"
    "IndividualScenarios/CTU-IoT-Malware-Capture-34-1/bro/conn.log.labeled"
)
_MISSING_VALUES = frozenset({"", "-", "(empty)"})
_CANONICAL_MISSING_FIELDS = (
    "src_ip",
    "dst_ip",
    "src_port",
    "dst_port",
    "protocol",
    "service",
    "duration",
    "orig_bytes",
    "resp_bytes",
    "orig_pkts",
    "resp_pkts",
    "label",
    "detailed-label",
)

NORMALIZED_EVENT_SCHEMA = pa.schema(
    [
        pa.field("event_id", pa.string(), nullable=False),
        pa.field("source_type", pa.string(), nullable=False),
        pa.field("source_dataset", pa.string(), nullable=False),
        pa.field("scenario_id", pa.string()),
        pa.field("dataset_version", pa.string(), nullable=False),
        pa.field("source_event_id", pa.string(), nullable=False),
        pa.field("raw_payload_reference", pa.string(), nullable=False),
        pa.field("raw_checksum", pa.string()),
        pa.field("schema_version", pa.string(), nullable=False),
        pa.field("observed_at", pa.timestamp("us", tz="UTC"), nullable=False),
        pa.field("ingested_at", pa.timestamp("us", tz="UTC"), nullable=False),
        pa.field("event_type", pa.string(), nullable=False),
        pa.field("session_id", pa.string()),
        pa.field("src_ip", pa.string()),
        pa.field("dst_ip", pa.string()),
        pa.field("src_port", pa.int64()),
        pa.field("dst_port", pa.int64()),
        pa.field("protocol", pa.string()),
        pa.field("service", pa.string()),
        pa.field("connection_state", pa.string()),
        pa.field("history", pa.string()),
        pa.field("tunnel_parents", pa.string()),
        pa.field("orig_bytes", pa.int64()),
        pa.field("resp_bytes", pa.int64()),
        pa.field("missed_bytes", pa.int64()),
        pa.field("orig_packets", pa.int64()),
        pa.field("resp_packets", pa.int64()),
        pa.field("network_bytes", pa.int64()),
        pa.field("packet_count", pa.int64()),
        pa.field("session_duration_seconds", pa.float64()),
        pa.field("ground_truth_label", pa.string(), nullable=False),
        pa.field("label_source", pa.string()),
        pa.field("attack_category", pa.string()),
        pa.field("adapter_name", pa.string(), nullable=False),
        pa.field("adapter_version", pa.string(), nullable=False),
        pa.field("transformation_version", pa.string(), nullable=False),
        pa.field("quality_flags", pa.string(), nullable=False),
    ]
)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as input_file:
        for chunk in iter(lambda: input_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _clean(value: str | None) -> str | None:
    if value is None or value in _MISSING_VALUES:
        return None
    return value


def _parse_int(value: str | None) -> int | None:
    cleaned = _clean(value)
    if cleaned is None:
        return None
    return int(cleaned)


def _parse_float(value: str | None) -> float | None:
    cleaned = _clean(value)
    if cleaned is None:
        return None
    return float(cleaned)


def _parse_ip(value: str | None) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    cleaned = _clean(value)
    return None if cleaned is None else ipaddress.ip_address(cleaned)


def _separator_from_header(line: str) -> str:
    encoded = line.partition(" ")[2].strip()
    if encoded == r"\x09":
        return "\t"
    if encoded.startswith(r"\x") and len(encoded) == 4:
        return chr(int(encoded[2:], 16))
    if len(encoded) == 1:
        return encoded
    raise ValueError(f"unsupported Zeek separator: {encoded!r}")


def _split_tunnel_parents(value: str | None, separator: str) -> tuple[str, ...]:
    cleaned = _clean(value)
    if cleaned is None:
        return ()
    return tuple(item for item in cleaned.split(separator) if item)


def _coarse_label(label: str | None, detailed_label: str | None) -> GroundTruthLabel:
    candidate = (detailed_label or label or "").casefold()
    if not candidate:
        return GroundTruthLabel.UNKNOWN
    if candidate == "benign":
        return GroundTruthLabel.BENIGN
    return GroundTruthLabel.MALICIOUS


def _event_from_record(
    record: dict[str, str],
    *,
    line_number: int,
    raw_reference: str,
    raw_checksum: str,
    dataset_version: str,
    ingested_at: datetime,
) -> SecurityEvent:
    timestamp = _parse_float(record.get("ts"))
    if timestamp is None:
        raise ValueError("missing ts")
    source_event_id = _clean(record.get("uid")) or f"line-{line_number}"
    label = _clean(record.get("label"))
    detailed_label = _clean(record.get("detailed-label"))
    src_port = _parse_int(record.get("id.orig_p"))
    dst_port = _parse_int(record.get("id.resp_p"))
    orig_bytes = _parse_int(record.get("orig_bytes"))
    resp_bytes = _parse_int(record.get("resp_bytes"))
    orig_packets = _parse_int(record.get("orig_pkts"))
    resp_packets = _parse_int(record.get("resp_pkts"))
    missed_bytes = _parse_int(record.get("missed_bytes"))
    network_bytes = (
        (orig_bytes or 0) + (resp_bytes or 0)
        if orig_bytes is not None or resp_bytes is not None
        else None
    )
    packet_count = (
        (orig_packets or 0) + (resp_packets or 0)
        if orig_packets is not None or resp_packets is not None
        else None
    )
    source = SourceRecordRef(
        source_type=SourceType.IOT23,
        source_dataset=IOT23_DATASET_NAME,
        scenario_id=IOT23_DATASET_NAME,
        dataset_version=dataset_version,
        source_event_id=source_event_id,
        raw_payload_reference=raw_reference,
        raw_checksum=raw_checksum,
    )
    details = NetworkEventDetails(
        src_ip=_parse_ip(record.get("id.orig_h")),
        dst_ip=_parse_ip(record.get("id.resp_h")),
        src_port=src_port,
        dst_port=dst_port,
        protocol=_clean(record.get("proto")),
        service=_clean(record.get("service")),
        connection_state=_clean(record.get("conn_state")),
        history=_clean(record.get("history")),
        tunnel_parents=_split_tunnel_parents(record.get("tunnel_parents"), ","),
        orig_bytes=orig_bytes,
        resp_bytes=resp_bytes,
        missed_bytes=missed_bytes,
        orig_packets=orig_packets,
        resp_packets=resp_packets,
        network_bytes=network_bytes,
        packet_count=packet_count,
        session_duration_seconds=_parse_float(record.get("duration")),
    )
    ground_truth_label = _coarse_label(label, detailed_label)
    return SecurityEvent(
        event_id=event_id_for(source),
        source=source,
        observed_at=datetime.fromtimestamp(timestamp, tz=UTC),
        ingested_at=ingested_at,
        event_type="network_connection",
        session_id=source_event_id,
        details=details,
        ground_truth_label=ground_truth_label,
        label_source=(
            "iot23_stratosphere_label"
            if ground_truth_label is not GroundTruthLabel.UNKNOWN
            else None
        ),
        attack_category=detailed_label,
        provenance=EventProvenance(
            adapter_name="iot23_zeek_conn_log",
            adapter_version=IOT23_ADAPTER_VERSION,
            transformation_version=IOT23_TRANSFORMATION_VERSION,
            processed_at=ingested_at,
        ),
    )


def parse_iot23_conn_log(
    input_path: str | Path,
    *,
    ingested_at: datetime,
    dataset_version: str = IOT23_DATASET_VERSION,
    dataset_name: str = IOT23_DATASET_NAME,
    raw_reference: str | None = None,
    report_generated_at: datetime | None = None,
) -> ParseResult:
    """Parse a labeled Zeek `conn.log` file into canonical events and a quality report."""

    path = Path(input_path)
    checksum = _sha256_file(path)
    raw_path = raw_reference or path.as_posix()
    separator = "\t"
    fields: list[str] | None = None
    events: list[SecurityEvent] = []
    issues: list[ParseIssue] = []
    seen_event_ids: set[str] = set()
    missing_counts: Counter[str] = Counter()
    labels: Counter[str] = Counter()
    source_labels: Counter[str] = Counter()
    rows_seen = 0
    duplicate_event_ids = 0

    with path.open("r", encoding="utf-8", errors="strict", newline="") as input_file:
        for line_number, raw_line in enumerate(input_file, start=1):
            line = raw_line.rstrip("\r\n")
            if not line:
                continue
            if line.startswith("#separator"):
                separator = _separator_from_header(line)
                continue
            if line.startswith("#fields"):
                fields_payload = line[len("#fields") :].lstrip(" \t")
                fields = (
                    fields_payload.split(separator)
                    if separator in fields_payload
                    else fields_payload.split()
                )
                continue
            if line.startswith("#"):
                continue
            rows_seen += 1
            if fields is None:
                issues.append(
                    ParseIssue(
                        line_number=line_number,
                        issue_type="malformed_row",
                        message="missing #fields header",
                    )
                )
                continue
            values = line.split(separator)
            if len(values) != len(fields):
                issues.append(
                    ParseIssue(
                        line_number=line_number,
                        issue_type="malformed_row",
                        message=f"expected {len(fields)} fields, received {len(values)}",
                    )
                )
                continue
            record = dict(zip(fields, values, strict=True))
            for field_name in _CANONICAL_MISSING_FIELDS:
                if _clean(record.get(field_name)) is None:
                    missing_counts[field_name] += 1
            try:
                event = _event_from_record(
                    record,
                    line_number=line_number,
                    raw_reference=raw_path,
                    raw_checksum=checksum,
                    dataset_version=dataset_version,
                    ingested_at=ingested_at,
                )
            except (TypeError, ValueError, ValidationError) as error:
                issue_message = (
                    "record validation failed"
                    if isinstance(error, ValidationError)
                    else f"record parsing failed ({type(error).__name__})"
                )
                issues.append(
                    ParseIssue(
                        line_number=line_number,
                        issue_type="invalid_record",
                        message=issue_message,
                    )
                )
                continue
            event_key = str(event.event_id)
            if event_key in seen_event_ids:
                duplicate_event_ids += 1
                issues.append(
                    ParseIssue(
                        line_number=line_number,
                        issue_type="duplicate_event",
                        message=f"duplicate event_id {event_key}",
                    )
                )
                continue
            seen_event_ids.add(event_key)
            events.append(event)
            labels[event.ground_truth_label.value] += 1
            source_label = _clean(record.get("detailed-label")) or _clean(record.get("label"))
            if source_label:
                source_labels[source_label] += 1

    if fields is None:
        issues.append(
            ParseIssue(
                line_number=1,
                issue_type="malformed_row",
                message="missing #fields header",
            )
        )
    observed_times = [event.observed_at for event in events]
    report = IngestionReport.with_utc_timestamp(
        source_type=SourceType.IOT23.value,
        dataset_name=dataset_name,
        dataset_version=dataset_version,
        input_path=raw_path,
        raw_checksum=checksum,
        report_generated_at=report_generated_at or datetime.now(UTC),
        rows_seen=rows_seen,
        accepted_rows=len(events),
        rejected_rows=len(issues),
        duplicate_event_ids=duplicate_event_ids,
        missing_counts=dict(missing_counts),
        label_distribution=dict(labels),
        source_label_distribution=dict(source_labels),
        observed_start=min(observed_times) if observed_times else None,
        observed_end=max(observed_times) if observed_times else None,
        issues=tuple(issues),
    )
    return ParseResult(events=tuple(events), report=report)


def _event_to_row(event: SecurityEvent) -> dict[str, Any]:
    details = event.details
    if not isinstance(details, NetworkEventDetails):
        raise TypeError("IoT-23 normalized output requires network details")
    return {
        "event_id": str(event.event_id),
        "source_type": event.source.source_type.value,
        "source_dataset": event.source.source_dataset,
        "scenario_id": event.source.scenario_id,
        "dataset_version": event.source.dataset_version,
        "source_event_id": event.source.source_event_id,
        "raw_payload_reference": event.source.raw_payload_reference,
        "raw_checksum": event.source.raw_checksum,
        "schema_version": event.schema_version,
        "observed_at": event.observed_at,
        "ingested_at": event.ingested_at,
        "event_type": event.event_type,
        "session_id": event.session_id,
        "src_ip": str(details.src_ip) if details.src_ip is not None else None,
        "dst_ip": str(details.dst_ip) if details.dst_ip is not None else None,
        "src_port": details.src_port,
        "dst_port": details.dst_port,
        "protocol": details.protocol,
        "service": details.service,
        "connection_state": details.connection_state,
        "history": details.history,
        "tunnel_parents": json.dumps(details.tunnel_parents),
        "orig_bytes": details.orig_bytes,
        "resp_bytes": details.resp_bytes,
        "missed_bytes": details.missed_bytes,
        "orig_packets": details.orig_packets,
        "resp_packets": details.resp_packets,
        "network_bytes": details.network_bytes,
        "packet_count": details.packet_count,
        "session_duration_seconds": details.session_duration_seconds,
        "ground_truth_label": event.ground_truth_label.value,
        "label_source": event.label_source,
        "attack_category": event.attack_category,
        "adapter_name": event.provenance.adapter_name,
        "adapter_version": event.provenance.adapter_version,
        "transformation_version": event.provenance.transformation_version,
        "quality_flags": json.dumps(event.provenance.quality_flags),
    }


def write_normalized_parquet(events: Iterable[SecurityEvent], output_path: str | Path) -> None:
    """Write canonical events to a stable, typed Parquet schema."""

    rows = [_event_to_row(event) for event in events]
    table = pa.Table.from_pylist(rows, schema=NORMALIZED_EVENT_SCHEMA)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, output, compression="zstd")


def _manifest_for_result(
    result: ParseResult, *, raw_path: Path, manifest_path: Path
) -> DatasetManifest:
    report = result.report
    file_path = report.input_path if not Path(report.input_path).is_absolute() else raw_path.name
    manifest = DatasetManifest(
        manifest_id=manifest_id_for(
            report.dataset_name, report.dataset_version, report.raw_checksum
        ),
        dataset_name=report.dataset_name,
        dataset_version=report.dataset_version,
        source_url_or_generator=IOT23_SOURCE_URL,
        selected_scenarios=(report.dataset_name,),
        acquired_or_generated_at=report.report_generated_at,
        license_or_terms_note=(
            "Official scenario page states authorization is required to use these files."
        ),
        files=(
            ManifestFile(
                relative_path=file_path,
                sha256=report.raw_checksum,
                size_bytes=raw_path.stat().st_size,
                record_count=report.accepted_rows,
            ),
        ),
        record_count=report.accepted_rows,
        observed_start=report.observed_start,
        observed_end=report.observed_end,
        label_distribution=report.label_distribution,
        adapter_version=IOT23_ADAPTER_VERSION,
        transformation_version=IOT23_TRANSFORMATION_VERSION,
    )
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(manifest.model_dump_json(indent=2) + "\n")
    return manifest


def write_ingestion_outputs(
    result: ParseResult,
    *,
    input_path: str | Path,
    parquet_path: str | Path,
    report_path: str | Path,
    manifest_path: str | Path,
) -> DatasetManifest:
    """Write normalized Parquet, quality report, and dataset manifest."""

    raw_path = Path(input_path)
    write_normalized_parquet(result.events, parquet_path)
    report_file = Path(report_path)
    report_file.parent.mkdir(parents=True, exist_ok=True)
    report_file.write_text(result.report.model_dump_json(indent=2) + "\n")
    return _manifest_for_result(result, raw_path=raw_path, manifest_path=Path(manifest_path))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Authorized IoT-23 bro/conn.log.labeled file",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/processed/iot23_capture_34_1"),
    )
    parser.add_argument("--ingested-at", required=True, help="UTC ISO-8601 timestamp for this run")
    parser.add_argument("--dataset-version", default=IOT23_DATASET_VERSION)
    parser.add_argument("--raw-reference", help="Relative source reference stored in events")
    parser.add_argument("--fail-on-rejects", action="store_true")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    ingested_at = datetime.fromisoformat(args.ingested_at.replace("Z", "+00:00"))
    result = parse_iot23_conn_log(
        args.input,
        ingested_at=ingested_at,
        dataset_version=args.dataset_version,
        raw_reference=args.raw_reference,
    )
    output_dir = args.output_dir
    manifest = write_ingestion_outputs(
        result,
        input_path=args.input,
        parquet_path=output_dir / "events.parquet",
        report_path=output_dir / "quality_report.json",
        manifest_path=output_dir / "dataset_manifest.json",
    )
    print(
        json.dumps(
            {
                "accepted_rows": result.report.accepted_rows,
                "rejected_rows": result.report.rejected_rows,
                "duplicate_event_ids": result.report.duplicate_event_ids,
                "output_dir": str(output_dir),
                "manifest_id": str(manifest.manifest_id),
            },
            sort_keys=True,
        )
    )
    return 2 if args.fail_on_rejects and result.report.rejected_rows else 0


if __name__ == "__main__":
    raise SystemExit(main())
