"""The identity rule (`docs/identity_rule.md`) as executable properties.

The rule: an identifier is a versioned content address over exactly the fields that constitute the
entity's identity, and over nothing else. Issues #35, #38 and #40 were three independent instances
of
a violation, which is what makes this a rule rather than a bug fix.

Every test here checks one of the four obligations the rule document states:

1. DISTINCTNESS   - two instances differing in a defining field get different ids.
2. STABILITY      - identical input gives an identical id, repeatably.
3. DUPLICATES     - a genuine repeat is detected; a genuine second decision is not.
4. DOWNSTREAM     - every reference in the spine still resolves to the object it names.

Each test also asserts the *falsifier*: the property this rule exists to prevent. A test that only
confirms the ids differ would pass for any hash function; these pin the specific defect.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

from aegistrace.detection.evidence import build_evidence_bundle
from aegistrace.detection.findings import aggregate_findings
from aegistrace.detection.ml import emit_ml_detections
from aegistrace.ingestion.ctu13 import parse_ctu13_binetflow
from aegistrace.review.history import append_review, new_history
from aegistrace.schemas.events import (
    Ctu13FlowDetails,
    EventProvenance,
    SecurityEvent,
    SourceRecordRef,
    SourceType,
    event_id_for,
    event_id_v1_for,
)
from aegistrace.schemas.findings import DetectionSeverity
from aegistrace.schemas.review import (
    EscalationState,
    HumanReview,
    ReviewDecision,
    ReviewTier,
    review_id_for,
    review_id_v1_for,
)
from aegistrace.schemas.triage import AssessorRole, TriageCategory, triage_id_for

CREATED_AT = datetime(2026, 10, 9, 12, 0, tzinfo=UTC)
FIXTURE = Path("data/fixtures/ctu13/scenario_11.binetflow")
CHECKSUM_A = "a" * 64
CHECKSUM_B = "b" * 64


# --------------------------------------------------------------------------------------------
# 1. EVIDENCE - issue #38
# --------------------------------------------------------------------------------------------


def _source(*, checksum: str | None, line: str = "line-1",
    path: str = "fileA.binetflow") -> SourceRecordRef:
    return SourceRecordRef(
        source_type=SourceType.CTU13,
        source_dataset="CTU-13",
        scenario_id="11",
        dataset_version="1.0.0",
        source_event_id=line,
        raw_payload_reference=path,
        raw_checksum=checksum,
    )


def _event(source: SourceRecordRef, **details: object) -> SecurityEvent:
    details.setdefault("source_label", "flow=Background")
    return SecurityEvent(
        event_id=event_id_for(source),
        source=source,
        observed_at=CREATED_AT,
        ingested_at=CREATED_AT,
        event_type="network_flow",
        provenance=EventProvenance(
            adapter_name="identity_rule_test",
            adapter_version="1.0.0",
            transformation_version="1.0.0",
            processed_at=CREATED_AT,
        ),
        details=Ctu13FlowDetails(
            src_ip="10.0.0.1", dst_ip="198.51.100.9", dst_port=80, protocol="tcp",
            **details,
        ),
    )


def test_issue_38_distinct_files_cannot_collide_on_a_line_number() -> None:
    """DISTINCTNESS. The #38 defect: two different records sharing one id.

    `source_event_id` is `line-N`, which is arrival bookkeeping numbered per file. Without the file
    checksum, two different files of the same scenario collide on every matching line number.
    """

    a = _event(
        _source(checksum=CHECKSUM_A, path="fileA.binetflow"),
        source_label="malicious",
        network_bytes=1000,
    )
    b = _event(
        _source(checksum=CHECKSUM_B, path="fileB.binetflow"),
        source_label="benign",
        network_bytes=123456,
    )

    assert a.event_id != b.event_id, "two different records must not share an event_id"
    assert a.model_dump() != b.model_dump()
    # The falsifier: v1 genuinely collided, so this asserts the defect was real rather than assumed.
    assert event_id_v1_for(a.source) == event_id_v1_for(b.source)


def test_issue_38_same_file_still_yields_the_same_id() -> None:
    """STABILITY. The documented property - re-ingesting a file must not mint new ids."""

    first = _event(_source(checksum=CHECKSUM_A))
    second = _event(_source(checksum=CHECKSUM_A))

    assert first.event_id == second.event_id
    assert first.event_id == event_id_for(_source(checksum=CHECKSUM_A))


def test_event_identity_is_enforced_by_construction_not_convention() -> None:
    """A hand-supplied event_id that disagrees with the source is refused.

    This is why patching only the parser's binding could not forge ids during the #38 investigation:
    `SecurityEvent.validate_evidence_identity` recomputes the id from the source.
    """

    with pytest.raises(ValidationError, match="event_id does not match"):
        SecurityEvent(
            event_id=uuid4(),
            source=_source(checksum=CHECKSUM_A),
            observed_at=CREATED_AT,
            ingested_at=CREATED_AT,
            event_type="network_flow",
            provenance=EventProvenance(
                adapter_name="t",
                adapter_version="1.0.0",
                transformation_version="1.0.0",
                processed_at=CREATED_AT,
            ),
            details=Ctu13FlowDetails(
                src_ip="10.0.0.1", dst_ip="198.51.100.9", dst_port=80, protocol="tcp",
                source_label="flow=Background",
            ),
        )


# --------------------------------------------------------------------------------------------
# 2. AI ASSESSMENTS - issue #35
# --------------------------------------------------------------------------------------------


#: A fixed bundle id. A fresh uuid4 per call would make every "identical input" comparison
#: vacuously different and every distinctness test pass for the wrong reason.
BUNDLE_ID = uuid4()


def _assessment_id(**overrides: object) -> object:
    payload: dict = {
        "role": AssessorRole.TRIAGE_ANALYST.value,
        "evidence_bundle_id": BUNDLE_ID,
        "input_snapshot_digest": "c" * 64,
        "category": TriageCategory.SUSPICIOUS.value,
        "summary": "a summary",
        "severity": DetectionSeverity.MEDIUM.value,
        "cited_evidence_ids": ("evidence-a",),
    }
    payload.update(overrides)
    return triage_id_for(**payload)  # type: ignore[arg-type]


def test_issue_35_severity_is_identity_bearing() -> None:
    """DISTINCTNESS. The engine distinguishes on severity, so the identity must too."""

    low = _assessment_id(severity=DetectionSeverity.LOW.value)
    high = _assessment_id(severity=DetectionSeverity.HIGH.value)

    assert low != high, "the agreement engine reports severity_mismatch, so ids must differ"


def test_issue_35_cited_evidence_is_identity_bearing() -> None:
    """DISTINCTNESS. The engine reports evidence_divergence, so citations must move the id."""

    one = _assessment_id(cited_evidence_ids=("evidence-a",))
    two = _assessment_id(cited_evidence_ids=("evidence-a", "evidence-b", "evidence-c"))

    assert one != two, "different evidence means a different assessment"


def test_citation_order_cannot_change_an_assessment_identity() -> None:
    """R1 without an ordering trap: an assessor's listing order is not a property of its finding."""

    forward = _assessment_id(cited_evidence_ids=("a", "b", "c"))
    backward = _assessment_id(cited_evidence_ids=("c", "b", "a"))

    assert forward == backward


