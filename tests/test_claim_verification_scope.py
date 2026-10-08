"""Issue #34: `verify_claim` checks evidence KIND, not whether the evidence exists.

The defect was a record that overstated what had been established. `verify_claim` inspects only each
`EvidenceReference.kind` — it is given no bundle and no resolution context, so existence is not
checkable there by construction. But the success path reported:

    "cited evidence supports the declared category (model_inference)"

That sentence is about the **evidence**. What was actually established is a statement about the
evidence's **kind**. A claim citing a fabricated identifier was therefore reported as though the
evidence had been checked.

These tests pin the corrected scope. They do NOT claim the substantive fix: making resolution
checkable requires a schema/signature decision recorded on the issue, because it changes
`ClaimVerification` or `verify_claim`'s public contract.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from aegistrace.schemas.findings import Claim, ClaimType, EvidenceReference
from aegistrace.verification import verify_claim

CREATED_AT = datetime(2026, 10, 9, 12, 0, tzinfo=UTC)

#: Deliberately unresolvable. Nothing in the repository can resolve these, which is the point: the
#: function has no resolver, so it must not report as though it had used one.
FABRICATED = {
    ClaimType.MODEL_INFERENCE: ("model_score", "detection://does-not-exist/999"),
    ClaimType.REFERENCE_BACKED_FACT: ("external", "https://example.invalid/ghost"),
    ClaimType.DETERMINISTIC_DERIVATION: ("detection", "totally made up prose"),
}


def _claim(claim_type: ClaimType, kind: str, reference: str) -> Claim:
    return Claim(
        claim_id=uuid4(),
        claim_type=claim_type,
        statement="a statement",
        evidence_references=(EvidenceReference(kind=kind, reference=reference),),  # type: ignore[arg-type]
        created_at=CREATED_AT,
    )


def test_issue_34_a_fabricated_reference_is_not_reported_as_though_checked() -> None:
    """The record must state that resolution was not checked, for every strong category."""

    for claim_type, (kind, reference) in FABRICATED.items():
        verification = verify_claim(_claim(claim_type, kind, reference))

        # The kind genuinely is admissible, so the claim is not downgraded - that part was correct.
        assert verification.verified is True
        assert verification.effective_type is claim_type

        # But the record must not read as though the evidence were examined.
        joined = " ".join(verification.reasons)
        assert "admissible kind" in joined, claim_type
        assert "resolution was NOT checked" in joined, (
            f"{claim_type}: the record must say what was not checked"
        )


def test_issue_34_the_overstating_wording_is_gone() -> None:
    """The exact sentence that overstated the check must not come back.

    It asserted something about the evidence while only the evidence's kind had been examined.
    """

    verification = verify_claim(_claim(ClaimType.MODEL_INFERENCE, "model_score", "model_score:1"))
    assert not any(
        "supports the declared category" in reason for reason in verification.reasons
    ), "the old wording claimed more than the function established"


def test_issue_34_the_contract_is_stated_on_the_function() -> None:
    """A reader of the function must be told the scope without having to read the issue."""

    doc = verify_claim.__doc__ or ""
    assert "does not verify that the cited evidence exists" in doc
    assert "kind" in doc.lower()


def test_issue_34_controls_are_unchanged() -> None:
    """The four controls the issue requires to stay as they were."""

    # 1. An uncited claim is downgraded.
    uncited = Claim(
        claim_id=uuid4(),
        claim_type=ClaimType.OBSERVED_FACT,
        statement="s",
        created_at=CREATED_AT,
    )
    assert verify_claim(uncited).verified is False

    # 2. Wrong-kind evidence is downgraded.
    wrong_kind = _claim(ClaimType.OBSERVED_FACT, "model_score", "model_score:1")
    assert verify_claim(wrong_kind).verified is False

    # 3. An explicit abstention is still verified, and is not given the resolution caveat, because
    #    it asserts nothing about evidence that would need resolving.
    abstention = Claim(
        claim_id=uuid4(),
        claim_type=ClaimType.UNKNOWN_INSUFFICIENT_EVIDENCE,
        statement="s",
        created_at=CREATED_AT,
    )
    abstention_result = verify_claim(abstention)
    assert abstention_result.verified is True
    assert abstention_result.effective_type is ClaimType.UNKNOWN_INSUFFICIENT_EVIDENCE
    assert not any("resolution was NOT checked" in r for r in abstention_result.reasons)

    # 4. AI_INTERPRETATION on a model score is still verified.
    interpretation = _claim(ClaimType.AI_INTERPRETATION, "model_score", "model_score:1")
    assert verify_claim(interpretation).verified is True


def test_issue_34_downgrade_paths_do_not_gain_the_resolution_caveat() -> None:
    """The caveat belongs only where the claim was accepted on kind.

    A downgraded claim is already unverified, so adding "resolution was not checked" would be noise
    and would blur the distinction the issue asks to make visible.
    """

    downgraded = verify_claim(_claim(ClaimType.OBSERVED_FACT, "model_score", "model_score:1"))
    assert downgraded.verified is False
    assert not any("resolution was NOT checked" in reason for reason in downgraded.reasons)
