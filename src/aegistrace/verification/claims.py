"""Claim verification against the epistemic taxonomy.

A taxonomy is only worth having if something enforces it. This module reads a :class:`Claim` and
returns a :class:`ClaimVerification` — it never edits the claim. That separation matters: the
original statement, including a wrong or unsupported one, stays in the record so that a reviewer can
see what was asserted, while the verification records what the cited evidence can actually carry.

Verification is deliberately conservative. When a claim cites evidence that cannot support its
declared category, the claim is not quietly re-labelled into something stronger or waved through; it
is downgraded to ``UNKNOWN_INSUFFICIENT_EVIDENCE`` and marked unverified.

**What this checks, and what it does NOT (issue #34).** Every rule below tests the *kind* of the
cited evidence — ``event``, ``detection``, ``model_score``, ``external``, ``repository``. It does
**not** check that a cited reference resolves to anything, because the function is given no bundle
and no resolution context: existence cannot be checked by construction, not merely by omission.
``verified=True`` therefore means "the cited evidence is of an admissible kind for this category",
**not** "the evidence was found". A caller that needs resolution must use the layer that has a
resolver (``verification/evidence_assertions.py``, which reports ``UNRESOLVED`` and ``AMBIGUOUS`` as
distinct violations). Making that distinction visible in the record itself is an open decision
recorded on issue #34.
"""

from __future__ import annotations

from aegistrace.schemas.findings import Claim, ClaimType, ClaimVerification, EvidenceReference

_MODEL_SCORE = "model_score"
_OBSERVATION_KINDS = frozenset({"event"})
_DERIVATION_KINDS = frozenset({"event", "detection"})
_REFERENCE_KINDS = frozenset({"external", "repository"})

_RESOLUTION_NOT_CHECKED = (
    "reference resolution was NOT checked: this function is given no bundle or resolution context, "
    "so it cannot determine whether a cited identifier exists (issue #34)"
)


def _kinds(references: tuple[EvidenceReference, ...]) -> set[str]:
    return {reference.kind for reference in references}


def verify_claim(claim: Claim) -> ClaimVerification:
    """Check whether a claim's cited evidence is of an admissible KIND for its declared category.

    This does not verify that the cited evidence exists: no bundle or resolution context is
    supplied, so existence is not checkable here (issue #34). The returned ``reasons`` state that
    explicitly, so the record cannot be read as an existence check.
    """

    kinds = _kinds(claim.evidence_references)

    if claim.claim_type is ClaimType.UNKNOWN_INSUFFICIENT_EVIDENCE:
        return ClaimVerification(
            claim_id=claim.claim_id,
            verified=True,
            effective_type=ClaimType.UNKNOWN_INSUFFICIENT_EVIDENCE,
            reasons=("explicit abstention; the evidence does not support a stronger category",),
        )

    if not claim.evidence_references:
        return ClaimVerification(
            claim_id=claim.claim_id,
            verified=False,
            effective_type=ClaimType.UNKNOWN_INSUFFICIENT_EVIDENCE,
            reasons=(
                "no evidence references were cited; an uncited statement cannot be verified",
            ),
        )

    # These two rules are minimums, not exclusions: a claim may cite additional evidence of any
    # kind and still pass. Issue #15 records the reasoning.
    if claim.claim_type is ClaimType.OBSERVED_FACT and not (kinds & _OBSERVATION_KINDS):
        return ClaimVerification(
            claim_id=claim.claim_id,
            verified=False,
            effective_type=ClaimType.UNKNOWN_INSUFFICIENT_EVIDENCE,
            reasons=(
                "an observed fact must cite at least one event reference",
                "a model score is not an observation",
            ),
        )

    if claim.claim_type is ClaimType.DETERMINISTIC_DERIVATION and not (kinds & _DERIVATION_KINDS):
        return ClaimVerification(
            claim_id=claim.claim_id,
            verified=False,
            effective_type=ClaimType.UNKNOWN_INSUFFICIENT_EVIDENCE,
            reasons=(
                "a deterministic derivation must cite at least one event or detection reference",
                "nothing about a model score is deterministic",
            ),
        )

    if claim.claim_type is ClaimType.MODEL_INFERENCE and _MODEL_SCORE not in kinds:
        return ClaimVerification(
            claim_id=claim.claim_id,
            verified=False,
            effective_type=ClaimType.UNKNOWN_INSUFFICIENT_EVIDENCE,
            reasons=(
                "a model inference must cite at least one model-score reference",
                "the cited evidence cannot carry a model inference",
            ),
        )

    if claim.claim_type is ClaimType.REFERENCE_BACKED_FACT and not (kinds & _REFERENCE_KINDS):
        return ClaimVerification(
            claim_id=claim.claim_id,
            verified=False,
            effective_type=ClaimType.UNKNOWN_INSUFFICIENT_EVIDENCE,
            reasons=(
                "a reference-backed fact must cite at least one external or repository reference",
            ),
        )

    return ClaimVerification(
        claim_id=claim.claim_id,
        verified=True,
        effective_type=claim.claim_type,
        reasons=(
            # Says what was actually established. The previous wording - "cited evidence
            # supports the declared category" - asserted something about the EVIDENCE while only
            # the evidence's KIND had been examined, so a claim citing a fabricated identifier was
            # reported as though the evidence had been checked (issue #34).
            "the cited evidence is of an admissible kind for the declared category "
            f"({claim.claim_type.value})",
            _RESOLUTION_NOT_CHECKED,
        ),
    )


__all__ = ["verify_claim"]
