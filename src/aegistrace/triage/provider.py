"""The provider boundary: the only place a triage assessor can be reached.

AegisTrace must not send anything anywhere without human interference. That is a property of the
code, not of a runbook, so this module is written so that **egress is impossible to reach** in the
current repository state:

* There is no HTTP client here and no import of one. The module imports only the standard library
  and this project's own schemas. There is therefore no code path in this module that can open a
  socket, resolve a hostname, or read a credential.
* A :class:`ProviderDescriptor` carries ``requires_egress`` and a :class:`ProviderKind`, and the
  schema itself rejects contradictory pairings. A descriptor that claims to be remote but requires
  no egress cannot be constructed, and neither can an offline descriptor that demands egress.
* The two providers implemented here are offline. :class:`RecordedTriageProvider` replays frozen
  text; :class:`StubTriageProvider` synthesises mechanical text from the request alone. Neither
  calls a model.
* Every response records ``synthetic``. An offline descriptor's response is *forced* to
  ``synthetic=True`` at validation time, so a replayed or stubbed response can never be presented
  as a real model's assessment.

The orchestrator in :mod:`aegistrace.triage.run` performs the second half of the guarantee: it
refuses, with a raised error, to run a provider whose descriptor requires egress unless the frozen
governance artifact explicitly says egress is approved. The freeze is ``BLOCKED_HUMAN``, so a
remote provider is refused before any work happens.

**What this module cannot prove.** It cannot prove what a future remote provider does with data once
a human approves the transport, and a ``REMOTE`` descriptor is a declaration by the caller rather
than a property this code can verify. That governance question is recorded in
``configs/triage_provider_freeze.json`` and answered by a human, not by this module.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from datetime import datetime
from enum import StrEnum
from typing import Any, Protocol

from pydantic import field_validator, model_validator

from aegistrace.schemas.common import FrozenSchema, NonEmptyText, Sha256, normalize_utc
from aegistrace.schemas.triage import AssessorRole


class ProviderKind(StrEnum):
    """How a provider would obtain a response, if it were permitted to run."""

    OFFLINE_RECORDED = "offline_recorded"
    OFFLINE_STUB = "offline_stub"
    REMOTE = "remote"


class ProviderDescriptor(FrozenSchema):
    """Who a provider claims to be, and whether reaching it would leave the machine.

    The validator makes the contradiction unrepresentable: ``REMOTE`` and ``requires_egress=True``
    travel together, and every ``OFFLINE_*`` kind travels with ``requires_egress=False``. A caller
    cannot quietly describe an offline provider that needs a network or a remote one that does not.
    """

    name: NonEmptyText
    model_id: NonEmptyText
    model_family: NonEmptyText
    kind: ProviderKind
    requires_egress: bool

    @model_validator(mode="after")
    def validate_egress_matches_kind(self) -> ProviderDescriptor:
        if self.kind is ProviderKind.REMOTE and not self.requires_egress:
            raise ValueError("a REMOTE provider must declare requires_egress=True")
        if self.kind is not ProviderKind.REMOTE and self.requires_egress:
            raise ValueError(
                f"an offline provider ({self.kind.value}) must declare requires_egress=False"
            )
        return self


class ProviderRequest(FrozenSchema):
    """The complete, frozen input sent to one assessor role.

    Both roles receive the *same* ``snapshot_json`` and ``snapshot_digest``; only ``role`` differs.
    """

    role: AssessorRole
    snapshot_digest: Sha256
    snapshot_json: NonEmptyText
    prompt: NonEmptyText


class ProviderResponse(FrozenSchema):
    """One raw provider response, content-addressed and marked as synthetic when it is not real.

    ``synthetic`` is not a courtesy label. It is a validated consequence of the descriptor: a
    response from an offline descriptor must be ``synthetic=True``, and a response may only claim
    ``synthetic=False`` when its descriptor is ``REMOTE``.
    """

    descriptor: ProviderDescriptor
    role: AssessorRole
    snapshot_digest: Sha256
    raw_text: NonEmptyText
    request_digest: Sha256
    response_digest: Sha256
    synthetic: bool
    created_at: datetime

    @field_validator("created_at")
    @classmethod
    def normalize_created_at(cls, value: datetime) -> datetime:
        return normalize_utc(value)

    @model_validator(mode="after")
    def validate_synthetic_matches_descriptor(self) -> ProviderResponse:
        if self.descriptor.kind is not ProviderKind.REMOTE and not self.synthetic:
            raise ValueError(
                f"response from offline provider {self.descriptor.name!r} must be synthetic=True; "
                "a non-synthetic response may only come from a REMOTE provider"
            )
        return self


class TriageProvider(Protocol):
    """The only shape the orchestrator knows: a descriptor plus one completion call."""

    @property
    def descriptor(self) -> ProviderDescriptor: ...

    def complete(self, request: ProviderRequest) -> ProviderResponse: ...


def digest_text(value: str) -> str:
    """Content-address a text payload with SHA-256."""

    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def request_digest(request: ProviderRequest) -> str:
    """Content-address a request, so a response can name exactly what it answered."""

    return digest_text(request.model_dump_json())


def _response_from(
    *,
    descriptor: ProviderDescriptor,
    request: ProviderRequest,
    raw_text: str,
    created_at: datetime,
) -> ProviderResponse:
    """Assemble a response, deriving synthetic from the descriptor rather than the caller."""

    return ProviderResponse(
        descriptor=descriptor,
        role=request.role,
        snapshot_digest=request.snapshot_digest,
        raw_text=raw_text,
        request_digest=request_digest(request),
        response_digest=digest_text(raw_text),
        synthetic=descriptor.kind is not ProviderKind.REMOTE,
        created_at=created_at,
    )


class RecordedTriageProvider:
    """Deterministic offline replay of previously captured response text.

    The mapping is keyed by ``(role, snapshot_digest)``, so a recorded response can only be returned
    for the exact snapshot it was captured against. A missing key is an error rather than a silent
    empty response, because silently inventing an answer is the failure mode this project is built
    to avoid.
    """

    def __init__(
        self,
        descriptor: ProviderDescriptor,
        responses: Mapping[tuple[AssessorRole, str], str],
        created_at: datetime,
    ) -> None:
        if descriptor.kind is ProviderKind.REMOTE or descriptor.requires_egress:
            raise ValueError(
                f"RecordedTriageProvider is offline; descriptor {descriptor.name!r} is remote"
            )
        self._descriptor = descriptor
        self._responses = dict(responses)
        self._created_at = created_at

    @property
    def descriptor(self) -> ProviderDescriptor:
        return self._descriptor

    def complete(self, request: ProviderRequest) -> ProviderResponse:
        key = (request.role, request.snapshot_digest)
        try:
            raw_text = self._responses[key]
        except KeyError:
            raise KeyError(
                f"no recorded response for role {request.role.value!r} "
                f"and snapshot digest {request.snapshot_digest!r}"
            ) from None
        return _response_from(
            descriptor=self._descriptor,
            request=request,
            raw_text=raw_text,
            created_at=self._created_at,
        )


class StubTriageProvider:
    """A deterministic, non-intelligent stand-in for wiring and tests.

    It is not a model and does not pretend to be one. Its output is derived only from the request:
    it echoes the role and snapshot digest and cites the bundle's finding identifier so the result
    is schema-admissible. The descriptor naming rules (``stub-`` prefix, ``stub`` in the family) and
    the ``synthetic=True`` validation make it impossible to mistake for a real assessment.
    """

    def __init__(self, descriptor: ProviderDescriptor, created_at: datetime) -> None:
        if descriptor.kind is not ProviderKind.OFFLINE_STUB or descriptor.requires_egress:
            raise ValueError(
                f"StubTriageProvider requires an OFFLINE_STUB descriptor; "
                f"got {descriptor.kind.value}"
            )
        if "stub" not in descriptor.model_family.casefold():
            raise ValueError("a stub descriptor's model_family must contain the word 'stub'")
        if not descriptor.model_id.startswith("stub-"):
            raise ValueError("a stub descriptor's model_id must start with 'stub-'")
        self._descriptor = descriptor
        self._created_at = created_at

    @property
    def descriptor(self) -> ProviderDescriptor:
        return self._descriptor

    def complete(self, request: ProviderRequest) -> ProviderResponse:
        snapshot: Any = json.loads(request.snapshot_json)
        finding_id = ""
        if isinstance(snapshot, Mapping):
            finding_id = str(snapshot.get("finding_id", ""))
        payload = {
            "category": "insufficient_evidence",
            "severity": "low",
            "summary": (f"stub response for role {request.role.value}; no model was invoked"),
            "evidence_summary": (f"mechanical echo of snapshot digest {request.snapshot_digest}"),
            "confidence_statement": (
                "not applicable: this text is generated mechanically, not inferred"
            ),
            "cited_evidence_ids": [finding_id] if finding_id else [],
            "uncertainties": ["synthetic stub output carries no analytical judgement"],
            "unsupported_claim_flags": [],
            "next_step": "discard this synthetic response and obtain a real assessment",
        }
        raw_text = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return _response_from(
            descriptor=self._descriptor,
            request=request,
            raw_text=raw_text,
            created_at=self._created_at,
        )


__all__ = [
    "ProviderDescriptor",
    "ProviderKind",
    "ProviderRequest",
    "ProviderResponse",
    "RecordedTriageProvider",
    "StubTriageProvider",
    "TriageProvider",
    "digest_text",
    "request_digest",
]
