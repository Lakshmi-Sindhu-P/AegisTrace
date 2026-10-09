# Pending Owner Decisions

**Purpose.** One place to see every decision currently waiting on the owner. This is an **index**: it
carries the one-line recommendation and a pointer to where the full argument lives. It deliberately
does not restate the arguments — see `docs/learning_map.md` for the documentation map and the
"Duplication rule" below.

**Status vocabulary** matches `MEMORY.md`: `CURRENT / IMPLEMENTED` → `APPROVED INTENT / DESIGN` →
`PLANNED, NOT IMPLEMENTED` → `VALIDATED`.

**Why a decision is here rather than already done.** The autonomy categories are: **A — engineering**
(act independently), **B — product/architectural contract** (recommend; ask when the behaviour is not
already established), **C — research/governance** (explicit approval required). Anything in this file
is B or C. Category A work is not listed here; it is simply done.

---

## Decided by the owner (2026-10-09)

Three decisions were answered on 2026-10-09. They are recorded here so the answer is not re-asked,
with a pointer to where the decision is implemented. The verbatim decisions live in the session
record; the engineering consequences are in the commits and issue comments named below.

| # | Question | Owner's answer | Implemented in |
|---|---|---|---|
| 30 | Does `HumanReview.tier` mean the tier **required** or the tier **conducted**? | **Conducted.** `TierAssignment` retains the tier required. Reconcile the two, report unmet requirements **explicitly**, and **do not assume a simple numerical ordering of tiers** (a D outcome is a different kind of result, not a higher one). Preserve review history; add regression tests. | Issue #30; `src/aegistrace/schemas/review.py`, `src/aegistrace/review/tiers.py` |
| 37 | Should an ingest accepting **zero** records refuse? | **Refuse, with a non-zero exit code**, whether the source was empty or every row was rejected. Preserve diagnostics and rejection reasons. Distinguish this from a successful ingest followed by zero detections or filter matches. | Issue #37; commit `e2ba0e7` |
| UI | Which visual direction for the local UI? | **Investigation Bench (C) as the primary shell**, with **Chain of Custody (A) as the persistent evidence/provenance system**, and **Two Witnesses (B) as a dedicated AI-assessment comparison view**. Workflow: findings → evidence inspection → AI-assessment comparison (when available) → review requirements → human decision. Document navigation, major views, component boundaries and data dependencies **before** implementation. | `docs/ui_architecture.md` (design); implementation `PLANNED, NOT IMPLEMENTED` |

**The UI approval is scoped.** The owner approved the *architectural and interaction direction* — not
new research claims, not altered governance contracts, and not fabricated functionality, confidence
measures or operational capabilities. Nothing in the UI may present a synthetic (offline-stub)
assessment as a real experimental result.

---

## Still waiting on the owner

| # | Decision | Category | Recommendation | Detail lives in |
|---|---|---|---|---|
| 27 | Should the registry validator **reject** a command that omits a repair step? | C | **Approve**, but not the wording as filed — it is unimplementable. Use the checkable invariant instead: if the manifest records `artifact_repair`, the command must name a repair script. | Issue #27 (comment) |
| 32 | Who owns the 20-bundle triage sample — the corpus or the caller? | B | **Corpus (a).** The preregistration attributes the sample to the corpus, so the corpus should own it. This fixes the evaluation population, so it is pre-data and would be a protocol violation to change later. | Issue #32 |
| 33 | Rename `TriageComparison.left`/`right`? | B | **Rename** to role-named fields. The convention is already documented in the schema; only the names still contradict it. | Issue #33 |
| 34 | Make the kind/resolved distinction visible in the record? | B | **Both**: give `verify_claim` a resolution context, and split `verified` into `kind_admissible` + `resolution`. | Issue #34; `docs/identity_decision_register.md` |

**Four decisions were closed as "not genuinely required"** — #38, #40, #42 and (from round 36) the
former #37 recommendation — because the identity rule already governs them, or because the fix made
the rule unnecessary. They are recorded in `docs/identity_decision_register.md` so the reasoning is
not lost, but they need no answer.

**Parts of the listed issues are already done.** Re-running each issue's own reproduction established
that #30's proposed fixes 2 and 3 (decision/escalation coherence, and `review_id` matching its own
content) landed during the identity work, and that #33's convention is already documented in the
schema. Each issue's comment carries the current state, so the table above lists only what is
genuinely outstanding.

---

## Notes that change how you should read the table

**#27's criterion 4 cannot be implemented as filed.** The validator has no oracle for "what actually
ran", so "reject a command that is a strict prefix of the true pipeline" is unimplementable in
general. The substitute check is narrower, purely cross-file, and would have caught the defect.

**#34 is partially fixed.** The record no longer overstates what was checked. What remains is making
the distinction visible in the *schema* rather than in prose, which is the part that needs you.

**Nothing here blocks unrelated work.** Per the operating protocol, `READY` issues that are not
waiting on a decision remain runnable, and the engineering work that does not touch these contracts
continues independently.

---

## Duplication rule

This file is an index. If a decision's argument needs to be extended, extend it **where the detail
already lives** and update the pointer here — do not copy the argument into this file. A second copy
is a second thing to keep true, and this project has already paid for that mistake once: the
recurring defect class is *a record that reports success over a scope it does not cover*, and stale
duplicated documentation is the documentation-shaped version of it.
