"""Typed configuration loaded from TOML with explicit environment overrides."""

from __future__ import annotations

import os
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

EnvironmentName = Literal["development", "test", "production"]
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class RuntimeSettings(BaseModel):
    """Runtime behavior that is safe to store in version control."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    environment: EnvironmentName = "development"
    log_level: LogLevel = "INFO"


class StorageSettings(BaseModel):
    """Local data root; sensitive and bulk subdirectories remain gitignored."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    root_dir: Path = Field(default=Path("data"))

    @property
    def raw_dir(self) -> Path:
        """Return the local raw-data directory."""

        return self.root_dir / "raw"

    @property
    def interim_dir(self) -> Path:
        """Return the local intermediate-data directory."""

        return self.root_dir / "interim"

    @property
    def processed_dir(self) -> Path:
        """Return the local processed-data directory."""

        return self.root_dir / "processed"


class AegisTraceSettings(BaseModel):
    """Top-level application settings."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    runtime: RuntimeSettings = Field(default_factory=RuntimeSettings)
    storage: StorageSettings = Field(default_factory=StorageSettings)


def load_settings(
    config_path: str | Path = "configs/default.toml",
    *,
    environ: Mapping[str, str] | None = None,
) -> AegisTraceSettings:
    """Load settings from TOML and apply the documented environment overrides.

    Only non-secret settings are currently supported. Future secrets must be read
    directly from the environment by their owning integration and must never be
    serialized into this model or logged.
    """

    path = Path(config_path)
    with path.open("rb") as config_file:
        raw_config = tomllib.load(config_file)

    environment = os.environ if environ is None else environ
    runtime = dict(raw_config.get("runtime", {}))
    storage = dict(raw_config.get("storage", {}))

    if value := environment.get("AEGISTRACE_ENV"):
        runtime["environment"] = value
    if value := environment.get("AEGISTRACE_LOG_LEVEL"):
        runtime["log_level"] = value.upper()
    if value := environment.get("AEGISTRACE_DATA_DIR"):
        storage["root_dir"] = value

    return AegisTraceSettings.model_validate({"runtime": runtime, "storage": storage})
