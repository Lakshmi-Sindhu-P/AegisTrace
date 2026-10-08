"""A scenario-local feature dataset must actually be scenario-local.

`BehavioralFeatureDataset` and `CausalFeatureDataset` both describe themselves as "scenario-local"
in their own docstrings, and both builders refuse a dataset that mixes scenarios. The schemas did
not, and a stored dataset is read back with `model_validate`, which never calls a builder.

That gap is not cosmetic. Every per-scenario split in the evaluation assumes one capture per
dataset, so a mixed dataset would be pooled and reported as though it were one capture's worth of
evidence - silently, because nothing downstream re-derives the scenario set from the records.

The uniform case and the empty case must both keep working: an empty dataset is legal.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from aegistrace.features.behavioral import (
    BEHAVIORAL_FEATURE_NAMES,
    BehavioralFeatureDataset,
    BehavioralFeatureRecord,
)
from aegistrace.features.causal import (
    CAUSAL_FEATURE_NAMES,
    CausalFeatureDataset,
    CausalFeatureRecord,
)
from aegistrace.schemas.events import GroundTruthLabel

OBSERVED_AT = datetime(2026, 10, 9, 12, 0, tzinfo=UTC)


def _behavioral(scenario_id: str) -> BehavioralFeatureRecord:
    return BehavioralFeatureRecord(
        event_id=uuid4(),
        scenario_id=scenario_id,
        source_event_id="line-1",
        observed_at=OBSERVED_AT,
        ground_truth_label=GroundTruthLabel.UNKNOWN,
        values=tuple(0.0 for _ in BEHAVIORAL_FEATURE_NAMES),
    )


def _causal(scenario_id: str) -> CausalFeatureRecord:
    return CausalFeatureRecord(
        event_id=uuid4(),
        scenario_id=scenario_id,
        source_event_id="line-1",
        observed_at=OBSERVED_AT,
        ground_truth_label=GroundTruthLabel.UNKNOWN,
        values=tuple(0.0 for _ in CAUSAL_FEATURE_NAMES),
    )


@pytest.mark.parametrize(
    ("dataset_cls", "record_factory", "collection"),
    [
        (BehavioralFeatureDataset, _behavioral, "behavioral"),
        (CausalFeatureDataset, _causal, "causal"),
    ],
)
def test_a_single_scenario_dataset_is_accepted(
    dataset_cls: type, record_factory, collection: str
) -> None:
    """The control: what the builders actually produce must still validate."""

    dataset = dataset_cls(records=(record_factory("11"), record_factory("11")))
    assert {record.scenario_id for record in dataset.records} == {"11"}

    # An empty dataset is legal and has no scenario to disagree about.
    assert dataset_cls(records=()).records == ()


@pytest.mark.parametrize(
    ("dataset_cls", "record_factory", "collection"),
    [
        (BehavioralFeatureDataset, _behavioral, "behavioral"),
        (CausalFeatureDataset, _causal, "causal"),
    ],
)
def test_a_dataset_mixing_scenarios_is_refused(
    dataset_cls: type, record_factory, collection: str
) -> None:
    records = (record_factory("11"), record_factory("12"))

    # The probe varies its input: the records really do name two scenarios.
    assert len({record.scenario_id for record in records}) == 2

    with pytest.raises(ValidationError, match="one scenario per dataset"):
        dataset_cls(records=records)


@pytest.mark.parametrize(
    ("dataset_cls", "record_factory"),
    [(BehavioralFeatureDataset, _behavioral), (CausalFeatureDataset, _causal)],
)
def test_a_mixed_dataset_cannot_be_loaded_from_json(
    dataset_cls: type, record_factory
) -> None:
    """The path that mattered: stored datasets are read, not rebuilt through a builder."""

    # Build a legal dataset, then forge the mix in its stored bytes.
    valid = dataset_cls(records=(record_factory("11"),))
    payload = json.loads(valid.model_dump_json())
    assert dataset_cls.model_validate(payload).records[0].scenario_id == "11"

    second = json.loads(dataset_cls(records=(record_factory("12"),)).model_dump_json())
    payload["records"] = [*payload["records"], *second["records"]]
    assert len({r["scenario_id"] for r in payload["records"]}) == 2

    with pytest.raises(ValidationError, match="one scenario per dataset"):
        dataset_cls.model_validate(payload)
