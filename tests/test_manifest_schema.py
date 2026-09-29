"""Contract tests for dataset provenance manifests."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from aegistrace.schemas.manifests import DatasetManifest, ManifestFile


def valid_manifest_payload() -> dict[str, object]:
    return {
        "manifest_id": str(uuid4()),
        "dataset_name": "synthetic-contract-fixtures",
        "dataset_version": "1.0.0",
        "source_url_or_generator": "aegistrace.tests.fixture_generator",
        "selected_scenarios": ["network-event-contract"],
        "acquired_or_generated_at": datetime(2026, 9, 20, 12, 0, tzinfo=UTC),
        "license_or_terms_note": "Project-authored synthetic fixture.",
        "files": [
            {
                "relative_path": "data/fixtures/events/synthetic_network_event.json",
                "sha256": "a" * 64,
                "size_bytes": 100,
                "record_count": 1,
            }
        ],
        "record_count": 1,
        "observed_start": datetime(2026, 9, 20, 12, 0, tzinfo=UTC),
        "observed_end": datetime(2026, 9, 20, 12, 0, tzinfo=UTC),
        "label_distribution": {"benign": 1},
        "adapter_version": "1.0.0",
        "transformation_version": "1.0.0",
    }


def test_valid_dataset_manifest() -> None:
    manifest = DatasetManifest.model_validate(valid_manifest_payload())

    assert manifest.record_count == 1
    assert manifest.files[0].record_count == 1
    assert manifest.acquired_or_generated_at.tzinfo is UTC


def test_absolute_manifest_path_is_rejected() -> None:
    payload = valid_manifest_payload()
    files = payload["files"]
    assert isinstance(files, list)
    assert isinstance(files[0], dict)
    files[0]["relative_path"] = "/private/data.json"

    with pytest.raises(ValidationError, match="relative"):
        DatasetManifest.model_validate(payload)


def test_invalid_checksum_is_rejected() -> None:
    with pytest.raises(ValidationError, match="sha256"):
        ManifestFile(
            relative_path="data/fixture.json",
            sha256="not-a-sha256",
            size_bytes=1,
        )


def test_partial_observed_range_is_rejected() -> None:
    payload = valid_manifest_payload()
    payload["observed_end"] = None

    with pytest.raises(ValidationError, match="provided together"):
        DatasetManifest.model_validate(payload)


def test_label_distribution_cannot_exceed_records() -> None:
    payload = valid_manifest_payload()
    payload["label_distribution"] = {"benign": 2}

    with pytest.raises(ValidationError, match="record_count"):
        DatasetManifest.model_validate(payload)
