"""Tests for typed TOML configuration and explicit environment overrides."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from aegistrace.config import load_settings


def test_load_default_settings() -> None:
    settings = load_settings()

    assert settings.runtime.environment == "development"
    assert settings.runtime.log_level == "INFO"
    assert settings.storage.root_dir == Path("data")
    assert settings.storage.raw_dir == Path("data/raw")


def test_environment_overrides_are_explicit() -> None:
    settings = load_settings(
        environ={
            "AEGISTRACE_ENV": "test",
            "AEGISTRACE_LOG_LEVEL": "debug",
            "AEGISTRACE_DATA_DIR": "tmp/test-data",
        }
    )

    assert settings.runtime.environment == "test"
    assert settings.runtime.log_level == "DEBUG"
    assert settings.storage.processed_dir == Path("tmp/test-data/processed")


def test_unknown_toml_key_is_rejected(tmp_path: Path) -> None:
    config_file = tmp_path / "invalid.toml"
    config_file.write_text('[runtime]\nlog_level = "INFO"\nunexpected = true\n')

    with pytest.raises(ValidationError, match="unexpected"):
        load_settings(config_file, environ={})


def test_invalid_environment_override_is_rejected() -> None:
    with pytest.raises(ValidationError, match="environment"):
        load_settings(environ={"AEGISTRACE_ENV": "staging"})


def test_missing_config_file_fails_clearly(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_settings(tmp_path / "missing.toml", environ={})
