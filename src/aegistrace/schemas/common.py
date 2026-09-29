"""Shared schema constraints and timestamp normalization."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
SchemaVersion = Annotated[str, StringConstraints(pattern=r"^\d+\.\d+\.\d+$")]
Sha256 = Annotated[str, StringConstraints(to_lower=True, pattern=r"^[0-9a-f]{64}$")]


class FrozenSchema(BaseModel):
    """Strict immutable base for evidence and provenance records."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)


def normalize_utc(value: datetime) -> datetime:
    """Require a timezone-aware timestamp and normalize it to UTC."""

    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must include a timezone")
    return value.astimezone(UTC)
