"""Deterministic orchestrator for the two independent, mutually blind triage assessments.

This module wires the frozen pieces together — the snapshot, the provider boundary, assessment
admission, and the agreement engine — without ever gaining the ability to leak data:

* It calls :func:`assert_provider_permitted` for both providers **before** any other work. A
  provider whose descriptor requires egress is refused with a raised :class:`PermissionError`
  unless the freeze artifact's status is explicitly approved. The freeze is ``BLOCKED_HUMAN``, so a
  remote provider is refused here and no request is ever built for it.
* It never writes to disk and never mutates the incoming bundles. The only side effect is the
  in-memory :class:`TriageRun` it returns.
* For each bundle it builds the snapshot **once** and sends the byte-identical
  ``snapshot_json``/``snapshot_digest`` to both roles. Both responses must report that same digest;
  a mismatch is recorded as an abort rather than compared, because comparing two different inputs
  would measure the inputs instead of the assessors.
* Budget exhaustion and the digest mismatch are recorded as an ``aborted`` run with a reason, not
  raised as exceptions. A raised error is reserved for a governance refusal, which is a different
  kind of event: it must stop the process rather than produce a partial record.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from pydantic import Field, field_validator, model_validator

from aegistrace.schemas.common import FrozenSchema, NonEmptyText, normalize_utc
from aegistrace.schemas.findings import EvidenceBundle
from aegistrace.schemas.triage import (
    AssessorRole,
    ProviderMetadata,
    RawResponseReference,
    TriageComparison,
)
from aegistrace.triage.agreement import compare_assessments
from aegistrace.triage.assessment import AssessmentOutcome, build_assessment
from aegistrace.triage.provider import (
    ProviderDescriptor,
    ProviderKind,
    ProviderRequest,
    ProviderResponse,
    TriageProvider,
)
from aegistrace.triage.snapshot import canonical_snapshot_json, snapshot_digest

_BASE = "https://github.com/Lakshmi-Sindhu-P/AegisTrace"
TRIAGE_RUN_ID_NAMESPACE = uuid5(NAMESPACE_URL, f"{_BASE}/triage-runs/v1")

#: Freeze statuses that mean a human has approved network egress. Deliberately small, and
#: deliberately excludes ``BLOCKED_HUMAN``; adding a value here is a governance change.
APPROVED_EGRESS_FREEZE_STATUSES: frozenset[str] = frozenset(
    {"APPROVED", "EGRESS_APPROVED", "HUMAN_APPROVED"}
)

#: Version of the provider interface contract, recorded in provider metadata. The descriptor
#: intentionally does not carry a model version; pinning a real model version is a governance
#: decision recorded in the freeze artifact, not something this boundary may invent.
PROVIDER_INTERFACE_VERSION = "1.0.0"
TRIAGE_PROMPT_VERSION = "1.0.0"

_TRIAGE_PROMPT = (
    "Assess the evidence bundle described by the canonical snapshot below. Cite only evidence "
    "identifiers present in the snapshot. Return a structured assessment with category, severity, "
    "summary, evidence_summary, confidence_statement, cited_evidence_ids, uncertainties, "
    "unsupported_claim_flags, and next_step. Abstention is a valid answer."
)


def _independence_finding(
    analyst: ProviderDescriptor, adjudicator: ProviderDescriptor
) -> tuple[bool, str, str | None]:
    """The single implementation of the independence question.

    Returns ``(established, basis, colliding_field)``. ``colliding_field`` names the
    identity-bearing field the two descriptors share (``"model_id"`` or ``"model_family"``),
    or ``None`` when the run is not established for a non-identity reason (the offline
    stand-in case). Both the guard and the recorded determination read this function so
    their criteria cannot drift apart.
    """

    if (
        analyst.kind is not ProviderKind.REMOTE
        or adjudicator.kind is not ProviderKind.REMOTE
    ):
        # The basis stays the mechanical stand-in reason for *any* offline pair, but two roles
        # handed the very same descriptor is still one stand-in answering twice, so it carries an
        # identity collision the guard refuses. Distinct offline descriptors stay runnable.
        return (
            False,
            "synthetic offline providers (stub or recorded replay) are mechanical stand-ins that "
            "do not reason, so a run over them cannot establish assessor independence",
            "descriptor" if analyst == adjudicator else None,
        )
    if analyst.model_id == adjudicator.model_id:
        return (
            False,
            f"both providers share model_id {analyst.model_id!r}; one model answering twice under "
            "two labels is not independence, however the family is labelled",
            "model_id",
        )
    if analyst.model_family == adjudicator.model_family:
        return (
            False,
            f"both providers share model_family {analyst.model_family!r}; two prompts over one "
            "model family measure the prompt, not the evidence",
            "model_family",
        )
    return (
        True,
        f"distinct remote descriptors with distinct model_ids ({analyst.model_id!r} vs "
        f"{adjudicator.model_id!r}) and distinct model families ({analyst.model_family!r} vs "
        f"{adjudicator.model_family!r}); independence rests on the descriptors' own declaration "
        "and is not proof of the transport",
        None,
    )


def assert_assessors_independent(
    analyst: ProviderDescriptor, adjudicator: ProviderDescriptor
) -> None:
    """Refuse, with a raised error, a run where one assessor is asked to answer twice.

    The verdict comes from :func:`_independence_finding`, the same implementation the recorded
    determination uses, so the guard cannot enforce a weaker criterion than the record claims. The
    refusal is scoped to a genuine identity collision: two descriptors that share a ``model_id``
    (or are the identical descriptor) are the same assessor however they are named or their family
    is labelled. A pair that merely shares a ``model_family`` while declaring distinct models is
    left runnable but is recorded as not-established, and *distinct* offline stand-ins likewise run
    under a determination that never claims independence.
    """

    established, _basis, colliding_field = _independence_finding(analyst, adjudicator)
    if established or colliding_field is None or colliding_field == "model_family":
        return
    if colliding_field == "model_id":
        shared = f"share model_id {analyst.model_id!r}"
    else:
        shared = f"are the identical descriptor {analyst.name!r}"
    raise ValueError(
        f"analyst and adjudicator providers {shared} (colliding field: {colliding_field}); one "
        "assessor answering twice under two labels is not independence, so the run is refused"
    )


def _independence_determination(
    analyst: ProviderDescriptor, adjudicator: ProviderDescriptor
) -> tuple[bool, str]:
    """Decide, and explain in plain language, whether assessor independence is established.

    Independence requires two *distinct* descriptors that share neither ``model_id`` nor
    ``model_family``; the ``model_id`` is compared too, because one model answering twice is not
    independence however the family is labelled. An offline stub or recorded-replay provider is a
    mechanical, non-intelligent stand-in, so a run over any offline descriptor is permitted but can
    never establish independence.
    """

    established, basis, _colliding_field = _independence_finding(analyst, adjudicator)
    return established, basis


def assert_provider_permitted(descriptor: ProviderDescriptor, freeze_status: str) -> None:
    """Refuse, with a raised error, any provider that needs egress without explicit approval.

    This is the whole point of the boundary: the refusal is executable code, so egress cannot be
    reached by forgetting a convention. A provider that does not require egress passes untouched.
    """

    if not descriptor.requires_egress:
        return
    if freeze_status.strip().upper() in APPROVED_EGRESS_FREEZE_STATUSES:
        return
    approved = ", ".join(sorted(APPROVED_EGRESS_FREEZE_STATUSES))
    raise PermissionError(
        f"provider {descriptor.name!r} (model {descriptor.model_id!r}) requires network egress, "
        f"but freeze status {freeze_status!r} is not an approved egress status ({approved}); "
        "refusing to run it"
    )


class RunBudget(FrozenSchema):
    """Mirror of the freeze artifact's ``budget`` block, enforced at run time."""

    max_bundles_per_run: int = Field(ge=0)
    max_assessments_per_run: int = Field(ge=0)
    max_total_calls: int = Field(ge=0)


