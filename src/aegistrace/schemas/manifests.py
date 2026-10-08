"""Dataset snapshot and file-integrity manifests."""

from __future__ import annotations

from datetime import datetime
from typing import Self
from uuid import NAMESPACE_URL, UUID, uuid5

from pydantic import Field, field_validator, model_validator

from aegistrace.schemas.common import (
    FrozenSchema,
    NonEmptyText,
    SchemaVersion,
    Sha256,
    normalize_utc,
)

MANIFEST_ID_NAMESPACE = uuid5(
    NAMESPACE_URL, "https://github.com/Lakshmi-Sindhu-P/AegisTrace/manifests/v1"
)


def manifest_id_for(dataset_name: str, dataset_version: str, raw_checksum: str) -> UUID:
    """Derive a repeatable manifest ID from the dataset snapshot identity."""

    return uuid5(MANIFEST_ID_NAMESPACE, f"{dataset_name}|{dataset_version}|{raw_checksum}")


class ManifestFile(FrozenSchema):
    """One immutable file referenced by a dataset manifest."""

    relative_path: NonEmptyText
    sha256: Sha256
    size_bytes: int = Field(ge=0)
    record_count: int | None = Field(default=None, ge=0)

    @field_validator("relative_path")
    @classmethod
    def require_relative_path(cls, value: str) -> str:
        """Prevent machine-specific absolute paths from entering durable manifests."""

        if value.startswith(("/", "~")):
            raise ValueError("manifest paths must be relative")
        return value


class DatasetManifest(FrozenSchema):
    """Provenance required for an acquired or generated dataset snapshot."""

    schema_version: SchemaVersion = "1.0.0"
    manifest_id: UUID
    dataset_name: NonEmptyText
    dataset_version: NonEmptyText
    source_url_or_generator: NonEmptyText
    selected_scenarios: tuple[NonEmptyText, ...] = ()
    acquired_or_generated_at: datetime
    license_or_terms_note: NonEmptyText
    files: tuple[ManifestFile, ...] = Field(min_length=1)
    record_count: int = Field(ge=0)
    observed_start: datetime | None = None
    observed_end: datetime | None = None
    label_distribution: dict[NonEmptyText, int] = Field(default_factory=dict)
    adapter_version: SchemaVersion
    transformation_version: SchemaVersion
    parent_manifest_id: UUID | None = None

    @field_validator("acquired_or_generated_at", "observed_start", "observed_end")
    @classmethod
    def normalize_manifest_timestamp(cls, value: datetime | None) -> datetime | None:
        """Normalize present manifest timestamps to UTC."""

        return None if value is None else normalize_utc(value)

    @field_validator("label_distribution")
    @classmethod
    def require_non_negative_label_counts(cls, value: dict[str, int]) -> dict[str, int]:
        """Reject impossible negative class counts."""

        if any(count < 0 for count in value.values()):
            raise ValueError("label counts must be non-negative")
        return value

    @model_validator(mode="after")
    def validate_time_range_and_counts(self) -> Self:
        """Validate internal manifest consistency without inventing missing metadata."""

        if (self.observed_start is None) != (self.observed_end is None):
            raise ValueError("observed_start and observed_end must be provided together")
        if (
            self.observed_start is not None
            and self.observed_end is not None
            and self.observed_end < self.observed_start
        ):
            raise ValueError("observed_end must not precede observed_start")
        # Issue #19: an unlabelled dataset may be legitimately unlabelled, so an empty
        # distribution is rejected only when records exist to label.  Without this floor a
        # manifest declaring record_count > 0 with no label_distribution passed vacuously
        # (sum({}) == 0 <= record_count for any record_count).
        if self.record_count > 0 and not self.label_distribution:
            raise ValueError("label_distribution must not be empty when record_count > 0")
        if sum(self.label_distribution.values()) > self.record_count:
            raise ValueError("label distribution cannot exceed record_count")
        return self
