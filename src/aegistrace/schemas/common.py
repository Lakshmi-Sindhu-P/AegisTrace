"""Shared schema constraints and timestamp normalization."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from typing import Annotated, Any, Self

from pydantic import BaseModel, ConfigDict, StringConstraints

NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
SchemaVersion = Annotated[str, StringConstraints(pattern=r"^\d+\.\d+\.\d+$")]
Sha256 = Annotated[str, StringConstraints(to_lower=True, pattern=r"^[0-9a-f]{64}$")]


class FrozenSchema(BaseModel):
    """Strict immutable base for evidence and provenance records."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    def model_copy(
        self, *, update: Mapping[str, Any] | None = None, deep: bool = False
    ) -> Self:
        """Copy the model, re-validating whenever fields are replaced (issue #42).

        Pydantic v2 does **not** re-run validators for `model_copy(update=...)`, so any invariant
        enforced only by a `@model_validator` can be bypassed by copying a valid instance and
        overwriting a field. That makes the schema look like the guarantee while the real guarantee
        is whatever hand-written checks the caller happens to perform.

        Re-validating when `update` is supplied closes that escape hatch for every schema in the
        project, rather than for the one call site that was noticed. A copy with no `update` is not
        re-validated: no field changed, so re-running validators would cost time without adding a
        guarantee.

        This is not merely defensive. Two latent defects were being hidden by the old behaviour and
        are fixed alongside it: `behavioral.py` built a `SecurityEvent` whose `event_id` did not
        match its own source (which `SecurityEvent` explicitly forbids), and `append_review` built a
        `ReviewHistory` that never passed through `ReviewHistory`'s own subject check.
        """

        if update:
            return type(self).model_validate({**self.model_dump(), **update})
        return super().model_copy(update=update, deep=deep)


def normalize_utc(value: datetime) -> datetime:
    """Require a timezone-aware timestamp and normalize it to UTC."""

    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must include a timezone")
    return value.astimezone(UTC)


def require_uniform_scenario(scenarios: Iterable[str], *, collection: str) -> None:
    """Require every record in a scenario-local collection to name the same scenario.

    The feature builders already refuse a mixed dataset, but they are bypassed by the path that
    reads stored records: ``Dataset.model_validate(...)``. A dataset spanning two captures would
    otherwise load and be pooled as though it were scenario-local, which is the assumption every
    per-scenario split in the evaluation rests on.

    ``collection`` names the feature family so the message matches the builder's.
    """

    distinct = set(scenarios)
    if len(distinct) > 1:
        raise ValueError(
            f"{collection} features require one scenario per dataset; "
            f"found {len(distinct)}: {sorted(distinct)}"
        )