class TriageRun(FrozenSchema):
    """One bounded, reproducible execution of the two-role triage over a set of bundles."""

    run_id: UUID
    created_at: datetime
    freeze_version: NonEmptyText
    analyst_descriptor: ProviderDescriptor
    adjudicator_descriptor: ProviderDescriptor
    budget: RunBudget
    calls_made: int = Field(ge=0)
    assessments: tuple[AssessmentOutcome, ...] = ()
    comparisons: tuple[TriageComparison, ...] = ()
    aborted: bool
    abort_reason: NonEmptyText | None = None
    synthetic: bool
    independence_established: bool = False
    independence_basis: NonEmptyText = (
        "not determined: this record was constructed without an independence determination"
    )

    @field_validator("created_at")
    @classmethod
    def normalize_created_at(cls, value: datetime) -> datetime:
        return normalize_utc(value)

    @model_validator(mode="after")
    def validate_abort_reason(self) -> TriageRun:
        if self.aborted and self.abort_reason is None:
            raise ValueError("an aborted run must record an abort_reason")
        if not self.aborted and self.abort_reason is not None:
            raise ValueError("a completed run must not record an abort_reason")
        return self


def _int_from(mapping: Mapping[str, Any], key: str) -> int:
    value = mapping.get(key, 0)
    return value if isinstance(value, int) else 0