def test_an_admitted_assessment_is_now_at_least_as_well_identified_as_a_rejected_one() -> None:
    """The asymmetry #35 was found through: a rejection was content-addressed, an admission was not.

    `failed_attempt_id_for` hashes the raw response digest. An admitted assessment now hashes its
    conclusion, so neither is identified by less than the other.
    """

    base = _assessment_id()
    assert _assessment_id(severity=DetectionSeverity.HIGH.value) != base
    assert _assessment_id(category=TriageCategory.LIKELY_MALICIOUS.value) != base
    assert _assessment_id(summary="a different summary") != base


# --------------------------------------------------------------------------------------------
# 3. HUMAN REVIEWS - issue #40
# --------------------------------------------------------------------------------------------


REVIEW_SUBJECT = uuid4()


def _review_id(**overrides: object) -> object:
    payload: dict = {
        "subject_triage_id": REVIEW_SUBJECT,
        "subject_role": AssessorRole.TRIAGE_ANALYST.value,
        "reviewer_ref": "reviewer-1",
        "decision": ReviewDecision.CONFIRM.value,
        "final_disposition": "confirmed",
        "supersedes_review_id": None,
    }
    payload.update(overrides)
    return review_id_for(**payload)  # type: ignore[arg-type]


def test_issue_40_a_changed_disposition_changes_the_identity() -> None:
    """DISTINCTNESS. The #40 defect: the conclusion was absent from the identity."""

    confirmed = _review_id(final_disposition="confirmed")
    rejected = _review_id(final_disposition="rejected outright")

    assert confirmed != rejected


