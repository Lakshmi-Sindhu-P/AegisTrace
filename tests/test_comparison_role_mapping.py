"""`TriageComparison.roles` must actually map `assessment_ids`, and the roles must be distinct.

The comparison engine already guarantees both: it builds `roles` and `assessment_ids` in parallel,
and `compare_assessments` refuses two assessments that share a role, because independence requires
one assessment per role.

The schema did not state either rule. That matters more than it looks, for two reasons:

1. A comparison is read back from stored artifacts rather than rebuilt, so `model_validate` was the
   only check a stored record ever met - and it passed records whose `roles` could not map their
   `assessment_ids`.
2. `left_only_evidence_ids` is *interpreted* through `roles[0]`. A misaligned record therefore
   silently attributes evidence to the wrong assessor, and a same-role record claims an
   independence it does not have - which is precisely the property the agreement metric measures.

An empty `roles` is the "not recorded" state and stays legal.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from aegistrace.schemas.triage import (
    AssessorRole,
    TriageComparison,
    comparison_id_for,
)

CREATED_AT = datetime(2026, 10, 9, 12, 0, tzinfo=UTC)
ANALYST = AssessorRole.TRIAGE_ANALYST
ADJUDICATOR = AssessorRole.EXPERT_ADJUDICATOR


def _comparison(roles: tuple[AssessorRole, ...], assessment_count: int) -> TriageComparison:
    """Build a comparison with `assessment_count` assessments and the given roles."""

    bundle_id = uuid4()
    assessment_ids = tuple(uuid4() for _ in range(assessment_count))
    return TriageComparison(
        comparison_id=comparison_id_for(
            evidence_bundle_id=bundle_id, assessment_ids=assessment_ids
        ),
        evidence_bundle_id=bundle_id,
        assessment_ids=assessment_ids,
        roles=roles,
        agreement=True,
        agreement_score=1.0,
        escalation_recommended=False,
        created_at=CREATED_AT,
    )


def test_aligned_roles_are_accepted() -> None:
    """The control: what the engine actually produces must still validate."""

    comparison = _comparison((ANALYST, ADJUDICATOR), 2)
    assert comparison.roles == (ANALYST, ADJUDICATOR)
    assert len(comparison.roles) == len(comparison.assessment_ids) == 2

    # A single-assessment comparison is a legal shape.
    single = _comparison((ANALYST,), 1)
    assert len(single.roles) == len(single.assessment_ids) == 1

    # And an unrecorded `roles` stays legal - it is the documented "not recorded" state.
    assert _comparison((), 2).roles == ()


def test_roles_must_map_assessment_ids_one_to_one() -> None:
    with pytest.raises(ValidationError, match="roles must map assessment_ids one-to-one"):
        _comparison((ANALYST,), 2)

    with pytest.raises(ValidationError, match="roles must map assessment_ids one-to-one"):
        _comparison((ANALYST, ADJUDICATOR), 1)


def test_two_assessments_may_not_share_a_role() -> None:
    """This is the property the agreement metric is supposed to measure."""

    with pytest.raises(ValidationError, match="distinct role"):
        _comparison((ANALYST, ANALYST), 2)

    with pytest.raises(ValidationError, match="distinct role"):
        _comparison((ADJUDICATOR, ADJUDICATOR), 2)


def test_a_misaligned_record_cannot_be_loaded_from_json() -> None:
    """The path that mattered: stored records are read, not rebuilt through the engine."""

    valid = _comparison((ANALYST, ADJUDICATOR), 2)
    payload = json.loads(valid.model_dump_json())
    reloaded = TriageComparison.model_validate(payload)
    assert reloaded.roles == (ANALYST, ADJUDICATOR)

    # Drop a role from the stored bytes: the mapping no longer covers the assessments.
    payload["roles"] = payload["roles"][:1]
    with pytest.raises(ValidationError, match="roles must map assessment_ids one-to-one"):
        TriageComparison.model_validate(payload)

    # And forge a same-role pair in the stored bytes.
    payload["roles"] = [payload["roles"][0], payload["roles"][0]]
    with pytest.raises(ValidationError, match="distinct role"):
        TriageComparison.model_validate(payload)


def test_the_schema_is_the_guarantee_not_the_engine() -> None:
    """The schema must reject the same-role shape the engine rejects.

    The engine's own refusal and the engine-vs-schema agreement are asserted in
    `test_comparison_field_semantics.py`, which already carries the full assessment fixtures. What
    matters here is that the shape is refused when presented to the schema directly, so that
    removing the engine's check cannot reopen the gap.
    """

    with pytest.raises(ValidationError, match="distinct role"):
        _comparison((ANALYST, ANALYST), 2)
