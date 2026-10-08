# LLM A/B Triage — Pre-Registered Analysis Protocol

**Status: `FROZEN_PRE_DATA`** — frozen at `2026-10-09T00:00:00Z`, before any provider output exists.

Machine-readable source of truth: [`configs/llm_ab_preregistration.json`](../configs/llm_ab_preregistration.json).
This document renders that artifact; where the two differ, the JSON governs.

This protocol governs the **independently frozen LLM A/B triage**. The provider run it describes is
currently **blocked** (see [`configs/triage_provider_freeze.json`](../configs/triage_provider_freeze.json),
status `BLOCKED_HUMAN`). Writing the protocol before the run is the entire point: an analysis
protocol chosen after seeing model output is a story fitted to that output.

## Hypothesis

**H1.** On the deterministic, label-free triage corpus, two mutually blind assessors instantiated
from two distinct model families will cite substantially overlapping evidence on most bundles, so
that the mean per-bundle Jaccard overlap of cited evidence ids across a complete 20-bundle run is at
least 0.50.

This is falsifiable: the run produces a number, and the number can fall below 0.50.

## The single primary metric

**`mean_per_bundle_agreement_score`** — the unweighted arithmetic mean of
`TriageComparison.agreement_score` over exactly one comparison per bundle, for the 20 bundles of a
complete run.

`agreement_score` is the **Jaccard overlap of the two assessments' cited evidence ids**:

```text
agreement_score = len(shared_evidence_ids)
                  / (len(shared_evidence_ids) + len(left_only_evidence_ids) + len(right_only_evidence_ids))
```

and it is defined as **0.0 when neither side cites anything**. It is produced by deterministic code
(`aegistrace.triage.agreement.compare_assessments`), not by a model, so the same two assessment
records always yield the same score. The value is read from the stored comparison records; it is
never recomputed with an alternative definition.

**Why this metric is primary.** It is the only quantity in the pipeline that directly measures what
H1 asserts — how much the two independent assessors actually agree on the evidence — and it is
computable from stored records without any human judgement, any ground truth, or any extra model
call. Agreement *rate* (`agreement: bool`) would be primary, but it is strictly all-or-nothing:
`evidence_divergence` fires whenever the cited sets differ by even one id, so the boolean collapses
almost every real comparison to "disagree". The Jaccard score keeps the graded information the
schema already records in `shared_evidence_ids`, `left_only_evidence_ids`, and
`right_only_evidence_ids`.

## Decision rule

H1 is **supported** if and only if **both** hold:

1. the run is **complete** — all 20 planned bundles assessed by both roles, one comparison stored
   per bundle, no abort; and
2. `mean_per_bundle_agreement_score >= 0.50`.

Support direction is **higher**: the threshold is a floor, not a ceiling.

The 0.50 threshold is a **stated convention, not a derived value**, and is recorded as a judgement
call in the JSON. At Jaccard 0.50 the shared citations are at least as numerous as the combined
divergent citations. No published anchor for this quantity exists in this repository, so the number
is fixed here, before the data, precisely so it cannot be chosen after the mean is seen.

An **aborted** run (budget exhaustion, snapshot digest mismatch, or an inadmissible response) is
**inconclusive**: it neither supports nor refutes H1. Partial results must never be aggregated over
the completed subset, and the run must never be extended or re-sampled to rescue the decision.

## Refutation condition

**This experiment fails if** a complete 20-bundle run yields
`mean_per_bundle_agreement_score < 0.50`.

In that case the pre-registered claim that two model families cite substantially overlapping
evidence on most bundles is **false** for this corpus, this prompt version, and this pairing, and
must be reported as a negative result. A partial or aborted run does not refute H1; it leaves H1
unassessed. The experiment can therefore lose, and losing is a reportable outcome.

## Exploratory metrics (secondary only)

Every entry below is marked `"exploratory": true` in the JSON and **must never be presented as the
primary result**:

