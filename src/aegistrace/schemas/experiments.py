"""Strict tracked experiment-run and artifact lineage schemas."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, field_validator, model_validator

from aegistrace.schemas.agent_trace import CommitId
from aegistrace.schemas.common import (
    FrozenSchema,
    NonEmptyText,
    SchemaVersion,
    Sha256,
    normalize_utc,
)

SEALED_SCENARIO_ID = "CTU-Malware-Capture-Botnet-48"
ExperimentStatus = Literal["IMPLEMENTED", "VALIDATED", "PROTOTYPE", "PLANNED"]
ArtifactKind = Literal["artifact", "report", "config"]


class ExperimentArtifact(FrozenSchema):
    """A digest-backed path referenced by one tracked experiment run."""

    path: NonEmptyText
    digest: Sha256
    kind: ArtifactKind
    tracked: bool

    @field_validator("path")
    @classmethod
    def require_relative_path(cls, value: str) -> str:
        """Keep registry paths portable and prevent accidental absolute paths."""

        if Path(value).is_absolute():
            raise ValueError("experiment artifact paths must be relative")
        return value


class ExperimentRun(FrozenSchema):
    """One reproducible experiment declaration and its evidence references."""

    schema_version: SchemaVersion = "1.0.0"
    experiment_id: NonEmptyText
    name: NonEmptyText
    status: ExperimentStatus
    created_at: datetime
    code_version: CommitId
    dataset_versions: tuple[NonEmptyText, ...] = Field(min_length=1)
    feature_versions: tuple[SchemaVersion, ...] = Field(min_length=1)
    training_scenarios: tuple[NonEmptyText, ...] = ()
    validation_scenarios: tuple[NonEmptyText, ...] = ()
    sealed_scenarios: tuple[NonEmptyText, ...] = (SEALED_SCENARIO_ID,)
    seed: int = Field(ge=0)
    command: NonEmptyText
    configuration: dict[str, Any] = Field(default_factory=dict)
    artifact_refs: tuple[ExperimentArtifact, ...] = Field(min_length=1)
    documentation_refs: tuple[NonEmptyText, ...] = Field(min_length=1)
    claim_boundary: NonEmptyText

    @field_validator("created_at")
    @classmethod
    def normalize_timestamp(cls, value: datetime) -> datetime:
        """Require timezone-aware timestamps and normalize to UTC."""

        return normalize_utc(value)

    @model_validator(mode="after")
    def enforce_sealed_scenario_boundary(self) -> ExperimentRun:
        """Require explicit protection for the sealed final scenario."""

        if SEALED_SCENARIO_ID not in self.sealed_scenarios:
            raise ValueError("registry runs must explicitly list sealed Scenario 7")
        scenarios = (*self.training_scenarios, *self.validation_scenarios)
        if SEALED_SCENARIO_ID in scenarios:
            raise ValueError("sealed Scenario 7 cannot be a training or validation scenario")
        return self


class ExperimentRegistry(FrozenSchema):
    """Tracked collection of reproducible experiment declarations."""

    schema_version: SchemaVersion = "1.0.0"
    registry_version: SchemaVersion = "1.0.0"
    runs: tuple[ExperimentRun, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def require_unique_experiment_ids(self) -> ExperimentRegistry:
        """Prevent silent replacement of an experiment declaration."""

        identifiers = [run.experiment_id for run in self.runs]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("experiment_id values must be unique")
        return self
