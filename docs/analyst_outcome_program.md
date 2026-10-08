# Analyst-Outcome Evidence Program

**Status:** APPROVED 2026-10-08 by the repository owner.

**Decision.** Pursue analyst-decision-outcome evidence through three stages, in this order, before
involving any external expert:

1. **Decision-theoretic replay** on labels already held — no human participants.
2. **Deterministic reviewer simulation** — an explicit, swept reviewer model.
3. **Secondary analysis of published human-factors data** — to anchor, not to replace.

**Rationale.** No cyber-domain contacts are available to run a live analyst study. The one available
expert is reserved for *independent verification of the method once it is complete*, not as a source
of study data. The owner's requirement is that the work be defensible enough that expert review is a
confirmation step, not a rescue. This program is designed so that each stage produces a claim that is
honest about its own limits.

---

## Stage 1 — Decision-theoretic replay (no humans)

**Question.** Given a fixed reviewer budget of `K` alerts, does routing alerts by the project's
uncertainty signal reach more true positives than routing by model score alone?

**Inputs.** Scored flows with ground-truth labels, drawn from the frozen held-out battery
(`docs/phase3_heldout_design.md`) and the validation pool. No new data collection.

**Policies compared.**

- rank by model score (descending);
- rank by uncertainty (for example distance from the frozen threshold, or predictive entropy);
- rank at random (negative control);
- oracle ranking (upper bound).

**Metrics.** True positives retrieved at budget `K`; alerts required to reach a target recall;
area under the coverage-versus-budget curve; and the same quantities at each capture separately,
because the held-out battery showed family-dependent failure.

**Claim this permits.** "On these captures, routing by *X* reaches *Y* more true positives than
routing by *Z* at a budget of `K` alerts."

**Claim this forbids.** Anything about human decision quality, analyst behaviour, over-reliance,
automation bias, or real SOC outcomes. This measures the **value of the routing**, not human
cognition.

**Why it is sound.** Deterministic, reproducible, requires no recruitment and no ethics approval, and
the labels are already held and already used for the detector's own measurement.

---

## Stage 2 — Deterministic reviewer simulation

**Purpose.** Show that the Stage 1 conclusion is not an artifact of one routing rule.

**Method.** Write the reviewer down as an explicit policy — for example a threshold-based escalation
rule with a per-shift budget — and sweep reviewer strictness × budget × routing policy. Report
escalation rate, false-escalation rate, missed-detection rate, and reviewer load.

**Claim this permits.** A system-level sensitivity analysis *under stated reviewer assumptions*.

**Claim this forbids.** Presenting simulated reviewer behaviour as observed human behaviour.

---

## Stage 3 — Secondary analysis of published human-factors data

**Purpose.** Bound the assumptions that Stage 2 had to invent.

**Method.** Identify published alert-triage / usable-security studies that report human decision
distributions or per-alert handling times, and use them **only** to justify the parameter ranges
swept in Stage 2.

**Claim this permits.** "The reviewer assumptions used in Stage 2 are consistent with reported human
behaviour in [published study]."

**Claim this forbids.** Pooling published human data as though this project collected it, or
presenting another study's participants as this project's evidence.

**Caveat.** Availability is uncertain and must be checked; if no suitable study is found, Stage 2
must state its assumptions as assumptions.

---

## Deferred: external expert verification

Once Stages 1–3 are complete, the external expert is asked to review:

- the definition of the routing metric and whether it measures what it claims;
- the Stage 2 reviewer assumptions and whether the sweep ranges are defensible;
- whether the Stage 3 anchoring is fair or selective.

This is an **independent verification role**, consistent with the project's evidence hierarchy
(external review is supporting evidence, never authoritative truth). It is not a substitute for
collected human data and must not be reported as one.

---

## Relationship to the rest of the project

- The detector chapter is already closed by the held-out battery; Stage 1 can run directly on those
  detector outputs.
- The finding/evidence spine (Milestone 5, issue #7) is the layer a human reviewer would actually
  see, so Stage 2 should express its reviewer input in terms of findings and evidence bundles once
  those exist.
- This program does not change the frozen detector policy, and no stage tunes it.
