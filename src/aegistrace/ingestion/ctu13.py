"""Parser and normalized-output writer for CTU-13 Argus bidirectional flows.

The adapter intentionally accepts the text ``.binetflow`` artifact only.  It does
not fetch or execute malware, and it keeps CTU-13's source label and Argus fields
in a dedicated typed detail model instead of pretending they are Zeek fields.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import ipaddress
import json
import sys
from collections import Counter
from collections.abc import Iterable
from datetime import UTC, datetime, tzinfo
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pyarrow as pa
import pyarrow.parquet as pq
from pydantic import JsonValue, ValidationError

from aegistrace.ingestion.report import (
    IngestionReport,
    ParseIssue,
    ParseResult,
    ingestion_exit_code,
    ingestion_exit_reason,
)
from aegistrace.schemas.events import (
    Ctu13FlowDetails,
    EventProvenance,
    GroundTruthLabel,
    SecurityEvent,
    SourceRecordRef,
    SourceType,
    event_id_for,
)
from aegistrace.schemas.manifests import DatasetManifest, ManifestFile, manifest_id_for

CTU13_DATASET_NAME = "CTU-13"
CTU13_DATASET_VERSION = "2011-bidirectional-flow-labels-v1"
CTU13_SCENARIO_ID = "CTU-Malware-Capture-Botnet-52"
CTU13_ADAPTER_VERSION = "1.0.0"
CTU13_TRANSFORMATION_VERSION = "1.0.0"
CTU13_SOURCE_URL = (
    "https://mcfp.felk.cvut.cz/publicDatasets/CTU-Malware-Capture-Botnet-52/"
    "detailed-bidirectional-flow-labels/capture20110818-2.binetflow"
)
CTU13_SOURCE_TIMEZONE = "Europe/Prague"
_MISSING_VALUES = frozenset({"", "-", "(empty)", "-1"})
_FIELDS = (
    "StartTime",
    "Dur",
    "Proto",
    "SrcAddr",
    "Sport",
    "Dir",
    "DstAddr",
    "Dport",
    "State",
    "sTos",
    "dTos",
    "TotPkts",
    "TotBytes",
    "SrcBytes",
    "Label",
)


def ctu13_source_url(scenario_id: str, filename: str) -> str:
    """Build the authoritative per-scenario labeled-flow URL."""

    return (
        "https://mcfp.felk.cvut.cz/publicDatasets/"
        f"{scenario_id}/detailed-bidirectional-flow-labels/{filename}"
    )


_MISSINGNESS_FIELDS = (
    "StartTime",
    "Dur",
    "Proto",
    "SrcAddr",
    "Sport",
    "Dir",
    "DstAddr",
    "Dport",
    "State",
    "sTos",
    "dTos",
    "TotPkts",
    "TotBytes",
    "SrcBytes",
    "Label",
)

CTU13_NORMALIZED_EVENT_SCHEMA = pa.schema(
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
        pa.field("source_src_address", pa.string()),
        pa.field("source_dst_address", pa.string()),
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
        pa.field("flow_direction", pa.string()),
        pa.field("source_tos", pa.int64()),
        pa.field("destination_tos", pa.int64()),
        pa.field("source_label", pa.string(), nullable=False),
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
    if value is None:
        return None
    cleaned = value.strip()
    return None if cleaned in _MISSING_VALUES else cleaned


def _parse_int(value: str | None) -> int | None:
    cleaned = _clean(value)
    return None if cleaned is None else int(cleaned)


def _parse_port(value: str | None) -> int | None:
    cleaned = _clean(value)
    if cleaned is None:
        return None
    return int(cleaned, 16) if cleaned.casefold().startswith("0x") else int(cleaned)


def _parse_float(value: str | None) -> float | None:
    cleaned = _clean(value)
    return None if cleaned is None else float(cleaned)


def _parse_ip(value: str | None) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    cleaned = _clean(value)
    if cleaned is None:
        return None
    try:
        return ipaddress.ip_address(cleaned)
    except ValueError:
        return None


def _parse_timezone(value: str | tzinfo) -> tzinfo:
    return ZoneInfo(value) if isinstance(value, str) else value


def _parse_timestamp(value: str | None, source_timezone: tzinfo) -> datetime:
    cleaned = _clean(value)
    if cleaned is None:
        raise ValueError("missing StartTime")
    normalized = cleaned.replace("/", "-")
    try:
        timestamp = datetime.fromisoformat(normalized)
    except ValueError:
        timestamp = datetime.strptime(normalized, "%Y-%m-%d %H:%M:%S")
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        timestamp = timestamp.replace(tzinfo=source_timezone)
    return timestamp.astimezone(UTC)


def _source_label(value: str | None) -> str:
    cleaned = _clean(value)
    if cleaned is None:
        raise ValueError("missing Label")
    return cleaned


def _label_without_prefix(source_label: str) -> str:
    prefix, separator, remainder = source_label.partition("=")
    return remainder.strip() if separator and prefix.casefold() == "flow" else source_label


def _coarse_label(source_label: str) -> GroundTruthLabel:
    normalized = _label_without_prefix(source_label).casefold()
    if normalized == "normal" or normalized.startswith("from-normal"):
        return GroundTruthLabel.BENIGN
    if normalized == "botnet" or normalized.startswith("from-botnet"):
        return GroundTruthLabel.MALICIOUS
    # Background and To-* labels are not authoritative evidence about the sender.
    return GroundTruthLabel.UNKNOWN


def _event_from_record(
    record: dict[str, str],
    *,
    line_number: int,
    raw_reference: str,
    raw_checksum: str,
    dataset_version: str,
    scenario_id: str,
    ingested_at: datetime,
    source_timezone: tzinfo,
) -> SecurityEvent:
    source_label = _source_label(record.get("Label"))
    ground_truth_label = _coarse_label(source_label)
    source_event_id = f"line-{line_number}"
    source = SourceRecordRef(
        source_type=SourceType.CTU13,
        source_dataset=CTU13_DATASET_NAME,
        scenario_id=scenario_id,
        dataset_version=dataset_version,
        source_event_id=source_event_id,
        raw_payload_reference=raw_reference,
        raw_checksum=raw_checksum,
    )
    return SecurityEvent(
        event_id=event_id_for(source),
        source=source,
        observed_at=_parse_timestamp(record.get("StartTime"), source_timezone),
        ingested_at=ingested_at,
        event_type="network_flow",
        session_id=source_event_id,
        details=Ctu13FlowDetails(
            src_ip=_parse_ip(record.get("SrcAddr")),
            dst_ip=_parse_ip(record.get("DstAddr")),
            source_src_address=_clean(record.get("SrcAddr")),
            source_dst_address=_clean(record.get("DstAddr")),
            src_port=_parse_port(record.get("Sport")),
            dst_port=_parse_port(record.get("Dport")),
            protocol=_clean(record.get("Proto")),
            connection_state=_clean(record.get("State")),
            orig_bytes=_parse_int(record.get("SrcBytes")),
            network_bytes=_parse_int(record.get("TotBytes")),
            packet_count=_parse_int(record.get("TotPkts")),
            session_duration_seconds=_parse_float(record.get("Dur")),
            flow_direction=_clean(record.get("Dir")),
            source_tos=_parse_int(record.get("sTos")),
            destination_tos=_parse_int(record.get("dTos")),
            source_label=source_label,
        ),
        ground_truth_label=ground_truth_label,
        label_source="ctu13_stratosphere_label",
        attack_category=source_label
        if ground_truth_label is not GroundTruthLabel.UNKNOWN
        else None,
        provenance=EventProvenance(
            adapter_name="ctu13_argus_binetflow",
            adapter_version=CTU13_ADAPTER_VERSION,
            transformation_version=CTU13_TRANSFORMATION_VERSION,
            processed_at=ingested_at,
            quality_flags=(f"source_timestamp_timezone_assumed:{source_timezone}",),
        ),
    )


def _flow_distributions(
    events: Iterable[SecurityEvent],
) -> dict[str, JsonValue]:
    protocols: Counter[str] = Counter()
    directions: Counter[str] = Counter()
    states: Counter[str] = Counter()
    durations: list[float] = []
    byte_counts: list[int] = []
    for event in events:
        details = event.details
        if not isinstance(details, Ctu13FlowDetails):
            continue
        if details.protocol:
            protocols[details.protocol] += 1
        if details.flow_direction:
            directions[details.flow_direction] += 1
        if details.connection_state:
            states[details.connection_state] += 1
        if details.session_duration_seconds is not None:
            durations.append(details.session_duration_seconds)
        if details.network_bytes is not None:
            byte_counts.append(details.network_bytes)

    distributions: dict[str, JsonValue] = {
        "protocol": dict(protocols),
        "direction": dict(directions),
        "connection_state": dict(states),
    }
    if durations:
        distributions["duration_seconds"] = {
            "min": min(durations),
            "max": max(durations),
            "mean": sum(durations) / len(durations),
        }
    if byte_counts:
        distributions["total_bytes"] = {
            "min": min(byte_counts),
            "max": max(byte_counts),
            "mean": sum(byte_counts) / len(byte_counts),
        }
    return distributions


def parse_ctu13_binetflow(
    input_path: str | Path,
    *,
    ingested_at: datetime,
    dataset_version: str = CTU13_DATASET_VERSION,
    scenario_id: str = CTU13_SCENARIO_ID,
    source_timezone: str | tzinfo = CTU13_SOURCE_TIMEZONE,
    raw_reference: str | None = None,
    report_generated_at: datetime | None = None,
) -> ParseResult:
    """Parse one CTU-13 labeled bidirectional Argus text-flow file."""

    path = Path(input_path)
    checksum = _sha256_file(path)
    raw_path = raw_reference or path.as_posix()
    timezone = _parse_timezone(source_timezone)
    events: list[SecurityEvent] = []
    issues: list[ParseIssue] = []
    missing_counts: Counter[str] = Counter()
    labels: Counter[str] = Counter()
    source_labels: Counter[str] = Counter()
    row_fingerprints: set[str] = set()
    rows_seen = 0
    duplicate_source_records = 0

    with path.open("r", encoding="utf-8", errors="strict", newline="") as input_file:
        header_line = input_file.readline()
        try:
            header = tuple(next(csv.reader([header_line], strict=True))) if header_line else ()
        except csv.Error:
            header = ()
        if tuple(item.strip() for item in header) != _FIELDS:
            issues.append(
                ParseIssue(
                    line_number=1,
                    issue_type="malformed_row",
                    message="unexpected CTU-13 header",
                )
            )
            header_valid = False
        else:
            header_valid = True

        for line_number, raw_line in enumerate(input_file, start=2):
            if not raw_line.strip():
                continue
            rows_seen += 1
            if not header_valid:
                issues.append(
                    ParseIssue(
                        line_number=line_number,
                        issue_type="malformed_row",
                        message="cannot parse rows after invalid header",
                    )
                )
                continue
            try:
                values = next(csv.reader([raw_line], strict=True))
            except csv.Error:
                issues.append(
                    ParseIssue(
                        line_number=line_number,
                        issue_type="malformed_row",
                        message="invalid CSV row",
                    )
                )
                continue
            if len(values) != len(_FIELDS):
                issues.append(
                    ParseIssue(
                        line_number=line_number,
                        issue_type="malformed_row",
                        message=f"expected {len(_FIELDS)} fields, received {len(values)}",
                    )
                )
                continue
            record = dict(zip(_FIELDS, values, strict=True))
            for field_name in _MISSINGNESS_FIELDS:
                if _clean(record.get(field_name)) is None:
                    missing_counts[field_name] += 1
            fingerprint = hashlib.sha256(raw_line.strip().encode("utf-8")).hexdigest()
            if fingerprint in row_fingerprints:
                duplicate_source_records += 1
                issues.append(
                    ParseIssue(
                        line_number=line_number,
                        issue_type="duplicate_source_record",
                        message="duplicate source row fingerprint",
                    )
                )
                continue
            row_fingerprints.add(fingerprint)
            try:
                event = _event_from_record(
                    record,
                    line_number=line_number,
                    raw_reference=raw_path,
                    raw_checksum=checksum,
                    dataset_version=dataset_version,
                    scenario_id=scenario_id,
                    ingested_at=ingested_at,
                    source_timezone=timezone,
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
            events.append(event)
            labels[event.ground_truth_label.value] += 1
            source_label = (
                event.details.source_label if isinstance(event.details, Ctu13FlowDetails) else ""
            )
            source_labels[source_label] += 1

    observed_times = [event.observed_at for event in events]
    report = IngestionReport.with_utc_timestamp(
        source_type=SourceType.CTU13.value,
        dataset_name=CTU13_DATASET_NAME,
        dataset_version=dataset_version,
        input_path=raw_path,
        raw_checksum=checksum,
        report_generated_at=report_generated_at or datetime.now(UTC),
        rows_seen=rows_seen,
        accepted_rows=len(events),
        rejected_rows=len(issues),
        duplicate_event_ids=0,
        duplicate_source_records=duplicate_source_records,
        missing_counts=dict(missing_counts),
        label_distribution=dict(labels),
        source_label_distribution=dict(source_labels),
        flow_distributions=_flow_distributions(events),
        observed_start=min(observed_times) if observed_times else None,
        observed_end=max(observed_times) if observed_times else None,
        issues=tuple(issues),
    )
    return ParseResult(events=tuple(events), report=report)


def _event_to_row(event: SecurityEvent) -> dict[str, Any]:
    details = event.details
    if not isinstance(details, Ctu13FlowDetails):
        raise TypeError("CTU-13 normalized output requires CTU-13 flow details")
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
        "source_src_address": details.source_src_address,
        "source_dst_address": details.source_dst_address,
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
        "flow_direction": details.flow_direction,
        "source_tos": details.source_tos,
        "destination_tos": details.destination_tos,
        "source_label": details.source_label,
        "ground_truth_label": event.ground_truth_label.value,
        "label_source": event.label_source,
        "attack_category": event.attack_category,
        "adapter_name": event.provenance.adapter_name,
        "adapter_version": event.provenance.adapter_version,
        "transformation_version": event.provenance.transformation_version,
        "quality_flags": json.dumps(event.provenance.quality_flags),
    }


def write_ctu13_normalized_parquet(
    events: Iterable[SecurityEvent], output_path: str | Path
) -> None:
    """Write canonical CTU-13 events with their source-specific fields typed."""

    rows = [_event_to_row(event) for event in events]
    table = pa.Table.from_pylist(rows, schema=CTU13_NORMALIZED_EVENT_SCHEMA)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, output, compression="zstd")


def _manifest_for_result(
    result: ParseResult,
    *,
    raw_path: Path,
    manifest_path: Path,
    scenario_id: str,
    source_url: str,
) -> DatasetManifest:
    report = result.report
    file_path = report.input_path if not Path(report.input_path).is_absolute() else raw_path.name
    manifest = DatasetManifest(
        manifest_id=manifest_id_for(
            report.dataset_name, report.dataset_version, report.raw_checksum
        ),
        dataset_name=report.dataset_name,
        dataset_version=report.dataset_version,
        source_url_or_generator=source_url,
        selected_scenarios=(scenario_id,),
        acquired_or_generated_at=report.report_generated_at,
        license_or_terms_note=(
            "Creative Commons Attribution (CC-BY); cite the Stratosphere Laboratory "
            "CTU-13 dataset and Garcia et al. (2014). Only labeled text flows were acquired; "
            "no packets or executables were downloaded."
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
        adapter_version=CTU13_ADAPTER_VERSION,
        transformation_version=CTU13_TRANSFORMATION_VERSION,
    )
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(manifest.model_dump_json(indent=2) + "\n")
    return manifest


def write_ctu13_ingestion_outputs(
    result: ParseResult,
    *,
    input_path: str | Path,
    parquet_path: str | Path,
    report_path: str | Path,
    manifest_path: str | Path,
    scenario_id: str | None = None,
    source_url: str | None = None,
) -> DatasetManifest:
    """Write normalized Parquet, quality report, and dataset manifest."""

    raw_path = Path(input_path)
    write_ctu13_normalized_parquet(result.events, parquet_path)
    report_file = Path(report_path)
    report_file.parent.mkdir(parents=True, exist_ok=True)
    report_file.write_text(result.report.model_dump_json(indent=2) + "\n")
    resolved_scenario_id = (
        scenario_id
        or (result.events[0].source.scenario_id if result.events else None)
        or CTU13_SCENARIO_ID
    )
    resolved_source_url = source_url or ctu13_source_url(resolved_scenario_id, raw_path.name)
    return _manifest_for_result(
        result,
        raw_path=raw_path,
        manifest_path=Path(manifest_path),
        scenario_id=resolved_scenario_id,
        source_url=resolved_source_url,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="CTU-13 .binetflow file")
    parser.add_argument("--output-dir", type=Path, default=Path("data/processed/ctu13_scenario_11"))
    parser.add_argument("--ingested-at", required=True, help="UTC ISO-8601 timestamp for this run")
    parser.add_argument("--report-generated-at", help="UTC ISO-8601 report timestamp")
    parser.add_argument("--dataset-version", default=CTU13_DATASET_VERSION)
    parser.add_argument("--scenario-id", default=CTU13_SCENARIO_ID)
    parser.add_argument("--source-url", help="Authoritative source URL recorded in the manifest")
    parser.add_argument("--source-timezone", default=CTU13_SOURCE_TIMEZONE)
    parser.add_argument("--raw-reference", help="Relative source reference stored in events")
    parser.add_argument("--fail-on-rejects", action="store_true")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    ingested_at = datetime.fromisoformat(args.ingested_at.replace("Z", "+00:00"))
    report_generated_at = (
        datetime.fromisoformat(args.report_generated_at.replace("Z", "+00:00"))
        if args.report_generated_at
        else ingested_at
    )
    result = parse_ctu13_binetflow(
        args.input,
        ingested_at=ingested_at,
        dataset_version=args.dataset_version,
        scenario_id=args.scenario_id,
        source_timezone=args.source_timezone,
        raw_reference=args.raw_reference,
        report_generated_at=report_generated_at,
    )
    output_dir = args.output_dir
    manifest = write_ctu13_ingestion_outputs(
        result,
        input_path=args.input,
        parquet_path=output_dir / "events.parquet",
        report_path=output_dir / "quality_report.json",
        manifest_path=output_dir / "dataset_manifest.json",
        scenario_id=args.scenario_id,
        source_url=args.source_url,
    )
    print(
        json.dumps(
            {
                "accepted_rows": result.report.accepted_rows,
                "rejected_rows": result.report.rejected_rows,
                "duplicate_source_records": result.report.duplicate_source_records,
                "output_dir": str(output_dir),
                "manifest_id": str(manifest.manifest_id),
            },
            sort_keys=True,
        )
    )
    reason = ingestion_exit_reason(result.report, fail_on_rejects=args.fail_on_rejects)
    if reason is not None:
        print(f"ingest_ctu13: refusing to report success: {reason}", file=sys.stderr)
    return ingestion_exit_code(result.report, fail_on_rejects=args.fail_on_rejects)


if __name__ == "__main__":
    raise SystemExit(main())
