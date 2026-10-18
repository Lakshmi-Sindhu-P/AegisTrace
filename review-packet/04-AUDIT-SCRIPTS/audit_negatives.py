"""Read-only probe: negatives -- rules the schema DOES enforce (helper/schema agree)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from aegistrace.features.network import FEATURE_NAMES, FeatureDataset, FeatureRecord
from aegistrace.review.history import new_history
from aegistrace.schemas.findings import EvidenceBundle, Finding
from aegistrace.schemas.review import ReviewHistory
from aegistrace.schemas.triage import TriageComparison
from aegistrace.triage.corpus import TriageCorpus
from aegistrace.triage.provider import ProviderDescriptor, ProviderKind
from aegistrace.triage.run import RunBudget, TriageRun

CREATED_AT = datetime(2026, 10, 8, 13, 0, tzinfo=UTC)
DIGEST = "a" * 64


def check(label, fn):
    try:
        fn()
        print(f"{label}: ACCEPTED  <-- expected REFUSED")
    except Exception as exc:
        print(f"{label}: REFUSED ({type(exc).__name__})")


print("== schema-enforced negatives ==")
check(
    "TriageCorpus(entries=())            [corpus.py:88 rule]",
    lambda: TriageCorpus(
        corpus_version="1.0.0", corpus_digest=DIGEST, created_at=CREATED_AT, entries=()
    ),
)
check(
    "EvidenceBundle(detection_ids=())    [evidence.py:137 rule]",
    lambda: EvidenceBundle(
        evidence_bundle_id=uuid4(), bundle_version="1.0.0", finding_id=uuid4(),
        detection_ids=(), event_summaries=(), created_at=CREATED_AT,
    ),
)
check(
    "FeatureRecord(scenario_id=None)     [network.py:206 rule]",
    lambda: FeatureRecord(
        event_id=uuid4(), scenario_id=None, source_event_id="line-1",
        ground_truth_label="unknown", values=tuple(0.0 for _ in FEATURE_NAMES),
    ),
)
check(
    "FeatureRecord(values=wrong length)  [network.py:80 rule]",
    lambda: FeatureRecord(
        event_id=uuid4(), scenario_id="11", source_event_id="line-1",
        ground_truth_label="unknown", values=(0.0,),
    ),
)
check(
    "FeatureDataset(feature_names=bad)   [network.py:95 rule]",
    lambda: FeatureDataset(feature_names=("nope",), records=()),
)
check(
    "Finding(window_end<window_start)    [findings.py validate_window]",
    lambda: Finding(
        finding_id=uuid4(), aggregation_version="1.0.0", event_ids=(uuid4(),),
        detection_ids=(uuid4(),), source_host="h", window_start=CREATED_AT,
        window_end=datetime(2026, 10, 8, 12, 0, tzinfo=UTC),
        proposed_severity="low", created_at=CREATED_AT, note="n",
    ),
)
check(
    "ProviderDescriptor(REMOTE,egress=False) [provider.py:71]",
    lambda: ProviderDescriptor(
        name="n", model_id="m", model_family="f", kind=ProviderKind.REMOTE,
        requires_egress=False,
    ),
)
check(
    "TriageRun(aborted,no reason)        [run.py:220]",
    lambda: TriageRun(
        run_id=uuid4(), created_at=CREATED_AT, freeze_version="1.0.0",
        analyst_descriptor=ProviderDescriptor(
            name="a", model_id="stub-a", model_family="offline stub",
            kind=ProviderKind.OFFLINE_STUB, requires_egress=False),
        adjudicator_descriptor=ProviderDescriptor(
            name="b", model_id="stub-b", model_family="offline stub",
            kind=ProviderKind.OFFLINE_STUB, requires_egress=False),
        budget=RunBudget(max_bundles_per_run=1, max_assessments_per_run=1, max_total_calls=1),
        calls_made=0, aborted=True, abort_reason=None, synthetic=True,
    ),
)
check(
    "TriageRun(completed,with reason)    [run.py:222]",
    lambda: TriageRun(
        run_id=uuid4(), created_at=CREATED_AT, freeze_version="1.0.0",
        analyst_descriptor=ProviderDescriptor(
            name="a", model_id="stub-a", model_family="offline stub",
            kind=ProviderKind.OFFLINE_STUB, requires_egress=False),
        adjudicator_descriptor=ProviderDescriptor(
            name="b", model_id="stub-b", model_family="offline stub",
            kind=ProviderKind.OFFLINE_STUB, requires_egress=False),
        budget=RunBudget(max_bundles_per_run=1, max_assessments_per_run=1, max_total_calls=1),
        calls_made=0, aborted=False, abort_reason="why", synthetic=True,
    ),
)
check(
    "ReviewHistory(dangling supersede)   [review.py:241, the #42 fix]",
    lambda: ReviewHistory.model_validate(
        {
            "subject_triage_id": str(uuid4()),
            "reviews": [
                {
                    "review_id": str(uuid4()), "subject_triage_id": str(uuid4()),
                    "subject_role": "triage_analyst", "reviewer_ref": "r", "tier":
                    "tier_a_machine_check", "decision": "confirm", "notes": "n",
                    "reviewed_at": CREATED_AT.isoformat(), "escalation_state": "none",
                    "final_disposition": "d", "supersedes_review_id": str(uuid4()),
                }
            ],
        }
    ),
)
print()
print("== control: valid constructions still pass ==")
print("ReviewHistory(empty) ACCEPTED:", new_history(uuid4()).reviews == ())
print("TriageComparison roles aligned ACCEPTED:", TriageComparison(
    comparison_id=uuid4(), evidence_bundle_id=uuid4(), assessment_ids=(uuid4(), uuid4()),
    roles=("triage_analyst", "expert_adjudicator"), agreement=True, agreement_score=1.0,
    escalation_recommended=False, created_at=CREATED_AT,
).roles)