- `escalation_rate` — fraction of the 20 comparisons with `escalation_recommended == true`;
- `category_agreement_rate` — fraction without `category_mismatch`;
- `one_side_insufficient_evidence_rate` — fraction with `one_side_insufficient_evidence`;
- `mean_cited_evidence_ids_per_role` — citation volume, reported per role;
- `failed_assessment_rate` — fraction preserved as `FailedAssessment`; a nonzero value is a reason
  to distrust the primary metric, not a result.

## Sample plan and stopping rule

- **Corpus:** the deterministic, label-free corpus from `aegistrace.triage.corpus.build_corpus`.
  Entries are sorted and the digest is taken over canonical JSON, so the same bundles reproduce the
  same `corpus_digest` anywhere. The corpus carries no ground-truth label.
- **Complete run:** 20 bundles, 40 assessments (2 roles × 20), 20 comparisons.
- **Smoke test:** one bundle, both roles, run first as a plumbing check and excluded from every
  metric and from the 20. It validates structure, never an assessor.
- **Stopping rule:** stop at 20 completed bundles, or earlier on any frozen abort condition
  (provider error rate above 20 percent, snapshot digest mismatch, any response that would be stored
  without citations, or budget exhaustion). Never extend after partial results are inspected.
- **Budget:** `max_bundles_per_run` 20, `max_assessments_per_run` 40, `max_retries_per_assessment` 1,
  `max_total_calls` 60. The smoke test consumes 2 of the 60 calls.

## Analysis constraints

- No threshold and no prompt may change after any model output is seen.
- No run may be extended, restarted, or re-sampled after partial results are inspected.
- No completed bundle may be dropped from the primary metric, including abstentions; an
  `insufficient_evidence` disposition stays in the denominator.
- The deterministic comparison engine is the authority for `agreement_score`.
- Only the primary metric decides H1; the threshold may not be relaxed to convert a refutation into
  a support.

## Uncontrolled confounds

Prompt wording can shift which evidence ids an assessor cites. Provider training-data overlap is
unknown, so two families may share priors through common corpora. `temperature: 0.0` reduces but does
not eliminate sampling variance across provider versions. The corpus is small (20 bundles) and drawn
from a limited set of captures, so the mean is not a stable population estimate and no confidence
interval is pre-registered. The engine scores exact id-set overlap, so equivalent reasoning that
cites a different id is scored as divergence. Independence is enforced on the input snapshot
contract, not on the providers' internal state, and provider retention or training use of egressed
public-research addresses is governed outside this experiment.

## Not claimed

This experiment does not measure triage **correctness** — it uses no ground truth, so higher
agreement does not mean the assessors are right. It does not establish that the two families are
genuinely independent. It makes no claim about analyst behaviour, over-reliance, trust calibration,
or automation bias. It makes no operational or generalization claim. It does not establish that 0.50
is a good operating point. A supported result is not evidence that the dispositions are usable for
routing or escalation in any real system.

## Why this was written before the run

A pre-registration is only meaningful if it **predates the outputs it constrains**. If the metric,
the threshold, or the decision rule were chosen after seeing the numbers, they would be selected to
fit those numbers, and the "result" would be a description of the data rather than a test of a
claim. That failure is undetectable from the write-up alone — which is why it must be prevented by
construction. This protocol was therefore frozen while **nothing has run**: no provider is
designated, no credential path exists, no assessment has been produced, and the provider freeze
status is `BLOCKED_HUMAN`.

Two mechanisms keep that claim checkable:

1. **The attestation.** `pre_data_attestation` in the JSON records the observed state at freeze
   time — `provider_freeze_status` = `BLOCKED_HUMAN`, `measured_spend` = `0 - nothing has been
   sent`, `provider_runs_completed` = 0, `assessments_on_disk` = 0 — each verified by inspection
   rather than assumed, with corroborating evidence listed.
2. **The ordering check.** `scripts/validate_preregistration.py` requires `frozen_at` to be strictly
   earlier than the `created_at` of every registry run that references a provider or triage run. A
   protocol written after such a run is rejected by executable code, not by convention.

## Reproducing the check

```bash
.venv/bin/python scripts/validate_preregistration.py
.venv/bin/python -m pytest tests/test_preregistration.py -q --no-cov
```
