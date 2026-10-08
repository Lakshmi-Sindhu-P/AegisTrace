"""Turn a provider payload into a valid assessment, or preserve it as a failed attempt.

The architecture rule is that invalid or uncited model output is stored as a *failed attempt*, never
silently coerced into a valid one. This module implements that rule as a single decision point, so
there is exactly one place where a raw model response becomes an admissible record.

A note on abstention: ``insufficient_evidence`` is a valid category, but it still has to cite the
evidence it reviewed. "I looked at this bundle and it does not support a conclusion" is an
assessment; "I looked at nothing" is not.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

from aegistrace.schemas.detections import DetectionSeverity
from aegistrace.schemas.findings import EvidenceBundle
from aegistrace.schemas.triage import (
    AssessorRole,
    FailedAssessment,
    ProviderMetadata,
    RawResponseReference,
    TriageAssessment,
    TriageCategory,
    failed_attempt_id_for,
    triage_id_for,
)
from aegistrace.triage.snapshot import bundle_evidence_ids, snapshot_digest

AssessmentOutcome = TriageAssessment | FailedAssessment

_REQUIRED_TEXT_FIELDS = ("summary", "evidence_summary", "confidence_statement", "next_step")
_TEXT_LIST_FIELDS = ("uncertainties", "unsupported_claim_flags")


def _text_tuple(payload: Mapping[str, Any], key: str) -> tuple[str, ...]:
    value = payload.get(key)
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return ()
    return tuple(str(item) for item in value)


def _collect_reasons(payload: Any, bundle: EvidenceBundle) -> list[str]:
    """Collect every reason this payload is inadmissible, rather than failing on the first."""

    if not isinstance(payload, Mapping):
        return ["response is not a structured object"]

    reasons: list[str] = []
    for field_name in _REQUIRED_TEXT_FIELDS:
        value = payload.get(field_name)
        if not isinstance(value, str) or not value.strip():
            reasons.append(f"missing or empty required field: {field_name}")

    try:
        TriageCategory(str(payload.get("category")).casefold())
    except ValueError:
        reasons.append(f"unknown category: {payload.get('category')!r}")

    try:
        DetectionSeverity(str(payload.get("severity")).casefold())
    except ValueError:
        reasons.append(f"unknown severity: {payload.get('severity')!r}")

    cited = payload.get("cited_evidence_ids")
    if not isinstance(cited, Sequence) or isinstance(cited, (str, bytes)) or not cited:
        reasons.append("assessment cites no evidence; an uncited assessment is not admissible")
    else:
        allowed = bundle_evidence_ids(bundle)
        unknown = sorted(str(item) for item in cited if str(item) not in allowed)
        if unknown:
            reasons.append(f"cited evidence not present in the bundle: {', '.join(unknown)}")

    return reasons


def build_assessment(
    *,
    role: AssessorRole,
    bundle: EvidenceBundle,
    payload: Any,
    provider_metadata: ProviderMetadata,
    raw_response: RawResponseReference,
    created_at: datetime,
) -> AssessmentOutcome:
    """Admit a provider payload as an assessment, or preserve it as a failed attempt."""

    digest = snapshot_digest(bundle)
    reasons = _collect_reasons(payload, bundle)

    if reasons:
        return FailedAssessment(
            attempt_id=failed_attempt_id_for(
                role=role.value,
                evidence_bundle_id=bundle.evidence_bundle_id,
                input_snapshot_digest=digest,
                raw_digest=raw_response.digest,
            ),
            role=role,
            evidence_bundle_id=bundle.evidence_bundle_id,
            input_snapshot_digest=digest,
            failure_reasons=tuple(reasons),
            provider_metadata=provider_metadata,
            raw_response=raw_response,
            created_at=created_at,
        )

    category = TriageCategory(str(payload["category"]).casefold())
    summary = str(payload["summary"]).strip()
    return TriageAssessment(
        triage_id=triage_id_for(
            role=role.value,
            evidence_bundle_id=bundle.evidence_bundle_id,
            input_snapshot_digest=digest,
            category=category.value,
            summary=summary,
        ),
        role=role,
        evidence_bundle_id=bundle.evidence_bundle_id,
        bundle_version=bundle.bundle_version,
        finding_ids=(bundle.finding_id,),
        input_snapshot_digest=digest,
        category=category,
        severity=DetectionSeverity(str(payload["severity"]).casefold()),
        summary=summary,
        evidence_summary=str(payload["evidence_summary"]).strip(),
        confidence_statement=str(payload["confidence_statement"]).strip(),
        cited_evidence_ids=tuple(str(item) for item in payload["cited_evidence_ids"]),
        uncertainties=_text_tuple(payload, "uncertainties"),
        unsupported_claim_flags=_text_tuple(payload, "unsupported_claim_flags"),
        next_step=str(payload["next_step"]).strip(),
        provider_metadata=provider_metadata,
        raw_response=raw_response,
        created_at=created_at,
    )


__all__ = ["AssessmentOutcome", "build_assessment"]
