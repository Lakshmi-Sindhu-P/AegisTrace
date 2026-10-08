"""Tests for the provider boundary and the independent-triage orchestrator.

The properties defended here are the ones the governance freeze depends on: an offline provider can
never be mistaken for a real model, a remote provider cannot run while the freeze is
``BLOCKED_HUMAN``, a recorded response cannot be invented for an unknown snapshot, and a run is
deterministic and refuses to compare two different inputs.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

from aegistrace.detection.evidence import build_evidence_bundle
from aegistrace.detection.findings import aggregate_findings
from aegistrace.detection.ml import emit_ml_detections
from aegistrace.schemas.events import (
    Ctu13FlowDetails,
    EventProvenance,
    SecurityEvent,
    SourceRecordRef,
    SourceType,
    event_id_for,
)
from aegistrace.schemas.findings import EvidenceBundle
from aegistrace.schemas.triage import AssessorRole, FailedAssessment, TriageAssessment
from aegistrace.triage.provider import (
    ProviderDescriptor,
    ProviderKind,
    ProviderRequest,
    ProviderResponse,
    RecordedTriageProvider,
    StubTriageProvider,
    digest_text,
    request_digest,
)
from aegistrace.triage.run import (
    APPROVED_EGRESS_FREEZE_STATUSES,
    RunBudget,
    TriageRun,
    assert_provider_permitted,
    run_independent_triage,
)
from aegistrace.triage.snapshot import snapshot_digest

BASE = datetime(2026, 10, 8, 12, 0, tzinfo=UTC)
CREATED_AT = datetime(2026, 10, 8, 13, 0, tzinfo=UTC)
REPO_ROOT = Path(__file__).resolve().parents[1]
FREEZE_PATH = REPO_ROOT / "configs" / "triage_provider_freeze.json"


def _event(offset_seconds: float, src_ip: str) -> SecurityEvent:
    observed_at = BASE + timedelta(seconds=offset_seconds)
    source = SourceRecordRef(
        source_type=SourceType.CTU13,
        source_dataset="CTU-13",
        scenario_id="11",
        dataset_version="1.0.0",
        source_event_id=f"{src_ip}@{offset_seconds}",
        raw_payload_reference="data/fixtures/ctu13/scenario_11.binetflow",
    )
    return SecurityEvent(
        event_id=event_id_for(source),
        source=source,
        observed_at=observed_at,
        ingested_at=observed_at,
        event_type="network_flow",
        provenance=EventProvenance(
            adapter_name="test_fixture",
            adapter_version="1.0.0",
            transformation_version="1.0.0",
            processed_at=observed_at,
        ),
        details=Ctu13FlowDetails(
            src_ip=src_ip,
            dst_ip="198.51.100.9",
            dst_port=80,
            protocol="tcp",
            source_label="flow=Background",
        ),
    )


def _bundle(src_ip: str = "10.0.0.1") -> EvidenceBundle:
    events = tuple(_event(offset, src_ip) for offset in (0.0, 10.0, 20.0))
    scores = {event.event_id: 0.95 for event in events}
    detections = emit_ml_detections(
        events,
        scores,
        detector_name="ctu13_phase3_random_forest",
        detector_version="1.0.0",
        model_name="random_forest",
        feature_version="1.1.0",
        threshold=0.2,
        created_at=CREATED_AT,
    )
    finding = aggregate_findings(detections, events, created_at=CREATED_AT)[0]
    return build_evidence_bundle(finding, detections, events, created_at=CREATED_AT)


def _assessment_text(bundle: EvidenceBundle, *, category: str, severity: str, summary: str) -> str:
    payload = {
        "category": category,
        "severity": severity,
        "summary": summary,
        "evidence_summary": "three flow events from one source host",
        "confidence_statement": "deterministic grouping; no payload inspection",
        "cited_evidence_ids": [str(bundle.finding_id)],
        "uncertainties": ["no payload available"],
        "unsupported_claim_flags": [],
        "next_step": "route to human review",
    }
    return json.dumps(payload, sort_keys=True)


def _recorded_descriptor(
    name: str = "offline-recorded-fixture",
    model_id: str = "recorded-fixture-2026-10-08",
) -> ProviderDescriptor:
    return ProviderDescriptor(
        name=name,
        model_id=model_id,
        model_family="recorded-fixture",
        kind=ProviderKind.OFFLINE_RECORDED,
        requires_egress=False,
    )


def _adjudicator_recorded_descriptor() -> ProviderDescriptor:
    return _recorded_descriptor(
        name="offline-recorded-adjudicator",
        model_id="recorded-adjudicator-fixture-2026-10-08",
    )


def _stub_descriptor(
    name: str = "offline-stub",
    model_id: str = "stub-deterministic-echo",
) -> ProviderDescriptor:
    return ProviderDescriptor(
        name=name,
        model_id=model_id,
        model_family="deterministic-stub",
        kind=ProviderKind.OFFLINE_STUB,
        requires_egress=False,
    )


def _adjudicator_stub_descriptor() -> ProviderDescriptor:
    return _stub_descriptor(name="offline-stub-adjudicator", model_id="stub-deterministic-echo-2")


def _recorded_pair(
    bundle: EvidenceBundle,
) -> tuple[RecordedTriageProvider, RecordedTriageProvider]:
    """Two distinct offline descriptors, one per role, sharing the same recorded responses."""

    responses = _recorded_responses(bundle)
    return (
        RecordedTriageProvider(_recorded_descriptor(), responses, CREATED_AT),
        RecordedTriageProvider(_adjudicator_recorded_descriptor(), responses, CREATED_AT),
    )


def _remote_descriptor(
    name: str = "remote-llm-provider",
    model_id: str = "remote-model-v1",
    model_family: str = "remote-family",
) -> ProviderDescriptor:
    return ProviderDescriptor(
        name=name,
        model_id=model_id,
        model_family=model_family,
        kind=ProviderKind.REMOTE,
        requires_egress=True,
    )


def _recorded_responses(bundle: EvidenceBundle) -> dict[tuple[AssessorRole, str], str]:
    digest = snapshot_digest(bundle)
    return {
        (AssessorRole.TRIAGE_ANALYST, digest): _assessment_text(
            bundle,
            category="likely_malicious",
            severity="high",
            summary="analyst reads this as hostile",
        ),
        (AssessorRole.EXPERT_ADJUDICATOR, digest): _assessment_text(
            bundle,
            category="likely_benign",
            severity="low",
            summary="adjudicator reads this as benign",
        ),
    }


def _freeze(**budget_overrides: int) -> dict:
    data = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    if budget_overrides:
        data = dict(data)
        data["budget"] = {**data["budget"], **budget_overrides}
    return data


def _approved_freeze() -> dict:
    """The repo freeze with an approved egress status, for exercising remote descriptors."""

    data = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    data["status"] = "APPROVED"
    return data


class _RecordingProvider:
    """Offline provider that forwards to a recorded provider and keeps the requests it saw."""

    def __init__(self, descriptor: ProviderDescriptor, responses, created_at: datetime) -> None:
        self._inner = RecordedTriageProvider(descriptor, responses, created_at)
        self.requests: list[ProviderRequest] = []

    @property
    def descriptor(self) -> ProviderDescriptor:
        return self._inner.descriptor

    def complete(self, request: ProviderRequest) -> ProviderResponse:
        self.requests.append(request)
        return self._inner.complete(request)


class _RemoteProvider:
    """A remote descriptor whose transport is a tripwire: calling it means the boundary failed."""

    def __init__(self) -> None:
        self.calls = 0

    @property
    def descriptor(self) -> ProviderDescriptor:
        return _remote_descriptor()

    def complete(self, request: ProviderRequest) -> ProviderResponse:
        self.calls += 1
        raise AssertionError("a remote provider must never be reached")


class _MismatchedDigestProvider:
    """Offline provider that lies about the snapshot digest it answered."""

    def __init__(self, descriptor: ProviderDescriptor, created_at: datetime) -> None:
        self._descriptor = descriptor
        self._created_at = created_at

    @property
    def descriptor(self) -> ProviderDescriptor:
        return self._descriptor

    def complete(self, request: ProviderRequest) -> ProviderResponse:
        raw_text = json.dumps({"category": "suspicious"}, sort_keys=True)
        return ProviderResponse(
            descriptor=self._descriptor,
            role=request.role,
            snapshot_digest="b" * 64,
            raw_text=raw_text,
            request_digest=request_digest(request),
            response_digest=digest_text(raw_text),
            synthetic=True,
            created_at=self._created_at,
        )


class _NonJsonProvider:
    """Offline provider returning free text rather than structured JSON."""

    def __init__(self, descriptor: ProviderDescriptor, created_at: datetime) -> None:
        self._descriptor = descriptor
        self._created_at = created_at

    @property
    def descriptor(self) -> ProviderDescriptor:
        return self._descriptor

    def complete(self, request: ProviderRequest) -> ProviderResponse:
        raw_text = f"not-json: role={request.role.value} digest={request.snapshot_digest}"
        return ProviderResponse(
            descriptor=self._descriptor,
            role=request.role,
            snapshot_digest=request.snapshot_digest,
            raw_text=raw_text,
            request_digest=request_digest(request),
            response_digest=digest_text(raw_text),
            synthetic=True,
            created_at=self._created_at,
        )


def test_remote_descriptor_without_egress_is_rejected() -> None:
    with pytest.raises(ValidationError, match="REMOTE provider must declare requires_egress=True"):
        ProviderDescriptor(
            name="contradiction",
            model_id="m",
            model_family="f",
            kind=ProviderKind.REMOTE,
            requires_egress=False,
        )


def test_offline_descriptor_requiring_egress_is_rejected() -> None:
    with pytest.raises(ValidationError, match="must declare requires_egress=False"):
        ProviderDescriptor(
            name="contradiction",
            model_id="m",
            model_family="f",
            kind=ProviderKind.OFFLINE_STUB,
            requires_egress=True,
        )


def test_recorded_provider_rejects_a_remote_descriptor() -> None:
    with pytest.raises(ValueError, match="is remote"):
        RecordedTriageProvider(_remote_descriptor(), {}, CREATED_AT)


def test_recorded_provider_raises_on_a_missing_key_naming_role_and_digest() -> None:
    provider = RecordedTriageProvider(_recorded_descriptor(), {}, CREATED_AT)
    request = ProviderRequest(
        role=AssessorRole.TRIAGE_ANALYST,
        snapshot_digest="c" * 64,
        snapshot_json="{}",
        prompt="p",
    )

    with pytest.raises(KeyError) as excinfo:
        provider.complete(request)

    assert "triage_analyst" in str(excinfo.value)
    assert "c" * 64 in str(excinfo.value)


def test_offline_response_claiming_non_synthetic_is_rejected() -> None:
    request = ProviderRequest(
        role=AssessorRole.TRIAGE_ANALYST,
        snapshot_digest="c" * 64,
        snapshot_json="{}",
        prompt="p",
    )
    with pytest.raises(ValidationError, match="must be synthetic=True"):
        ProviderResponse(
            descriptor=_stub_descriptor(),
            role=AssessorRole.TRIAGE_ANALYST,
            snapshot_digest="c" * 64,
            raw_text="{}",
            request_digest=request_digest(request),
            response_digest=digest_text("{}"),
            synthetic=False,
            created_at=CREATED_AT,
        )


def test_stub_output_is_always_synthetic() -> None:
    bundle = _bundle()
    provider = StubTriageProvider(_stub_descriptor(), CREATED_AT)
    request = ProviderRequest(
        role=AssessorRole.EXPERT_ADJUDICATOR,
        snapshot_digest=snapshot_digest(bundle),
        snapshot_json=json.dumps(bundle.model_dump(mode="json")),
        prompt="p",
    )

    response = provider.complete(request)

    assert response.synthetic is True
    assert response.response_digest == digest_text(response.raw_text)
    assert provider.descriptor.model_id.startswith("stub-")
    assert "stub" in provider.descriptor.model_family


def test_stub_provider_rejects_a_descriptor_that_could_be_mistaken_for_a_model() -> None:
    bad = ProviderDescriptor(
        name="offline-stub",
        model_id="deepseek-v4-flash",
        model_family="real-model",
        kind=ProviderKind.OFFLINE_STUB,
        requires_egress=False,
    )
    with pytest.raises(ValueError, match="model_family must contain"):
        StubTriageProvider(bad, CREATED_AT)

    unstubbed_id = ProviderDescriptor(
        name="offline-stub",
        model_id="echo",
        model_family="deterministic-stub",
        kind=ProviderKind.OFFLINE_STUB,
        requires_egress=False,
    )
    with pytest.raises(ValueError, match="must start with 'stub-'"):
        StubTriageProvider(unstubbed_id, CREATED_AT)


def test_stub_provider_rejects_a_recorded_descriptor() -> None:
    with pytest.raises(ValueError, match="requires an OFFLINE_STUB descriptor"):
        StubTriageProvider(_recorded_descriptor(), CREATED_AT)


def test_remote_provider_is_refused_under_blocked_human() -> None:
    provider = _RemoteProvider()

    with pytest.raises(PermissionError) as excinfo:
        run_independent_triage(
            bundles=[_bundle()],
            analyst_provider=provider,
            adjudicator_provider=provider,
            freeze=_freeze(),
            created_at=CREATED_AT,
        )

    message = str(excinfo.value)
    assert "remote-llm-provider" in message
    assert "BLOCKED_HUMAN" in message
    assert provider.calls == 0


def test_assert_provider_permitted_refuses_and_allows() -> None:
    assert "BLOCKED_HUMAN" not in APPROVED_EGRESS_FREEZE_STATUSES
    assert_provider_permitted(_stub_descriptor(), "BLOCKED_HUMAN")

    with pytest.raises(PermissionError, match="BLOCKED_HUMAN"):
        assert_provider_permitted(_remote_descriptor(), "BLOCKED_HUMAN")

    for status in APPROVED_EGRESS_FREEZE_STATUSES:
        assert_provider_permitted(_remote_descriptor(), status)


def test_run_over_recorded_responses_is_deterministic_and_byte_identical() -> None:
    bundle = _bundle()
    responses = _recorded_responses(bundle)

    def _run() -> str:
        analyst = RecordedTriageProvider(_recorded_descriptor(), responses, CREATED_AT)
        adjudicator = RecordedTriageProvider(
            _adjudicator_recorded_descriptor(), responses, CREATED_AT
        )
        run = run_independent_triage(
            bundles=[bundle],
            analyst_provider=analyst,
            adjudicator_provider=adjudicator,
            freeze=_freeze(),
            created_at=CREATED_AT,
        )
        return run.model_dump_json()

    first, second = _run(), _run()

    assert first == second
    run = json.loads(first)
    assert run["calls_made"] == 2
    assert len(run["assessments"]) == 2
    assert len(run["comparisons"]) == 1
    assert run["synthetic"] is True
    assert run["aborted"] is False
    assert run["comparisons"][0]["escalation_recommended"] is True


def test_both_roles_receive_the_identical_snapshot() -> None:
    bundle = _bundle()
    responses = _recorded_responses(bundle)
    analyst = _RecordingProvider(_recorded_descriptor(), responses, CREATED_AT)
    adjudicator = _RecordingProvider(_adjudicator_recorded_descriptor(), responses, CREATED_AT)

    run_independent_triage(
        bundles=[bundle],
        analyst_provider=analyst,
        adjudicator_provider=adjudicator,
        freeze=_freeze(),
        created_at=CREATED_AT,
    )

    requests = [*analyst.requests, *adjudicator.requests]
    assert len(requests) == 2
    digests = {request.snapshot_digest for request in requests}
    snapshots = {request.snapshot_json for request in requests}
    assert digests == {snapshot_digest(bundle)}
    assert len(snapshots) == 1
    assert {request.role for request in requests} == {
        AssessorRole.TRIAGE_ANALYST,
        AssessorRole.EXPERT_ADJUDICATOR,
    }


def test_budget_exhaustion_aborts_rather_than_raises() -> None:
    bundle = _bundle()
    analyst, adjudicator = _recorded_pair(bundle)

    run = run_independent_triage(
        bundles=[bundle],
        analyst_provider=analyst,
        adjudicator_provider=adjudicator,
        freeze=_freeze(max_total_calls=1),
        created_at=CREATED_AT,
    )

    assert run.aborted is True
    assert run.calls_made == 0
    assert run.assessments == ()
    assert run.abort_reason is not None and "call budget" in run.abort_reason


def test_assessment_budget_exhaustion_aborts_rather_than_raises() -> None:
    bundles = [_bundle("10.0.0.1"), _bundle("10.0.0.2")]
    responses: dict[tuple[AssessorRole, str], str] = {}
    for bundle in bundles:
        responses.update(_recorded_responses(bundle))
    analyst = RecordedTriageProvider(_recorded_descriptor(), responses, CREATED_AT)
    adjudicator = RecordedTriageProvider(_adjudicator_recorded_descriptor(), responses, CREATED_AT)

    run = run_independent_triage(
        bundles=bundles,
        analyst_provider=analyst,
        adjudicator_provider=adjudicator,
        freeze=_freeze(max_assessments_per_run=2),
        created_at=CREATED_AT,
    )

    assert run.aborted is True
    assert run.calls_made == 2
    assert len(run.assessments) == 2
    assert run.abort_reason is not None and "assessment budget" in run.abort_reason


def test_bundle_overflow_is_enforced_and_recorded() -> None:
    bundles = [_bundle("10.0.0.1"), _bundle("10.0.0.2")]
    responses: dict[tuple[AssessorRole, str], str] = {}
    for bundle in bundles:
        responses.update(_recorded_responses(bundle))
    analyst = RecordedTriageProvider(_recorded_descriptor(), responses, CREATED_AT)
    adjudicator = RecordedTriageProvider(
        _adjudicator_recorded_descriptor(), responses, CREATED_AT
    )

    run = run_independent_triage(
        bundles=bundles,
        analyst_provider=analyst,
        adjudicator_provider=adjudicator,
        freeze=_freeze(max_bundles_per_run=1),
        created_at=CREATED_AT,
    )

    assert run.aborted is True
    assert run.calls_made == 2
    assert len(run.assessments) == 2
    assert run.abort_reason is not None and "bundle budget" in run.abort_reason


def test_snapshot_digest_mismatch_between_roles_aborts() -> None:
    analyst = _MismatchedDigestProvider(_stub_descriptor(), CREATED_AT)
    adjudicator = _MismatchedDigestProvider(_adjudicator_stub_descriptor(), CREATED_AT)

    run = run_independent_triage(
        bundles=[_bundle()],
        analyst_provider=analyst,
        adjudicator_provider=adjudicator,
        freeze=_freeze(),
        created_at=CREATED_AT,
    )

    assert run.aborted is True
    assert run.assessments == ()
    assert run.comparisons == ()
    assert run.abort_reason is not None and "snapshot digest mismatch" in run.abort_reason


def test_stub_run_produces_admissible_synthetic_assessments() -> None:
    bundle = _bundle()
    analyst = StubTriageProvider(_stub_descriptor(), CREATED_AT)
    adjudicator = StubTriageProvider(_adjudicator_stub_descriptor(), CREATED_AT)

    run = run_independent_triage(
        bundles=[bundle],
        analyst_provider=analyst,
        adjudicator_provider=adjudicator,
        freeze=_freeze(),
        created_at=CREATED_AT,
    )

    assert run.synthetic is True
    assert run.independence_established is False
    assert all(isinstance(item, TriageAssessment) for item in run.assessments)
    assert len(run.comparisons) == 1
    assert {item.role for item in run.assessments} == {
        AssessorRole.TRIAGE_ANALYST,
        AssessorRole.EXPERT_ADJUDICATOR,
    }


def test_non_json_provider_text_is_preserved_as_a_failed_attempt() -> None:
    analyst = _NonJsonProvider(_stub_descriptor(), CREATED_AT)
    adjudicator = _NonJsonProvider(_adjudicator_stub_descriptor(), CREATED_AT)
    run = run_independent_triage(
        bundles=[_bundle()],
        analyst_provider=analyst,
        adjudicator_provider=adjudicator,
        freeze=_freeze(),
        created_at=CREATED_AT,
    )

    assert all(isinstance(item, FailedAssessment) for item in run.assessments)
    assert run.comparisons[0].escalation_recommended is True


def test_stub_handles_a_snapshot_without_a_finding_id() -> None:
    provider = StubTriageProvider(_stub_descriptor(), CREATED_AT)
    request = ProviderRequest(
        role=AssessorRole.TRIAGE_ANALYST,
        snapshot_digest="d" * 64,
        snapshot_json="{}",
        prompt="p",
    )

    payload = json.loads(provider.complete(request).raw_text)

    assert payload["cited_evidence_ids"] == []
    assert payload["category"] == "insufficient_evidence"


def test_missing_budget_block_aborts_without_raising() -> None:
    bundle = _bundle()
    analyst, adjudicator = _recorded_pair(bundle)
    freeze = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    freeze.pop("budget")

    run = run_independent_triage(
        bundles=[bundle],
        analyst_provider=analyst,
        adjudicator_provider=adjudicator,
        freeze=freeze,
        created_at=CREATED_AT,
    )

    assert run.aborted is True
    assert run.budget.max_total_calls == 0


def test_boundary_modules_cannot_open_a_network_connection() -> None:
    forbidden = re.compile(
        r"^\s*(?:import|from)\s+"
        r"(requests|httpx|aiohttp|urllib|http\.client|socket|openai|anthropic|litellm)\b"
    )
    for name in ("provider.py", "run.py"):
        source = (REPO_ROOT / "src" / "aegistrace" / "triage" / name).read_text(encoding="utf-8")
        offenders = [line for line in source.splitlines() if forbidden.match(line)]
        assert offenders == [], f"{name} imports a network module: {offenders}"


def test_run_never_mutates_incoming_bundles() -> None:
    bundle = _bundle()
    before = bundle.model_dump_json()
    analyst, adjudicator = _recorded_pair(bundle)

    run = run_independent_triage(
        bundles=[bundle],
        analyst_provider=analyst,
        adjudicator_provider=adjudicator,
        freeze=_freeze(),
        created_at=CREATED_AT,
    )

    assert bundle.model_dump_json() == before
    assert run.assessments[0].evidence_bundle_id == bundle.evidence_bundle_id


def test_triage_run_rejects_an_abort_reason_that_contradicts_its_state() -> None:
    descriptor = _stub_descriptor()
    common = {
        "run_id": uuid4(),
        "created_at": CREATED_AT,
        "freeze_version": "1.0.0",
        "analyst_descriptor": descriptor,
        "adjudicator_descriptor": descriptor,
        "budget": RunBudget(max_bundles_per_run=1, max_assessments_per_run=2, max_total_calls=2),
        "calls_made": 0,
        "synthetic": True,
    }

    with pytest.raises(ValidationError, match="must record an abort_reason"):
        TriageRun(**common, aborted=True)
    with pytest.raises(ValidationError, match="must not record an abort_reason"):
        TriageRun(**common, aborted=False, abort_reason="should not be here")


class _DeclaredRemoteProvider:
    """A REMOTE descriptor answered locally; used only to exercise independence determination."""

    def __init__(
        self, descriptor: ProviderDescriptor, raw_text: str, created_at: datetime
    ) -> None:
        self._descriptor = descriptor
        self._raw_text = raw_text
        self._created_at = created_at
        self.calls = 0

    @property
    def descriptor(self) -> ProviderDescriptor:
        return self._descriptor

    def complete(self, request: ProviderRequest) -> ProviderResponse:
        self.calls += 1
        return ProviderResponse(
            descriptor=self._descriptor,
            role=request.role,
            snapshot_digest=request.snapshot_digest,
            raw_text=self._raw_text,
            request_digest=request_digest(request),
            response_digest=digest_text(self._raw_text),
            synthetic=False,
            created_at=self._created_at,
        )


def test_one_assessor_under_two_labels_is_refused() -> None:
    bundle = _bundle()
    provider = _RecordingProvider(_recorded_descriptor(), _recorded_responses(bundle), CREATED_AT)

    with pytest.raises(ValueError, match="not independence"):
        run_independent_triage(
            bundles=[bundle],
            analyst_provider=provider,
            adjudicator_provider=provider,
            freeze=_freeze(),
            created_at=CREATED_AT,
        )

    assert provider.requests == []


def test_governance_gate_precedes_the_independence_check() -> None:
    provider = _RemoteProvider()

    with pytest.raises(PermissionError, match="requires network egress"):
        run_independent_triage(
            bundles=[_bundle()],
            analyst_provider=provider,
            adjudicator_provider=provider,
            freeze=_freeze(),
            created_at=CREATED_AT,
        )

    assert provider.calls == 0


def test_distinct_offline_descriptors_run_but_do_not_establish_independence() -> None:
    bundle = _bundle()
    analyst, adjudicator = _recorded_pair(bundle)

    run = run_independent_triage(
        bundles=[bundle],
        analyst_provider=analyst,
        adjudicator_provider=adjudicator,
        freeze=_freeze(),
        created_at=CREATED_AT,
    )

    assert run.aborted is False
    assert run.calls_made == 2
    assert run.independence_established is False
    assert "synthetic offline providers" in run.independence_basis


def _declared_remote_pair(
    bundle: EvidenceBundle, analyst_family: str, adjudicator_family: str
) -> tuple[_DeclaredRemoteProvider, _DeclaredRemoteProvider]:
    raw = _assessment_text(
        bundle, category="likely_malicious", severity="high", summary="declared remote reading"
    )
    analyst = _DeclaredRemoteProvider(
        _remote_descriptor(name="remote-analyst", model_id="m-a", model_family=analyst_family),
        raw,
        CREATED_AT,
    )
    adjudicator = _DeclaredRemoteProvider(
        _remote_descriptor(
            name="remote-adjudicator", model_id="m-b", model_family=adjudicator_family
        ),
        raw,
        CREATED_AT,
    )
    return analyst, adjudicator


def test_remote_providers_sharing_a_family_do_not_establish_independence() -> None:
    bundle = _bundle()
    analyst, adjudicator = _declared_remote_pair(bundle, "shared-family", "shared-family")

    run = run_independent_triage(
        bundles=[bundle],
        analyst_provider=analyst,
        adjudicator_provider=adjudicator,
        freeze=_approved_freeze(),
        created_at=CREATED_AT,
    )

    assert run.independence_established is False
    assert "model_family" in run.independence_basis


def test_remote_providers_with_distinct_families_establish_independence() -> None:
    bundle = _bundle()
    analyst, adjudicator = _declared_remote_pair(bundle, "family-a", "family-b")

    run = run_independent_triage(
        bundles=[bundle],
        analyst_provider=analyst,
        adjudicator_provider=adjudicator,
        freeze=_approved_freeze(),
        created_at=CREATED_AT,
    )

    assert run.independence_established is True
    assert "distinct remote descriptors" in run.independence_basis