def test_issue_40_the_two_assessor_roles_cannot_share_a_review_identity() -> None:
    """DISTINCTNESS. `subject_role` names which blind assessor is being reviewed."""

    analyst = _review_id(subject_role=AssessorRole.TRIAGE_ANALYST.value)
    adjudicator = _review_id(subject_role=AssessorRole.EXPERT_ADJUDICATOR.value)

    assert analyst != adjudicator


def test_issue_40_superseding_different_reviews_are_different_reviews() -> None:
    """DISTINCTNESS. A correction is identified partly by what it corrects."""

    first = _review_id(decision=ReviewDecision.REVISE.value, supersedes_review_id=uuid4())
    second = _review_id(decision=ReviewDecision.REVISE.value, supersedes_review_id=uuid4())

    assert first != second


def test_recording_time_cannot_change_a_review_identity() -> None:
    """R2: `reviewed_at` is recording bookkeeping, so it is not identity.

    This is the property that makes two distinct dispositions in the same instant representable -
    the exact case #40 found unrepresentable.
    """

    def identity() -> object:
        return review_id_for(
            subject_triage_id=REVIEW_SUBJECT,
            subject_role=AssessorRole.TRIAGE_ANALYST.value,
            reviewer_ref="r",
            decision="confirm",
            final_disposition="d",
        )

    assert identity() == identity()
    # ...and the falsifier: v1 DID move with the clock, which is the defect.
    assert review_id_v1_for(
        subject_triage_id=REVIEW_SUBJECT, reviewer_ref="r", decision="confirm",
            reviewed_at=CREATED_AT
    ) != review_id_v1_for(
        subject_triage_id=REVIEW_SUBJECT, reviewer_ref="r", decision="confirm",
        reviewed_at=CREATED_AT + timedelta(seconds=1),
    )


@pytest.mark.parametrize("minutes", [0, 1, 600])
def test_same_instant_distinct_dispositions_are_both_recordable(minutes: int) -> None:
    """DUPLICATES. A reviewer changing their mind must be able to record it.

    Under v1 both reviews hashed `(subject, reviewer, decision, reviewed_at)` and therefore collided
    whenever they shared a timestamp, so `append_review` refused the second as a duplicate.
    """

    subject = uuid4()
    stamp = CREATED_AT + timedelta(minutes=minutes)

    def make(disposition: str, supersedes: object = None) -> HumanReview:
        return HumanReview(
            review_id=review_id_for(
                subject_triage_id=subject,
                subject_role=AssessorRole.TRIAGE_ANALYST.value,
                reviewer_ref="reviewer-1",
                decision=ReviewDecision.CONFIRM.value,
                final_disposition=disposition,
                supersedes_review_id=supersedes,  # type: ignore[arg-type]
            ),
            subject_triage_id=subject,
            subject_role=AssessorRole.TRIAGE_ANALYST,
            reviewer_ref="reviewer-1",
            tier=ReviewTier.B_GUIDED_JUNIOR,
            decision=ReviewDecision.CONFIRM,
            notes="n",
            reviewed_at=stamp,
            escalation_state=EscalationState.NONE,
            final_disposition=disposition,
            supersedes_review_id=supersedes,  # type: ignore[arg-type]
        )

    history = append_review(new_history(subject), make("confirmed"))
    # A changed mind is recorded as a correction, exactly as the append-only chain requires.
    history = append_review(
        history, make("changed my mind", supersedes=history.reviews[0].review_id)
    )

    assert len(history.reviews) == 2
    assert history.reviews[0].final_disposition != history.reviews[1].final_disposition


