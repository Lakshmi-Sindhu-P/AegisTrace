"""Structured data-quality output for ingestion runs."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field, JsonValue

from aegistrace.schemas.common import (
    FrozenSchema,
    NonEmptyText,
    SchemaVersion,
    Sha256,
    normalize_utc,
)
from aegistrace.schemas.events import SecurityEvent


class ParseIssue(FrozenSchema):
    """Safe summary of one rejected input row; raw values are never copied into reports."""

    line_number: int = Field(ge=1)
    issue_type: Literal[
        "malformed_row", "invalid_record", "duplicate_event", "duplicate_source_record"
    ]
    message: NonEmptyText


class IngestionReport(FrozenSchema):
    """Counts and distributions emitted alongside normalized output."""

    schema_version: SchemaVersion = "1.0.0"
    source_type: NonEmptyText
    dataset_name: NonEmptyText
    dataset_version: NonEmptyText
    input_path: NonEmptyText
    raw_checksum: Sha256
    report_generated_at: datetime
    rows_seen: int = Field(ge=0)
    accepted_rows: int = Field(ge=0)
    rejected_rows: int = Field(ge=0)
    duplicate_event_ids: int = Field(ge=0)
    duplicate_source_records: int = Field(default=0, ge=0)
    missing_counts: dict[NonEmptyText, int] = Field(default_factory=dict)
    label_distribution: dict[NonEmptyText, int] = Field(default_factory=dict)
    source_label_distribution: dict[NonEmptyText, int] = Field(default_factory=dict)
    flow_distributions: dict[NonEmptyText, JsonValue] = Field(default_factory=dict)
    observed_start: datetime | None = None
    observed_end: datetime | None = None
    issues: tuple[ParseIssue, ...] = ()

    @classmethod
    def with_utc_timestamp(cls, **values: object) -> IngestionReport:
        """Construct a report while normalizing its generated timestamp."""

        timestamp = values.get("report_generated_at")
        if isinstance(timestamp, datetime):
            values["report_generated_at"] = normalize_utc(timestamp)
        return cls.model_validate(values)


class ParseResult(FrozenSchema):
    """Parsed events and their quality report."""

    events: tuple[SecurityEvent, ...]
    report: IngestionReport
