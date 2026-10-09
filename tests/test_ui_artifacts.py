"""Tests for the read-only UI artifact access layer (``aegistrace.ui.artifacts``).

These tests exist to prove the two honesty rules the module's docstring encodes:

1. A missing or malformed artifact *raises* ``ArtifactUnavailableError``; it never becomes an
   empty view. An empty screen and a broken screen must not look the same.
2. The synthetic flag is *read*, never inferred: ``SpineArtifactView.synthetic`` is
   ``not providers_configured``, and ``warning`` is surfaced verbatim.

Every failure case here is built as a JSON fixture in ``tmp_path``; nothing depends on the real
committed-ish artifact except test ``test_real_artifact_loads``, which is wrapped in a skip when the
artifact is not present. The real artifact is never modified.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aegistrace.ui.artifacts import (
    DEFAULT_SPINE_ARTIFACT,
    ArtifactUnavailableError,
    SpineRecordView,
    load_spine_artifact,
)


# --------------------------------------------------------------------------- #
# fixtures / helpers
# --------------------------------------------------------------------------- #
def minimal_payload() -> dict:
    """A small but *valid* payload: empty records, zero counts, provider-less."""
    return {
        "created_at": "2026-10-08T13:00:00+00:00",
        "freeze_version": "1.0.0",
        "network_egress": "none",
        "providers_configured": False,
        "warning": "no providers configured",
        "bundle_count": 0,
        "record_count": 0,
        "records": [],
    }


def write_payload(tmp_path: Path, *, name: str, payload: object) -> Path:
    """Serialize ``payload`` to a JSON file under ``tmp_path`` and return its path."""
    path = tmp_path / name
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


# --------------------------------------------------------------------------- #
# (a) valid payload loads; every field round-trips exactly against the payload
# --------------------------------------------------------------------------- #
def test_valid_payload_roundtrips(tmp_path):
    digest_a = "a1" * 32  # 64-char sha-256 hex
    digest_b = "b2" * 32
    payload = {
        "created_at": "2026-01-02T03:04:05+00:00",
        "freeze_version": "9.8.7",
        "network_egress": "no-telemetry",
        "providers_configured": True,
        "warning": "real providers, watch the egress",
        "bundle_count": 3,
        "record_count": 2,
        "records": [
            {
                "spine_id": "spine-1",
                "evidence_bundle_id": "bundle-1",
                "finding_id": "finding-1",
                "snapshot_digest": digest_a,
                "tier": "tier_a_machine_check",
                "machine_checks_passed": True,
                "review_count": 2,
            },
            {
                "spine_id": "spine-2",
                "evidence_bundle_id": "bundle-2",
                "finding_id": "finding-2",
                "snapshot_digest": digest_b,
                "tier": "tier_c_expert_judgment",
                "machine_checks_passed": False,
                "review_count": 0,
            },
        ],
    }
    path = write_payload(tmp_path, name="valid.json", payload=payload)

    view = load_spine_artifact(path)

    # top-level scalar fields round-trip exactly against the payload we wrote
    assert view.source_path == str(path)  # source_path comes from the path, not the payload
    assert view.created_at == payload["created_at"]
    assert view.freeze_version == payload["freeze_version"]
    assert view.network_egress == payload["network_egress"]
    assert view.providers_configured is True
    assert view.warning == payload["warning"]
    assert view.bundle_count == payload["bundle_count"]
    assert view.record_count == payload["record_count"]

    # records round-trip exactly, in order, field for field
    assert len(view.records) == len(payload["records"])
    for got, expected in zip(view.records, payload["records"], strict=True):
        assert got.spine_id == expected["spine_id"]
        assert got.evidence_bundle_id == expected["evidence_bundle_id"]
        assert got.finding_id == expected["finding_id"]
        assert got.snapshot_digest == expected["snapshot_digest"]
        assert got.tier == expected["tier"]
        assert got.machine_checks_passed is expected["machine_checks_passed"]
        assert got.review_count == expected["review_count"]


# --------------------------------------------------------------------------- #
# (b) synthetic is read in BOTH directions
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "providers_configured,expected_synthetic",
    [
        (False, True),  # no providers -> synthetic
        (True, False),  # providers configured -> NOT synthetic
    ],
    ids=["no_providers_is_synthetic", "configured_providers_is_not_synthetic"],
)
def test_synthetic_flag_read_both_directions(tmp_path, providers_configured, expected_synthetic):
    payload = minimal_payload()
    payload["providers_configured"] = providers_configured
    path = write_payload(tmp_path, name="synth.json", payload=payload)

    view = load_spine_artifact(path)

    assert view.synthetic is expected_synthetic
    # the flag must follow the *declaration*, in both directions
    assert view.synthetic is not providers_configured


# --------------------------------------------------------------------------- #
# (c) warning surfaced verbatim, awkward characters included
# --------------------------------------------------------------------------- #
def test_warning_surfaced_verbatim_with_awkward_characters(tmp_path):
    awkward = (
        "!! SYNTHETIC \"quoted\" \\backslash\\ /slash/ -dash- "
        "\u20ac EUR \u2192 arrow \n second line\tindented"
    )
    payload = minimal_payload()
    payload["warning"] = awkward
    # leading/trailing whitespace would be stripped by NonEmptyText and are not
    # part of "verbatim" semantics; assert every interior character survives.
    assert awkward == awkward.strip()
    path = write_payload(tmp_path, name="warn.json", payload=payload)

    view = load_spine_artifact(path)

    assert view.warning == awkward
    assert view.warning == payload["warning"]


# --------------------------------------------------------------------------- #
# (d) missing file -> ArtifactUnavailableError naming the path
# --------------------------------------------------------------------------- #
def test_missing_file_raises_with_path_in_message(tmp_path):
    missing = tmp_path / "does-not-exist.json"

    with pytest.raises(ArtifactUnavailableError) as excinfo:
        load_spine_artifact(missing)

    assert str(missing) in str(excinfo.value)
    assert "not found" in str(excinfo.value)


# --------------------------------------------------------------------------- #
# (e) invalid JSON -> ArtifactUnavailableError
# --------------------------------------------------------------------------- #
def test_invalid_json_raises(tmp_path):
    path = tmp_path / "broken.json"
    path.write_text("{ this is not json", encoding="utf-8")

    with pytest.raises(ArtifactUnavailableError):
        load_spine_artifact(path)


# --------------------------------------------------------------------------- #
# (f) JSON that is not an object (list / number / string) -> ArtifactUnavailableError
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("root", [[1, 2, 3], 42, "just a string"], ids=["list", "number", "string"])
def test_non_object_json_raises(tmp_path, root):
    path = write_payload(tmp_path, name="root.json", payload=root)

    with pytest.raises(ArtifactUnavailableError):
        load_spine_artifact(path)


# --------------------------------------------------------------------------- #
# (g) records not a list -> ArtifactUnavailableError
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("records", ["abc", 5, {"a": 1}], ids=["string", "int", "empty_dict"])
def test_records_not_a_list_raises(tmp_path, records):
    payload = minimal_payload()
    payload["records"] = records
    path = write_payload(tmp_path, name="records.json", payload=payload)

    with pytest.raises(ArtifactUnavailableError):
        load_spine_artifact(path)


# --------------------------------------------------------------------------- #
# (h) a record that is not an object -> ArtifactUnavailableError
# --------------------------------------------------------------------------- #
def test_record_not_an_object_raises(tmp_path):
    payload = minimal_payload()
    payload["records"] = ["not-a-dict"]
    path = write_payload(tmp_path, name="badrecord.json", payload=payload)

    with pytest.raises(ArtifactUnavailableError):
        load_spine_artifact(path)


# --------------------------------------------------------------------------- #
# (i) a record missing a required field -> ArtifactUnavailableError
# --------------------------------------------------------------------------- #
def test_record_missing_field_raises(tmp_path):
    broken_record = {
        "spine_id": "spine-1",
        "evidence_bundle_id": "bundle-1",
        "finding_id": "finding-1",
        "snapshot_digest": "a" * 64,
        # missing: tier
        "machine_checks_passed": True,
        "review_count": 0,
    }
    payload = minimal_payload()
    payload["records"] = [broken_record]
    path = write_payload(tmp_path, name="missingfield.json", payload=payload)

    with pytest.raises(ArtifactUnavailableError):
        load_spine_artifact(path)


# --------------------------------------------------------------------------- #
# (j) required top-level field missing -> ArtifactUnavailableError naming it
# --------------------------------------------------------------------------- #
def test_required_top_level_field_missing_raises_naming_it(tmp_path):
    payload = minimal_payload()
    payload.pop("freeze_version")
    path = write_payload(tmp_path, name="notop.json", payload=payload)

    with pytest.raises(ArtifactUnavailableError) as excinfo:
        load_spine_artifact(path)

    assert "freeze_version" in str(excinfo.value)


# --------------------------------------------------------------------------- #
# (k) negative review_count -> ArtifactUnavailableError (schema has ge=0)
# --------------------------------------------------------------------------- #
def test_negative_review_count_raises(tmp_path):
    record = {
        "spine_id": "spine-1",
        "evidence_bundle_id": "bundle-1",
        "finding_id": "finding-1",
        "snapshot_digest": "a" * 64,
        "tier": "tier_a_machine_check",
        "machine_checks_passed": True,
        "review_count": -1,
    }
    payload = minimal_payload()
    payload["records"] = [record]
    path = write_payload(tmp_path, name="neg.json", payload=payload)

    with pytest.raises(ArtifactUnavailableError):
        load_spine_artifact(path)


# --------------------------------------------------------------------------- #
# (l) EMPTY but VALID artifact loads successfully and is distinguishable from failure
# --------------------------------------------------------------------------- #
def test_empty_valid_artifact_loads(tmp_path):
    # a genuinely empty artifact (records=[], counts 0) is a fact about the
    # evidence and must load; it must NOT be conflated with a broken/missing file.
    payload = minimal_payload()
    path = write_payload(tmp_path, name="empty.json", payload=payload)

    view = load_spine_artifact(path)

    assert view.records == ()
    assert view.record_count == 0
    assert view.bundle_count == 0
    assert view.synthetic is True  # still reads providers_configured


# --------------------------------------------------------------------------- #
# (m) tier_label maps a known tier and returns an UNKNOWN tier unchanged
# --------------------------------------------------------------------------- #
def test_tier_label_maps_known_tier():
    record = SpineRecordView(
        spine_id="spine-1",
        evidence_bundle_id="bundle-1",
        finding_id="finding-1",
        snapshot_digest="a" * 64,
        tier="tier_b_guided_junior",
        machine_checks_passed=True,
        review_count=1,
    )
    assert record.tier_label == "Tier B - guided junior review"


def test_tier_label_returns_unknown_tier_unchanged():
    record = SpineRecordView(
        spine_id="spine-1",
        evidence_bundle_id="bundle-1",
        finding_id="finding-1",
        snapshot_digest="a" * 64,
        tier="tier_z_future_unknown",
        machine_checks_passed=True,
        review_count=0,
    )
    # the UI must show an unrecognised tier as-is rather than guess at it
    assert record.tier_label == "tier_z_future_unknown"


# --------------------------------------------------------------------------- #
# (n) real committed-ish artifact loads when present
# --------------------------------------------------------------------------- #
def test_real_artifact_loads_when_present():
    path = Path(DEFAULT_SPINE_ARTIFACT)
    if not path.exists():
        pytest.skip(
            f"real spine artifact {DEFAULT_SPINE_ARTIFACT} not present in this checkout; "
            "the (n) contract check is skipped, not failed"
        )

    view = load_spine_artifact(path)

    assert view.records and len(view.records) == 1
    # the demo artifact declares providers_configured: false, so it is synthetic
    assert view.providers_configured is False
    assert view.synthetic is True

# --------------------------------------------------------------------------- #
# The two remaining failure paths: an unreadable path, and an unusable field.
# Both were added to close the project's guard ratchet, which requires every
# raise to be executable by a test rather than merely present.
# --------------------------------------------------------------------------- #
def test_an_unreadable_path_raises_artifact_unavailable(tmp_path):
    """A path that exists but cannot be read as text must raise, not fall through.

    A directory is the portable way to provoke this: `Path.read_text` raises `IsADirectoryError`,
    an `OSError` that is NOT a `FileNotFoundError`, so it takes the second handler. Without that
    handler the raw `OSError` would escape the module's contract.
    """

    directory = tmp_path / "a-directory"
    directory.mkdir()

    with pytest.raises(ArtifactUnavailableError) as excinfo:
        load_spine_artifact(directory)

    assert "could not be read" in str(excinfo.value)
    assert str(directory) in str(excinfo.value)


def test_a_negative_bundle_count_raises_artifact_unavailable(tmp_path):
    """A field that is present but unusable must raise, not be silently coerced.

    `bundle_count` carries `ge=0`. A negative value is rejected by the schema, and the module
    converts that into `ArtifactUnavailableError` rather than letting a bare `ValueError` escape -
    so a caller catching the documented error type catches every read failure.
    """

    payload = minimal_payload()
    payload["bundle_count"] = -1
    path = write_payload(tmp_path, name="negative-bundle-count.json", payload=payload)

    with pytest.raises(ArtifactUnavailableError) as excinfo:
        load_spine_artifact(path)

    assert "unusable field" in str(excinfo.value)
    assert str(path) in str(excinfo.value)