def test_a_genuine_duplicate_is_still_refused() -> None:
    """DUPLICATES, the other direction. Widening the identity must not admit real duplicates."""

    subject = uuid4()
    review = HumanReview(
        review_id=review_id_for(
            subject_triage_id=subject,
            subject_role=AssessorRole.TRIAGE_ANALYST.value,
            reviewer_ref="reviewer-1",
            decision=ReviewDecision.CONFIRM.value,
            final_disposition="confirmed",
        ),
        subject_triage_id=subject,
        subject_role=AssessorRole.TRIAGE_ANALYST,
        reviewer_ref="reviewer-1",
        tier=ReviewTier.B_GUIDED_JUNIOR,
        decision=ReviewDecision.CONFIRM,
        notes="n",
        reviewed_at=CREATED_AT,
        escalation_state=EscalationState.NONE,
        final_disposition="confirmed",
    )

    history = append_review(new_history(subject), review)

    with pytest.raises(ValueError, match="already recorded"):
        append_review(history, review)


def test_v1_ids_remain_reproducible_for_historical_records() -> None:
    """R3. A pre-change id must stay explainable by naming the version that produced it."""

    subject = uuid4()
    legacy = review_id_v1_for(
        subject_triage_id=subject, reviewer_ref="r", decision="confirm", reviewed_at=CREATED_AT
    )
    assert legacy == review_id_v1_for(
        subject_triage_id=subject, reviewer_ref="r", decision="confirm", reviewed_at=CREATED_AT
    )
    # v1 and v2 must not agree, or the version switch would be a no-op.
    assert legacy != review_id_for(
        subject_triage_id=subject,
        subject_role=AssessorRole.TRIAGE_ANALYST.value,
        reviewer_ref="r",
        decision="confirm",
        final_disposition="d",
    )


# --------------------------------------------------------------------------------------------
# 4. DOWNSTREAM INTEGRITY
# --------------------------------------------------------------------------------------------


def test_downstream_ids_follow_the_event_identity() -> None:
    """DOWNSTREAM. Every derived id must move with the event id and stay mutually consistent."""

    result = parse_ctu13_binetflow(
        FIXTURE, ingested_at=CREATED_AT, scenario_id="11",
        raw_reference="fixture", report_generated_at=CREATED_AT,
    )
    events = tuple(result.events)
    assert events, "the fixture must yield events"

    for event in events:
        assert event.event_id == event_id_for(event.source), "the declared id must match the source"

    scores = {event.event_id: 0.95 for event in events}
    detections = emit_ml_detections(
        events, scores, detector_name="d", detector_version="1.0.0", model_name="m",
        feature_version="1.1.0", threshold=0.2, created_at=CREATED_AT,
    )
    findings = aggregate_findings(detections, events, created_at=CREATED_AT)
    bundle = build_evidence_bundle(findings[0], detections, events, created_at=CREATED_AT)

    detection_ids = {detection.detection_id for detection in detections}
    event_ids = {event.event_id for event in events}

    assert bundle.finding_id == findings[0].finding_id
    assert set(bundle.detection_ids) <= detection_ids, "every cited detection must exist"
    assert {summary.event_id for summary in bundle.event_summaries} <= event_ids, (
        "every cited event must exist"
    )


def test_distinct_events_yield_distinct_bundles_end_to_end() -> None:
    """DOWNSTREAM. Two different files must not produce one bundle."""

    def bundle_for(checksum: str, path: str) -> object:
        source = _source(checksum=checksum, path=path)
        event = _event(source)
        events = (event,)
        detections = emit_ml_detections(
            events, {event.event_id: 0.95}, detector_name="d", detector_version="1.0.0",
            model_name="m", feature_version="1.1.0", threshold=0.2, created_at=CREATED_AT,
        )
        findings = aggregate_findings(detections, events, created_at=CREATED_AT)
        return build_evidence_bundle(findings[0], detections, events, created_at=CREATED_AT)

    first = bundle_for(CHECKSUM_A, "fileA.binetflow")
    second = bundle_for(CHECKSUM_B, "fileB.binetflow")

    assert first.evidence_bundle_id != second.evidence_bundle_id  # type: ignore[attr-defined]
    assert first.finding_id != second.finding_id  # type: ignore[attr-defined]