def _parse_payload(raw_text: str) -> Any:
    """Parse provider text into a payload; malformed text is preserved as inadmissible input."""

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        return raw_text


def _provider_metadata(descriptor: ProviderDescriptor) -> ProviderMetadata:
    return ProviderMetadata(
        provider=descriptor.name,
        model=descriptor.model_id,
        model_version=PROVIDER_INTERFACE_VERSION,
        prompt_version=TRIAGE_PROMPT_VERSION,
    )


def _raw_reference(
    descriptor: ProviderDescriptor, response: ProviderResponse
) -> RawResponseReference:
    return RawResponseReference(
        reference=(
            f"{descriptor.kind.value}://{descriptor.name}/"
            f"{response.role.value}/{response.response_digest}"
        ),
        digest=response.response_digest,
        structured=isinstance(_parse_payload(response.raw_text), Mapping),
    )


def triage_run_id_for(
    *,
    freeze_version: str,
    analyst_descriptor: ProviderDescriptor,
    adjudicator_descriptor: ProviderDescriptor,
    snapshot_digests: tuple[str, ...],
    created_at: datetime,
) -> UUID:
    """Derive a run identity from the freeze, the descriptors, the inputs, and the timestamp.

    The snapshot digests are sorted before hashing so the run identity does not depend on the order
    in which the bundles were supplied, matching every other identity function in the project.
    """

    identity = json.dumps(
        [
            freeze_version,
            analyst_descriptor.model_dump(mode="json"),
            adjudicator_descriptor.model_dump(mode="json"),
            sorted(snapshot_digests),
            normalize_utc(created_at).isoformat(),
        ],
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
        default=str,
    )
    return uuid5(TRIAGE_RUN_ID_NAMESPACE, identity)


