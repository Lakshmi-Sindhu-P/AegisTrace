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

## Stage 1 — Result (2026-10-08): the hypothesis is REFUTED on this data

**The expected result did not happen, and that is the finding.** Routing by uncertainty did **not**
reach more true positives than routing by model score. It lost on **every** capture, and on two
captures it was worse than reviewing alerts at random.

Artifact: `data/evaluation/phase3_analyst_replay/replay_summary.json`
Code: `src/aegistrace/evaluation/analyst_replay.py`, `scripts/run_analyst_outcome_replay.py`
Frozen threshold `0.20`, no threshold search, model refit from the frozen policy on captures 52+47
only. Uncertainty is operationalized as **ascending distance from the decision boundary**.

True positives retrieved at a budget of 100 alerts (`model_score` / `uncertainty` / `random`):

| Capture | Family | Labeled | Malicious | TP@100 ms/un/rn | AUC ms/un/rn |
|---|---|---|---|---|---|
| 46 | Neris (validation) | 5,561 | 901 | 100 / 84 / 13 | 0.994 / 0.576 / 0.524 |
| 53 | (validation) | 9,783 | 2,168 | 100 / 37 / 26 | 0.979 / 0.445 / 0.553 |
| 48 | RBot (previously opened) | 1,732 | 63 | 24 / 20 / 2 | 0.801 / 0.676 / 0.497 |
| 49 | Murlo (held out) | 78,766 | 6,127 | **100 / 8 / 9** | 0.982 / 0.179 / 0.508 |
| 50 | Neris (held out) | 214,880 | 184,987 | 100 / 96 / 84 | 1.000 / 0.758 / 0.878 |
| 54 | Virut (held out) | 71,782 | 40,003 | **100 / 59 / 60** | 0.982 / 0.727 / 0.693 |

**Uncertainty beats model score in 0 of 6 captures.** On capture 49 it retrieves 8 true positives at
budget 100 while random retrieves 9; on 54 it retrieves 59 while random retrieves 60. Beating a
random queue is the minimum bar for a routing signal to mean anything, and on those two captures
uncertainty does not clear it.

**Interpretation.** Alerts sitting near the frozen threshold skew *benign* on these captures. The
score ranking already concentrates malicious rows at the top, so spending a scarce review budget on
boundary-adjacent alerts spends it on the rows the model is least able to separate — and those rows
are mostly benign. Threshold distance is therefore not merely uninformative here; it is
anti-correlated with maliciousness at the top of the queue.

**What this does and does not refute.** It refutes *threshold-distance* uncertainty as a routing
signal on these captures with this detector. It does not refute uncertainty routing in general:
predictive entropy, ensemble disagreement, or calibration-based uncertainty are different
operationalizations and were not tested. Any future attempt must be registered as a new experiment
with its own hypothesis, not folded into this one.

**Consequences.**

1. The honest headline for the project is a **negative result**: on this detector and these captures,
   model-score ordering is the strongest available routing signal, and the uncertainty signal that
   motivated Stage 1 actively misleads.
2. Stage 2's sweep must therefore treat routing policy as a variable it may *fail* to improve on,
   and must report model score as the incumbent baseline rather than an also-ran.
3. Stage 3's literature must be read for evidence about *which* alert properties predict analyst
   usefulness. The result above suggests that decision-boundary proximity is not one of them.
4. No tuning followed this result, and none may: the detector policy and threshold are frozen.

**Boundary, restated because it matters.** This measures the value of the *routing* of
already-computed scores. It is not a study of human cognition, and it supports no claim about analyst
behaviour, over-reliance, trust calibration, or automation bias.

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
