"""Read-only probe: helpers that raise on a schema invariant the schema itself does not enforce.

Every probe asserts that the object it builds actually DIFFERS from the valid control
(the offending field is printed), so an "ACCEPTED" line can never come from an accidentally
valid object.

STATUS -- historical probe, pinned to a superseded commit.
    This script was run against the tree *before* commit f7db9ef ("fix(schemas): enforce four
    builder-side invariants in the schemas that own them"), which moved the spine's
    `_assert_history_open` invariant into the schemas themselves. That symbol no longer exists,
    so this script does NOT import against the current tree. It is retained as the provenance of
    that fix, not as a live check. `audit_negatives.py` is the probe that still runs.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from aegistrace.detection.evidence import build_evidence_bundle
from aegistrace.detection.findings import aggregate_findings
from aegistrace.detection.ml import emit_ml_detections
from aegistrace.features.behavioral import (
    BEHAVIORAL_FEATURE_NAMES,
    BehavioralFeatureDataset,
    BehavioralFeatureRecord,
    build_ctu13_behavioral_features,
)
from aegistrace.features.causal import (
    CAUSAL_FEATURE_NAMES,
    CausalFeatureDataset,
    CausalFeatureRecord,
    build_ctu13_causal_features,
)
from aegistrace.review.history import append_review, new_history
from aegistrace.schemas.detections import DetectionSeverity
from aegistrace.schemas.events import (
    Ctu13FlowDetails,
    EventProvenance,
    SecurityEvent,
    SourceRecordRef,
    SourceType,
    event_id_for,
)
from aegistrace.schemas.review import (
    EscalationState,
    HumanReview,
    ReviewDecision,
    ReviewTier,
    review_id_for,
)
from aegistrace.schemas.triage import (
    AssessorRole,
    DisagreementReason,
    ProviderMetadata,
    RawResponseReference,
    TriageAssessment,
    TriageCategory,
    TriageComparison,
)
from aegistrace.spine import SpineRecord, _assert_history_open, run_spine
from aegistrace.triage.agreement import compare_assessments
from aegistrace.triage.provider import (
    ProviderDescriptor,
    ProviderKind,
    StubTriageProvider,
)

FREEZE = json.loads(
    Path("configs/triage_provider_freeze.json").read_text(encoding="utf-8")
)
BASE = datetime(2026, 10, 8, 12, 0, tzinfo=UTC)
CREATED_AT = datetime(2026, 10, 8, 13, 0, tzinfo=UTC)
DIGEST = "a" * 64

print("=" * 78)
print("PROBE 1: TriageComparison vs compare_assessments (live working tree)")
print("=" * 78)


def _assessment(role, bundle_id, triage_id, cited=("finding-1",)):
    return TriageAssessment(
        triage_id=triage_id,
        role=role,
        evidence_bundle_id=bundle_id,
        bundle_version="1.0.0",
        finding_ids=(uuid4(),),
        input_snapshot_digest=DIGEST,
        category=TriageCategory.SUSPICIOUS,
        severity=DetectionSeverity.MEDIUM,
        summary="summary",
        evidence_summary="evidence summary",
        confidence_statement="moderate confidence",
        cited_evidence_ids=cited,
        next_step="escalate",
        provider_metadata=ProviderMetadata(
            provider="stub", model="stub", model_version="1", prompt_version="1.0.0"
        ),
        raw_response=RawResponseReference(reference="raw://1", digest=DIGEST, structured=True),
        created_at=CREATED_AT,
    )


bundle_id = uuid4()
analyst_id, adjudicator_id = uuid4(), uuid4()
analyst = _assessment(AssessorRole.TRIAGE_ANALYST, bundle_id, analyst_id)
adjudicator = _assessment(AssessorRole.EXPERT_ADJUDICATOR, bundle_id, adjudicator_id)
control = compare_assessments(analyst, adjudicator, created_at=CREATED_AT)
print(f"CONTROL from helper : roles={[r.value for r in control.roles]} "
      f"distinct_ids={len(set(control.assessment_ids)) == len(control.assessment_ids)}")


def _comparison(roles, assessment_ids, reasons=()):
    return TriageComparison(
        comparison_id=uuid4(),
        evidence_bundle_id=bundle_id,
        assessment_ids=assessment_ids,
        roles=roles,
        agreement=not reasons,
        agreement_score=0.0 if reasons else 1.0,
        disagreement_reasons=reasons,
        escalation_recommended=bool(reasons),
        created_at=CREATED_AT,
    )


# 1a: duplicate roles -- concurrently fixed while this audit ran
try:
    _comparison((AssessorRole.TRIAGE_ANALYST, AssessorRole.TRIAGE_ANALYST),
                (analyst_id, adjudicator_id))
    print("1a duplicate roles -> ACCEPTED (no longer expected)")
except Exception as exc:
    print(f"1a duplicate roles -> REFUSED by new validator: {type(exc).__name__}")

# 1b: duplicate assessment_ids (same assessment under two roles) -- still unguarded
dup_id = _comparison(
    (AssessorRole.TRIAGE_ANALYST, AssessorRole.EXPERT_ADJUDICATOR),
    (analyst_id, analyst_id),
    reasons=(DisagreementReason.CATEGORY_MISMATCH,),
)
assert len(set(dup_id.assessment_ids)) < len(dup_id.assessment_ids), "probe input does not vary"
print(f"1b DIRECT assessment_ids={[str(a)[:8] for a in dup_id.assessment_ids]} "
      f"distinct={len(set(dup_id.assessment_ids))}/{len(dup_id.assessment_ids)} -> ACCEPTED")
revived = TriageComparison.model_validate(json.loads(dup_id.model_dump_json()))
print(f"1b JSON ROUND-TRIP assessment_ids={[str(a)[:8] for a in revived.assessment_ids]} "
      f"-> ACCEPTED")

# 1c: empty roles + duplicate ids (the documented "not recorded" state skips the new validator)
no_roles = _comparison(
    (), (analyst_id, analyst_id), reasons=(DisagreementReason.CATEGORY_MISMATCH,)
)
assert no_roles.roles == () and len(set(no_roles.assessment_ids)) < len(no_roles.assessment_ids)
direct_ids = [str(a)[:8] for a in no_roles.assessment_ids]
print(f"1c DIRECT roles={no_roles.roles} assessment_ids={direct_ids} -> ACCEPTED")
revived = TriageComparison.model_validate(json.loads(no_roles.model_dump_json()))
print(f"1c JSON ROUND-TRIP roles={revived.roles} -> ACCEPTED")

for label, left, right in (
    ("same role", analyst, _assessment(AssessorRole.TRIAGE_ANALYST, bundle_id, uuid4())),
    ("same identifier", analyst, analyst),
):
    try:
        compare_assessments(left, right, created_at=CREATED_AT)
        print(f"HELPER {label}: DID NOT RAISE (unexpected)")
    except ValueError as exc:
        print(f"HELPER {label}: REFUSED -> {exc}")

print()
print("=" * 78)
print("PROBE 2: BehavioralFeatureDataset vs build_ctu13_behavioral_features")
print("=" * 78)


def _event(offset, src_ip, scenario_id):
    observed_at = BASE + timedelta(seconds=offset)
    source = SourceRecordRef(
        source_type=SourceType.CTU13,
        source_dataset="CTU-13",
        scenario_id=scenario_id,
        dataset_version="1.0.0",
        source_event_id=f"{src_ip}@{offset}",
        raw_payload_reference="data/fixtures/ctu13/scenario_11.binetflow",
    )
    return SecurityEvent(
        event_id=event_id_for(source),
        source=source,
        observed_at=observed_at,
        ingested_at=observed_at,
        event_type="network_flow",
        provenance=EventProvenance(
            adapter_name="probe",
            adapter_version="1.0.0",
            transformation_version="1.0.0",
            processed_at=observed_at,
        ),
        details=Ctu13FlowDetails(
            src_ip=src_ip, dst_ip="198.51.100.9", dst_port=80, protocol="tcp",
            source_label="flow=Background",
        ),
    )


def _brec(scenario_id):
    return BehavioralFeatureRecord(
        event_id=uuid4(),
        scenario_id=scenario_id,
        source_event_id="line-1",
        observed_at=BASE,
        ground_truth_label="unknown",
        values=tuple(0.0 for _ in BEHAVIORAL_FEATURE_NAMES),
    )


mixed = BehavioralFeatureDataset(records=(_brec("11"), _brec("12")))
scenarios = sorted({r.scenario_id for r in mixed.records})
assert len(scenarios) == 2, "probe input does not vary"
print(f"DIRECT scenario_ids={scenarios} -> ACCEPTED (2 distinct scenarios)")
revived = BehavioralFeatureDataset.model_validate(json.loads(mixed.model_dump_json()))
roundtrip_ids = sorted({r.scenario_id for r in revived.records})
print(f"JSON ROUND-TRIP scenario_ids={roundtrip_ids} -> ACCEPTED")
try:
    build_ctu13_behavioral_features((_event(0, "10.0.0.1", "11"), _event(10, "10.0.0.2", "12")))
    print("HELPER: DID NOT RAISE (unexpected)")
except ValueError as exc:
    print(f"HELPER: REFUSED -> {exc}")

print()
print("=" * 78)
print("PROBE 3: CausalFeatureDataset vs build_ctu13_causal_features")
print("=" * 78)


def _crec(scenario_id):
    return CausalFeatureRecord(
        event_id=uuid4(),
        scenario_id=scenario_id,
        source_event_id="line-1",
        observed_at=BASE,
        ground_truth_label="unknown",
        values=tuple(0.0 for _ in CAUSAL_FEATURE_NAMES),
    )


mixed = CausalFeatureDataset(records=(_crec("11"), _crec("12")))
scenarios = sorted({r.scenario_id for r in mixed.records})
assert len(scenarios) == 2, "probe input does not vary"
print(f"DIRECT scenario_ids={scenarios} -> ACCEPTED (2 distinct scenarios)")
revived = CausalFeatureDataset.model_validate(json.loads(mixed.model_dump_json()))
roundtrip_ids = sorted({r.scenario_id for r in revived.records})
print(f"JSON ROUND-TRIP scenario_ids={roundtrip_ids} -> ACCEPTED")
try:
    build_ctu13_causal_features((_event(0, "10.0.0.1", "11"), _event(10, "10.0.0.2", "12")))
    print("HELPER: DID NOT RAISE (unexpected)")
except ValueError as exc:
    print(f"HELPER: REFUSED -> {exc}")

print()
print("=" * 78)
print("PROBE 4: SpineRecord vs _assert_history_open / run_spine")
print("=" * 78)


def _bundle(src_ip="10.0.0.1"):
    events = tuple(_event(offset, src_ip, "11") for offset in (0.0, 10.0, 20.0))
    scores = {event.event_id: 0.95 for event in events}
    detections = emit_ml_detections(
        events, scores, detector_name="ctu13_phase3_random_forest", detector_version="1.0.0",
        model_name="random_forest", feature_version="1.1.0", threshold=0.2, created_at=CREATED_AT,
    )
    finding = aggregate_findings(detections, events, created_at=CREATED_AT)[0]
    return build_evidence_bundle(finding, detections, events, created_at=CREATED_AT)


def _stub(name, model_id):
    return StubTriageProvider(
        ProviderDescriptor(
            name=name, model_id=model_id, model_family="offline stub, not a model",
            kind=ProviderKind.OFFLINE_STUB, requires_egress=False,
        ),
        CREATED_AT,
    )


record = run_spine(
    bundles=(_bundle(),),
    analyst_provider=_stub("stub-triage-analyst", "stub-analyst-1"),
    adjudicator_provider=_stub("stub-expert-adjudicator", "stub-adjudicator-1"),
    freeze=FREEZE,
    created_at=CREATED_AT,
)[0]
print(f"CONTROL from run_spine: review_count={len(record.review_history.reviews)}")

review = HumanReview(
    review_id=review_id_for(
        subject_triage_id=record.review_history.subject_triage_id,
        subject_role=AssessorRole.TRIAGE_ANALYST,
        reviewer_ref="audit-probe",
        decision=ReviewDecision.CONFIRM,
        final_disposition="confirmed",
    ),
    subject_triage_id=record.review_history.subject_triage_id,
    subject_role=AssessorRole.TRIAGE_ANALYST,
    reviewer_ref="audit-probe",
    tier=ReviewTier.A_MACHINE_CHECK,
    decision=ReviewDecision.CONFIRM,
    notes="a review the spine must never carry",
    reviewed_at=CREATED_AT,
    escalation_state=EscalationState.NONE,
    final_disposition="confirmed",
)
closed = append_review(new_history(record.review_history.subject_triage_id), review)
assert len(closed.reviews) == 1, "probe input does not vary"
payload = json.loads(record.model_dump_json())
payload["review_history"] = json.loads(closed.model_dump_json())
assert payload["review_history"]["reviews"], "payload does not actually vary"
revived = SpineRecord.model_validate(payload)
print(f"DIRECT SpineRecord.model_validate(review_count={len(revived.review_history.reviews)}) "
      f"-> ACCEPTED (spine record carrying a human review)")
try:
    _assert_history_open(revived)
    print("HELPER _assert_history_open: DID NOT RAISE (unexpected)")
except RuntimeError as exc:
    print(f"HELPER _assert_history_open: REFUSED -> {exc}")

print()
print("=" * 78)
print("PROBE 5 (near-miss): ProviderDescriptor stub naming vs StubTriageProvider")
print("=" * 78)

bad_family = ProviderDescriptor(
    name="stub-x", model_id="stub-x", model_family="gpt-4", kind=ProviderKind.OFFLINE_STUB,
    requires_egress=False,
)
bad_prefix = ProviderDescriptor(
    name="stub-y", model_id="gpt-4", model_family="offline stub", kind=ProviderKind.OFFLINE_STUB,
    requires_egress=False,
)
assert bad_family.model_family != "offline stub" and bad_prefix.model_id != "stub-y"
print(f"DIRECT model_family={bad_family.model_family!r} (no 'stub') -> ACCEPTED")
print(f"DIRECT model_id={bad_prefix.model_id!r} (no 'stub-' prefix) -> ACCEPTED")
revived = ProviderDescriptor.model_validate(json.loads(bad_family.model_dump_json()))
print(f"JSON ROUND-TRIP model_family={revived.model_family!r} -> ACCEPTED")
for label, desc in (("family", bad_family), ("prefix", bad_prefix)):
    try:
        StubTriageProvider(desc, CREATED_AT)
        print(f"HELPER StubTriageProvider ({label}): DID NOT RAISE (unexpected)")
    except ValueError as exc:
        print(f"HELPER StubTriageProvider ({label}): REFUSED -> {exc}")