def run_independent_triage(
    *,
    bundles: Sequence[EvidenceBundle],
    analyst_provider: TriageProvider,
    adjudicator_provider: TriageProvider,
    freeze: Mapping[str, Any],
    created_at: datetime,
) -> TriageRun:
    """Run both roles over every bundle within budget, or abort with a recorded reason."""

    freeze_status = str(freeze.get("status", ""))
    freeze_version = str(freeze.get("freeze_version", "")) or "unknown"

    # Governance refusal comes first, before any snapshot, request, or budget is touched.
    assert_provider_permitted(analyst_provider.descriptor, freeze_status)
    assert_provider_permitted(adjudicator_provider.descriptor, freeze_status)

    # Independence is a precondition of the run, checked alongside the governance gate and still
    # before any snapshot or budget work.
    assert_assessors_independent(analyst_provider.descriptor, adjudicator_provider.descriptor)
    independence_established, independence_basis = _independence_determination(
        analyst_provider.descriptor, adjudicator_provider.descriptor
    )

    raw_budget = freeze.get("budget")
    budget_map: Mapping[str, Any] = raw_budget if isinstance(raw_budget, Mapping) else {}
    budget = RunBudget(
        max_bundles_per_run=_int_from(budget_map, "max_bundles_per_run"),
        max_assessments_per_run=_int_from(budget_map, "max_assessments_per_run"),
        max_total_calls=_int_from(budget_map, "max_total_calls"),
    )

    # Canonical order matches build_corpus so a run over the corpus's bundle set selects its
    # entries[:max_bundles_per_run] regardless of caller order.
    ordered_bundles = sorted(
        bundles,
        key=lambda bundle: (str(bundle.evidence_bundle_id), str(bundle.finding_id)),
    )
    selected = ordered_bundles[: budget.max_bundles_per_run]
    bundle_overflow = len(ordered_bundles) > budget.max_bundles_per_run

    assessments: list[AssessmentOutcome] = []
    comparisons: list[TriageComparison] = []
    calls_made = 0
    aborted = False
    abort_reason: str | None = None

    for bundle in selected:
        if calls_made + 2 > budget.max_total_calls:
            aborted = True
            abort_reason = (
                f"call budget exhausted before bundle {bundle.evidence_bundle_id}: "
                f"{calls_made} of {budget.max_total_calls} calls used"
            )
            break
        if len(assessments) + 2 > budget.max_assessments_per_run:
            aborted = True
            abort_reason = (
                f"assessment budget exhausted before bundle {bundle.evidence_bundle_id}: "
                f"{len(assessments)} of {budget.max_assessments_per_run} assessments stored"
            )
            break

        snapshot_json = canonical_snapshot_json(bundle)
        digest = snapshot_digest(bundle)

        analyst_response = analyst_provider.complete(
            ProviderRequest(
                role=AssessorRole.TRIAGE_ANALYST,
                snapshot_digest=digest,
                snapshot_json=snapshot_json,
                prompt=_TRIAGE_PROMPT,
            )
        )
        calls_made += 1
        adjudicator_response = adjudicator_provider.complete(
            ProviderRequest(
                role=AssessorRole.EXPERT_ADJUDICATOR,
                snapshot_digest=digest,
                snapshot_json=snapshot_json,
                prompt=_TRIAGE_PROMPT,
            )
        )
        calls_made += 1

        if (
            analyst_response.snapshot_digest != digest
            or adjudicator_response.snapshot_digest != digest
        ):
            aborted = True
            abort_reason = (
                f"snapshot digest mismatch for bundle {bundle.evidence_bundle_id}: both roles must "
                f"report {digest}"
            )
            break

        analyst_assessment = build_assessment(
            role=AssessorRole.TRIAGE_ANALYST,
            bundle=bundle,
            payload=_parse_payload(analyst_response.raw_text),
            provider_metadata=_provider_metadata(analyst_provider.descriptor),
            raw_response=_raw_reference(analyst_provider.descriptor, analyst_response),
            created_at=created_at,
        )
        adjudicator_assessment = build_assessment(
            role=AssessorRole.EXPERT_ADJUDICATOR,
            bundle=bundle,
            payload=_parse_payload(adjudicator_response.raw_text),
            provider_metadata=_provider_metadata(adjudicator_provider.descriptor),
            raw_response=_raw_reference(adjudicator_provider.descriptor, adjudicator_response),
            created_at=created_at,
        )
        assessments.extend((analyst_assessment, adjudicator_assessment))
        comparisons.append(
            compare_assessments(analyst_assessment, adjudicator_assessment, created_at=created_at)
        )

    if not aborted and bundle_overflow:
        aborted = True
        abort_reason = (
            f"bundle budget exhausted: {len(ordered_bundles)} bundles supplied, "
            f"max_bundles_per_run={budget.max_bundles_per_run}"
        )

    # Offline providers are synthetic by construction, so any offline descriptor makes the run
    # synthetic. This is true even when the run aborts before a single response is produced.
    synthetic = (
        analyst_provider.descriptor.kind is not ProviderKind.REMOTE
        or adjudicator_provider.descriptor.kind is not ProviderKind.REMOTE
    )

    return TriageRun(
        run_id=triage_run_id_for(
            freeze_version=freeze_version,
            analyst_descriptor=analyst_provider.descriptor,
            adjudicator_descriptor=adjudicator_provider.descriptor,
            snapshot_digests=tuple(snapshot_digest(bundle) for bundle in selected),
            created_at=created_at,
        ),
        created_at=created_at,
        freeze_version=freeze_version,
        analyst_descriptor=analyst_provider.descriptor,
        adjudicator_descriptor=adjudicator_provider.descriptor,
        budget=budget,
        calls_made=calls_made,
        assessments=tuple(assessments),
        comparisons=tuple(comparisons),
        aborted=aborted,
        abort_reason=abort_reason,
        synthetic=synthetic,
        independence_established=independence_established,
        independence_basis=independence_basis,
    )


__all__ = [
    "APPROVED_EGRESS_FREEZE_STATUSES",
    "PROVIDER_INTERFACE_VERSION",
    "TRIAGE_PROMPT_VERSION",
    "RunBudget",
    "TriageRun",
    "assert_assessors_independent",
    "assert_provider_permitted",
    "run_independent_triage",
    "triage_run_id_for",
]
