# AegisTrace — GitHub Issue History

44 issues exported from `Lakshmi-Sindhu-P/AegisTrace`. Each entry preserves the problem → cause → attempts → failures → solution → change → proof chain.

| # | State | Title |
|---|---|---|
| 1 | CLOSED | [Foundation] Seed issue, trace, and reusable-lesson provenance |
| 2 | CLOSED | [Phase 3] Validate a causal host/time representation for residual flows |
| 3 | CLOSED | [Phase 3] Diagnose Scenario 10/51 causal overlap subgroup |
| 4 | CLOSED | [Quality] Harden Phase 3 reproducibility and evidence checks |
| 5 | CLOSED | [Quality] Correct post-repair documentation drift and add CI |
| 6 | CLOSED | [Phase 3] Scenario-held-out detector generalization check |
| 7 | CLOSED | [Milestone 5] Deterministic finding and evidence spine |
| 8 | CLOSED | [Finding] Reported detector recall is bounded by the alert-volume cap, not model quality |
| 9 | CLOSED | Phase 3 behavioral feature builder: superlinear prior-window scan blocks large captures |
| 10 | OPEN | [Milestone 6] Analyst-outcome evidence program (stages 1-3) |
| 11 | OPEN | [Milestone 7] LLM evaluation corpus, provider freeze, and independent A/B triage |
| 12 | CLOSED | [Milestone 8] Tiered human review and append-only review history |
| 13 | CLOSED | classify_tier routes a case with zero or one assessment to Tier A, the least-scrutiny tier |
| 14 | CLOSED | A single model answering as both assessor roles is accepted and reported as independent agreement |
| 15 | CLOSED | verify_claim lets a model score carry OBSERVED_FACT and DETERMINISTIC_DERIVATION |
| 16 | CLOSED | Two repo validators report a clean pass on empty input |
| 17 | CLOSED | Two sibling machine checks still pass vacuously for zero assessments (incomplete fix of #13) |
| 18 | CLOSED | Leakage audits return passed=True for an empty baseline |
| 19 | CLOSED | Three further guards accept degenerate input and report success |
| 20 | CLOSED | spine_id is not stable: it changes with bundle ordering and when an unrelated bundle is added |
| 21 | CLOSED | Timing values in three evaluation artifacts make their recorded manifest digests irreproducible |
| 22 | CLOSED | Feature builders emit records in raw input order, so artifacts differ for the same logical input |
| 23 | CLOSED | Reproducibility flag is not transitive: uncertainty_summary.json claims true but consumes two false artifacts |
| 24 | CLOSED | Transitivity check silently passes on a fresh clone, where CI runs and no artifact bytes exist |
| 25 | CLOSED | validate_results_ledger crashes with a traceback instead of reporting on malformed input |
| 26 | CLOSED | Independence guard and determination disagree, and shared model_id is never compared |
| 27 | OPEN | Stability artifact provenance omits the repair step that rewrote it |
| 28 | CLOSED | Adopt guard falsification as a standing check: 44 guard raises the suite never executed |
| 29 | CLOSED | Ledger evidence is unverified: the validator checks artifact digests, never the claimed values |
| 30 | CLOSED | Tiered review records a tier it never reconciles with the assignment it judges |
| 31 | CLOSED | build_evidence_bundle is quadratic and its Iterable contract is a lie |
| 32 | OPEN | The 20-bundle sample is set by argument order, but the preregistration attributes it to the corpus |
| 33 | OPEN | TriageComparison's left/right evidence fields do not track the left/right arguments |
| 34 | OPEN | verify_claim checks evidence kind but never whether the cited reference exists |
| 35 | CLOSED | triage_id omits severity and cited evidence, so distinct assessments can share an identity |
| 36 | CLOSED | SNAPSHOT_FIELDS is derived from EvidenceBundle, so the snapshot allowlist guard cannot fail |
| 37 | CLOSED | Empty-but-valid ingestion input reports a clean success over zero rows (both parsers) |
| 38 | CLOSED | event_id_for ignores row content and raw_checksum, so distinct records collide |
| 39 | CLOSED | rejected_rows counts the header issue, so accepted+rejected != rows_seen |
| 40 | CLOSED | review_id_for ignores final_disposition and subject_role, so distinct human judgments collide |
| 41 | CLOSED | Dead guard: the FAILED_ASSESSMENT branch in classify_tier is unreachable |
| 42 | CLOSED | model_copy bypasses HumanReview and ReviewHistory validators (latent) |
| 43 | CLOSED | Schema validators do not enforce builder-side invariants (TriageComparison, feature datasets, SpineRecord) |
| 44 | CLOSED | Vacuous test assertions: a test that cannot fail is indistinguishable from one that passes |

---

## #1 — [Foundation] Seed issue, trace, and reusable-lesson provenance

**State:** CLOSED  |  **Opened:** 2026-09-29T05:35:42Z  |  **Closed:** 2026-09-29T05:37:53Z

State: DONE

## Objective
Establish the approved Option-A provenance foundation without an autonomous scheduler.

## Problem and origin
The repository had `AGENTS.md` and `MEMORY.md`, but no structured issue lifecycle, redacted execution trace schema/validator, or versioned reusable-lesson store.

## Attempts and decision
Design/reconciliation first; implementation was approval-gated. Full OTel, GitHub Actions scheduling, self-modifying governance, and background agents were explicitly excluded.

## Change
Commit `ad6b498` adds:
- issue forms and lifecycle documentation;
- explicit ignored local trace paths;
- strict Pydantic trace and lesson schemas;
- JSONL/solution validators;
- append-only `docs/solution_knowledge.json` storage;
- MIT license.

## Evidence and validation
- Local trace reference: `.context/traces/seed-option-a-implementation.jsonl`
- Code/version: `ad6b498`
- `uv run pytest`: 60 passed, 91.95% coverage
- `uv run ruff check .`: passed
- `uv run mypy src`: passed
- `uv run python scripts/validate_solution_knowledge.py docs/solution_knowledge.json`: passed

## Outcome
The foundation is ready for one real AegisTrace task. No scheduler or automatic governance changes are enabled.

## Follow-up
Use issue #2 for the first real task under this protocol before proposing further orchestration features.

### Comment — 2026-09-29T05:36:34Z

Trace linkage (append-only): `cd2918b77eca34c0472434a77ba2a68071d3c9fbae33049c3e6890550d9e1282` in `.context/traces/seed-option-a-implementation.jsonl`; code version `ad6b498`; local validator: `valid_records=1`. The trace records the approved implementation action, source refs, validation, and outcome.

### Comment — 2026-09-29T05:37:52Z

Outcome: DONE. The approved Option-A provenance foundation is implemented and pushed in `ad6b498`; trace linkage is recorded in issue comments and locally validated. Follow-up work is tracked in #2.

---

## #2 — [Phase 3] Validate a causal host/time representation for residual flows

**State:** CLOSED  |  **Opened:** 2026-09-29T05:35:54Z  |  **Closed:** 2026-09-29T06:58:16Z

State: READY

## Objective
Use the new issue/trace protocol on the next real AegisTrace investigation: determine whether richer causal host/time-window representation reduces the 3,192 malicious validation cases missed by RF, HGB, and SVM.

## Scope and boundaries
- Training/validation data only; Scenario 7 remains sealed.
- Preserve `Background` and `To-*` as unknown.
- No fusion, new model family, LLM, scheduler, or governance changes.
- Use only prior observations within each scenario; audit leakage explicitly.

## Dependency
Depends on completed foundation issue #1. Unrelated READY work remains independent.

## Evidence
- `docs/phase3_model_stability.md`
- `data/evaluation/phase3_model_stability/stability_summary.json` (local ignored artifact)
- code baseline `ad6b498`
- local trace reference: `.context/traces/phase3-residual-representation.jsonl`

## Acceptance and validation
- Define each added feature, source fields, units, missingness, leakage risk, and version.
- Compare against the frozen RF/HGB/SVM reference with scenario-aware metrics.
- Record attempts, failures, validation commands, and outcome in this issue.
- Promote a reusable lesson only through a separate validated lesson version.

## Stop conditions
Use `BLOCKED_HUMAN` for authorization, sealed-data ambiguity, material scope changes, or a decision not supported by repository evidence.

### Comment — 2026-09-29T05:37:51Z

Trace linkage: local redacted trace `.context/traces/phase3-residual-representation.jsonl`; trace_id `058e2c5e01ef913391b23b3ffa8ce7557ac36597ac05940f53f9c9e0e6fe8664`; code version `ad6b498`; action `issue_create` completed; validation `validate_agent_trace.py` returned `valid_records: 1`. This issue remains `READY` and is the first post-seed real-work follow-up.

### Comment — 2026-09-29T06:58:09Z

State: DONE

## Problem
Issue #2 asked whether a richer causal host/time representation reduces malicious validation flows missed by RF, HGB, and SVM, without opening Scenario 7.

## Cause / hypothesis
The validated `1.1.0` family represented prior 60/300-second rate/diversity, asymmetry, and repeated-short behavior, but residuals suggested missing recency, reuse, protocol-diversity, longer-window, and prior-volume context.

## Attempts and failures
- Added and tested a separate `1.2.0` representation; the `1.1.0` contract was not changed.
- Refit only RF, HGB, and Linear SVM with the same training/validation scenarios, seed, score semantics, and precision/workload operating policy.
- Found no single-model operational improvement: RF recall changed from 0.2685 to 0.2607, HGB remained a zero-alert fallback, and SVM recall changed from 0.2898 to 0.2548. SVM PR-AUC increased, but its constrained operating point worsened.
- Found and repaired a concrete reference defect: the prior HGB zero-alert correction had not regenerated disagreement/residual sections. The repair also removed an O(n²) residual quantile loop.

## Change
- Feature implementation: `src/aegistrace/features/causal.py`
- Experiment runner: `scripts/run_phase3_causal_representation.py`
- Reference/candidate reconciliation: `scripts/correct_stability_operating_point.py`, `scripts/reconcile_phase3_causal_artifact.py`
- Documentation: `docs/features.md`, `docs/phase3_causal_representation.md`, `docs/phase3_model_stability.md`, `docs/methodology.md`, `docs/evaluation.md`, `docs/roadmap.md`, `docs/learning_notes/phase_3.md`, `docs/resume_evidence.md`, `MEMORY.md`
- Reusable lesson: `solution:regenerate-derived-evidence-after-policy-change@1.0.0` in `docs/solution_knowledge.json`

## Proof / outcome
- Corrected `1.1.0` all-three residual: 68,353 malicious validation cases.
- `1.2.0` residual: 64,986, a 3,367-case (4.9%) reduction caused by lower RF/SVM overlap; no individual constrained operating point improved.
- The gain is dominated by Scenario 10/51, so it does not justify fusion, a new model family, or a final-policy promotion.
- Validation: `uv run pytest` -> 61 passed, 90.20% coverage; Ruff passed; mypy passed; trace validator -> 2 records; solution validator -> 1 solution.
- Commits: `0d0a22d` (implementation/docs), `2e1b393` (lesson/memory).
- Local redacted provenance trace (gitignored): `.context/traces/phase3-causal-representation.jsonl`; trace IDs `9b048f5f...b57` and `2f1e0918...15f8`.
- Scenario 7 remained sealed throughout; no LLM, fusion, scheduler, governance change, or new model family was added.

## Follow-up
Keep Scenario 7 sealed. The next independent READY work should audit the Scenario 10/51 residual subgroup with one narrower scenario-held-out representation hypothesis before any final-policy decision.

### Comment — 2026-09-29T06:58:15Z

Outcome: DONE. The causal representation study, reference-artifact repair, validation evidence, trace linkage, and reusable lesson are complete. Scenario 7 remained sealed. Follow-up work should use a new READY issue for the Scenario 10/51 residual audit.

---

## #3 — [Phase 3] Diagnose Scenario 10/51 causal overlap subgroup

**State:** CLOSED  |  **Opened:** 2026-09-29T08:43:05Z  |  **Closed:** 2026-09-29T08:57:07Z

State: CLOSED (completed)

Objective: Determine the structural differences between malicious validation cases where the 1.2.0 causal host/time representation changes Random Forest/Linear SVM overlap and residual cases where it does not, and test one narrower causal representation hypothesis.

Dependency: Issue #2 is complete and its conclusions are preserved.

Scope:
- Use only the existing training/validation pool (training captures 52/47; validation captures 46/53/45/51).
- Compare frozen 1.1.0 and causal 1.2.0 validation outputs and feature artifacts.
- Scenario 7 (capture 48) remains sealed: do not load, score, tune, or use for feature selection.
- Unknown Background and To-* traffic remains unknown and is excluded from supervised ground truth.
- No fusion, new model family, LLM layer, scheduler, governance expansion, or final-policy promotion.

Acceptance criteria:
- Classify malicious cases into deterministic overlap-change, unique-catch, shared-residual, and unchanged-residual groups.
- Compare feature distributions and scenario/protocol/temporal/host context without putting labels, IDs, filenames, or scenario identifiers into model matrices.
- Test one narrower causal representation hypothesis only if the observed subgroup structure supports it; a negative result is valid.
- Preserve checksums, feature versions, policy, seed, and validation commands.
- Record the issue -> trace -> experiment -> validation -> lesson chain.
- Update documentation, MEMORY.md, and reusable solution knowledge only where evidence justifies it.
- Scenario 7 remains sealed and no unrelated infrastructure changes are made.

Outcome:
- 112,001 malicious validation cases reconciled by deterministic event ID.
- RF/SVM union categories: causal-only 10,564; reference-only 7,197; both-residual 57,789; both-union 36,451.
- Scenario 10/51 contains 10,234 causal-only and 55,385 both-residual cases.
- A localized high-rate, repeated-short, low-destination-diversity burst-density hypothesis is supported descriptively in Scenario 10/51, not causally or as a generalization claim.
- 1.2.0 is not promoted; fusion, a new model family, Scenario 7 evaluation, and orchestration expansion remain deferred.

Evidence: docs/phase3_causal_overlap.md; scripts/analyze_phase3_causal_overlap.py; ignored data/evaluation/phase3_causal_overlap/overlap_summary.json; local .context/traces/phase3-causal-overlap-diagnosis.jsonl; solution:case-level-overlap-before-representation-promotion@1.0.0; commits 55bbbf4, 25e03e8, and 76e5603.

### Comment — 2026-09-29T08:57:02Z

## Outcome

Issue #3 is complete. The bounded diagnostic compared the corrected 1.1.0 stability case records with the 1.2.0 causal case records over the existing four non-sealed validation captures. It did not refit models, tune thresholds, promote 1.2.0, reopen Scenario 7, or add fusion/model families/orchestration.

### Evidence

- Reconciled 112,001 authoritative malicious validation cases by deterministic event ID.
- RF/SVM union categories: causal-only 10,564; reference-only 7,197; both residual 57,789; both union 36,451.
- The net union change is 3,367 cases, matching Issue #2's residual decrease.
- Scenario 10/51 (capture 51) contains 10,234 causal-only cases and 55,385 both-residual cases.
- In that subgroup, causal-only median 60-second source-connection and repeated-short counts are 2.125x the unchanged-residual median, while median 60-second destination diversity is equal (ratio 1.0x).
- This supports one localized descriptive burst-density hypothesis. It does not explain all residuals, establish causality, generalize beyond one capture, or justify promoting 1.2.0.

### Repository/provenance

- Implementation/report: commit 55bbbf4
- Reusable lesson: commit 25e03e8
- Remote branch: add-persistent-project-memory contains 25e03e8
- Report: docs/phase3_causal_overlap.md
- Diagnostic: scripts/analyze_phase3_causal_overlap.py
- Artifact: data/evaluation/phase3_causal_overlap/overlap_summary.json (gitignored)
- Trace: .context/traces/phase3-causal-overlap-diagnosis.jsonl (5 valid records)
- Lesson: solution:case-level-overlap-before-representation-promotion@1.0.0
- Scenario 7 remains sealed.

### Validation

- uv run python scripts/analyze_phase3_causal_overlap.py --created-at 2026-09-29T03:15:00Z
- uv run pytest: 61 passed, 90.20% coverage
- uv run ruff check .: passed
- uv run mypy src: passed
- trace validator: 5 valid records
- solution validator: 2 solutions
- git diff --check: passed

### Next step

Either test this narrow burst-density hypothesis on a scenario-held-out non-sealed capture with the same frozen operating policy, or stop detector expansion and begin deterministic finding aggregation. No human decision is required for the bounded result; any policy promotion, Scenario 7 opening, fusion, or new model-family scope change still requires separate evidence and approval.

### Comment — 2026-09-29T08:57:06Z

Closing as completed after the bounded overlap diagnostic, validation, provenance trace, and reusable lesson. Scenario 7 remains sealed; Issue #2 conclusions are preserved.

### Comment — 2026-09-29T09:00:57Z

Provenance correction: the initial issue-create command succeeded with an empty body because its stdin payload was not attached. The closed issue body was reconciled afterward with the full objective, scope, acceptance criteria, outcome, evidence, and deferred boundaries; no research scope or result changed. This repair is recorded as trace event f2d96e8490823d3ec73edfe987249bcbdd00d43e7c91116417358a294332afb5.

---

## #4 — [Quality] Harden Phase 3 reproducibility and evidence checks

**State:** CLOSED  |  **Opened:** 2026-09-30T21:55:43Z  |  **Closed:** 2026-09-30T22:12:37Z

State: READY

Objective: Strengthen the completed Phase 3 work without changing detector families, reopening Scenario 7, adding fusion, or expanding orchestration/governance.

Dependency: Issues #1, #2, and #3 are complete.

Bounded implementation scope:
1. Add deterministic tests for the Issue #3 overlap diagnostic using small synthetic artifacts, including category assignment, unchanged common features, output determinism, and sealed-Scenario-7 rejection.
2. Add a small tracked ExperimentRun registry and strict validator. Seed it with the existing validated Phase 3 benchmark, stability, causal representation, and overlap diagnostic runs. The registry records code revision, dataset/feature versions, split, seed, configuration, command, artifact/checksum references, and status; it is not a scheduler.
3. Add validation/report consistency checks so tracked claims and generated summaries can be reconciled to machine-readable artifacts without duplicating raw evaluation data.
4. Add deterministic uncertainty summaries where they can be computed from existing validation outputs without changing model selection or thresholds. Do not use Scenario 7.
5. Update methodology, roadmap, resume evidence, MEMORY.md, and the learning note with the new reproducibility boundary.

Planning-only follow-ups (do not execute in this issue):
- one scenario-held-out test of the burst-density hypothesis requires an independent non-sealed capture or an explicitly approved split redesign;
- deterministic finding/evidence aggregation is the next product layer if detector expansion remains unjustified.

Acceptance criteria:
- Scenario 7 is rejected by tests and remains unloaded.
- Existing detector artifacts and Issue #2/#3 conclusions are unchanged.
- Registry and validators pass with reproducible digests and no secrets/raw trace output.
- All claims remain scoped to CTU-13 validation evidence; unknown labels remain unknown.
- Full tests, Ruff, mypy, trace validation, registry validation, and diff checks pass.
- Issue history records implementation, validation, commits, outcome, and follow-ups.

### Comment — 2026-09-30T22:12:34Z

State: DONE

Outcome: completed the approved bounded Phase 3 quality-hardening slice without changing detector artifacts, thresholds, model families, Scenario 7 status, or orchestration scope.

Implemented:
- strict ExperimentRun/ExperimentRegistry schemas and tracked registry (`docs/experiment_registry.json`, five run declarations);
- registry and Phase 3 evidence validators with artifact-digest and sealed-Scenario-7 checks;
- deterministic Issue #3 overlap-diagnostic tests;
- aggregate Wilson uncertainty summary from existing confusion counts (`data/evaluation/phase3_uncertainty/uncertainty_summary.json`); this is not a PR-AUC confidence interval and does not establish generalization;
- reusable lesson `solution:registry-and-uncertainty-boundary@1.0.0` with issue/trace/code/evidence/supersession linkage.

Validation:
- `uv run pytest`: 70 passed, 90.56% coverage
- `uv run ruff check .`: passed
- `uv run mypy src`: passed
- registry validator: five runs, all required local artifacts present
- Phase 3 evidence validator: five known artifacts, Scenario 7 sealed
- solution knowledge validator: three lessons
- trace validator: six valid records in `.context/traces/phase3-quality-hardening.jsonl`
- `git diff --check`: passed

Commits/push:
- `f792c88` implementation and documentation hardening
- `4bab654` reusable lesson
- pushed to `origin/add-persistent-project-memory`

Follow-ups remain planning-only and require a bounded new issue/approval where applicable: an independent non-sealed scenario or approved split redesign for the burst-density hypothesis, then deterministic findings/evidence aggregation. Scenario 7 remains sealed.

### Comment — 2026-09-30T22:12:36Z

State: DONE — implementation, validation, outcome, commits, trace, lesson, and bounded follow-ups are recorded above.

---

## #5 — [Quality] Correct post-repair documentation drift and add CI

**State:** CLOSED  |  **Opened:** 2026-10-08T03:25:05Z  |  **Closed:** 2026-10-08T03:25:07Z

State: DONE

Problem
Issue #4's reproducibility hardening repaired a stale HGB-derived operating point in `data/evaluation/phase3_model_stability/stability_summary.json`, but `MEMORY.md` and `docs/evaluation.md` kept the pre-repair figures, contradicting the repaired artifact and `docs/methodology.md`.

Change (branch `agent/dsh/takeover`)
- `8e2aa03` docs(memory): SVM unique malicious coverage 155 -> 13,576; all-three residual 3,192 -> 68,353; removed the non-existent `docker-compose.yml` and `artifacts/` paths from the MEMORY.md repository shape; annotated the historical figure in `docs/phase3_model_stability.md`.
- `47fe534` ci: added `.github/workflows/ci.yml` (pytest 90% coverage gate, Ruff, mypy, plus clean-checkout-safe registry and solution-knowledge validators).

Evidence / verification
- `stability_summary.json`: `.svm_unique_coverage.total_unique_cases` = 13576; `.residual_error_analysis.total_cases` = 68353.
- `docs/methodology.md` already stated the corrected values.
- `.venv/bin/python -m pytest -q` -> 70 passed, 90.56% coverage.
- Ruff and mypy clean; `scripts/validate_phase3_evidence.py` exit 0; registry and solution-knowledge validators pass.

Claim boundary
Documentation and CI only. No detector output, threshold, model family, or feature version changed. Scenario 7 (capture 48) remains sealed.

### Comment — 2026-10-08T03:25:06Z

Closed as completed on branch agent/dsh/takeover (commits 8e2aa03, 47fe534). Verified: 70 passed / 90.56% coverage, Ruff and mypy clean, all validators pass.

---

## #6 — [Phase 3] Scenario-held-out detector generalization check

**State:** CLOSED  |  **Opened:** 2026-10-08T03:25:08Z  |  **Closed:** 2026-10-08T09:02:19Z

State: PROPOSED — blocked on one owner decision: which unused CTU-13 capture to acquire as the held-out test.

Objective
Close the detector chapter with one bounded, test-only, scenario-held-out check of the localized burst-density hypothesis, with no tuning.

Context
Issue #3 found the `1.2.0` causal representation's union gain (all-three residual 68,353 -> 64,986) concentrated in capture 51 / Scenario 10, and labeled it a descriptive localized hypothesis. It has never been tested on an unseen capture. The frozen policy is `configs/phase3_frozen_policy.json` (balanced Random Forest, behavioral `1.1.0`, seed 42, raw scores, threshold 0.20).

Scope
- Acquire exactly one unused original CTU-13 capture (candidates: 42/S1, 43/S2, 44/S3, 49/S8, 50/S9, 54/S13); CC-BY labeled text flows only, never packets or executables.
- Designate it test-only: never used for fitting, threshold selection, feature selection, or model comparison.
- Run the frozen policy unchanged once; report per-scenario precision, recall, F1, PR-AUC, alert volume, and the burst-density subgroup check.
- Accept the result whether favorable or unfavorable. No post-test tuning.

Out of scope
- Scenario 7 (capture 48) remains sealed.
- No fusion, no new model family, no `1.2.0` promotion, no threshold change.

Acceptance criteria
- Source checksum, manifest, and experiment-registry entry recorded.
- Test-only status enforced in code/arguments and stated in the artifact.
- A negative result is recorded as a valid outcome.
- MEMORY.md, docs, and a local trace updated in the same change.

Stop conditions
Use `BLOCKED_HUMAN` if capture licensing or labeled-file availability cannot be verified, or if the owner declines the capture.

### Comment — 2026-10-08T05:49:48Z

Design decisions recorded 2026-10-08 from owner discussion:

**Goal framing**
- This is being pursued as a RESEARCH CONTRIBUTION, not a commercial product. The repo's portfolio-artifact objective remains, but the primary aim is a defensible finding about evidence-grounded, human-oversight-first AI triage.

**Split design (supersedes any random row-level split)**
- The unit of splitting is the whole capture, never the row. Random row splits leak because flows from the same host/time window are near-duplicates; the repo already mandates grouped splits in `docs/evaluation.md`.
- Two pools: a PRACTICE pool (train/validate; rotate the validation capture so we can iterate many times) and a SEALED EXAM pool (opened once, no changes afterward).
- Test BOTH a same-family capture (clean test of whether the learned pattern transfers) and a different-family capture (cross-family generality).
- Report every capture individually, never only a pooled average.

**Status**
- A bounded landscape scan and a read-only diagnostic pass (metric reconciliation, label audit, error inspection) are running. This issue's capture choice and final scope will be set after those results.

### Comment — 2026-10-08T09:02:18Z

## State: DONE

Held-out generalization check completed at the frozen policy
(`aegistrace-phase3-behavioral-rf-validation-frozen-v1`, threshold `0.20`) with **no threshold search
and no tuning**.

- Runner: `scripts/run_phase3_heldout_battery.py`
- Artifact: `data/evaluation/phase3_heldout/heldout_summary.json` (ignored)
- Design and results: `docs/phase3_heldout_design.md`

### Result

| Exam capture | Family | Relation | Labeled | Malicious | Prevalence | Precision | Recall | Unknown rows | Unknown alerts | Unknown share |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 48 (Sc7) | RBot | same family | 1,732 | 63 | 0.036 | 0.8182 | 0.1429 | 112,345 | 47,822 | 0.426 |
| 50 (Sc9) | Neris | same family | 214,880 | 184,987 | 0.861 | 0.9993 | 0.9987 | 1,872,622 | 806,968 | 0.431 |
| 49 (Sc8) | Murlo | unseen family | 78,766 | 6,127 | 0.078 | 0.4694 | 0.9675 | 2,875,464 | 1,004,819 | 0.349 |
| 54 (Sc13) | Virut | unseen family | 71,782 | 40,003 | 0.557 | 0.9597 | 0.4515 | 1,853,367 | 623,135 | 0.336 |

### Interpretation

- Transfer within training families is near-perfect (50 Neris: precision `0.9993`, recall `0.9987`).
- Unseen families fail **non-uniformly**: 49 (Murlo) collapses precision (`0.4694`) while 54 (Virut)
  collapses recall (`0.4515`). The failure mode is family-dependent, not a single weakness.
- Capture 48's recall (`0.1429`) rests on 63 malicious rows (9 caught) and is not a stable estimate.
- Unknown-label alert share is `33.6%`-`43.1%` on every capture, consistent with the validation
  pool's `43.7%` (`docs/phase3_evaluation_diagnosis.md`, Evidence 5).

### Deviations

- **Capture 44 was not measured.** Its working set exceeds the 16 GB host memory with the current
  parser (4,710,639 rows); it thrashed swap rather than completing. The four measured captures still
  give a balanced battery: two training families (RBot, Neris) and two unseen families (Murlo, Virut).
- Capture 48 was previously opened by the historical baseline at feature `1.0.0`. It is therefore
  labelled "previously opened for the historical baseline; held out from the current frozen policy".
  Including it consumed the one-time Scenario 7 opening.

### Blocker encountered and fixed

Feature building for large captures was blocked by a superlinear prior-window scan (see #9). Fixed
with a provably output-identical O(1) mirror deque.

### Proof

- `pytest` 71 passed / 90.59% coverage; `ruff check .` clean; `mypy` clean (27 source files).
- Feature-pipeline reproducibility: rebuilding captures 46 (129,832 rows) and 53 (325,471 rows) from
  raw reproduces the frozen artifacts exactly across all 32 features plus the label column.

No threshold, model, feature, or frozen policy changed, and no tuning followed the result.

---

## #7 — [Milestone 5] Deterministic finding and evidence spine

**State:** CLOSED  |  **Opened:** 2026-10-08T03:25:23Z  |  **Closed:** 2026-10-08T09:25:33Z

State: PROPOSED — the next product layer, independent of the held-out detector check.

Objective
Build the provenance-preserving investigation spine that every later capability depends on: versioned detector records, deterministic finding aggregation, immutable evidence bundles, and claim verification.

Why
The amended research target (multi-model investigation with independent AI review) cannot be evaluated until findings and evidence bundles exist. The project rule is: no LLM triage before findings and evidence bundles.

Scope
1. Emit ML/SVM outputs as versioned DetectionResult records with preserved score semantics (no cross-model score comparison).
2. Finding schema plus deterministic, label-free aggregation by host/time/destination/port; preserve every event ID, detection ID, score, rule, and feature version.
3. Immutable EvidenceBundle per docs/architecture.md.
4. Provenance-preservation, grouping-stability, and label-leakage tests.
5. Claim-verification layer with the claim-type taxonomy (OBSERVED_FACT, DETERMINISTIC_DERIVATION, REFERENCE_BACKED_FACT, MODEL_INFERENCE, AI_INTERPRETATION, UNKNOWN_INSUFFICIENT_EVIDENCE).

Out of scope
- No LLM, no fusion, no UI, no Scenario 7, and no change to the frozen detector policy.

Acceptance criteria
- An integration test traces event -> detection -> finding -> evidence bundle without losing provenance.
- Grouping is stable under small time-window changes and never uses research labels.
- Full tests, Ruff, mypy, and validators pass.

### Comment — 2026-10-08T05:50:27Z

Scope updated 2026-10-08 for the RESEARCH CONTRIBUTION goal.

**Hard acceptance criterion (owner requirement)**
- No code path may take an automated response action. The system may observe, aggregate, verify, and recommend; a human decides and acts. This must be *enforceable and testable* (a test that fails if any response/blocking path is introduced), not merely documented.

**Framing**
- The deliverable is a defensible finding about evidence-grounded, human-oversight-first triage, plus the reproducible artifact. It is not a commercial product and makes no production or prevention claim.

**Dependencies**
- Scope and sequencing will be finalized after the running read-only diagnostics (metric reconciliation, label audit, error inspection) and the landscape scan. If the detector's binding constraint turns out to be the metric or the alert-volume policy rather than the model, the detector assumptions in this issue may change.

### Comment — 2026-10-08T09:25:32Z

## State: DONE

Milestone 5 is implemented and verified. No LLM, fusion, UI, or Scenario 7 was touched, and no
detector policy, feature builder, or existing schema field was changed.

### Delivered

| Scope item | Module |
|---|---|
| ML outputs as versioned `DetectionResult` with preserved score semantics | `src/aegistrace/detection/ml.py` |
| `Finding` schema + deterministic label-free aggregation | `src/aegistrace/schemas/findings.py`, `src/aegistrace/detection/findings.py` |
| Immutable `EvidenceBundle` | `src/aegistrace/detection/evidence.py`, `src/aegistrace/schemas/findings.py` |
| Claim verification with the claim-type taxonomy | `src/aegistrace/verification/claims.py` |
| Provenance, stability, and leakage tests | `tests/test_findings.py` |

### Acceptance criteria

**An integration test traces event -> detection -> finding -> evidence bundle without losing
provenance.** `test_event_to_detection_to_finding_to_bundle_preserves_provenance` asserts that every
finding `event_id` and `detection_id` resolves to a real event/detection, that the bundle's
`event_summaries` cover the finding's events exactly, and that each score reference carries the
model name and feature version.

**Grouping is stable under small time-window changes and never uses research labels.**

- `test_grouping_is_stable_across_window_changes_and_input_order`: two bursts separated by 540s with
  a 20s largest within-burst gap. Any window in (20, 540) must give the same two findings; windows
  120-500 are asserted byte-identical, and reversed input produces the same output.
- `test_aggregation_never_consults_research_labels`: three inputs identical except for
  `ground_truth_label` (benign / malicious / unknown) produce byte-identical findings.

**Full tests, Ruff, mypy, and validators pass.** `pytest` 80 passed / 90.85% coverage; `ruff check .`
clean; `mypy` clean on 33 source files; experiment registry (5 runs / 5 artifacts), solution
knowledge, Phase 3 evidence (Scenario 7 sealed), and agent-trace validators all pass.

### Design decisions a reviewer should check

1. **Gap-based grouping instead of fixed calendar buckets.** Fixed buckets make the grouping an
   artifact of where the grid falls, so nudging the window silently reshapes findings. Single-linkage
   by observed-time gap depends only on how far apart events actually are, which is what makes the
   stability claim checkable rather than asserted.
2. **Cross-model scores are never compared.** `ScoreReference` keeps detector identity, model
   identity, and the feature version. There is deliberately no API that ranks alerts across models;
   inventing one is a documented policy decision, not this module's job.
3. **`missing_context` and `limitations` are required contract fields.** A bundle that does not state
   what it lacks invites a reviewer to over-read it.
4. **An uncited claim is downgraded, not accepted.** `verify_claim` returns
   `UNKNOWN_INSUFFICIENT_EVIDENCE` with `verified=False` and never edits the original claim, so a
   wrong assertion stays visible in the record instead of being silently corrected.

### Process note

Three delegated attempts to implement this milestone failed or stalled with an empty working tree
(the first preferred model failed repeatedly; the second read the codebase then stalled and was
stopped; the third failed without writing). The working tree was verified clean between attempts, so
no partial or duplicated work was carried forward, and implementation was completed directly in the
main session.

Refs: commit `659d0e7`; local trace `.context/traces/phase3-milestone5-spine.jsonl` (6 records,
validated).

---

## #8 — [Finding] Reported detector recall is bounded by the alert-volume cap, not model quality

**State:** CLOSED  |  **Opened:** 2026-10-08T05:53:40Z  |  **Closed:** 2026-10-08T09:25:53Z

State: VALIDATING — read-only diagnostic, 2026-10-08. No policy, artifact, or code was modified.

## Problem
The Phase 3 stability study reports operating-point recall around 27% and a 68,353-case all-model residual, which has been read as "the detector is weak." The repaired artifacts show that figure is an artifact of the evaluation policy, not of model discrimination.

## Evidence — data/evaluation/phase3_model_stability/stability_summary.json
Pooled labeled validation population: `support` 165,276 = `positive_count` 112,001 (67.8%) + `negative_count` 53,275.

Random Forest:
- threshold 0.20 (the frozen policy): precision 0.9903, recall 0.9949, TP 111,426, FP 1,092, FN 575, known_alerts 112,518 (680.8 per 1,000 labeled) — `eligible=False`.
- threshold 0.73 (selected operating point): precision 0.99987, recall 0.2685, TP 30,072, FP 4, FN 81,929, known_alerts 30,076 (182.0 per 1,000) — `eligible=True`.

HistGradientBoosting at threshold 0.20: precision 0.9954, recall 0.9931, FN 772.

Operating policy (same artifact): maximize recall subject to `precision >= 0.95` AND `alerts_per_1000_labeled_flows <= 200`.

## Mechanism
The labeled population is 67.8% positive. A cap of 200 alerts per 1,000 labeled flows permits flagging at most 20% of labeled rows, so even a perfect ranker can capture at most 20 / 67.8 = **29.5%** of positives. The observed 26.9% is ~91% of that mathematical ceiling. The cap, not the model, is the binding constraint. `alerts_per_1000_labeled_flows` is population-dependent and behaves as a recall ceiling whenever the labeled set is mostly positive.

## Consequence
- The frozen threshold (0.20) already achieves ~99% recall at ~99% precision on labeled validation; it was excluded only because it exceeds the workload cap.
- The genuine open uncertainty is the **unknown-label population**: the hardening artifact records 186,269 alerts at the frozen threshold across 455,303 total rows, which have no authoritative class and cannot be scored.
- The rules detector is separately and genuinely weak (recall 0.0013); this finding concerns the supervised models only.

## Caveats
- Validation evidence only (captures 45/46/53/51); not a held-out or real-world generalization claim.
- Does not establish performance on the unknown population.

## Next
Reframe the detector chapter: measure at the frozen threshold on a capture-grouped held-out set and report the unknown-label workload separately, instead of selecting a threshold under a labeled-population-relative cap.

### Comment — 2026-10-08T06:01:56Z

Research-landscape addendum (bounded, 2026-10-08)

A scan via the open OpenAlex index (seven topical queries; papers not read in full) found that "evidence-grounded LLM-assisted SOC investigation" is **already an occupied area** — e.g. *Argus: Evidence-Grounded LLM-Assisted Investigation for Security Operations Centers* (2026, https://doi.org/10.5281/zenodo.22259142) and *Insider Threat Detection and Evidence-Grounded Triage Using a Heterogeneous Dual-Branch Network and a Constrained LLM Agent* (2026, https://doi.org/10.3390/app16147054). LLM injection/hallucination risk inside the SOC is also actively studied.

Implication for this finding: the defensible contribution is **method and measurement**, not another triage system — evaluation under label scarcity (94.3% of validation rows are unlabelled here), unknown-label workload as a first-class result, and independently frozen dual-role adjudication that refuses agreement-as-truth.

Full scan: `docs/research_landscape.md`. Commercial products and market sizing were **not** verified because web search was unavailable; the scan is not a systematic review.

### Comment — 2026-10-08T09:25:52Z

## State: DONE

The finding stands as recorded, and its "Next" step has now been completed.

### Next step resolved

The recommended reframe was approved as policy on 2026-10-08 and executed:

1. **Reframe approved.** The Phase 3 evaluation diagnosis is no longer a proposal: the frozen
   threshold is measured on capture-grouped held-out captures and the unknown-label workload is
   reported separately, instead of selecting a threshold under a labeled-population-relative cap.
   Recorded in `MEMORY.md`.
2. **Unknown-label workload measured.** `scripts/report_phase3_unknown_workload.py` produces Evidence
   5 in `docs/phase3_evaluation_diagnosis.md`. At the frozen threshold `0.20`, the frozen balanced
   Random Forest raises `1,189,850` alerts on `2,720,880` unlabeled rows (43.7% of unlabeled traffic)
   and `1,302,368` across all `2,886,156` rows.
3. **Capture-grouped held-out battery run.** Issue #6 (closed): four exam captures measured at the
   frozen threshold with no threshold search. Within training families the policy transfers almost
   perfectly (50 Neris: precision `0.9993`, recall `0.9987`); unseen families degrade non-uniformly
   (49 Murlo precision `0.4694`; 54 Virut recall `0.4515`). Results in
   `docs/phase3_heldout_design.md`.

### Consequence for the original claim

The mechanism recorded here is confirmed rather than hypothetical: the frozen threshold does achieve
the ~99% labeled recall this issue predicted, the reported ~27% operating-point recall was a property
of the workload cap, and the held-out battery now supplies exactly the capture-grouped measurement
this issue asked for. The cap arithmetic (`20 / 67.8 = 29.5%` ceiling, observed `26.9%`) is unchanged
and still correct.

Nothing in this diagnostic was invalidated, and no threshold, artifact, or frozen policy was changed
by it.

Refs: #6 (closed); `docs/phase3_evaluation_diagnosis.md` Evidence 5; `docs/phase3_heldout_design.md`.

---

## #9 — Phase 3 behavioral feature builder: superlinear prior-window scan blocks large captures

**State:** CLOSED  |  **Opened:** 2026-10-08T07:31:11Z  |  **Closed:** 2026-10-08T09:02:22Z

## State: IN_PROGRESS

## Problem

Building behavioral `1.1.0` features for the held-out exam captures (44/49/50/54, 263-640 MB) did
not complete in roughly 55 minutes even for the first capture. The same builder had previously
processed every cached capture (largest 179 MB / 1.3 M rows) in reasonable time, so the exam
captures were assumed to be merely large.

## Cause

`build_ctu13_behavioral_features` computed `prior_connections` as

```python
sum(flow.observed_at > connection_cutoff for flow in state.flows)
```

scanning the host's entire 300 s window on every event. For a host with F flows inside one window
the total work is O(F^2). Normal captures have small windows, so the cost stayed invisible;
spam/botnet captures (for example Virut) produce bursts large enough to make a single capture take
hours.

Measured: 129,832 rows (capture 46) built in 15.8 s (~8.2 k rows/s), so 1.9 M rows should take about
four minutes. Capture 54 exceeded 30 minutes, which is superlinear.

## Solution

Maintain a second deque `_HostState.recent` that mirrors the 60 s prior-flow window in insertion
order. Pop expired entries from the left, then `prior_connections = len(state.recent)`. This is the
identical count in O(1) amortized time.

## Proof of semantic equivalence

Rebuilt two cached captures from raw and compared every one of the 32 features plus the label column
against the frozen cached artifacts:

- capture 46: 129,832 rows, **IDENTICAL**
- capture 53: 325,471 rows, **IDENTICAL**

Method: `scripts/run_phase3_heldout_battery.py --features-only --feature-dir data/evaluation/phase3_heldout_repro`,
then column-wise `pyarrow.Table.equals` against `data/evaluation/phase3_model_stability/`.

## Gate

`pytest` 70 passed / 90.49% coverage; `ruff check .` clean; `mypy` clean (27 source files).

## Note

This is a performance fix, not a methodology change: no feature value, threshold, model, or frozen
policy changed, and no held-out data was consumed to derive it.

### Comment — 2026-10-08T09:02:21Z

## State: DONE

Fixed and verified.

### Change

`src/aegistrace/features/behavioral.py`: `prior_connections` now reads `_HostState.recent`, a deque
mirroring the 60s prior-flow window, instead of scanning the host's whole 300s window on every event.
O(1) amortized, identical count.

### Proof of semantic equivalence

Rebuilt cached captures from raw and compared all 32 features plus the label column against the
frozen artifacts:

- capture 46: 129,832 rows — **IDENTICAL**
- capture 53: 325,471 rows — **IDENTICAL**

### Effect

Capture 54 (1,925,149 rows) went from >30 minutes (killed mid-run) to **248.65 s**.

### Regression test

`tests/test_features.py::test_behavioral_prior_connection_count_expires_at_sixty_seconds`

### Gate

`pytest` 71 passed / 90.59% coverage; `ruff` clean; `mypy` clean.

Performance fix only: no feature value, threshold, model, or frozen policy changed, and no held-out
data was consumed to derive it.

### Residual limitation

Captures above roughly 2M rows still exceed the 16 GB host memory during parsing. Capture 49
(2,954,230 rows) completed only after the battery runner released parsed events before materializing
the matrix; capture 44 (4,710,639 rows) remains unmeasured. Lifting this ceiling would need a
streaming or chunked parser and is not required for this issue.

---

## #10 — [Milestone 6] Analyst-outcome evidence program (stages 1-3)

**State:** OPEN  |  **Opened:** 2026-10-08T09:14:15Z  |  **Closed:** —

## State: APPROVED — not started

Program doc: [`docs/analyst_outcome_program.md`](../blob/main/docs/analyst_outcome_program.md),
approved 2026-10-08 by the owner.

### Objective

Produce defensible analyst-decision-outcome evidence without a live analyst study, in three ordered
stages.

### Why

No cyber-domain contacts are available to run a human study. The one available expert is of a very
high standard and time-constrained, so the project must exhaust its own options first and involve that
expert only to independently verify a *completed* method — not to rescue an unfinished one.

### Scope

1. **Decision-theoretic replay** on already-held labels: given a reviewer budget `K`, compare ranking
   by model score vs. uncertainty vs. random vs. oracle. Metrics: true positives at `K`,
   alerts-to-target-recall, coverage-curve area, reported per capture.
2. **Deterministic reviewer simulation**: encode reviewer policies as explicit rules and sweep
   strictness × budget × routing policy; report escalation rate, false-escalation rate,
   missed-detection rate, and reviewer load.
3. **Secondary analysis of published human-factors data**: use published alert-triage studies only to
   bound Stage 2's parameter ranges.

### Out of scope

- No human participants, no recruitment, no ethics submission.
- No change to the frozen detector policy.
- No claim of human decision quality, analyst behaviour, over-reliance, automation bias, or real SOC
  outcomes from Stages 1-3.

### Acceptance criteria

- The Stage 1 result is deterministic and reproducible from a committed script.
- Every stage states explicitly what it can and cannot claim.
- Stage 3 either finds suitable published data or states Stage 2's assumptions as assumptions.
- Full tests, Ruff, mypy, and validators pass.

### Dependencies

- Stage 1 can run directly on the closed detector chapter's outputs
  (`docs/phase3_heldout_design.md`).
- Stage 2 should express reviewer input in terms of findings and evidence bundles once Milestone 5
  (#7) lands.

### Comment — 2026-10-08T10:12:28Z

## Stage 1 — `IN_PROGRESS`

Starting stage 1 (decision-theoretic replay) per the approved order 1 → 3 → 4. No human participants,
no new data collection, no external contact.

**Question.** Given a fixed reviewer budget `K`, does routing alerts by the project's uncertainty
signal retrieve more true positives than routing by model score alone?

**Inputs (all already local and verified present).** The frozen policy's own training captures
(52, 47), the validation pool (46, 53), and the four measured battery captures (48, 49, 50, 54).
Capture 44 remains excluded: 4,710,639 rows exceeds available RAM, as recorded in
`docs/phase3_heldout_design.md`.

**Policies.** `model_score` (descending), `uncertainty` (ascending distance from the frozen
threshold), `random` (seeded negative control), `oracle` (upper bound).

**Why `random` matters.** A routing policy that beats `model_score` is only meaningful if it also
beats `random`. Without that control, a win could simply mean the model's ranking carries no signal
on that capture.

**Measurement constraints.**
- No threshold change, no refit, no feature change. This is measurement only.
- `UNKNOWN`-label rows are excluded from the labeled evaluation and reported separately. They are
  never counted as false positives.
- Each capture is reported separately. The battery showed family-dependent failure (Murlo and Virut
  both collapsed on different axes), so a pooled figure would hide precisely the effect of interest.
  Any pooled number will be labelled as losing capture identity.
- Training data is the frozen policy's own training captures, so no exam capture informs fitting.

**What this can claim.** "On these captures, routing by X reaches Y more true positives than routing
by Z at a budget of K alerts."

**What this forbids.** Anything about human decision quality, analyst behaviour, over-reliance,
automation bias, or real SOC outcomes. This measures the value of the **routing**, not human
cognition. That boundary is enforced in the artifact's own limitations block, not just stated here.

### Comment — 2026-10-08T10:17:37Z

## Stage 1 — `VALIDATED`, and the hypothesis is **REFUTED**

The expected result did not happen. Routing by uncertainty did **not** reach more true positives than
routing by model score. It lost on **every** capture, and on two captures it was worse than reviewing
alerts at random.

Commit `59e55c3`. Artifact `data/evaluation/phase3_analyst_replay/replay_summary.json`, sha256
`1d00ec29273207958d3a48d0c63b8b1a69fcc8e5d3375c342a2c59169a956abe`. Re-running the runner today
reproduces that digest **byte-for-byte** in 44 seconds, so the result is reproducible, not incidental.

### Numbers

True positives at a budget of 100 alerts (`model_score` / `uncertainty` / `random`):

| Capture | Family | Labeled | Malicious | TP@100 | AUC ms/un/rn |
|---|---|---|---|---|---|
| 46 | Neris (validation) | 5,561 | 901 | 100 / 84 / 13 | 0.994 / 0.576 / 0.524 |
| 53 | (validation) | 9,783 | 2,168 | 100 / 37 / 26 | 0.979 / 0.445 / 0.553 |
| 48 | RBot (previously opened) | 1,732 | 63 | 24 / 20 / 2 | 0.801 / 0.676 / 0.497 |
| **49** | **Murlo (held out)** | 78,766 | 6,127 | **100 / 8 / 9** | 0.982 / 0.179 / 0.508 |
| 50 | Neris (held out) | 214,880 | 184,987 | 100 / 96 / 84 | 1.000 / 0.758 / 0.878 |
| **54** | **Virut (held out)** | 71,782 | 40,003 | **100 / 59 / 60** | 0.982 / 0.727 / 0.693 |

Uncertainty beats model score in **0 of 6** captures. On 49 and 54 it does not even beat random.

### Interpretation

Boundary-adjacent alerts skew **benign** on these captures. Spending a scarce review budget on
threshold-adjacent alerts spends it where the model cannot separate the classes — and those rows are
mostly harmless. Threshold distance is therefore not merely uninformative here; it is
anti-correlated with maliciousness at the top of the queue.

### Scope of the refutation — do not over-read this

Refuted: **threshold-distance** uncertainty as a routing signal, for this detector, on these captures.

Not refuted: predictive entropy, ensemble disagreement, or calibration-based uncertainty. Those are
different operationalizations and were never tested. Any future attempt is a new experiment with its
own hypothesis, not a continuation of this one.

### Consequences

1. The honest headline is a **negative result**. Model-score ordering is the strongest available
   routing signal here, and the uncertainty signal that motivated Stage 1 actively misleads.
2. Stage 2 must treat `model_score` as the **incumbent baseline** to beat, not an also-ran.
3. Stage 3's literature should be read for which alert properties predict analyst usefulness.
   This result suggests decision-boundary proximity is not one of them.
4. No tuning followed the result, and none may: the detector policy and threshold remain frozen.

### Boundary, restated

This measures the value of the **routing** of already-computed scores. It is not a study of human
cognition and supports no claim about analyst behaviour, over-reliance, trust calibration, or
automation bias. Unknown-label rows were excluded from every metric and never counted as false
positives. Each capture was evaluated separately; no pooled figure is reported.

### Comment — 2026-10-08T10:23:44Z

## Stage 2 — `VALIDATED`: the stage 1 refutation survives the sweep

Stage 1 compared **one** retrieval rule. Stage 2 replaces that rule with an explicit reviewer *policy*
and sweeps it, so a reviewer-policy artifact can no longer explain the negative result.

Commit `7458f3f`. Artifact `data/evaluation/phase3_reviewer_simulation/simulation_summary.json`,
sha256 `88120f046ad0b9c836828cde1e9c9b6a47a9e362a05255165925fc735ceda4ef`.

### The reviewer model — a policy, not a person

A reviewer works alerts from a queue ordered by the routing policy, up to a **shift budget** `B`, and
escalates iff `score >= S`. Alerts past `B` are never worked. Sweep: `S` ∈ {0.1, 0.2, 0.3, 0.5, 0.7},
`B` ∈ {10, 25, 50, 100, 200}, over `model_score` / `uncertainty` / `random` — 75 policies per capture,
**450** across the six captures. `oracle` is omitted: it reads ground-truth labels and is not an
achievable reviewer policy.

### Result

Uncertainty beats `model_score` at equal `(S, B)` in **0 of 6 captures**. `model_score` is the best
routing policy at every strictness and every shift budget on every capture. Best true escalations at
`B = 200`:

| Capture | model_score | uncertainty | random |
|---|---|---|---|
| 46 | 200 | 175 | 32 |
| 53 | 200 | 116 | 34 |
| 48 | 10 | 2 | 0 |
| 49 | 200 | 10 | 15 |
| 50 | 200 | 192 | 169 |
| 54 | 200 | 104 | 60 |

Random again beats uncertainty on capture 49 (15 vs 10), independently reproducing stage 1.

### A detector observation, recorded rather than smoothed over

On capture 48 at `S = 0.1, B = 200`, `model_score` yields only **10** true escalations although stage 1
retrieved **33** true positives in the top 200. Ranking parity between the two was verified — identical
ordering and tie-breaks. The cause is the escalation rule meeting the probability scale: roughly 23 of
those top-200 malicious rows carry a RandomForest probability below 0.1, so `score >= 0.1` never
escalates them. This is the same recall collapse the held-out battery recorded for capture 48, and it
means an absolute strictness threshold is a blunt instrument on a poorly-calibrated capture.

### Metric convention, stated to prevent misreading

`false_escalation_rate` here is `false_escalations / escalations` — the complement of precision —
**not** false escalations per alert reviewed. The implemented convention differs from the one
originally specified; it is recorded in the module docstring, the program document, and the registry
rather than left ambiguous.

### Stage 3 evidence base, and a caught error

`docs/human_factors_evidence.md` now bounds what the simulation may assume. Two sources were
re-fetched and their numbers read from source tables, which **caught a transcription error** in the
delegated scan: the IDS false-alarm experiment's per-alert time is a median of **13.44 s vs 18.76 s**
(mean 13.95 vs 19.25), not the "15.6 s vs 21.4 s" first reported. Its precision medians (0.80 vs 0.33)
are correct. A control fetch that returned empty was diagnosed as broken network egress in the review
shell, not missing sources, and that spurious "not found" result was discarded.

**Two quantities have no usable published source** and must remain explicit free assumptions:
alerts-per-shift **workload thresholds**, and **SOC-specific automation bias**. No AegisTrace result
may claim to model real reviewer load or real over-reliance.

### Boundary

The reviewer is a policy, not a person. No claim about analyst decision quality, over-reliance, trust
calibration, or automation bias. Unknown-label rows are excluded from every metric; no pooled figure
is reported. The shift budgets and strictness values are free assumptions.

Gate: **132 passed / 91.72%**, ruff and mypy clean (45 files), registry at 7 runs with 0 missing
artifacts.

---

## #11 — [Milestone 7] LLM evaluation corpus, provider freeze, and independent A/B triage

**State:** OPEN  |  **Opened:** 2026-10-08T09:26:32Z  |  **Closed:** —

## State: `BLOCKED_HUMAN` — the provider-independent scope is implemented and verified; only the frozen A/B *execution* remains, and it needs a human decision on assessor independence (see the round-39 status comment).

Depends on an owner decision on LLM provider selection (see Dependencies). The provider-independent
parts (1, 2, and 5 below) can proceed without it.

### Objective

Build the LLM triage layer on top of the Milestone 5 spine: a frozen evaluation corpus, two
independently frozen assessor roles that cannot see each other's work, and a deterministic engine
that adjudicates their disagreement without an LLM in the loop.

### Why

This is the project's sharpest defensible research gap. The landscape scan (`docs/research_landscape.md`)
found the "LLM-assisted SOC investigation" area crowded, with closest prior art treating multi-agent
LLM triage as agents that **collaborate** over shared evidence. No security-triage work was found
that treats *mutual blindness between frozen assessors* as the experimental variable, with their
disagreement itself as the escalation signal. Milestone 5 exists precisely so that this layer has
findings and evidence bundles to reason over; the project rule forbids LLM triage before them.

### Scope

1. **`TriageAssessment` schema** per `docs/architecture.md`: triage id, evidence-bundle version,
   finding ids, summary, proposed category/severity, a non-probabilistic confidence statement, cited
   evidence ids, uncertainties, unsupported-claim flags, next step, provider/model/prompt metadata,
   raw structured response reference, creation time, review status, and a role field
   (`triage_analyst` or `expert_adjudicator`). It must accept `insufficient_evidence` as a valid
   outcome, and an invalid or uncited response must be stored as a failed attempt rather than coerced
   into a valid assessment.
2. **LLM evaluation corpus** built deterministically from Milestone 5 findings and evidence bundles.
   Frozen, digest-recorded, and reproducible from the committed builder.
3. **Provider selection** — the owner decides. Record the choice, its cost and data-governance
   implications, and the version pinning.
4. **Two independently frozen assessor roles** with separate input snapshots, so neither can observe
   the other's output, shared scratch state, or ordering.
5. **Deterministic agreement engine**: a `TriageComparison` record per architecture, retaining raw
   structured outputs, validator results, and disagreement reasons. The engine is deterministic code,
   not a model, and is what converts disagreement into an escalation signal.

### Out of scope

- No autonomous blocking, quarantine, or remediation action of any kind.
- No model fusion.
- No UI (that is the following milestone).
- No change to the frozen detector policy.

### Acceptance criteria

- Two assessors given the same bundle cannot observe each other's output; a test proves the isolation.
- The agreement engine is deterministic: identical inputs produce byte-identical comparisons.
- An uncited or malformed LLM response is stored as a failed attempt, never as a valid assessment.
- `insufficient_evidence` is representable end to end.
- Full tests, Ruff, mypy, and validators pass.

### Dependencies

- **Milestone 5 (Issue #7) — closed.** Findings, evidence bundles, and claim verification now exist.
- **Human decision required:** which LLM provider and model to freeze, including cost and the data
  governance of sending security evidence to a third party. `MEMORY.md` records that no provider has
  been selected, and provider choice is a high-impact governance decision that no agent may make
  autonomously.

### Comment — 2026-10-08T10:08:58Z

## Status: `BLOCKED_HUMAN` — provider run deferred, per owner condition

The owner approved the provider conditionally: freeze the exact configuration and establish
reproducibility, data-egress restrictions, a bounded budget, and independent execution; run a smoke
test first; and **defer execution and report the blocker if privacy or independence cannot be
established**. Two conditions fail, so the run is deferred. Nothing was sent to any provider;
measured spend is zero.

The frozen configuration is recorded in `configs/triage_provider_freeze.json` (`BLOCKED_HUMAN`). The
frozen detector policy is untouched.

### Condition 1 — provider access: not established

The repository has no LLM client and no credential path.

- `pyproject.toml` declares only `pyarrow`, `pydantic`, `scikit-learn`.
- No HTTP or LLM client exists anywhere in `src/`.
- `src/aegistrace/config.py:68` states that only **non-secret** settings are supported, and
  `logging_config.py` exists partly to redact secrets — the project deliberately has no secret
  handling yet.

Adding an LLM client and a credential path is a new dependency **and** a secret-handling decision.
Both are owner decisions, not agent decisions.

### Condition 2 — assessor independence: not established

This is the more serious one, because it goes to the research claim itself.

Both available providers advertise the **identical five models** — they are mirrors, not independent
sources. The only two models verified to work are `deepseek-v4-flash` and `deepseek-v4.1-flash`,
which are variants of the **same family**.

Two prompts over one model is not independence. Agreement between two instances of one model would
measure the model, not the assessors — which is exactly the variable this milestone exists to study.
No available pairing clears the bar.

### Egress audit: performed, not assumed

A real `EvidenceBundle` was built from the committed fixture and the exact canonical snapshot a
provider would receive was inspected.

**Clean:** 1685 bytes; no ground-truth label, no raw payload, no file path, no scenario identifier.
The single `"label"` string is the bundle stating that labels are deliberately excluded.

**Residual:** IP addresses do reach the snapshot. That is inherent — host identity is the grouping
key — and CTU-13 is a public published dataset, so these addresses are already public. Egressing them
is a governance decision, and the provider's retention and training-use terms must be recorded before
any first call.

### What is complete and unaffected

The corpus, schemas, isolation, assessment admission, and deterministic agreement engine are done and
independent of this decision. Milestone 7 cannot close, but nothing else is held up by it.

### What is needed from the owner

Designate the two assessor configurations and approve a credential path, **or** approve deferring the
run. If the second, the honest framing is that the project ships a frozen A/B triage *harness* with
the provider run unexecuted — which is still a defensible contribution, but it must be stated that
way and not implied to be a result.

### Comment — 2026-10-08T10:28:08Z

## Transport boundary — `CURRENT / IMPLEMENTED`, offline only. Issue stays `BLOCKED_HUMAN`.

Commit `f0f9c9f`. The blocker is unchanged and is still a human decision. What changed is that the
gate is now **enforced by the code** rather than asserted in a JSON file.

### Why this was buildable without unblocking anything

The blocker has two parts: **provider access** (no client, no credential path) and **assessor
independence** (no pairing with two distinct model families). Neither is resolved here.

What was missing was the *seam* — `raw_response` was consumed by `build_assessment` everywhere and
produced by nothing. A seam can be built offline. Adding a network client or a credential path is a
dependency and secret-handling decision, and neither was touched.

### The gate is a refusal, not a warning

`assert_provider_permitted` raises `PermissionError` for any descriptor requiring egress unless the
freeze artifact's status is in `APPROVED_EGRESS_FREEZE_STATUSES` — a small allowlist that
**deliberately excludes `BLOCKED_HUMAN`**.

Verified by exercising it, not by reading it:

| Descriptor | Freeze status | Observed behaviour |
|---|---|---|
| `REMOTE`, requires egress | `BLOCKED_HUMAN` (the repo's current value) | **refused** — `PermissionError` |
| `OFFLINE_STUB`, no egress | `BLOCKED_HUMAN` | permitted |
| `REMOTE`, requires egress | `APPROVED` | permitted |

The gate opens **and closes** with the human decision. It is not stuck shut, so approving the run is a
one-field change rather than a code change.

**No network-capable import exists in either new module.** The complete import set is `hashlib`,
`json`, `collections.abc`, `datetime`, `enum`, `typing`, `uuid`, `pydantic`, and existing
`aegistrace` modules.

### Structural guarantees

- An `OFFLINE_*` response can never claim `synthetic=False`, and a `REMOTE` descriptor can never
  declare `requires_egress=False`. Self-contradictory descriptors are rejected at construction.
- `run_independent_triage` builds each snapshot **once** and sends the byte-identical digest to both
  roles. A digest mismatch is recorded as an **abort**, not compared — comparing two different inputs
  would measure the inputs, not the assessors.
- Budget exhaustion is recorded as an abort with a reason, not raised as an exception, so a partially
  completed run cannot be mistaken for a complete one.
- The orchestrator never writes to disk and never mutates the incoming bundles.

### The one-off audit is now a permanent test

The egress audit was performed by hand once. A hand audit is a claim about one afternoon, not a
property of the code, so it is now `tests/test_snapshot_leakage.py`.

Unique sentinel tokens are written into the **raw input events**, and the tests assert they reach
neither the bundle nor the snapshot. The first version of this file was **caught being vacuous**: it
asserted the label was absent from the snapshot, but the label is dropped before the bundle is even
built, so the assertion proved nothing. It now asserts the whole chain and fails loudly if the
fixture stops containing label material.

The suite also pins that network addresses **do** reach the snapshot, so stripping them later is a
deliberate, visible change rather than a silent one.

### Stale status corrected

The freeze artifact still said `"transport_status": "NOT IMPLEMENTED - no client exists"`. Repository
evidence now contradicts that, so it was corrected — and `status` remains `BLOCKED_HUMAN` because the
egress decision itself is still open. `measured_spend` remains zero.

### Still needed from the owner

1. Designate the two assessor configurations.
2. Approve a credential path.
3. Set the freeze status to an approved value — this single field is the switch that permits egress.

Or approve deferring the run. Nothing has been sent anywhere.

Gate: **161 passed / 91.98%**, ruff and mypy clean (47 files).

### Comment — 2026-10-08T10:52:02Z

## State: `BLOCKED_HUMAN` — preregistration added while blocked

The provider run remains blocked on the two owner decisions below. While blocked I built the artifact whose value depends on existing **before** any model runs.

### Added: pre-registered A/B analysis protocol

`configs/llm_ab_preregistration.json` — status `FROZEN_PRE_DATA`.

A protocol written after seeing model outputs is worth nothing, so this was created now and carries a verified `pre_data_attestation` rather than an assertion:
- `provider_freeze_status`: `BLOCKED_HUMAN`
- `measured_spend`: `"0 - nothing has been sent"` (at `budget.measured_spend`)
- `provider_runs_completed`: `0`
- `assessments_on_disk`: `0`

**Primary metric (exactly one):** `mean_per_bundle_agreement_score` — unweighted mean of `TriageComparison.agreement_score` over 20 bundles. The Jaccard definition is restated inline so a reader need not infer it.

**Decision rule:** support iff a complete 20-bundle run has mean ≥ 0.50.
**Refutation:** a complete run with mean < 0.50. An abort is inconclusive, not refuting.

**Five judgement calls recorded with their basis, not presented as derived:**
1. the 0.50 threshold is a majority-overlap convention with no repository anchor;
2. the aggregate is an unweighted mean;
3. an abort is inconclusive;
4. the 20-bundle size is inherited from the freeze budget and is **not** a power calculation;
5. the eventual two-family pairing is **assumed** to satisfy independence, not tested.

### The property that makes it real

`scripts/validate_preregistration.py` fails if the protocol is no longer frozen pre-data, or if any registered run consuming the provider predates `frozen_at`. Verified by running it, not by reading a test:

| Registry run dated | Verdict |
|---|---|
| `2026-10-08T22:00:00Z`, provider command | exit 1 ✅ |
| `2026-10-10T00:00:00Z`, provider command | exit 0 ✅ |
| `2026-10-08T22:00:00Z`, unrelated command | exit 0 (no false positive) ✅ |

Wired into CI. Gate: 233 passed / 92.48%, ruff clean, mypy clean (48 files).

### The two decisions still required from the owner

1. **Provider access** — the repo has no LLM client and no credential path. Adding one is a new dependency and secret-handling decision.
2. **Assessor independence** — the only two verified-working models are the same family. Two prompts over one model is not independence.

The single field that switches egress on is `status` in `configs/triage_provider_freeze.json`. Nothing has been sent; spend is zero; the detector policy is untouched.

### Comment — 2026-10-09T05:22:04Z

## Round 39 — the provider-independent scope is implemented and verified; what remains is a human decision

Verified against the repository rather than against narration. Every acceptance criterion that does not require a live provider is met:

| Criterion | Status | Evidence |
|---|---|---|
| Two assessors cannot observe each other's output | **MET** | `src/aegistrace/triage/snapshot.py` — `input_snapshot` accepts **only** an `EvidenceBundle`, renders canonical key-sorted JSON, and content-addresses it via `snapshot_digest` so both sides provably received identical input. Covered by `tests/test_triage.py` and `tests/test_spine_integration.py`. |
| The agreement engine is deterministic | **MET** | `src/aegistrace/triage/agreement.py` — `compare_assessments` is pure code over the two records; identical inputs produce byte-identical `TriageComparison`. |
| An uncited or malformed response is stored as a failed attempt | **MET** | `FailedAssessment` in `src/aegistrace/schemas/triage.py`; it is never coerced into a valid assessment. |
| `insufficient_evidence` is representable end to end | **MET** | `TriageCategory.INSUFFICIENT_EVIDENCE` through to `ReviewTier.tier_d_insufficient_evidence`. |
| Full tests, Ruff, mypy and validators pass | **MET** | 600 passed / 96.00%; `ruff check .` clean; bare `mypy` clean (54 source files); guard ratchet 0 / baseline 0; all six governance validators pass. |

The corpus and the frozen A/B structure also exist: `configs/llm_ab_preregistration.json` is `FROZEN_PRE_DATA`, and the provider configuration is frozen in `configs/triage_provider_freeze.json`.

### What remains, and why it is a human decision

`configs/triage_provider_freeze.json` records `BLOCKED_HUMAN` with assessor independence **NOT ESTABLISHED**. This is not an implementation gap. Every reachable provider advertises one mirrored catalog, and the only two models verified working are the same family — so a "two-assessor" run would be two instances of one model, which would make the project's central experimental variable (mutual blindness between *independent* assessors) meaningless.

Nothing has been sent to any provider. Measured spend is zero. The frozen detector policy was not modified.

The owner's standing instruction on this was conditional: *"If data privacy or experimental independence cannot be established, defer execution and report the blocker."* Independence cannot be established with the currently reachable providers, so execution is **deferred, not skipped**. A human must decide whether to accept a same-family pairing (which would refute the independence premise the experiment rests on) or wait for a genuinely independent provider.

### State correction

The state line previously read `PROPOSED — partly blocked on a human decision`, which understated work that is now committed and verified. It now reads `BLOCKED_HUMAN`, naming the one real blocker.

---

## #12 — [Milestone 8] Tiered human review and append-only review history

**State:** CLOSED  |  **Opened:** 2026-10-08T09:35:58Z  |  **Closed:** 2026-10-09T05:15:11Z

## State

`DONE` — the review contracts, deterministic tier assignment, append-only history and the minimal local UI review-submission path are all implemented and verified. Closed by the round-38 comment below.

## Problem

The project's central promise is that nothing acts without human interference. Triage produces two
independent assessments and a deterministic comparison, but until now there was no contract for what
a human *does* with them: no reviewer tier, no disposition, and no rule preventing a correction from
silently erasing the earlier record.

## Scope

Provider-independent and fully deterministic. No LLM call, no network.

1. **Review contracts** (`src/aegistrace/schemas/review.py`) — `ReviewTier`, `ReviewDecision`,
   `EscalationState`, `MachineCheck`, `TierAssignment`, `HumanReview`, `ReviewHistory`.
2. **Deterministic tier assignment** (`src/aegistrace/review/tiers.py`) — Tier A machine checks of
   evidence mechanics, Tier B guided review, Tier C expert judgement, Tier D insufficient evidence.
3. **Append-only history** (`src/aegistrace/review/history.py`) — corrections supersede the latest
   review rather than overwriting it.
4. **Minimal local UI** — implemented (`src/aegistrace/ui/`), with the single write path (`POST /decision`) appending a `HumanReview` to the durable append-only store (`src/aegistrace/storage/reviews.py`) when a store path is configured, and refusing visibly when it is not.

## Tier rules (label-free, no model opinion)

- every admissible assessment abstained → Tier D
- an assessor failed, or the assessors disagreed → Tier C
- agreed but flagged uncertainty or unsupported claims → Tier B
- agreed with no flags and all machine checks passing → Tier A

A failing machine check can raise a tier but never lower one.

## Acceptance criteria

- [x] An uncited or malformed assessment cannot become a `HumanReview` subject (`#11` guarantees this).
- [x] Tier assignment is a pure function of the assessment/comparison records; no research label is read.
- [x] `append_review` rejects duplicates, foreign subjects, orphan supersessions, and a second review
      that does not supersede the latest.
- [x] `HumanReview` refuses to be constructed as a `REVISE` without a supersession link.
- [x] Gate green: 112 tests, 91.96% coverage, ruff clean, mypy clean (43 files), all four validators pass.
- [x] Minimal local UI for review submission — `POST /decision` appends a `HumanReview` through `ReviewStore` (append-only, `review_id` primary key, history re-validated on read, head journal detects truncation) and refuses visibly when no store is configured. Covered by 17 tests in `tests/test_ui_decision_store.py` plus 30 in `tests/test_storage_reviews.py` and `tests/test_storage_contract.py`.

## Excluded by design

Severity interpretation, prioritisation, automated disposition, notification, and any write path that
acts on a system under observation. This milestone records human judgement; it does not automate it.
The review store is a local, single-writer record of human judgement — appending a review is not a
path that acts on any system under observation.

### Comment — 2026-10-09T03:57:18Z

**Status: PARTIAL — the review layer and its append-only history are DONE; the local UI is now implemented except for the write path.** Committed as `51570e4`.

## What was already done (unchanged by this comment)

The deterministic half of this milestone was complete before this round: immutable `HumanReview`/`ReviewHistory` contracts, deterministic tier assignment with Tier A machine checks, and an append-only history where a correction supersedes rather than overwrites. Issue #30 closed the last gap in that layer by making `HumanReview.tier` mean the tier **conducted** and reconciling it against the tier **required** via `TierReconciliation`.

## What this round added: the minimal local UI

The UI direction the owner approved is now implemented: **Investigation Bench (C)** as the shell, **Chain of Custody (A)** as the provenance view, **Two Witnesses (B)** as the AI-assessment comparison view, in the owner's investigator order — findings → evidence → AI comparison → review requirements → human decision.

| Component | File |
|---|---|
| Read layer (the only filesystem touch, strictly read-only) | `src/aegistrace/ui/artifacts.py` |
| FastAPI app, 8 routes | `src/aegistrace/ui/app.py` |
| Five Jinja templates | `src/aegistrace/ui/templates/` |
| Stylesheet (no JavaScript anywhere) | `src/aegistrace/ui/static/app.css` |
| Loopback-only runner | `scripts/run_local_ui.py` |

The UI performs **no detection, no scoring, no ranking and no tier classification**. Tier assignment stays in `classify_tier`. It renders what the pipeline already computed.

### Two honesty properties, enforced in code rather than in prose

1. **A missing or malformed artifact RAISES; it never becomes an empty view.** An empty screen and a broken screen must not look the same. `ArtifactUnavailableError` names the path and the reason, and the page renders that reason instead of "no findings" — which would be a claim about the evidence rather than about the plumbing. The genuinely-empty-but-valid artifact is the boundary case, and is tested separately *because it must NOT raise*.
2. **The synthetic flag is read, never inferred from the data.** `synthetic` is the artifact's own `providers_configured` declaration, and its `warning` is surfaced verbatim on every page in a persistent, non-dismissible, text+shape banner.

### Loopback-only is structural, not documented

`scripts/run_local_ui.py` exposes **no `--host` flag at all** and binds one constant, `127.0.0.1`. A documented-only constraint is enforced by whoever reads the documentation; this one is enforced by the absence of the flag.

Verified **live**, not asserted:

```
http://127.0.0.1:8791/findings     -> 200
http://192.168.2.245:8791/findings -> 000  (refused)
bound to 0.0.0.0                   -> no
```

A missing artifact is refused with a non-zero exit **before** a socket is opened, because a server that starts and then shows "unavailable" makes the operator believe it works.

## What is deliberately NOT implemented — and says so on the page

**The review-append write path.** Appending a `HumanReview` requires a durable store to append to, and none exists (`storage/` is still absent). `POST /decision` therefore returns an explicit **"NOT recorded"** page. A form that silently discarded a human decision would be the worst failure an evidence-custody tool could have, so it refuses visibly instead of pretending to save.

**Real assessment data.** The comparison view always reports "AI assessment not available", because the artifact carries no assessments and no real (non-synthetic) run exists — the provider freeze is `BLOCKED_HUMAN`.

**No silent substitution.** An unknown `spine_id` renders "no such record" rather than falling back to the first record. Showing case B when case A was asked for is a substitution, not a convenience.

## Dependency shape

FastAPI / uvicorn / jinja2 / python-multipart are declared under a **new optional `ui` extra**, never in `dependencies`. The research library must not need a web server: detection, triage, tiering and review all work headless. A test asserts this structurally against `pyproject.toml`.

## Verification

54 new tests across `tests/test_ui_app.py` and `tests/test_ui_artifacts.py`. Mutation-verified on pristine copies with verified GREEN baselines, one at a time:

| Mutation | Result |
|---|---|
| Missing file returns an empty payload instead of raising | test **FAILS** — caught |
| `synthetic` always returns True | test **FAILS** — caught |
| `records`-is-a-list guard dropped | test **FAILS** — caught |
| `warning` hardcoded instead of surfaced | test **FAILS** — caught |
| `OSError` handler deleted | test **FAILS** — caught |
| `ValueError` wrapper replaced with a bare re-raise | test **FAILS** — caught |

The last two closed the **guard ratchet**, which had correctly flagged two raises in `artifacts.py` that no test executed. It is back at baseline 0.

One test of mine was **wrong** and the template was right: it demanded the literal "not experimental results" and failed against a banner correctly reading "NOT an experimental result". The assertion was made wording-independent rather than the template bent to match a brittle string.

Gate: **553 passed**, 96.00%, ruff clean, mypy clean (52 files), guard ratchet 0.

## Remaining work for this milestone

1. A durable store-backed read layer (`storage/`), so the UI reads records rather than a JSON file.
2. Wiring the write path: `POST /decision` → `append_review`, with the `ReviewHistory` and `SpineRecord.require_history_is_open` guarantees preserved.
3. Real (non-synthetic) assessment data for the comparison view — blocked on the provider freeze being resolved by a human.

None of these is started, and none is claimed.

### Comment — 2026-10-09T05:15:09Z

## Round 38 — the review-submission write path is implemented; Milestone 8 is complete

**State: `DONE`.** The last open acceptance criterion ("Minimal local UI for review submission") is met, and the append-only history it depends on is now durable and enforced on the **read** path as well as the write path.

### What changed

- **Durable store** — `src/aegistrace/storage/reviews.py` adds `ReviewStore`: an append-only DuckDB store whose only statements are CREATE, INSERT and SELECT. `review_id` is a primary key; the chain is re-validated when a stored history is **read**, not merely trusted. Declared under a new optional `storage` extra, never a core dependency, so the research library never imports a database (`duckdb` is imported lazily inside `open()`).
- **Truncation detection** — an append-only head journal records the head review and the count. It exists because probing found a real gap: deleting the **newest** review left a shorter but internally-valid chain that `validate_chain_is_linear` cannot see. Honest limit, stated rather than implied: DuckDB does not make a table immutable, so tampering is **detected, not prevented**.
- **The single write path is real** — `POST /decision` now appends a `HumanReview` when a store path is configured, and refuses **visibly** when it is not. The refusal distinguishes "nothing was written" from "the review WAS appended but the history could not be read back to confirm it" — which is why an earlier read-back-after-append helper was **deleted rather than repaired**: it made the first sentence potentially false.
- **Loopback unchanged** — `scripts/run_local_ui.py` gained `--store` and still exposes no `--host` flag; a missing store directory is refused with exit 2 before a socket opens.

### Proof

- 47 new tests: `tests/test_storage_reviews.py` (25), `tests/test_ui_decision_store.py` (17), `tests/test_storage_contract.py` (5). Mutation-verified, including a durable append asserted by **reopening** the store.
- Gate on the frozen tree: **600 passed, 96.00%**, `ruff check .` clean, bare `mypy` clean (54 source files), guard ratchet **0 / baseline 0**.
- All six governance validators pass; trace `.context/traces/round-38-review-store.jsonl` validates (12 records).

### Two defects found in this round's own work

1. `ReviewStore.open()` raised `UnboundLocalError` instead of `ReviewStoreError` when `duckdb.connect()` itself failed — the error path was less trustworthy than the happy path. Fixed and pinned by regression tests.
2. My first contract test for the no-mutating-SQL rule scanned source lines and captured two **prose error messages** as SQL, so a future message containing "delete" would have failed it for the wrong reason. Replaced with AST extraction plus explicit non-vacuity assertions.

### Still not implemented, and stated on the pages themselves

Real non-synthetic assessment data (the comparison view reports "AI assessment not available") and a durable **evidence** read layer. The first is blocked on `configs/triage_provider_freeze.json` (`BLOCKED_HUMAN`, independence `NOT ESTABLISHED`) — that is **#11**, not this milestone.

---

## #13 — classify_tier routes a case with zero or one assessment to Tier A, the least-scrutiny tier

**State:** CLOSED  |  **Opened:** 2026-10-08T10:53:48Z  |  **Closed:** 2026-10-08T11:01:38Z

## State

`PROPOSED` — defect confirmed by direct execution; fix proposed below for review.

## Problem

`classify_tier` can assign `tier_a_machine_check` — the cheapest human-review tier — to a subject that has **no assessments at all**, or **only one**. In both cases the recorded reason states that the assessors agreed, which is a claim the records do not support.

Tier A is defined as "assessors agreed without flags; only evidence mechanics need checking". Its whole justification is that agreement has already been established between two independent roles. When there is no second assessor, that precondition is absent, but the code does not notice.

## Cause

Two independent gaps, both of the same kind — a precondition that is vacuously satisfied.

1. `classify_tier` reads agreement from `comparison.disagreement_reasons` being empty. An empty list is treated as "the assessors agreed", but it is equally consistent with there being no assessors. The comparison's `agreement` flag is taken at face value and never reconciled against the number of assessments actually supplied.

2. `machine_checks` computes `all_assessments_admissible` as `len(admissible) == len(assessments)`, which is `0 == 0` and therefore **True** for an empty input. A report that reads "0 of 0 assessments were admissible: passed" is misleading wherever it is surfaced.

The existing abstention guard requires `bool(admissible)`, so an empty set skips the Tier D rule and falls through to the agreement branch.

## Reproduction

```
tier with ZERO assessments: tier_a_machine_check
tier with ONE assessment:   tier_a_machine_check
  reasons: ['assessors agreed without flags; only evidence mechanics need checking']
```

For the one-assessment case the comparison was built with `agreement=True` and no disagreement reasons, which is schema-valid: `TriageComparison.assessment_ids` has `min_length=1`, so a single-assessment comparison is permitted by the contract.

All four machine checks pass in both cases, including `all_assessments_admissible`.

## Severity — stated honestly

**Not currently reachable through the shipped path.** `compare_assessments(analyst, adjudicator)` requires two, and `run_spine` only builds a record when an assessment pair and a comparison both exist. So this is a latent defect in a public function of `src/aegistrace/review/`, not a live misrouting.

It is still worth fixing, for two reasons. The function is public and documented as deterministic; a caller supplying a partial or malformed comparison gets a confident Tier A rather than a refusal or an escalation. And the vacuous `all_assessments_admissible` result is misleading in any surfaced report regardless of tier.

## Proposed fix (for review)

Filling cases the documented rules do not cover, rather than changing any rule they do:

- zero admissible assessments -> Tier D, consistent with the existing "there is no conclusion to confirm" rule;
- exactly one admissible assessment -> Tier C, because a single unconfirmed opinion needs expertise rather than a signature;
- `all_assessments_admissible` must not report `passed` for an empty assessment set.

The one-assessment rule is a **design choice**, not a derivation, and is flagged as such. The alternative — refusing to classify fewer than two assessments at all — is defensible and is the owner's call.

## Acceptance criteria

- [ ] zero assessments cannot reach Tier A
- [ ] one assessment cannot reach Tier A
- [ ] `all_assessments_admissible` does not pass vacuously on an empty set
- [ ] two agreeing assessments still reach Tier A (no regression)
- [ ] a failing machine check still cannot lower a tier
- [ ] gate green: full suite, ruff, mypy

### Comment — 2026-10-08T11:01:37Z

## State: `DONE`

Fixed in `e3227cf`.

### What was wrong

`classify_tier` could assign `tier_a_machine_check` — the least human scrutiny, justified only by two roles having already agreed — to a subject with **zero or one** assessment. In the one-assessment case it recorded the reason *"assessors agreed without flags"* for a case with no second assessor.

Two vacuous preconditions:
- `classify_tier` read agreement as `disagreement_reasons` being empty, equally consistent with there being no assessors.
- `all_assessments_admissible` computed `len(admissible) == len(assessments)`, i.e. `0 == 0` → **True**, so a report could state *"0 of 0 assessments were admissible: passed"*.

The existing abstention guard requires `bool(admissible)`, so an empty set skipped the Tier D rule and fell through to the agreement branch.

### Fix

| Assessments | Tier before | Tier now |
|---|---|---|
| 0 | `tier_a_machine_check` ❌ | `tier_d_insufficient_evidence` ✅ |
| 1 | `tier_a_machine_check` ❌ | `tier_c_expert_judgment` ✅ |
| 2 agreeing | `tier_a_machine_check` | `tier_a_machine_check` (unchanged) ✅ |

`all_assessments_admissible` no longer passes vacuously; its detail now reads *"zero assessments were supplied, so admissibility cannot be confirmed"*.

No documented rule changed: branch order is untouched, the "a failing check can only raise a tier" property is intact, and two well-formed assessments still reach Tier A.

### Design choice flagged, not derived

One-assessment → Tier C is a **judgement call**, not a derivation, and is commented as such in the code citing this issue. Refusing to classify fewer than two assessments at all would also be defensible. Raising it here rather than deciding it silently.

### Honest severity

This was **latent, not live**. `compare_assessments` takes two and `run_spine` builds a record only when a pair and a comparison both exist, so the shipped path never produced it. It is a public function of the review layer that would return a confident Tier A to a caller supplying a partial comparison, and the vacuous check result was misleading wherever surfaced. Worth fixing; not worth calling a live misrouting.

### Verification

```
.venv/bin/python -m pytest -q            -> 238 passed, coverage 92.42%
.venv/bin/ruff check .                   -> All checks passed
.venv/bin/mypy                           -> Success, 48 source files
git diff --numstat tests/test_review.py  -> 56 insertions, 0 deletions
```

**Zero deletions in the test file** — no pre-existing test was modified or removed to make the fix pass.

---

## #14 — A single model answering as both assessor roles is accepted and reported as independent agreement

**State:** CLOSED  |  **Opened:** 2026-10-08T10:54:59Z  |  **Closed:** 2026-10-08T11:01:40Z

## State

`PROPOSED` — defect confirmed by direct execution. This undermines the project's central independence claim and should be treated as the higher-priority of the two defects found in this pass (see #13 for the other).

## Problem

The freeze artifact names this exact failure as its top concern:

> "The two assessors must not share model priors. **Two prompts over one model is not independence**; agreement between them would measure the prompt, not the evidence."

Nothing in the code enforces it. One provider wired to both roles is accepted, and the result is reported as perfect agreement:

```
=== both roles wired to the SAME provider ===
   ACCEPTED. aborted: False
   analyst descriptor == adjudicator descriptor: True
   comparison agreement: True | score: 1.0 | roles: ['triage_analyst', 'expert_adjudicator']
```

The run records that both descriptors are identical and then proceeds anyway, and the comparison displays two distinct role names even though one provider served both. A reader of that comparison record would conclude that two independent assessors agreed unanimously. They would be wrong: one model answered twice.

## Why this matters more than it looks

The project's claim is not "a model scored some findings". It is that **two mutually blind roles** produce assessments whose *disagreement* is the escalation signal. If a single model can serve both roles and score `agreement_score = 1.0`, then:

- `agreement` no longer measures independence; it measures prompt similarity;
- the escalation signal inverts — the least independent configuration produces the strongest apparent agreement;
- the failure is silent, which is the worst property for a guard whose job is to prevent false confidence.

`agreement_score` is the Jaccard overlap of cited evidence ids. Two runs of one model over one snapshot will cite the same evidence, so the score tends to 1.0 precisely when independence is absent. See also #11, where the pre-registered primary metric is `mean_per_bundle_agreement_score` — a run in this configuration would produce a maximally favourable primary metric for a maximally invalid reason.

## Reproduction

`run_independent_triage(bundles=[bundle], analyst_provider=p, adjudicator_provider=p, freeze=..., created_at=...)` where `p` is one `StubTriageProvider`. Accepted, `aborted=False`, `agreement=True`, `agreement_score=1.0`.

Directly, `compare_assessments` also accepts two assessments carrying the **same role**, and accepts the **same assessment object passed twice**, both yielding `agreement=True, agreement_score=1.0`.

## Proposed fix (for review)

1. **Refuse identical descriptors.** If `analyst_provider.descriptor == adjudicator_provider.descriptor`, raise. This is one assessor answering twice under two labels, and is wrong regardless of provider kind. It breaks nothing legitimate: the offline demo already uses two distinct descriptors (`stub-analyst-1` / `stub-adjudicator-1`).

2. **Record an independence determination on the run** rather than leaving it implicit: `independence_established: bool` plus a basis string. A run whose two descriptors share a `model_family` while being real (non-synthetic) providers has **not** established independence and must say so. Offline stub and recorded-replay providers are explicitly synthetic and non-intelligent, so they remain permitted, but the run must record that independence was not established.

3. **`compare_assessments` should refuse two assessments carrying the same role**, since a comparison between a role and itself is not a comparison.

## Design choices flagged, not derived

- Making identical descriptors a hard refusal rather than a recorded warning is a judgement call. Warning-and-recording would also be defensible.
- Whether a shared `model_family` with distinct `model_id`s should refuse outright, or only be recorded as non-independent, is the owner's call. The freeze artifact implies different families are required, so recording it as not-established is the conservative reading.

## Acceptance criteria

- [ ] one provider wired to both roles is refused, with a message naming the reason
- [ ] two assessments carrying the same role cannot produce `agreement=True`
- [ ] the same assessment object passed twice cannot produce `agreement=True`
- [ ] the offline demo and the spine still run (they use distinct descriptors)
- [ ] a run over two genuine but same-family providers records `independence_established: False` with a basis
- [ ] gate green: full suite, ruff, mypy

### Comment — 2026-10-08T11:01:39Z

## State: `DONE`

Fixed in `e3227cf`.

### What was wrong

The freeze artifact names this as its top concern — *"two prompts over one model is not independence; agreement between them would measure the prompt, not the evidence"* — and nothing in the code enforced it.

```
=== one provider wired to both roles ===
   ACCEPTED. aborted: False
   analyst descriptor == adjudicator descriptor: True
   comparison agreement: True | score: 1.0
   roles: ['triage_analyst', 'expert_adjudicator']
```

The run recorded that both descriptors were identical and proceeded anyway. `agreement_score` is the Jaccard overlap of cited evidence ids, so two passes of one model over one snapshot converge on the same citations and the score tends to **1.0 exactly when independence is absent**. The least independent configuration produced the strongest apparent agreement, silently.

This also bears on [#11](https://github.com/Lakshmi-Sindhu-P/AegisTrace/issues/11): the pre-registered primary metric is `mean_per_bundle_agreement_score`, so a run in this configuration would have produced a maximally favourable primary metric for a maximally invalid reason.

### Fix

- `run_independent_triage` **refuses identical descriptors**, after both governance refusals and before any budget or snapshot work.
- `TriageRun` gains `independence_established` and `independence_basis`, so the claim is recorded rather than left implicit. Offline stub and recorded-replay providers remain permitted but can never establish independence.
- `compare_assessments` refuses two assessments carrying the same role, and refuses the same identifier twice.

Exact refusal message:

```
ValueError: analyst and adjudicator providers share the descriptor 'same' (model 'stub-1');
one assessor answering twice under two labels is not independence, so the run is refused
```

### The honest framing is preserved

Rather than overclaiming, the basis for a genuine pairing reads:

> distinct remote descriptors with distinct model families ('famA' vs 'famB'); independence **rests on the descriptors' own declaration and is not proof of the transport**.

### Verification

```
.venv/bin/python -m pytest -q          -> 246 passed, coverage 92.48%
.venv/bin/ruff check .                 -> All checks passed
.venv/bin/mypy                         -> Success, 48 source files
run_offline_spine_demo.py              -> exit 0, records independence False
```

`_independence_determination` matrix, run directly:

| Pairing | Independence |
|---|---|
| remote, shared family | `False` ✅ |
| remote, distinct families | `True` ✅ |
| offline stub pair | `False` ✅ |
| remote + offline mix | `False` ✅ |

Governance ordering confirmed: an identical remote pair under the committed `BLOCKED_HUMAN` freeze raises `PermissionError` from the egress gate, **not** the new `ValueError` — so the egress boundary still takes precedence.

```
git diff --cached | grep "^-.*def test_"   -> no test function removed
```

The 44 deleted lines are helper signatures and same-provider call sites. `test_both_roles_receive_the_identical_snapshot` still asserts two requests, one digest, one snapshot, and both roles — now across two distinct providers. No assertion was weakened.

### Design choices flagged, not derived

1. Making identical descriptors a **hard refusal** rather than a recorded warning is a judgement call. Warning-and-recording would also be defensible.
2. A shared `model_family` with distinct `model_id`s is **recorded as non-independent rather than refused**. The freeze artifact implies different families are required, so refusing outright would also be defensible. Please say if you want that hardened.

### Note

Because the committed freeze is `BLOCKED_HUMAN`, the remote pairing branches cannot be reached end-to-end — the egress gate refuses first. The four matrix cases above were therefore verified by exercising `_independence_determination` directly rather than through a full run. Stated plainly rather than implied as end-to-end coverage.

---

## #15 — verify_claim lets a model score carry OBSERVED_FACT and DETERMINISTIC_DERIVATION

**State:** CLOSED  |  **Opened:** 2026-10-08T11:03:06Z  |  **Closed:** 2026-10-08T11:13:52Z

## State

`PROPOSED` — defect confirmed by direct execution.

## Problem

`verify_claim` enforces typed evidence requirements for `MODEL_INFERENCE` and `REFERENCE_BACKED_FACT`, but defines **no rule at all** for `OBSERVED_FACT`, `DETERMINISTIC_DERIVATION`, or `AI_INTERPRETATION`. Those three only require that *some* evidence be cited, so any evidence kind satisfies them.

The result is that the **weakest** evidence in the project's own hierarchy can carry the **strongest** claim category:

| Claim type | Cited evidence | Verified | Effective type |
|---|---|---|---|
| `OBSERVED_FACT` | `model_score` | **True** | `observed_fact` |
| `DETERMINISTIC_DERIVATION` | `model_score` | **True** | `deterministic_derivation` |
| `AI_INTERPRETATION` | `model_score` | True | `ai_interpretation` |
| `MODEL_INFERENCE` | `model_score` | True | `model_inference` |
| `REFERENCE_BACKED_FACT` | `model_score` | False | `unknown_insufficient_evidence` |

The last row shows the enforcement works where a rule exists. The problem is where no rule exists.

## Why this matters

The project states an evidence hierarchy: **raw source > normalized events > detector outputs and features > findings > LLM proposals > human review.** The taxonomy in `ClaimType` exists to keep statements pinned to the tier that can actually carry them.

`OBSERVED_FACT` backed only by a `model_score` inverts that hierarchy outright. A statement like *"this host was observed contacting the C2"* would be recorded as a **verified observed fact** on the strength of a probabilistic score — precisely the substitution the project is built to prevent, and the one a reader is least equipped to notice, because the claim carries the word "observed" and the verification says `verified: True`.

`DETERMINISTIC_DERIVATION` backed only by a `model_score` is a direct internal contradiction: nothing about a model score is deterministic.

`AI_INTERPRETATION` accepting a model score is **correct** and should not change.

## Reachability, stated honestly

**Latent, not live.** `Claim` is currently constructed only in `src/aegistrace/schemas/findings.py` and `tests/test_findings.py`; there is no production claim-generation path yet. `verify_claim` is the documented guard for the taxonomy, and it is the component that will be relied on when such a path is added. The gap is in the guard itself.

## Proposed fix (for review)

Define rules for the currently unguarded categories, in the same shape and with the same downgrade-to-`UNKNOWN_INSUFFICIENT_EVIDENCE` behaviour as the existing ones:

- **`OBSERVED_FACT`** must cite at least one `event` reference. "Observed" should mean observed in the source data, not inferred from a score.
- **`DETERMINISTIC_DERIVATION`** must cite at least one `event` or `detection` reference, so it cannot rest on a `model_score` alone.
- **`AI_INTERPRETATION`** and **`MODEL_INFERENCE`** unchanged.

All three should remain able to cite *additional* evidence of any kind; the rules are minimums, not exclusions.

## Design choices flagged, not derived

1. Requiring `event` specifically for `OBSERVED_FACT` (rather than accepting `detection` as well) is a **judgement call** about what "observed" means. A `DetectionResult` is the output of applying a threshold to a score, which is reproducible but is not a raw observation.
2. Whether `DETERMINISTIC_DERIVATION` should accept `detection` at all is arguable, since a detection derived from an ML score is only as deterministic as the score is reproducible.
3. An alternative is to make the taxonomy *exclusive* rather than minimum-based. That is a larger change and is not proposed here.

## Acceptance criteria

- [ ] `OBSERVED_FACT` citing only a `model_score` is unverified and downgraded
- [ ] `DETERMINISTIC_DERIVATION` citing only a `model_score` is unverified and downgraded
- [ ] `AI_INTERPRETATION` citing only a `model_score` is still verified (no regression)
- [ ] `MODEL_INFERENCE` and `REFERENCE_BACKED_FACT` behaviour unchanged
- [ ] an explicit `UNKNOWN_INSUFFICIENT_EVIDENCE` claim is still verified
- [ ] a claim citing `event` still reaches `OBSERVED_FACT` (no regression)
- [ ] gate green: full suite, ruff, mypy

### Comment — 2026-10-08T11:13:52Z

## State: `DONE`

Fixed in `5dac7c3`.

| Claim type | Cited | Before | After |
|---|---|---|---|
| `OBSERVED_FACT` | `model_score` | verified ❌ | **unverified, downgraded** ✅ |
| `DETERMINISTIC_DERIVATION` | `model_score` | verified ❌ | **unverified, downgraded** ✅ |
| `AI_INTERPRETATION` | `model_score` | verified | verified (unchanged, correct) ✅ |
| `MODEL_INFERENCE` | `model_score` | verified | verified (unchanged) ✅ |
| `REFERENCE_BACKED_FACT` | `model_score` | unverified | unverified (unchanged) ✅ |

New minimums: `OBSERVED_FACT` requires at least one `event` reference; `DETERMINISTIC_DERIVATION` requires at least one `event` or `detection`. Both are **minimums, not exclusions** — a claim citing additional evidence of any kind still passes.

Verified directly across **14 cases**, including three the implementer did not test:
- `OBSERVED_FACT` + `detection` alone → rejected (a detection is not a raw observation)
- `MODEL_INFERENCE` + `event` alone → rejected (needs a model-score reference)
- `OBSERVED_FACT` + no references → rejected

```
ruff              -> All checks passed
mypy              -> Success, 48 source files
pytest -q         -> 247 passed, coverage 92.50%
test_findings.py  -> 65 insertions, 0 deletions
```

Severity: **latent**. `Claim` is only constructed in the schema module and tests, so no production path produced this. The gap was in the guard the taxonomy depends on once such a path exists.

---

## #16 — Two repo validators report a clean pass on empty input

**State:** CLOSED  |  **Opened:** 2026-10-08T11:04:20Z  |  **Closed:** 2026-10-08T11:13:55Z

## State

`PROPOSED` — confirmed by direct execution. Lower severity than the other defects in this class (#13, #14, #15); recorded because it is the same failure mode in the project's own gates.

## Problem

Two of the repository's own validators report a clean pass on **empty input**:

```
$ .venv/bin/python scripts/validate_results_ledger.py /tmp/vac/ledger_empty.json
{"by_status": {}, "by_type": {}, "claim_count": 0, ...}          exit=0

$ .venv/bin/python scripts/validate_solution_knowledge.py /tmp/vac/solutions_empty.json
{"path": "...", "solution_count": 0}                             exit=0
```

A results ledger containing **zero claims** validates cleanly, and a solution store containing **zero lessons** validates cleanly. Both print a happy summary and exit 0.

This is the vacuous-precondition pattern: the checks verify the *shape* of each item and correctly reject a malformed one, but there is no floor, so an empty collection satisfies every constraint trivially. The contract "every claim is evidence-backed" is vacuously true when there are no claims.

## Why it matters, and how much

The useful comparison is the manifest validator, which gets this right:

```
$ .venv/bin/python scripts/verify_artifact_manifest.py /tmp/vac/manifest_empty.json
VIOLATION: registry artifact missing from manifest: data/evaluation/... (x9)
9 violation(s) found                                            exit=1
```

It fails closed because it cross-checks against the registry rather than only inspecting its own contents. The ledger and solution-store validators have no equivalent anchor.

**Severity: low to moderate.** It requires content to be deleted, and the content is version-controlled, so the diff would be visible in review. It is not a soundness bug in the verification logic. But the failure mode is the one a gate exists to prevent — a green signal for an artifact that has been emptied — and `docs/results.md` is linked from the README as the entry point for every claim the project makes. A silent emptying there would not be caught by CI.

## Proposed fix (for review)

Give both validators a non-empty floor, since neither store is legitimately empty in this project:

- `validate_results_ledger.py`: fail when the ledger contains zero claims.
- `validate_solution_knowledge.py`: fail when the store contains zero solutions.

A minimum count is deliberate rather than derived: this repository's invariant is that both stores are populated, so an empty one indicates corruption or an editing mistake rather than a valid state. If either store should ever legitimately be empty, this floor would need revisiting, and that is a judgement call.

Where feasible, prefer an anchor over a bare floor. `validate_experiment_registry.py` already fails closed on an empty `runs` list because the schema sets a minimum length, which is the cleanest version of this fix.

## Out of scope

`validate_preregistration.py` and `verify_artifact_manifest.py` were checked and fail closed correctly.

## Acceptance criteria

- [ ] `validate_results_ledger.py` exits non-zero on a ledger with zero claims
- [ ] `validate_solution_knowledge.py` exits non-zero on a store with zero solutions
- [ ] both still exit 0 on the real, populated artifacts (no regression)
- [ ] the failure message says the store is empty rather than reporting a per-item violation
- [ ] gate green: full suite, ruff, mypy

### Comment — 2026-10-08T11:13:54Z

## State: `DONE`

Fixed in `810528d`.

```
empty ledger    -> exit 1, "ledger is empty: expected at least one claim"
empty solutions -> exit 1, "solution knowledge store is empty: expected at least one solution"
real ledger     -> exit 0, claim_count 12
real solutions  -> exit 0, solution_count 6
```

The floor is **deliberate rather than derived**: both stores are populated by construction here, so an empty one signals corruption or an editing mistake rather than a valid state. If either should ever legitimately be empty, this needs revisiting — that is a judgement call, recorded rather than assumed.

For contrast, two neighbouring gates already fail closed and were left alone: `verify_artifact_manifest.py` exits 1 on an empty manifest because it cross-checks the registry, and `validate_experiment_registry.py` exits 1 on empty runs because its schema sets a minimum length. **An anchor is preferable to a bare floor where one is available.**

```
ruff           -> All checks passed
mypy           -> Success, 48 source files
pytest -q      -> 251 passed, coverage 92.50%
git diff --stat-> 27 insertions, 0 deletions
```

Severity: **low to moderate**. Requires content to be deleted, and the content is version-controlled so the diff would be visible. Not a soundness bug in the verification logic — but the failure mode is the one a gate exists to prevent, and `docs/results.md` is linked from the README as the entry point for every claim the project makes.

---

## #17 — Two sibling machine checks still pass vacuously for zero assessments (incomplete fix of #13)

**State:** CLOSED  |  **Opened:** 2026-10-08T11:07:13Z  |  **Closed:** 2026-10-08T11:10:17Z

## State

`PROPOSED` — confirmed by direct execution. This is an **incomplete fix of my own**: [#13](https://github.com/Lakshmi-Sindhu-P/AegisTrace/issues/13) fixed one of three vacuously-passing checks in the same function.

## Problem

`machine_checks` builds four checks. Issue #13 corrected `all_assessments_admissible`, which computed `len(admissible) == len(assessments)` and so returned `True` for `0 == 0`. Two sibling checks in the same tuple have the identical defect and were missed:

```
$ machine_checks(bundle, ())     # zero assessments
  all_assessments_admissible            passed=False   <- fixed by #13
  citations_resolve_to_bundle_evidence  passed=True    <- vacuous
  assessors_saw_identical_input         passed=True    <- vacuous
  bundle_states_its_own_gaps            passed=True
```

- **`citations_resolve_to_bundle_evidence`** computes `passed=not unresolved`, where `unresolved` is collected only from *admissible* assessments. With no admissible assessments the set is empty, so the check reports *"every cited identifier resolves to evidence in the bundle"* — having inspected no citations at all.
- **`assessors_saw_identical_input`** computes `len({digests}) <= 1`, which is `0 <= 1` for an empty set, so it asserts that all admissible assessments share one snapshot digest when there are none.

I observed both reporting `passed=True` while investigating #13 and fixed only the first. Recording that plainly: the same probe that found the defect also showed these two, and I did not act on them.

## Why the existing test missed it

`tests/test_review.py:276` asserts `any(not passed)` over the checks. That is satisfied by a single failing check, so it cannot detect additional checks passing vacuously. The assertion is weaker than the property it appears to guard.

## Reachability and severity

**Low, and latent.** The shipped tier outcome is unaffected: zero assessments now route to Tier D before the checks matter, so the misreport did not change a decision. The concern is the `MachineCheck` records themselves — they are part of `TierAssignment` and are surfaced to a reviewer as evidence-mechanics results. A record reading *"every cited identifier resolves to evidence in the bundle: passed"* for a case with no citations is a false statement in an audit artifact, which is the same objection as the `all_assessments_admissible` detail in #13.

## Proposed fix (for review)

- `citations_resolve_to_bundle_evidence` must not pass when there are no admissible assessments; its detail should say that no citations were available to resolve.
- `assessors_saw_identical_input` must not pass on an empty set; its detail should say no admissible assessments were compared.
- Strengthen the test so it asserts the **specific expected pass/fail value per check** for the empty-assessment case, rather than `any(not passed)`, so a future check cannot be added vacuously.

The wider lesson, worth recording: fixing one instance of a repeated defect pattern in a function is not fixing the pattern. All four checks should have been reviewed when the first was found.

## Acceptance criteria

- [ ] no machine check reports `passed=True` for zero admissible assessments
- [ ] the empty-assessment test asserts each check's expected value individually
- [ ] a well-formed two-assessment case still passes all four checks (no regression)
- [ ] the #13 tier outcomes are unchanged: 0 -> D, 1 -> C, 2 agreeing -> A
- [ ] gate green: full suite, ruff, mypy

### Comment — 2026-10-08T11:10:16Z

## State: `DONE`

Fixed in `6ccc152`.

`machine_checks(bundle, ())` now returns:

| Check | Before | After |
|---|---|---|
| `all_assessments_admissible` | False (fixed by #13) | False |
| `citations_resolve_to_bundle_evidence` | **True** ❌ | **False** ✅ |
| `assessors_saw_identical_input` | **True** ❌ | **False** ✅ |
| `bundle_states_its_own_gaps` | True | True |

No vacuous check remains. Tier outcomes unchanged: 0 → D, 1 → C, 2 agreeing → A. A two-assessment case still passes all four checks.

The test now asserts an **exact name-to-passed map over all four checks** instead of `any(not passed)`, so a future check cannot be added vacuously unnoticed. Test count 17 → 18; no test deleted.

```
ruff           -> All checks passed
mypy           -> Success, 48 source files
pytest -q      -> 255 passed, coverage 92.77%
```

### The lesson, recorded

I found the original defect in #13 by printing all four checks — the output that revealed `all_assessments_admissible` also showed these two as `True`, and I acted on only one. **Fixing one instance of a repeated defect pattern is not fixing the pattern.** The right move was to review all four checks the moment the first proved vacuous.

---

## #18 — Leakage audits return passed=True for an empty baseline

**State:** CLOSED  |  **Opened:** 2026-10-08T11:07:14Z  |  **Closed:** 2026-10-08T11:10:20Z

## State

`PROPOSED` — confirmed by direct execution. Highest-consequence finding of the vacuous-precondition audit, because these functions gate a leakage claim.

## Problem

Two leakage audits return `True` when given an empty baseline, so they report a **passed leakage audit having examined nothing**:

```
src/aegistrace/features/behavioral.py:228   audit_prior_window_causality
    if not baseline.records:
        return True

src/aegistrace/features/causal.py:300       audit_causal_prior_window
    if not baseline.records:
        return True
```

`run_phase3_hardening.py:245` records the first as `temporal_audit.passed` and emits it into the Phase 3 hardening report. A boolean that means "no temporal leakage was found" is returned for input containing no records to leak from.

This is the failure mode that matters most in this project's own terms. The Phase 3 feature work is the evidence base for the detector chapter, and its leakage controls are what make the reported metrics credible. A leakage audit that returns `True` on empty input is a check that cannot fail for the reason it exists.

## Reachability, stated honestly

**Latent for the Phase 3 report.** The current call site runs on a non-empty fixture, so the published hardening result was not produced by an empty audit. This is a guard that fails open, not a past result that is wrong — and I want to be precise about that rather than imply the Phase 3 numbers are affected. They are not, on present evidence.

The defect still needs fixing because these are the functions a future caller relies on, and the failure is silent: nothing distinguishes "audited, clean" from "audited nothing".

## Proposed fix (for review)

Do **not** simply change `return True` to `return False`, because that would report a *failed* leakage audit for a case that is merely unmeasurable — a different false statement. The honest outcomes are:

1. Return `False` (audit not passed) with a reason recording that the baseline was empty, so the caller's boolean is conservative; **or**
2. Change the return type to a small result carrying `passed` plus a reason, so "not audited" is distinguishable from "audited and clean".

Option 2 is more correct and more invasive. Option 1 is minimal and safe. I would take option 1 now and raise option 2 as a design question, but this is the owner's call since it touches how a validation result is represented.

Whichever is chosen, the reason string must say the baseline was empty rather than implying a clean audit.

## Acceptance criteria

- [ ] an empty baseline cannot yield `passed=True` from either audit
- [ ] the reason records that the baseline was empty
- [ ] a genuinely clean non-empty baseline still passes (no regression)
- [ ] `run_phase3_hardening.py` behaviour on its real fixture is unchanged, and the Phase 3 evidence validator still passes
- [ ] gate green: full suite, ruff, mypy

### Comment — 2026-10-08T11:10:19Z

## State: `DONE`

Fixed in `313ce69`.

Both audits now return `False` for an empty baseline, keeping the bare `bool` return type:

```
behavioral  empty baseline -> False   (was True)
causal      empty baseline -> False   (was True)
```

Each carries a comment recording that **empty means unmeasurable, not "no leakage found"** — changing `True` to `False` bare would have been wrong in the other direction.

### No published result is affected

The call site uses a non-empty fixture (`scenario_11`, 4 events) where `temporal_audit` still evaluates `True`. `run_phase3_hardening.py` needed no change and was not edited. **No Phase 3 result is retracted**, and no doc, dataset, or evaluation artifact was modified or regenerated.

```
ruff                    -> All checks passed
mypy                    -> Success, 48 source files
pytest -q               -> 255 passed, coverage 92.77%
validate_phase3_evidence -> 9/9 artifacts, 0 missing, scenario_7 sealed
```

### Design question for you

A bare boolean cannot distinguish **"audited and clean"** from **"audited nothing"**. Option 1 (chosen) is conservative and minimal. Option 2 — returning a small result carrying a reason, so the two states are distinguishable in the artifact — is more correct but changes how a validation result is represented. I did not make that call unilaterally. Say the word and I'll do it.

---

## #19 — Three further guards accept degenerate input and report success

**State:** CLOSED  |  **Opened:** 2026-10-08T11:07:46Z  |  **Closed:** 2026-10-08T11:13:44Z

## State

`PROPOSED` — confirmed by direct execution. Low severity; recorded so the class is closed rather than left half-fixed, which is the mistake made in [#17](https://github.com/Lakshmi-Sindhu-P/AegisTrace/issues/17).

## Problem

Three further guards accept degenerate input and report success. All were confirmed by execution during the vacuous-precondition audit.

### 1. `scripts/validate_agent_trace.py` — an empty trace file validates

A JSONL file with zero non-blank lines leaves `errors` empty, prints `{"valid_records": 0}` and exits 0. A missing or emptied trace is therefore indistinguishable from a valid one at the gate.

```
$ .venv/bin/python scripts/validate_agent_trace.py /tmp/empty.jsonl
{"path": "/tmp/empty.jsonl", "valid_records": 0}          exit=0
```

Given that this project's governance treats the trace log as the durable record of meaningful actions, a gate that passes on an empty log is worth closing. The summary does report `0`, so the information is present — the exit code is what fails to act on it.

### 2. `scripts/verify_artifact_manifest.py` — vacuous when both sides are empty

With `manifest.artifacts == []` **and** a registry whose runs carry no `artifact_refs`, both set-difference loops append nothing, so `violations == []` and the script exits 0 with `verified_on_disk: 0`.

This is narrow: the real registry does carry `artifact_refs`, so against the committed artifacts the script correctly exits 1 with 9 violations (verified). The vacuity needs the degenerate combination of *both* sides empty. The script reads raw JSON and applies no `runs` minimum to the registry it is handed.

### 3. `src/aegistrace/schemas/manifests.py` — label counts absent while records exist

`require_non_negative_label_counts` iterates `value.values()`, so `{}` yields `any(...) == False` and passes; and `validate_time_range_and_counts` computes `sum({}) == 0 <= record_count`, which holds for any `record_count`. A manifest declaring `record_count > 0` with **no** `label_distribution` therefore passes. *Suspected rather than fully isolated — see the audit note below.*

## Severity

**All three are low.** Each needs a degenerate input, and in cases 2 and 3 the committed artifacts are unaffected. They are recorded because the repo's own gates are its credibility, and because the audit that found them is only worth running if its confirmed findings get acted on.

## Proposed fix (for review)

- `validate_agent_trace.py`: exit non-zero when the file yields zero valid records, with a message saying no records were found. An empty trace log is not a valid trace log.
- `verify_artifact_manifest.py`: when the manifest has zero entries, fail rather than reporting zero violations — consistent with the floor added to the other two validators in [#16](https://github.com/Lakshmi-Sindhu-P/AegisTrace/issues/16). Keep the existing cross-check behaviour unchanged otherwise.
- `manifests.py`: decide whether a manifest with `record_count > 0` and an empty `label_distribution` is legal. If it is not, reject it. **This one needs a decision, not just a fix** — an unlabeled dataset manifest may be legitimately unlabelled, in which case the current behaviour is correct and should be documented rather than changed.

## Acceptance criteria

- [ ] an empty trace file makes `validate_agent_trace.py` exit non-zero
- [ ] the real traces under `.context/traces/` still validate (no regression)
- [ ] a zero-entry manifest makes `verify_artifact_manifest.py` exit non-zero
- [ ] the committed manifest still verifies 9 entries (no regression)
- [ ] `manifests.py` either rejects an empty `label_distribution` when `record_count > 0`, or documents why it is permitted — with the decision stated in the issue
- [ ] gate green: full suite, ruff, mypy

## Audit note

Item 3 is marked **suspected** in the source audit rather than confirmed, because the auditor could not isolate it from other manifest field errors. The implementer should confirm it by execution before changing anything, and should report if it does not reproduce.

### Comment — 2026-10-08T11:13:43Z

## State: `DONE`

Fixed in `f096fef`.

| Degenerate input | Before | After |
|---|---|---|
| empty trace file | exit 0, `valid_records: 0` ❌ | **exit 1**, "no records found" ✅ |
| blank-only trace file | exit 0 ❌ | **exit 1** ✅ |
| zero-entry manifest | exit 0, `violations: []` ❌ | **exit 1** ✅ |
| `record_count>0` + empty `label_distribution` | accepted ❌ | **rejected** ✅ |

### Item 3 was SUSPECTED and did reproduce

I asked the implementer to confirm it by execution before changing anything, rather than fixing a defect that might not exist. It reproduced:

```
record_count=1, labels={}          -> REJECTED "must not be empty when record_count > 0"
record_count=0, labels={}          -> accepted  (unlabelled manifest still legal)
record_count=5, labels={benign:5}  -> accepted
record_count=1, labels={x:5}       -> REJECTED "cannot exceed record_count"
```

The fix is deliberately narrow — rejection applies only when `record_count > 0` — so a **legitimately unlabelled dataset manifest is still accepted**. A bare non-empty floor would have been wrong here, which is why this needed a decision rather than just a fix.

### Preserved behaviour

`verify_artifact_manifest.py` deliberately **counts** absent artifacts rather than failing on them, because the evaluation artifacts are gitignored and not committed. That is unchanged; only the zero-entry floor was added.

### Verification

```
ruff               -> All checks passed
mypy               -> Success, 48 source files
pytest -q          -> 261 passed, coverage 92.78%
all 18 real traces -> exit 0, 18 valid, 0 invalid
real manifest      -> exit 0, 9 entries, 0 violations
```

No existing test modified or deleted (`git diff --stat -- tests/` = 42 insertions, 0 deletions).

---

## #20 — spine_id is not stable: it changes with bundle ordering and when an unrelated bundle is added

**State:** CLOSED  |  **Opened:** 2026-10-08T11:19:35Z  |  **Closed:** 2026-10-08T11:23:28Z

## State

`PROPOSED` — confirmed by direct execution.

## Problem

`spine_id` is not a stable identifier. It changes when the same bundles are listed in a different order, **and** when an unrelated bundle is added to the run.

```
=== same two bundles, reversed order ===
  forward run_id: adba48c7-a6a5-57a7-ac90-6413ead4e62b
  reverse run_id: 348340d7-c481-5c2d-a56f-7d7982f7daad
  run_id equal  : False
  ALL spine_ids stable: False

=== adding an unrelated bundle C to [A, B] ===
  bundle A: stable when C is added = False
  bundle B: stable when C is added = False
  A with [A,B]   -> b62cc530-bb46-5f10-843a-58d835970219
  A with [A,B,C] -> 0745530c-d0f9-5dde-bf38-a353e7e41514
```

A's own content is byte-identical in both runs. Only the composition of the batch it travelled in differs.

## Cause

Two independent contributions, both in the identity chain:

1. **`triage_run_id_for` does not sort its inputs.** It serializes `list(snapshot_digests)` in the order received (`src/aegistrace/triage/run.py:237`), so the run identity depends on bundle ordering.

2. **`spine_id` is derived from the enclosing run.** `spine_id_for(evidence_bundle_id, run_id, snapshot_digest)` includes `run_id`, which is a *batch-scoped* value. So a record's identity depends on every other record that happened to be in the same run.

Fixing only (1) corrects the reordering case but **not** the add-a-bundle case, because adding C changes the set of snapshot digests and therefore the run id.

## Why this is a defect rather than a design choice

This repository applies an explicit convention that identity derives from an entity's own content and is independent of ordering. It is stated in the code and applied without exception elsewhere:

| Function | Sorts before hashing | Documented |
|---|---|---|
| `finding_id_for` | yes | *"does not depend on detection or input ordering"* |
| `evidence_bundle_id_for` | yes | — |
| `comparison_id_for` | yes | *"does not depend on which side was passed first"* |
| `corpus._corpus_digest` | yes | canonical JSON |
| `triage_run_id_for` | **no** | *"from the freeze, the descriptors, the inputs, and the timestamp"* |

`triage_run_id_for` is the only identity function that does not sort. Its docstring says "the inputs", which reads as set semantics, not sequence semantics.

## Consequence

A `SpineRecord` is the spine's durable identifier for *(bundle, comparison, tier, review history)*. If the identifier changes when an unrelated bundle joins the batch, then:

- two runs over overlapping bundles cannot be compared record-by-record;
- regenerating a batch with one more case silently re-identifies every prior record;
- the project's reproducibility story — artifact manifest, canonical digests, per-capture reporting — rests on identifiers that are stable for a given input, and these are not.

Reachability: **live** in the sense that `run_spine` is exercised and computes these ids on every call. Not yet consequential in any published artifact, because no provider run exists (the freeze is `BLOCKED_HUMAN`) and `data/` is gitignored. Nothing committed references a `spine_id` or `run_id` — verified by searching `docs/` and `configs/`.

## Proposed fix (for review)

**Part 1 — unambiguous.** Sort `snapshot_digests` inside `triage_run_id_for`, matching every sibling function. This also needs a test that the same bundle set in any order yields one run id.

**Part 2 — a design change, flagged.** `spine_id` should derive from the record's own content rather than the enclosing run:

```
spine_id_for(evidence_bundle_id, snapshot_digest, comparison_id)
```

replacing `run_id` with the per-bundle `comparison_id`, which is already derived deterministically from the bundle and its assessment ids. This makes a record's identity independent of batch composition, which is the property the other identity functions already have. The run id remains on `SpineRecord` as context, describing which batch the record was produced in.

Part 2 changes the signature of a public function, so it is raised for decision rather than assumed. Part 1 does not and should be done regardless. **I recommend doing both**, because Part 1 alone leaves the larger problem — that adding a case re-identifies every prior record — in place.

## Acceptance criteria

- [ ] the same bundle set in any order yields one `run_id`
- [ ] adding an unrelated bundle does not change an existing record's `spine_id`
- [ ] `spine_id` still differs for genuinely different bundles
- [ ] `run_id` remains recorded on `SpineRecord` as batch context
- [ ] the offline spine demo still runs, and the spine tests pass
- [ ] gate green: full suite, ruff, mypy

### Comment — 2026-10-08T11:23:27Z

## State: `DONE`

Fixed in `e24ee74`.

| Property | Before | After |
|---|---|---|
| Same bundles, reversed order | different `spine_id` ❌ | identical ✅ |
| Unrelated bundle added | every existing `spine_id` changed ❌ | unchanged ✅ |
| Different bundles | distinct ✅ | distinct ✅ |
| `run_id` for the same bundle set | order-dependent ❌ | stable ✅ |

Bundle A's identity, observed directly:

```
[A,B]   -> 13c161ea-dfc6-57be-b084-97aafc547ea7
[B,A]   -> 13c161ea-dfc6-57be-b084-97aafc547ea7
[A,B,C] -> 13c161ea-dfc6-57be-b084-97aafc547ea7
[C,B,A] -> 13c161ea-dfc6-57be-b084-97aafc547ea7
```

### Both parts done

1. `triage_run_id_for` now hashes `sorted(snapshot_digests)`.
2. `spine_id_for` now derives from the record's **own** content — `evidence_bundle_id`, `snapshot_digest`, `comparison_id` — instead of the batch-scoped `run_id`. `run_id` remains on `SpineRecord` as batch context.

Part 2 was implemented as recommended rather than deferred, because Part 1 alone would have left the larger problem — adding a case re-identifying every prior record — in place.

### How this was found

Not by looking for something missing, but by **testing a property the repo already states**. Every other identity function sorts and documents order-independence; `triage_run_id_for` was the lone exception. The inconsistency was the tell.

### Blast radius

None. Nothing committed referenced a `spine_id` or `run_id` (searched `docs/` and `configs/`), the provider run is `BLOCKED_HUMAN`, and `data/` is gitignored — so no artifact was invalidated by changing the derivation.

### Verification

```
ruff            -> All checks passed
mypy            -> Success, 48 source files
pytest -q       -> 265 passed, coverage 92.78%
pytest under PYTHONHASHSEED=0, 7, 999 -> 265 passed each time
offline demo    -> exit 0
```

No existing test deleted or modified. The four new tests assert the three stability properties above plus that `run_id` is still recorded.

---

## #21 — Timing values in three evaluation artifacts make their recorded manifest digests irreproducible

**State:** CLOSED  |  **Opened:** 2026-10-08T11:27:28Z  |  **Closed:** 2026-10-08T11:49:24Z

## State

`PROPOSED` — confirmed by direct execution and by inspecting the artifacts on disk.

## Problem

Three of the nine registered evaluation artifacts embed a **wall-clock timing measurement** in their serialized bytes. Their content therefore differs between two identical runs, so the sha256 recorded for them in `docs/artifact_manifest.json` can **never** be reproduced.

```
$ grep -n "fit_runtime_seconds" scripts/run_phase3_*.py
scripts/run_phase3_model_stability.py:223            "fit_runtime_seconds": runtime["fit_seconds"],
scripts/run_phase3_model_stability_cached.py:262     "fit_runtime_seconds": runtime["fit_seconds"],
scripts/run_phase3_causal_representation.py:220      "fit_runtime_seconds": runtime["fit_seconds"],
scripts/run_phase3_model_family_benchmark.py:227     "fit_runtime_seconds": runtime["fit_seconds"],
```

`fit_seconds` originates from `time.perf_counter()` (`src/aegistrace/evaluation/model_family.py:170-175`, `271-283`).

Confirmed present in the artifacts on disk, by streaming search:

```
data/evaluation/phase3_model_stability/stability_summary.json       found=True  (138,967,260 bytes scanned)
data/evaluation/phase3_causal_representation/causal_summary.json    found=True  ( 64,751,590 bytes scanned)
```

The manifest entries affected, including the two largest artifacts in the repository:

| Artifact | Size |
|---|---|
| `phase3_model_stability/stability_summary.json` | 138,967,260 B |
| `phase3_causal_representation/causal_summary.json` | 64,751,590 B |
| `phase3_model_family/benchmark_summary.json` | 1,825,712 B |

## Why this is a defect and not a nitpick

The manifest states its own purpose, and the README repeats it:

> "digest, size, and shape of each registered evaluation artifact, so a regenerating party can confirm they produced the same bytes."

For these three entries that confirmation is **impossible**, not merely difficult. A third party can regenerate the artifact correctly, in full, on matching hardware with a matching seed, and still get a different digest, because a timing measurement depends on machine load. `scripts/verify_artifact_manifest.py` will then report a violation against a correct regeneration.

So this is a **false reproducibility claim in a committed artifact**, in a project whose credibility rests on evidence-grounded claims. It is the same class of problem the results ledger exists to prevent: a statement the project makes that its own evidence cannot support.

Note the contrast with `#20`: there the identity was order-dependent but would have matched for a canonical order. Here the value is **irreproducible in principle**, not just under reordering.

## Reachability

**Live.** The artifacts exist on disk and the manifest records their digests. The provider blocker is unrelated — this is the Phase 3 evaluation chapter, which is `CURRENT / IMPLEMENTED`.

## Proposed fix (for review)

1. **Stop writing runtime into the artifact.** Timing is operational metadata, not research evidence. Record it in a sidecar (the experiment registry's `configuration`, or a separate non-content-addressed log) rather than in the digest-covered bytes. This makes the artifacts genuinely byte-reproducible.
2. **State the limitation plainly for the existing artifacts.** Their current digests were produced with timing embedded and cannot be reproduced. Do not silently leave the manifest implying otherwise. Options: mark those entries in the manifest as `reproducible: false` with a reason, or add the caveat to `docs/limitations.md` where the raw-bytes digest caveat already lives.
3. **Do not regenerate the large artifacts in this change** unless the owner asks. `stability_summary.json` is 139 MB, `causal_summary.json` is 65 MB, and a related capture already exceeds the 16 GB RAM ceiling. Regeneration is a costed decision.

## Design question for you

Whether the manifest should carry a per-entry reproducibility flag, or whether the caveat belongs only in `docs/limitations.md`, is a judgement call I am not making unilaterally. The flag is more honest at the point of use; the doc note is less invasive. I recommend the flag.

## Acceptance criteria

- [ ] no serialized evaluation artifact contains a wall-clock timing value
- [ ] the manifest no longer implies those three digests can be reproduced as recorded
- [ ] the limitation is stated where a reader encounters the digest
- [ ] `verify_artifact_manifest.py` still passes on the committed manifest
- [ ] gate green: full suite, ruff, mypy

### Comment — 2026-10-08T11:49:23Z

## State: `DONE` — fixed in `b3caccf`

Three registered artifacts embedded a `perf_counter` timing value in their serialized bytes, so their recorded sha256 could never be reproduced.

| Artifact | Size | Flag now |
|---|---|---|
| `phase3_model_stability/stability_summary.json` | 138,967,260 B | `false` |
| `phase3_causal_representation/causal_summary.json` | 64,751,590 B | `false` |
| `phase3_model_family/benchmark_summary.json` | 1,825,712 B | `false` |

**Confirmed present on disk** by streaming search, not inferred from the scripts.

`fit_seconds` is dropped from the serialized payload in all four producers and preserved for the operator as a stderr line. Verified it feeds no metric, threshold, or selection logic. All nine entries now carry `reproducible` plus a note, required by the verifier.

**Not done, deliberately:** no artifact under `data/` was regenerated. 139 MB and 65 MB, and regeneration is a costed decision for you. `git status --short` shows zero changes under `data/`.

This surfaced a further defect, filed as #23.

---

## #22 — Feature builders emit records in raw input order, so artifacts differ for the same logical input

**State:** CLOSED  |  **Opened:** 2026-10-08T11:27:54Z  |  **Closed:** 2026-10-08T11:49:27Z

## State

`PROPOSED` — confirmed by direct execution.

## Problem

The feature builders return their `records` tuple in **raw input order** rather than a canonical order. Feature *values* are order-invariant — they are computed over `sorted(selected)` — but the records collection is then rebuilt over the **unsorted** `selected`, so the emitted sequence follows the caller's iteration order.

```
src/aegistrace/features/network.py:199-216    build_ctu13_features
src/aegistrace/features/behavioral.py:200-214  (sorts for values, rebuilds records unsorted)
src/aegistrace/features/causal.py:277-291      (sorts for values, rebuilds records unsorted)
```

Proof by execution: record-sequence digests differ across original / reversed / shuffled input while the per-`event_id` value digests are **identical**, and all of them are identical across `PYTHONHASHSEED=0/1/2/3`.

```
record-sequence digest:  original be8885d2bc90 | reversed edcd60534dd2 | shuffled 045440584db6
per-event_id values:     identical in all three, and across all four seeds
```

## Why it matters

This is not run-to-run nondeterminism for a fixed file: the source file order is stable, so a single-scenario run is reproducible. The problem appears when a caller **concatenates scenarios** or iterates an unordered container, which is exactly what a cross-scenario evaluation does. Two callers assembling the same logical set of flows in different orders then produce different parquet row order, different serialized bytes, and therefore **different content-addressed feature artifacts for the same logical input**.

That matters for the same reason as [#21](https://github.com/Lakshmi-Sindhu-P/AegisTrace/issues/21): the project asserts reproducibility of its artifacts, and a digest that depends on incidental iteration order weakens that claim. It is the milder version of the same defect — reproducible under a canonical order, but no canonical order is enforced.

## Relationship to the convention

The repository already applies the "identity is order-independent" convention in its identity functions (`finding_id_for`, `comparison_id_for`, `triage_run_id_for` after [#20](https://github.com/Lakshmi-Sindhu-P/AegisTrace/issues/20)), and these builders already compute values over a sorted selection. The records collection simply was not brought along with it.

## Proposed fix (for review)

Emit `records` in a canonical order — the same deterministic key already used for value computation, or `event_id` where that is the natural stable key. This should not change any feature value, only the emitted sequence; that is testable by comparing the per-`event_id` value map before and after.

**This changes artifact bytes**, so it interacts with [#21](https://github.com/Lakshmi-Sindhu-P/AegisTrace/issues/21) and should be settled in the same pass: fixing the ordering without first removing the timing value would still leave the digests irreproducible.

## Acceptance criteria

- [ ] the three builders emit records in a deterministic canonical order
- [ ] feature values per `event_id` are unchanged (compared before and after)
- [ ] a reversed and a shuffled input produce byte-identical serialized output
- [ ] the ordering remains stable across `PYTHONHASHSEED` values
- [ ] gate green: full suite, ruff, mypy

## Not proposed

Sorting the input *before* feature computation. The values are already order-invariant; changing the computation input risks altering results for no benefit. Only the emitted sequence needs canonicalising.

### Comment — 2026-10-08T11:49:26Z

## State: `DONE` — fixed in `30c4eff`

The three CTU-13 feature builders emitted records in raw input order. Values were already order-invariant, but the records collection was rebuilt over the unsorted selection.

Record-sequence digests before (original / reversed / shuffled):

```
network     d30e886f04a9 | e1d9f341d2ff | 1d759574c52e   all different
behavioral  a04ce53bad91 | d7613a68e308 | a332a6ce8247   all different
causal      1cc52e32a7f9 | f555832c1dcb | c08ce2454185   all different
```

After: one value each, stable across four `PYTHONHASHSEED` values. **Per-`event_id` value digests identical before and after**, so no feature value changed. Parquet bytes byte-identical across input orders.

Found by a systematic determinism audit that exercised 17 functions under four hash seeds plus reversed and shuffled inputs. The same audit **proved clean**: `aggregate_findings`, `build_evidence_bundle`, `emit_ml_detections`, and every identity function.

**Already-produced artifacts:** network-derived artifacts under `data/` would change bytes. Nothing was regenerated.

---

## #23 — Reproducibility flag is not transitive: uncertainty_summary.json claims true but consumes two false artifacts

**State:** CLOSED  |  **Opened:** 2026-10-08T11:34:46Z  |  **Closed:** 2026-10-08T11:49:30Z

## State

`PROPOSED` — confirmed by direct execution. This is a defect **in the fix for [#21](https://github.com/Lakshmi-Sindhu-P/AegisTrace/issues/21)**, not in the original code.

## Problem

`#21` added a per-entry `reproducible` flag to `docs/artifact_manifest.json`. The flag currently answers the question *"does this artifact contain a timing value?"* — but the question it needs to answer is *"can these exact bytes recur?"*, and that requires following the dependency chain.

One entry is therefore mislabelled:

```
=== uncertainty_summary.json recorded inputs ===
  input: phase3_model_stability/stability_summary.json
     recorded digest : 2c793f4280f43b8bb78a21b8...
     manifest digest : 2c793f4280f43b8bb78a21b8...   MATCH
     that input's reproducible flag: False
  input: phase3_causal_representation/causal_summary.json
     recorded digest : e4fe308dbf472b24d42565f6...   MATCH
     that input's reproducible flag: False
```

`phase3_uncertainty/uncertainty_summary.json` is marked `reproducible: true`. It records, **inside its own bytes**, the digests of the two artifacts it consumed — both of which are marked `reproducible: false` because they embed a `perf_counter` timing value.

Reproducing `uncertainty_summary.json` correctly therefore requires inputs whose digests can never recur. A correct regeneration records different `inputs[].digest` values, which are part of its bytes, so its own digest cannot recur either. The recorded digests matching the manifest confirms the recording is accurate; it is the **flag** that is wrong.

## Scope

Checked all six entries currently marked `true` for a reference to any entry marked `false`. Exactly one is affected:

```
data/evaluation/phase3_uncertainty/uncertainty_summary.json
   REFERENCES  phase3_causal_representation/causal_summary.json
   REFERENCES  phase3_model_stability/stability_summary.json
```

The other five reference no unreproducible artifact and are correctly marked.

## Why it matters

This is the same class of error as the one `#21` was filed to fix: a committed claim that the project's own evidence cannot support. `#21` removed the timing value from future artifacts and flagged the three files that carried one, but did not notice that reproducibility is **transitive**. A reader who trusts the flag would attempt to reproduce `uncertainty_summary.json` and, following the chain, conclude their correct output was wrong.

Worth recording plainly: the fix was locally correct and globally incomplete. The parallel fix for [#22](https://github.com/Lakshmi-Sindhu-P/AegisTrace/issues/22) has the same shape — it is correct for the network builder and leaves the question of which already-produced artifacts change bytes to be answered separately.

## Proposed fix (for review)

1. Make `reproducible` transitive: an artifact is reproducible only if it is not itself timing-affected **and** none of its recorded `inputs[].digest` entries points at an artifact that is not reproducible. Follow the chain; guard against cycles since the manifest is data.
2. Mark `phase3_uncertainty/uncertainty_summary.json` as `reproducible: false`, with a `reproducibility_note` naming the unreproducible inputs rather than the timing cause, so the reason is accurate for that entry.
3. Extend `verify_artifact_manifest.py` to check the property, so the flag cannot drift from the digests. It already has the manifest and can read the small artifacts' `inputs` arrays; for the large ones it should not need to load them.

## Design question for you

Whether the flag should be **derived** at verification time rather than stored is a judgement call. A derived flag cannot go stale, but the dependency information lives in the artifacts, which are not committed — so a stored flag with a checked invariant may be the pragmatic choice. I lean toward storing it and verifying it, which is what item 3 does.

## Acceptance criteria

- [ ] an artifact whose recorded inputs include a non-reproducible artifact is not marked reproducible
- [ ] `uncertainty_summary.json` is marked `false` with a note naming its inputs, not the timing cause
- [ ] the other five entries marked `true` are unchanged
- [ ] `verify_artifact_manifest.py` fails if the flag contradicts the recorded input digests
- [ ] the check does not require loading the large artifacts
- [ ] gate green: full suite, ruff, mypy

### Comment — 2026-10-08T11:49:29Z

## State: `DONE` — fixed in `b3caccf`

A defect **in the fix for #21**, found by checking whether the two parallel fixes were consistent.

`uncertainty_summary.json` was marked `reproducible: true` while recording inside its own bytes the digests of two artifacts marked `false`:

```
input: phase3_model_stability/stability_summary.json      digest MATCHES manifest, flag false
input: phase3_causal_representation/causal_summary.json   digest MATCHES manifest, flag false
```

Reproducing it correctly needs inputs whose digests can never recur, and its own bytes embed those digests. The recorded digests matching the manifest confirmed the recording was **accurate** and the **flag** was wrong.

The verifier now computes a monotone fixpoint over recorded `inputs[].digest` — cycles terminate because the set only grows — and reads inputs only for entries declaring `inputs` under an 8 MiB ceiling, so the large artifacts are never loaded for this check (`input_graph_skipped_large: []`).

**Falsified rather than trusted:**

| Manifest | Exit |
|---|---|
| committed | 0 |
| uncertainty flipped back to `true` | **1**, specific violation |
| unrelated entry flipped to `false` | 0 (conservative direction) |

So the check is not vacuous.

Scope: checked all six `true` entries for a reference to a `false` one. Exactly one was affected.

---

## #24 — Transitivity check silently passes on a fresh clone, where CI runs and no artifact bytes exist

**State:** CLOSED  |  **Opened:** 2026-10-08T11:53:37Z  |  **Closed:** 2026-10-08T12:04:18Z

## State

`PROPOSED` — confirmed by direct execution. This is a defect **in the fix for [#23](https://github.com/Lakshmi-Sindhu-P/AegisTrace/issues/23)**, which was itself a fix for [#21](https://github.com/Lakshmi-Sindhu-P/AegisTrace/issues/21). The vacuous precondition was reintroduced by the change that removed one.

## Problem

The transitivity check added by #23 reads each artifact's recorded `inputs[].digest` from the artifact's **bytes**. On a fresh clone the artifacts do not exist — they are deliberately untracked — so the check silently does nothing and reports success.

Reproduced. `uncertainty_summary.json` set back to `reproducible: true`, which is exactly the state #23 must reject, verified against an empty base directory:

```
$ python scripts/verify_artifact_manifest.py /tmp/emptyclone/artifact_manifest.json --base-dir /tmp/emptyclone
{"manifest": "...", "entries": 9, "verified_on_disk": 0, "absent": 9,
 "input_graph_checked": [], "input_graph_skipped_large": [], "violations": []}
exit=0
```

Against the real workspace the same manifest state gives `exit=1` with a named violation. So the check is **live only on a machine that happens to hold the artifacts**, and inert everywhere else.

Two distinct silent passes cause this, both in `scripts/verify_artifact_manifest.py:100-123`:

1. `if not artifact.is_file(): continue` — an absent artifact contributes no inputs.
2. `except (OSError, json.JSONDecodeError): continue` — an unreadable or unparseable artifact contributes no inputs.

In both cases an entry with no recorded inputs has no unreproducible inputs, so it satisfies the transitivity property **by default**. The failure mode is inverted: an artifact the verifier cannot read makes the check pass rather than fail.

## Why this matters more than it looks

`scripts/verify_artifact_manifest.py --help` states the design intent:

> "Registry cross-checks, which never need artifact bytes and therefore always run. [...] This is the check CI can perform on a fresh clone where none of the artifacts exist."

The transitivity check was added to that same verifier but does **not** follow that principle — it is excluded from the class of checks that always run, precisely the class that matters in CI. On a fresh clone, the report shows `violations: []` next to `input_graph_checked: []`, and nothing distinguishes *"verified clean"* from *"not verified at all"*. A reader or a CI step sees success.

Note the shape: the manifest's own `top_level_keys` decides whether an entry is inspected at all. When artifacts are absent that metadata is never cross-checked against bytes either, so an entry misdeclaring its keys would also evade the check. The pre-existing byte check covers that case only when artifacts are present.

## Why the obvious fix is not the right one

Making absence a violation would break the documented fresh-clone workflow — the artifacts are deliberately untracked, so absence is normal and correct. But treating absence as "fine" is what causes this defect. The problem is not the absence; it is that the **dependency graph lives in uncommitted bytes** when it is needed precisely where those bytes do not exist.

## Proposed fix (for review)

**Primary: commit the input edges as manifest data.** Each entry records the artifact paths it consumes, so the transitive property is a pure function of the committed manifest and needs no artifact bytes. That places it in the same class as the registry cross-checks and makes it run on a fresh clone, in CI, always.

**Secondary, regardless:** never let "could not check" be indistinguishable from "checked clean". Report a distinct field — `input_graph_unverified`, naming each entry and the reason (absent, unreadable, unparseable, over the size ceiling) — separate from `input_graph_checked`. Today `input_graph_skipped_large` exists for one such case but absence and read failure are reported as nothing at all.

**Also:** when an entry's `top_level_keys` declares `inputs` but its payload has no readable `inputs` list, that is a contradiction between the recorded metadata and the artifact. It should be a violation, not a silent `continue`.

## Design question for you

Once the edges are committed data, should a mismatch between the committed edges and the artifact's actual `inputs` array be a **violation** or a **warning**? A violation is stronger but means the two must be updated together whenever an artifact is regenerated. I lean toward violation, since a stale dependency graph would silently under-check — the same failure this issue is about.

## Acceptance criteria

- [ ] the transitive check runs and can fail on a fresh clone with no artifact bytes present
- [ ] absent, unreadable, unparseable, and over-ceiling artifacts are each reported in a distinct field naming the entry and the reason
- [ ] `input_graph_checked: []` is never reported alongside a silent success when entries declared inputs
- [ ] an entry declaring `inputs` in `top_level_keys` whose payload has no `inputs` list is a violation
- [ ] the check still passes on the committed manifest in the real workspace
- [ ] gate green: full suite, ruff, mypy

### Comment — 2026-10-08T12:04:17Z

## State: `DONE` — fixed in `b272c67`

The transitivity check ran off artifact bytes, which are deliberately untracked — so on a fresh clone it silently did nothing. Reproduced before the fix:

```
exit=0, input_graph_checked=[], absent=9, violations=[]
```

with the uncertainty entry set to the state the check must reject.

**Cause:** an absent or unreadable artifact contributed no inputs, and an entry with no recorded inputs trivially has no unreproducible inputs — so it passed **by default**. Unreadable made the check *pass* rather than fail.

**Fix:** input edges are now committed manifest data (`recorded_inputs`), so the property is a pure function of the committed manifest. Only the uncertainty summary has real edges, consuming the causal and stability summaries.

Independently re-verified:

| Case | Result |
|---|---|
| fresh clone, committed manifest | exit 0, absence **reported** (`input_graph_unverified`) |
| fresh clone, uncertainty → `true` | **exit 1**, named violation, committed data only |
| real workspace | exit 0 |

New `input_graph_unverified` distinguishes *"could not check"* from *"checked clean"*. A declared `inputs` key with no readable array, and a committed-vs-actual edge mismatch, are now violations. Plain absence stays non-fatal so the fresh-clone workflow still works.

Worth naming: this is the **vacuous-precondition class reintroduced by the change that removed one**. #21 → #23 → #24 is a three-deep chain of the same pattern.

---

## #25 — validate_results_ledger crashes with a traceback instead of reporting on malformed input

**State:** CLOSED  |  **Opened:** 2026-10-08T11:57:39Z  |  **Closed:** 2026-10-08T12:04:20Z

## State

`PROPOSED` — low severity. Confirmed by execution. Fail-safe: the exit code is already correct.

## Problem

`scripts/validate_results_ledger.py` is the only validator that lets a malformed or absent input escape as a raw Python traceback instead of reporting a structured violation.

```
$ python scripts/validate_results_ledger.py /tmp/bad.json
Traceback (most recent call last):
  ...
json.decoder.JSONDecodeError: Expecting property name enclosed in double quotes: line 1 column 3 (char 2)
exit=1
```

Every sibling reports cleanly:

```
solutions: malformed json     exit=1  Expecting property name enclosed in double quotes: ...
registry:  malformed json     exit=1  Expecting property name enclosed in double quotes: ...
ledger:    malformed json     exit=1  Traceback (most recent call last): ...      <-- this issue
```

## Severity

**Low, and not a correctness defect.** The crash happens at the first step — loading the ledger JSON — so no validation partially runs and no check is skipped. The exit code is 1, so a CI gate still fails. Nothing is silently accepted.

Two reasons it is still worth fixing:

1. **A traceback is not a finding.** The project reports violations as structured, readable statements. A traceback buries the actual problem (the JSON is malformed, and where) under library internals — unhelpful for a reader who is not a programmer, and inconsistent with the tool's own contract.
2. **A crash is not a designed error path.** It means the failure mode was never considered. The sibling validators each handle it deliberately; this one does so by accident.

## Proposed fix

Catch `(OSError, json.JSONDecodeError, ValidationError, TypeError)` around the load and report it the way `validate_solution_knowledge.py` and `validate_experiment_registry.py` already do, exiting 1 with a message naming the path and the reason. No behavioural change beyond the message: the exit code stays 1.

## Acceptance criteria

- [ ] malformed and absent ledger inputs exit 1 with a structured message, not a traceback
- [ ] the message names the path and the reason
- [ ] the validator still passes on the committed ledger
- [ ] existing tests unchanged and green; full suite, ruff, mypy green

### Comment — 2026-10-08T12:04:19Z

## State: `DONE` — fixed in `b7e4212` (LOW severity)

`validate_results_ledger.py` was the only validator escaping as a raw Python traceback. Now:

```
before:  Traceback (most recent call last): ... json.decoder.JSONDecodeError, exit 1
after:   cannot load ledger /tmp/bad.json: Expecting property name enclosed in double quotes: line 1 column 3 (char 2), exit 1
absent:  cannot load ledger /tmp/does_not_exist.json: [Errno 2] No such file or directory, exit 1
```

**Recorded honestly as low severity, not inflated.** This was *not* a correctness defect: the crash was at the first step — loading the JSON — so no validation partially ran and no check was skipped, and the exit code was already 1, so a CI gate still failed. Nothing was silently accepted.

Fixed for two reasons only: a traceback is not a finding, and a crash means the error path was never designed.

---

## #26 — Independence guard and determination disagree, and shared model_id is never compared

**State:** CLOSED  |  **Opened:** 2026-10-08T12:10:33Z  |  **Closed:** 2026-10-08T12:16:19Z

## State

`PROPOSED` — confirmed by execution. Found by building a falsification suite, not by reading the code.

## Problem

The two functions that answer *"are these two assessors independent?"* use **different criteria**, and the enforcing guard is the weaker of the two. `model_id` is compared **nowhere**.

```
case                                   guard raises?  determination  verdict
--------------------------------------------------------------------------------
A. identical descriptors               YES (refused)  False          agree
B. name-only clones (same id+fam)      no (allowed)   False          <-- DISAGREE
C. SAME model_id, DIFFERENT family     no (allowed)   True           <-- FALSE INDEPENDENCE
D. genuinely different models          no (allowed)   True           agree
```

- `assert_assessors_independent` (`run.py:83`) tests **structural equality** — `analyst != adjudicator`.
- `_independence_determination` (`run.py:111`) tests **`model_family` equality**.

Case B: descriptors differing only in `name` pass the guard, while the determination correctly says not independent — one question, two answers.

Case C is the real defect. Two descriptors sharing `model_id="gpt-x"` but declaring different `model_family` strings are reported as **`independence_established=True`**. The same model answered both sides, and the record says independence was established.

## Why this matters

Independent assessors are the premise of the entire LLM A/B triage design: two independently frozen models read the same evidence, and **disagreement is the signal**. If one model can be booked under two family-name strings and be declared independent, the comparison silently degenerates into one model agreeing with itself — and `agreement_score: 1.0` would be recorded as evidence of *agreement between independent assessors*, which is precisely the misreading the design exists to prevent.

This is the same shape as the lineage of defects in #14, #17, #23 and #24: a claim of verification that the mechanism cannot actually support.

The docstring at `run.py:120` is honest that "independence rests on the descriptors' own declaration and is not proof of the transport". But it does not say the declaration is unchecked against `model_id` — and `model_id` sits in the same descriptor object. Two descriptors carrying the identical `model_id` are the one case where the declaration is contradicted by the descriptor's own data. Not comparing it is an oversight, not a principled limitation.

## Root cause

**The question is implemented twice, with divergent criteria.** Two functions, one meaning, so they can drift — and they have. Fixing only the comparison would leave the same trap for the next change.

## Proposed fix (for review)

1. **One implementation.** Have `assert_assessors_independent` derive its verdict from `_independence_determination` and raise when it returns `False`, rather than re-testing an independent condition. Drift then becomes structurally impossible.
2. **Compare both identity-bearing fields.** Independence should require distinct `model_id` **and** distinct `model_family`. A shared `model_id` means one model however the family is labelled.
3. **Keep the message honest.** The raised error should name which field collided, so a reader knows whether the refusal was a shared model or a shared family.

## Timeliness

Latent, not live: the provider is `BLOCKED_HUMAN` and no A/B run has occurred. **This must be fixed before the frozen A/B experiment runs** — the preregistration is `FROZEN_PRE_DATA`, so correcting the independence rule now is legitimate, whereas changing it after data collection would be a protocol violation.

## Acceptance criteria

- [ ] the guard refuses descriptors sharing `model_id` even when `model_family` differs
- [ ] the guard refuses descriptors sharing `model_family`, agreeing with `_independence_determination`
- [ ] guard and determination cannot disagree — one derives from the other, proven by a test over a matrix of descriptor pairs
- [ ] the error message names the colliding field
- [ ] gate green: full suite, ruff, mypy

### Comment — 2026-10-08T12:16:17Z

## State: `DONE` — fixed in `cabbc4c`

Two functions answered one question with different criteria; the enforcing guard was the weaker. `model_id` was compared **nowhere**.

| Case | Before | After |
|---|---|---|
| A identical | REFUSED / False | REFUSED / False |
| B name-only clones | allowed / False ← **disagree** | **REFUSED** / False |
| C same `model_id`, diff family | allowed / **True** ← **false independence** | **REFUSED** / False |
| D different id + family | allowed / True | allowed / True |
| E different id, same family | — | allowed / False (runs, recorded not-established) |

Case C: one model answering both sides under two family-name strings, recorded as independence established. **Root cause was duplicated logic** — the question was implemented twice and the two drifted, so fixing only the comparison would leave the trap. Now a single `_independence_finding` returns `(established, basis, colliding_field)`; the determination wraps it and the guard reads it, making drift structurally impossible.

The guard deliberately refuses only **identity collisions**. A shared family with distinct ids, and distinct offline stand-ins, still run and are recorded `independence_established=False` — existing tests require those paths to run, and "is this degenerate" is a different question from "is independence established".

Latent, not live — the provider is `BLOCKED_HUMAN`. Fixed now **deliberately**: the preregistration is `FROZEN_PRE_DATA`, so correcting the rule before data collection is legitimate; after it would be a protocol violation.

Found by executing the guard against its worst case, not by reading it. Four prior rounds read it and it looked correct.

---

## #27 — Stability artifact provenance omits the repair step that rewrote it

**State:** OPEN  |  **Opened:** 2026-10-08T12:14:07Z  |  **Closed:** —

## State

`PROPOSED` — confirmed by execution, with a proof that does not require re-running the pipeline.

## Problem

`stability_summary.json` was produced by **two** steps, but the machine-readable provenance records only the first.

```
registry command : uv run python scripts/run_phase3_model_stability_cached.py
recorded digest  : 2c793f4280f43b8bb78a21b8df940a800485a333966e05a3a595d7f8e6cc91b0
on-disk digest   : 2c793f4280f43b8bb78a21b8df940a800485a333966e05a3a595d7f8e6cc91b0   MATCH
repair step in recorded command: False
```

The artifact was additionally rewritten in place by `scripts/correct_stability_operating_point.py`, which is **not** in the recorded command.

### Proof that the recorded command cannot produce the recorded artifact

```
$ grep -c "artifact_repair" scripts/run_phase3_model_stability_cached.py
0
$ grep -c "artifact_repair" scripts/run_phase3_model_stability.py
0
$ python -c "import json;print('artifact_repair' in json.load(open('data/.../stability_summary.json')))"
True
$ grep -rln "artifact_repair" scripts/*.py
scripts/correct_stability_operating_point.py
```

The on-disk artifact contains an `artifact_repair` block that **only** the repair script writes, and that neither recorded producer can emit. So executing the registry's recorded command yields a different artifact than the registry records. No re-run is needed to establish this.

## What the repair actually changed

Not a cosmetic difference. Per `scripts/correct_stability_operating_point.py`, it rewrites HGB's `operating_threshold` to 1.0, its `operating_metrics`, alert volume, per-scenario confusion metrics, `selection_status`, adds `fallback_policy`, and recomputes `disagreement`, `svm_unique_coverage` and `residual_error_analysis`.

## Why this is worth fixing even though the artifact is already flagged

The stability entry is already marked `reproducible: false` because of [#21](https://github.com/Lakshmi-Sindhu-P/AegisTrace/issues/21). So no *false reproducibility claim* survives at the manifest level, which limits the severity. **But the note actively misleads a reproducing party about the cause:**

> "each model result embedded a wall-clock `fit_runtime_seconds` value measured with `time.perf_counter`, so this digest can NEVER be reproduced even by a correct regeneration"

A reader who regenerates, sees a diff, and reads that note will conclude the difference is timing noise. It is not only timing noise — the operating point, the metrics, the disagreement section and the residual analysis all differ. **The documentation would lead them to the wrong diagnosis**, which is worse than saying nothing.

## Second gap: `recorded_inputs` is empty

```
manifest recorded_inputs for the stability entry: []
```

The repair step reads four behavioral Parquet artifacts (`data/evaluation/phase3_model_stability/{46,53,45,51}_behavioral.parquet`). The entry therefore declares no inputs while a step in its production consumed four artifacts. This is precisely what the transitivity check added in [#23](https://github.com/Lakshmi-Sindhu-P/AegisTrace/issues/23) and [#24](https://github.com/Lakshmi-Sindhu-P/AegisTrace/issues/24) depends on, so an empty edge list here weakens that check for this entry.

## Mitigating facts, recorded fairly

- The repair **is documented in prose**: `docs/methodology.md:127` and `docs/phase3_causal_representation.md:86` both name `scripts/correct_stability_operating_point.py`.
- The repair's own reason is sound and honest: HGB's zero-alert fallback required the derived sections to be recomputed so they matched the corrected operating point. Recomputing rather than hand-editing is the right instinct.
- The artifact records `artifact_repair.status = "validated"` and confirms `scenario_7: "sealed; not loaded"`.
- The repair does not fabricate: the zero-alert confusion values are arithmetically implied by threshold 1.0.

So this is a **provenance-completeness** defect, not a fabricated-results defect. I am not claiming the numbers are wrong.

## Proposed fix (for review)

1. **Record the full pipeline in the registry.** Either extend `command` to both steps, or add a distinct field (e.g. `post_processing_commands`) so a repair is visible as a step rather than smuggled into `command`. A single `command` field that hides a second step is the root of this.
2. **Populate `recorded_inputs`** for the stability entry with the four behavioral Parquet paths.
3. **Extend the manifest note** so it names the repair as a second cause of digest difference, not only the timing value.
4. **Consider in-place repair generally.** Overwriting the artifact destroys the pre-repair bytes. A repair that writes a new version and records both digests would keep the earlier state readable — consistent with the append-only convention the review history already follows.

## Design question for you

Whether `correct_stability_operating_point.py` should be treated as a **legitimate documented repair** or as **something to be eliminated** by fixing the producer to emit the correct operating point directly is a judgement call about how the Phase 3 chapter presents its history. I lean toward keeping the repair (it is honest and the reason is sound) but making it machine-visible. Eliminating it would require regenerating a 139 MB artifact.

## Acceptance criteria

- [ ] the machine-readable provenance for the stability artifact names every step that wrote it
- [ ] `recorded_inputs` lists the behavioral Parquet artifacts the repair consumed
- [ ] the manifest note names the repair as a second cause of digest difference
- [ ] the registry validator rejects a `command` that is a strict prefix of the true pipeline, or the schema makes multi-step pipelines explicit
- [ ] gate green: full suite, ruff, mypy

### Comment — 2026-10-08T22:44:31Z

**Criteria 1–3 fixed** — commit `44fdf57`. **Criterion 4 is proposed below, not taken**, because it changes what a validator *rejects*.

## Your diagnosis was right, and I confirmed it independently
The recorded command provably cannot produce the recorded bytes. `artifact_repair` is in the artifact's own `top_level_keys` and only the repair script writes it. Your framing — *"the documentation would lead them to the wrong diagnosis, which is worse than saying nothing"* — is the correct severity assessment.

## One correction to your proposed fix
**Your input paths were wrong.** You wrote `{46,53,45,51}_behavioral.parquet`. The script builds `f"{scenario_id}_behavioral.parquet"` from the **full capture name**, and the files on disk are:

```
CTU-Malware-Capture-Botnet-45_behavioral.parquet
CTU-Malware-Capture-Botnet-46_behavioral.parquet
CTU-Malware-Capture-Botnet-51_behavioral.parquet
CTU-Malware-Capture-Botnet-53_behavioral.parquet
```

I verified against the directory listing before writing anything. Had I taken your text on trust, `recorded_inputs` would have pointed at four files that do not exist — a *new* provenance defect replacing the old one. Flagging it because it is the same class of error the issue is about.

## What changed
1. **Registry** — the recorded command now names both steps: `... run_phase3_model_stability_cached.py && ... correct_stability_operating_point.py`.
2. **Manifest `recorded_inputs`** — now the four real Parquet paths (was `[]`), restoring the edge the #23/#24 transitivity check depends on.
3. **Manifest note** — now names the repair as a **second, independent** cause of digest difference, and lists what it rewrote, so the timing explanation cannot be mistaken for the whole story.

I did **not** list the stability artifact as its own input. The repair reads its own pre-repair bytes in place; a self-edge would be degenerate in the transitive closure. The in-place rewrite is stated in the note instead.

## Tests that moved (and why that is not weakening them)
Four manifest tests asserted the input graph contained **exactly one** entry with committed edges. That was a true statement about the *old* manifest, not a contract, so I updated the assertions.

One was **renamed**: `test_committed_manifest_passes_and_reports_no_unverified_inputs` → `..._and_names_its_unverified_inputs`. The old name is now false: the stability entry declares edges and is far above `MAX_INPUT_SCAN_BYTES`, so the verifier correctly reports it **could not read it** rather than silently passing. That is the honest state, and the test now pins it.

## Criterion 4 — the decision I am NOT taking
> the registry validator rejects a `command` that is a strict prefix of the true pipeline

**As literally written this is unimplementable.** The validator cannot know the true pipeline — it has no oracle for "what actually ran". Any check would be guessing.

But there **is** a checkable invariant that would have caught #27 exactly:

> If the manifest records `artifact_repair` in an artifact's `top_level_keys`, then the registry `command` for that artifact must name a repair script.

Both halves already exist in committed data, so this is a pure cross-file consistency check needing no artifact bytes.

**Why I did not just add it:** it is a new rejection rule over governance artifacts, and AGENTS.md reserves governance-rule changes for owner approval. Adding a check is not obviously safe — it could reject legitimate future registries.

**My recommendation: approve it**, because a repair that is invisible to the machine-readable provenance is precisely the defect, and prose in `methodology.md` did not prevent it.

## Your design question
*Legitimate documented repair, or something to eliminate?* **I agree with your lean: keep it, make it machine-visible.** Eliminating it means regenerating a 139 MB artifact to fix a *documentation* problem, and the repair's reason is sound — recomputing derived sections rather than hand-editing them is the right instinct. Keeping it also preserves the honest history of how the Phase 3 operating point was corrected.

Gate: 445 passed / 95.63%, ruff clean, mypy clean, guard ratchet 0, registry + manifest validators pass.

---

## #28 — Adopt guard falsification as a standing check: 44 guard raises the suite never executed

**State:** CLOSED  |  **Opened:** 2026-10-08T12:14:55Z  |  **Closed:** 2026-10-08T12:49:18Z

## State

`IN_PROGRESS` — suites written and green; the standing count check is proposed.

## Context

Round 25 changed method. Instead of reading guards, every guard was **executed against the input it exists to reject**. A guard never observed failing is an untested claim.

The measurable form of this: **which `raise` statements does the test suite never execute?** Coverage reports line coverage, but a covered *function* says nothing about whether its *rejection* path ever ran.

Measured on the suite as it stood at round 25:

```
=== raise statements NEVER executed by the test suite: 44 ===
  detection/evidence.py:115          finding has no matching events to bundle
  detection/ml.py:70                 threshold must be within [0, 1]
  evaluation/analyst_replay.py:147,152,178,294
  evaluation/baselines.py:109,114
  evaluation/hardening.py:28,34,75
  evaluation/improvement.py:82,87
  evaluation/metrics.py:48,50
  evaluation/model_family.py:74,150,377
  evaluation/reviewer_simulation.py:195,204
  features/{behavioral,causal,network}.py   (7)
  ingestion/{ctu13,iot23}.py                (7)
  schemas/{agent_trace,experiments,findings,manifests,review}.py  (9)
  ...
```

**44 guards, none of which had ever been observed refusing anything.** Most were fine, but two defects were found by this method and neither was visible to code reading.

## What this produced

Two new standing suites:

- `tests/test_validator_falsification.py` — 25 cases, one per pydantic `model_validator` invariant, including the three in `schemas/experiments.py`. Every guard fired. No findings. Each `pytest.raises` matches the guard's exact message, so no pass is vacuous.
- `tests/test_decision_falsification.py` — 15 cases over the decision guards (tier classification, independence, agreement, claim verification, the two causality audits, review-history immutability). Two findings, both in the independence guard, both fixed in [#26](https://github.com/Lakshmi-Sindhu-P/AegisTrace/issues/26).

The method works: it found a **false independence claim** (`model_id` never compared, so one model under two family names was reported independent) plus a guard/determination disagreement. Static reading had missed both across four prior rounds.

## Proposed durable step

`scripts/report_unexecuted_guard_raises.py`: parse each `raise` in `src/aegistrace/`, check it against the coverage data, and **fail if the count of never-executed guard raises exceeds a recorded baseline**. Otherwise this number drifts back up silently, exactly as it did before.

Deliberately a *count with a ratchet*, not a hard zero: some raises are genuinely unreachable defensively, and forcing zero would invite deleting real guards to satisfy a metric. The ratchet makes every new untested guard a deliberate act.

## Note on scope

Not every unexecuted raise is a defect. Some are defensive against states the type system already prevents. The point is that each one is an **unverified claim**, and the project should be able to say which ones and why.

## Acceptance criteria

- [ ] a script reports never-executed `raise` statements in `src/aegistrace/` against coverage data
- [ ] it fails when the count exceeds the recorded baseline, so the number cannot silently grow
- [ ] the baseline and the reason for each accepted entry are recorded in the repo
- [ ] both falsification suites run in CI and in the default test command
- [ ] gate green: full suite, ruff, mypy

### Comment — 2026-10-08T12:16:18Z

## State: `IN_PROGRESS` — suites green and committed; the ratchet script remains

Two standing falsification suites committed in `fefdb2e`. New guard count: **331 passed / 93.41%**.

The measurement that motivated this:

```
raise statements in src/aegistrace/ NEVER executed by the test suite: 44
```

Coverage says a function ran; it never says the **rejection path** ran. 44 guards had never once been observed refusing anything. Most were fine — two real defects were found, both invisible to reading, both fixed in #26.

Remaining acceptance criterion: `scripts/report_unexecuted_guard_raises.py` with a **ratchet** baseline, so the count cannot silently grow. Deliberately a count and not a hard zero: some raises are genuinely unreachable defensively, and forcing zero would invite deleting real guards to satisfy a metric.

### Comment — 2026-10-08T12:17:15Z

**Measured after the two suites: 44 -> 35.** The validator suite accounts for the drop (the 9 schema `raise` lines in `findings`, `manifests`, `review`, `agent_trace` x4, `experiments`). The decision suite moves few, because most decision guards *return* a verdict (`False`, a tier, an unverified status) rather than raising — so they are covered by assertions, not by executed `raise` lines.

Remaining 35, by module: `evaluation/` (20), `features/` (7), `ingestion/` (7), plus `detection/evidence.py:115` and `detection/ml.py:70`.

Note what this means for the ratchet: a count of never-executed `raise` statements measures only one half of the falsification idea. The decision suite proves guards refuse without ever executing a `raise` line. The ratchet should therefore be scoped to *raise-based* guards and say so, rather than being treated as total guard coverage.

### Comment — 2026-10-08T12:22:18Z

**Inverse finding: three guard messages can never fire on the public path.**

`network.py:80`, `behavioral.py:58`, `causal.py:71` each sit on a `@field_validator` that can never run, because the same field also declares a `Field(min_length=26, max_length=26)` constraint. Pydantic applies the constraint first, so a wrong count raises `too_short`/`too_long` and the validator is skipped.

Verified by execution:

```
FEATURE_NAMES count = 26
  too few   -> ValidationError; CUSTOM message reached: False   (too_short)
  too many  -> ValidationError; CUSTOM message reached: False   (too_long)
  direct classmethod -> ValueError: expected 26 feature values
```

**The invariant is enforced** — a wrong count is genuinely refused — so there is no data risk and this is not a defect in the rejection behaviour. It is a defect in the *diagnostic*: the informative `expected 26 feature values` is reachable only by calling the classmethod directly, so a developer hitting this sees only pydantic's generic message.

This matters for the ratchet: a count of never-executed raises would flag these three forever, and the honest resolution is **delete the redundant validator or delete the redundant constraint**, not add a test that calls the classmethod to make the number go down. That would be optimising the metric.

Suggested ratchet rule: every never-executed raise must be classified as either *unreachable by design* (with a reason) or *needs a test*. These three are unreachable **by accident** — a third category, and the one worth surfacing.

### Comment — 2026-10-08T12:49:17Z

## State: `DONE`

All acceptance criteria met. The ratchet is committed in `5990190`; the count is **44 → 0**.

**What the round established.** Choosing to *execute* every guard against the input it exists to reject — rather than read it — found four defects that four prior rounds of reading had missed, including a false independence claim in the safeguard the whole A/B design rests on (#26).

**Suites** (all in the default test command):

| Suite | Cases | Findings |
|---|---|---|
| `test_validator_falsification.py` | 25 | none |
| `test_decision_falsification.py` | 15 | 2, both fixed in #26 |
| `test_evaluation_falsification.py` | 15 | none |
| `test_pipeline_falsification.py` | 13 | none |
| `test_remaining_falsification.py` | 10 | none |
| `test_guard_ratchet.py` | 7 | — |

The evaluation layer is the one that matters most and it is clean: `compute_binary_metrics` refuses a length mismatch and an out-of-range threshold, `calibration_summary` refuses scores outside `[0,1]`, and `replay_capture` refuses non-finite scores — each of which would otherwise have produced plausible numbers from invalid input.

**Ratchet**, independently falsified before commit:

| Case | Result |
|---|---|
| real repo | `unexecuted guard raises: 0 (baseline 0)`, exit 0 |
| `__main__` raise in source | excluded |
| raise marked executed | not reported |
| `exceed_count(count, baseline)` | `0/0:0, 1/0:1, 5/3:1, 2/3:0, 0/5:0` — all correct |

**Deliberately a ratchet, not a hard zero.** Some raises are genuinely unreachable defensively; forcing zero would invite deleting real guards to satisfy a metric. It fails only when the count *exceeds* the baseline, and prints a tighten note when it falls below so the baseline cannot drift above reality.

**The `__main__` correction is part of the finding, not a detail.** Two of the last nine hits were `raise SystemExit(main())` under `if __name__ == "__main__":` — CLI entry points, not guards. Counting them inflated the number and invited a test that imports the module as a script purely to make a metric go down. The exclusion is asserted in code.

**Third instance this round of the instrument being wrong rather than the code:** a first ratchet implementation reported **97** because coverage JSON keys are repo-relative while it looked them up by absolute path. 97 would have read as a catastrophic regression.

Gate: 384 passed / 95.44%, ruff clean, mypy clean (49 files).

---

## #29 — Ledger evidence is unverified: the validator checks artifact digests, never the claimed values

**State:** CLOSED  |  **Opened:** 2026-10-08T12:21:35Z  |  **Closed:** 2026-10-08T12:42:40Z

## State

`PROPOSED` — measured, with a working resolver.

## Problem

The results ledger grounds each claim in an artifact. `validate_results_ledger.py` verifies that the artifact **exists** and that its **digest matches the registry**. It never compares the claim's stated value to the artifact's contents.

So the check is real but answers a different question than it appears to. A matching digest proves *this is the right file*; it says nothing about *whether the numbers in this claim are the numbers in that file*. A claim could drift from its artifact and every validator would stay green.

For a project whose stated thesis is evidence-grounded claims, the grounding is currently **manual and unenforced**.

## Measured

Wrote a resolver for the ledger's already-machine-parseable evidence form and ran it over all 12 claims:

```
evidence strings: 25 total
  machine-checkable  :  2   (3 assertions)
  prose-only         : 23
assertions MATCHED   : 3
assertions MISMATCHED: 0
unresolved           : 0
```

**I found no incorrect numbers.** All three checkable assertions resolve exactly. This issue is about the *check*, not about wrong data, and should not be read as doubting the results.

## What the evidence looks like

Two of 25 strings are in a form the machine can already read:

```
Captures[scenario_id=CTU-Malware-Capture-Botnet-49].policies[policy=model_score].budgets[budget=100].true_positives = 100
```

The other 23 are prose:

```
"Uncertainty's true-positive count exceeds model_score's at 0 of the 9 tested budgets on each of the six evaluated captures."
```

The prose strings are *specific and checkable by a human* — that is genuinely valuable, and I am not proposing to delete them. The problem is that nothing enforces them, so their accuracy depends on the care taken at authoring time and is never re-verified afterwards.

## Why the digest check makes this worse rather than neutral

`--require-artifacts` prints a digest comparison, so the validator's output *looks* like grounding has been verified. A reader reasonably concludes the claim is tied to its evidence. The tie is real at the file level and absent at the content level, and the output does not distinguish them. A check that is silent about what it does not cover is read as covering it.

## What the resolver already does

~40 lines. Parses `root[sel=val].field = expected`, walks the artifact, handles the `A = true and B = false` multi-assertion form, and reports `MISMATCH` / `UNRESOLVED` separately so an absent path is never silently treated as agreement. It resolves all three current assertions.

Two false results during development are worth recording as method notes:

- The first resolver version did not split on `" and "`, so it read `true and headline.x = false` as one expected value and reported a spurious `MISMATCH`. **The first apparent data-integrity finding of the round was my own parser bug.** Fixed before reporting.
- Had I trusted the first run, I would have filed a fabricated defect against a correct claim.

## Proposed fix (for review)

1. **Resolve the machine-checkable assertions in CI.** `--require-artifacts` should fail when a `path = value` assertion resolves to a different value, and also when a path does not resolve (absent must be a distinct failure from mismatched).
2. **Distinguish the two evidence forms in the ledger schema** — checked assertions versus prose rationale — so it is visible which strings carry an enforced guarantee. Do not require all 23 to be converted at once.
3. **Convert where cheap.** Any prose string that is really one number can move to the checkable form; the remaining narrative stays and is honestly labelled as unenforced.
4. **Make the validator report its own coverage** — "3 of 25 evidence strings enforced" — so a clean run never implies more than it checked. This is the same defect as [#20](https://github.com/Lakshmi-Sindhu-P/AegisTrace/issues/20): a guard reporting success over a scope it does not actually cover.

## Acceptance criteria

- [ ] a `path = value` evidence assertion that disagrees with its artifact fails validation
- [ ] an unresolvable evidence path fails validation, distinctly from a value mismatch
- [ ] the ledger schema distinguishes enforced assertions from prose rationale
- [ ] the validator prints how many evidence strings it enforced, so a clean pass cannot be read as full coverage
- [ ] the resolver is unit-tested against a fixture, including the multi-assertion `and` form that produced the false positive above
- [ ] gate green: full suite, ruff, mypy

### Comment — 2026-10-08T12:42:39Z

## State: `DONE` — implemented in `8cec76e`

Enforcement added and **falsified independently** before committing, on a temporary copy of the real ledger:

| Case | Result |
|---|---|
| unmodified ledger | exit 0 |
| value corrupted (+7) | exit 1 — `evidence value mismatch` |
| path corrupted | exit 1 — `evidence path does not resolve` *(distinct message)* |

The target used was the multi-assertion `A = true and B = false` string itself — the exact form that produced a false mismatch in my first ad-hoc resolver during investigation.

**Coverage is now reported**, which is the substance of the fix:

```
{"assertions_checked": 3, "evidence_strings_enforced": 2, "evidence_strings_total": 25, ...}
```

A clean run now says "2 of 25 enforced" instead of implying that all evidence was verified. Previously the digest comparison's output *looked* like grounding had been checked while the claim's content was never read.

**Enforcement is deliberately conservative**: a string is enforced only if *every* `and` fragment parses as an assertion; if any fragment does not, the whole string is prose and unenforced. That reproduces the measured 25/2/3 baseline exactly rather than converting prose into fabricated failures. The 23 prose strings remain allowed — they are specific and human-checkable, and requiring them to be rewritten now would be scope creep.

Three failure kinds are kept distinct, because "the path is gone" and "the value moved" are different problems: value mismatch, unresolved path, and ambiguous selector (more than one list item matches — must not silently take the first).

**Result: 3 assertions matched, 0 mismatched. No incorrect numbers were found.** This issue was always about the check, not the data.

Remaining acceptance criteria met: resolver unit-tested (8 tests, including a regression test for the `and`-form false positive), validator reports its own coverage, gate green (377 passed / 95.44%, ruff clean, mypy clean 49 files). `docs/results_ledger.json` and everything under `data/` unchanged.

---

## #30 — Tiered review records a tier it never reconciles with the assignment it judges

**State:** CLOSED  |  **Opened:** 2026-10-08T12:51:52Z  |  **Closed:** 2026-10-09T03:39:56Z

## State

`PROPOSED` — confirmed by execution on the real schemas.

## Problem

The review layer records three governance facts but enforces none of the relationships between them. The tier is described in `schemas/review.py` as *"a claim about who is qualified to decide"* — but nothing ties a review to the tier the deterministic classifier actually assigned.

Executed against the real schemas:

```
=== can a review claim any tier? ===
  ACCEPTED  tier=D (case needed expert/insufficient) but decision=CONFIRM
  ACCEPTED  tier=A machine-check but decision=ESCALATE
  ACCEPTED  tier=C expert but decision=CONFIRM recorded with no expert evidence

=== is decision=ESCALATE consistent with escalation_state? ===
  ACCEPTED  decision=ESCALATE but escalation_state=NONE
  ACCEPTED  decision=CONFIRM but escalation_state=ESCALATED

=== does the review_id have to match its own content? ===
  ACCEPTED  review_id derived from a DIFFERENT subject/reviewer/decision
  ACCEPTED  arbitrary random review_id
```

### Three unenforced relationships

1. **Review tier vs assigned tier.** `classify_tier` computes a tier and `SpineRecord.tier` stores it ([spine.py:154](https://github.com/Lakshmi-Sindhu-P/AegisTrace/blob/agent/dsh/takeover/src/aegistrace/spine.py#L154)), but **no code path connects a `TierAssignment` to a `HumanReview`**. A Tier C case — the tier that exists because resolving it "needs expertise" — can be recorded as `CONFIRM`abed at Tier A machine check. The append-only history then shows it as a legitimate disposition. This is the governance claim the whole tier system exists to make, and the mechanism does not make it.

2. **Decision vs escalation state.** Verified by grep: `HumanReview.escalation_state` is **never read anywhere in `src/`** — only written, and only in tests. So `decision=ESCALATE` with `escalation_state=NONE` is accepted, and the escalation is invisible in the record. (`AgentTraceRecord` has its own `validate_escalation_state`; `HumanReview` has none.)

3. **Review identity vs derived identity.** `review_id_for` derives a deterministic id from subject, reviewer, decision and time — and is **never called in `src/`**, only exported and used by tests. So `HumanReview.review_id` is a free UUID: it may be random, or derived from a *different* subject and reviewer than the record it labels. Since the append-only chain deduplicates and links on `review_id`, lineage rests on a value nothing checks. Same class as [#21](https://github.com/Lakshmi-Sindhu-P/AegisTrace/issues/21) and [#24](https://github.com/Lakshmi-Sindhu-P/AegisTrace/issues/24).

## Why this matters and why it is not urgent

`classify_tier`, the schema and the append-only history are all sound — this is not a broken component, it is a **missing link** between two working ones. Nothing is live, because the human-review workflow that would consume it is not built yet (part of milestone 8, [#12](https://github.com/Lakshmi-Sindhu-P/AegisTrace/issues/12)).

But building that workflow on top of an unreconciled pair would bake the gap in, and the gap is precisely the "no autonomous action / expertise consumed where required" promise. Fixing it before the workflow exists is much cheaper than after.

## Proposed fix (for review)

1. **A single entry point** that records a review against the assignment it judges, refusing when they disagree. Reviews must not be constructible into a history without stating which `TierAssignment` they answer.
2. **Enforce decision/escalation coherence** as a schema invariant, since it is intrinsic to the record and needs no external context: `ESCALATE` requires a non-`NONE` state, and a non-`NONE` state requires `ESCALATE`.
3. **Require `review_id` to equal `review_id_for(...)`**, or derive it rather than accepting it. A supplied id that disagrees with its own content is a lineage hazard.
4. **Decide the semantics of `HumanReview.tier`** — see the design question below.

## Design question for the owner

`HumanReview.tier` is currently ambiguous, and the fix depends on which reading is intended:

- **(a) The tier the case required** — then it must equal `TierAssignment.tier`, and a mismatch is a defect.
- **(b) The tier at which this review was actually conducted** — then a *lower* value than required means expertise was skipped (refuse), and a *higher* value means the case was escalated beyond the minimum (allowable, but should be recorded as a deliberate over-escalation, not a silent discrepancy).

My recommendation is **(b) with both directions checked**, because it keeps one field meaning one thing and still lets a reviewer escalate upward. But this changes what the field means, so it needs your call rather than mine. I have not written the fix pending that.

## Acceptance criteria

- [ ] a review whose tier is below the assigned tier is refused
- [ ] a review at a higher tier than required is either refused or explicitly recorded as over-escalation
- [ ] `ESCALATE` without an escalation state, and an escalation state without `ESCALATE`, are both refused
- [ ] a `review_id` that disagrees with `review_id_for(...)` is refused, or is derived rather than accepted
- [ ] no review can be appended to a history without naming the `TierAssignment` it answers
- [ ] tests falsify each new guard against the input it exists to reject
- [ ] the guard ratchet still reports 0 unexecuted guard raises
- [ ] gate green: full suite, ruff, mypy

### Comment — 2026-10-08T13:08:19Z

## Status: two of three parts DONE (`4160838`); one part awaits your decision

**Done** — both intrinsic invariants, which need no external context:

- `validate_review_coherence` enforces escalation coherence in **both** directions with distinct messages.
- `review_id` must equal `review_id_for(...)` computed from the record's own fields.

Evidence the gap was live rather than theoretical: **two pre-existing tests** built reviews with `review_id=uuid4()` and had to be repaired — `test_spine_raises_if_a_review_were_present` and `test_spine_refuses_record_with_a_review`. The invariant those tests falsify is unchanged and still asserted.

Gate: 393 passed / 95.46%, ruff clean, mypy clean (49 files), guard ratchet 0, all three new guards exercised.

**Not done — needs you.** The third part, reconciling `HumanReview.tier` against the `TierAssignment` the review judges, is deliberately unimplemented because it depends on what `HumanReview.tier` is *supposed to mean*:

- **(a) the tier the case required** — then it must equal `TierAssignment.tier`, and any mismatch is a defect;
- **(b) the tier the review was actually conducted at** — then *below* required means expertise was skipped (refuse), and *above* required means a deliberate over-escalation (allowable, but should be recorded as such rather than as a silent discrepancy).

My recommendation is **(b)**, checking both directions, because it keeps one field meaning one thing and still allows a reviewer to escalate upward. But it changes what the field means, so it is yours to call. I did not guess, because guessing here would silently redefine a governance concept — the same class of mistake this issue exists to fix.

Once you choose, the remaining work is small: a single entry point that refuses a review whose tier is below the assignment, plus the owner-approved handling of the above-required case.

### Comment — 2026-10-08T22:54:25Z

**Status narrowed: 2 of your 4 proposed fixes are already implemented, and a third gap is now closed.**

I re-ran your reproduction. **Your issue text is stale** — and my first re-run was wrong too, which I'll own below.

## Your six "ACCEPTED" cases, re-run honestly

| Case | Your issue says | Now |
|---|---|---|
| `tier=D` but `decision=CONFIRM` | ACCEPTED | **still ACCEPTED** |
| `tier=A` machine-check but `decision=ESCALATE` | ACCEPTED | **still ACCEPTED** |
| `decision=ESCALATE` but `escalation_state=NONE` | ACCEPTED | **REFUSED** ✅ |
| `decision=CONFIRM` but `escalation_state=ESCALATED` | ACCEPTED | **REFUSED** ✅ |
| `review_id` derived from a different subject/reviewer/decision | ACCEPTED | **REFUSED** ✅ |
| arbitrary random `review_id` | ACCEPTED | **REFUSED** ✅ |

So **fix 2** (decision/escalation coherence) and **fix 3** (`review_id` must equal `review_id_for(...)`) landed during the identity work (#35/#38/#40). They are in `HumanReview.validate_review_coherence`.

## A correction to my own method, because it nearly produced a false report
My first re-run printed `ACCEPTED` for **all six** cases, including ones that are now refused. That was my bug, not yours and not the code's: I wrote `probe("decision=ESCALATE but escalation_state=NONE")` — **passing only the label and never the override**. Every probe built the same coherent default review, so every probe said ACCEPTED. The labels were decorative.

Had I stopped there I would have filed "the coherence validator does not fire" — a serious false claim about a working guard. It is the **tenth** time in this project that the measuring instrument was wrong rather than the code, and the second time in two rounds. I rebuilt the probe to construct each case explicitly and assert the expected result.

## What is genuinely left — fix 1 and fix 4
Only the **tier** relationship is unenforced, exactly as you diagnosed:

- `tier=D` (needs expertise) + `CONFIRM` → accepted
- `tier=A` (machine check) + `ESCALATE` → accepted

Your fix 1 (an entry point taking a `TierAssignment`) and fix 4 (what `HumanReview.tier` means) are the two that need you. **They are the same decision**: the entry point cannot refuse a mismatch until the field's meaning is fixed. So this is **one** decision, not two.

## The third gap I found and closed — commit `bec8bc5`
While checking where the chain is enforced I found a related hole **your issue did not mention**. `ReviewHistory` is documented as *"the append-only chain"* with *"the last entry unambiguously current"* — but that was enforced **only** by `append_review`. Durable histories are read back with `ReviewHistory.model_validate(...)`, which never calls it.

Executed against the real schema, `ReviewHistory` accepted a **dangling supersede link**, a **forked (non-linear) chain**, a first review superseding something, and **duplicate `review_id`s** — and a forged non-linear chain **survived a JSON round-trip**. So a corrupted or tampered history file loaded silently and presented a broken lineage as authoritative.

That is the same class as #21/#24/#42: a documented guarantee enforced on one path and bypassed on the one that matters. `ReviewHistory.validate_chain_is_linear` now enforces the helper's four rules with the helper's messages, so every history the helper can build still validates. **Category A** — the contract was already stated; this enforces it everywhere instead of adding a new rule. 7 new tests, including one asserting the helper and the schema reject the same shapes.

Gate: 452 passed / 95.66%, ruff clean, mypy clean, guard ratchet 0.

### Comment — 2026-10-09T03:39:56Z

**DONE** — implemented and committed as `3b3fbce`. Owner decision recorded in `docs/pending_decisions.md`.

## Owner decision (verbatim)

> "Approve Option 1. HumanReview.tier represents the tier actually conducted; TierAssignment retains the tier required. Reconcile the two, report unmet requirements explicitly, and do not assume a simple numerical ordering of tiers. Preserve review history and add regression tests."

## Problem -> cause

`HumanReview.tier` carried a tier that nothing ever compared to the `TierAssignment.tier` for the same
case. A case that **required** expert judgement but was only machine-checked was silently accepted.

## The three parts of the decision, and how each was satisfied

### 1. "HumanReview.tier represents the tier actually conducted; TierAssignment retains the tier required"

The meaning is fixed in the field description and the class docstring. The field is **not renamed** and
`review_id_for`'s inputs are unchanged, so stored records still load and the append-only history chain is
preserved.

### 2. "Do not assume a simple numerical ordering of tiers"

This is the crux, and it is why the relationship is an explicit map rather than a comparison:

```
_REQUIREMENT_SATISFIED_BY: dict[ReviewTier, frozenset[ReviewTier]]

    A <- {A, B, C}
    B <- {B, C}
    C <- {C}
    D <- {D}
```

`D_INSUFFICIENT_EVIDENCE` is **its own case and is never treated as "more than C"**. It is a terminal
*outcome* — the evidence did not support a decision — not a qualification level. Consequently:

| Conducted \ Required | A | B | C | D |
|---|---|---|---|---|
| A | yes | no | no | no |
| B | yes | yes | no | no |
| C | yes | yes | yes | **no** |
| D | **no** | **no** | **no** | yes |

Two cells are the whole point: a **D-conducted review satisfies no A/B/C requirement**, and a
**C-conducted review does not satisfy a D requirement**. A naive `conducted >= required` would have got
both wrong.

Exposed as `tier_satisfies_requirement(*, conducted, required)`, which reads the map, so the map is the
single source of truth.

### 3. "Reconcile the two, report unmet requirements explicitly"

New `TierReconciliation(FrozenSchema)` owns **both** halves — `assignment` (required) and `review`
(conducted) — with two `model_validator(mode="after")` methods.

The placement is the substance of the fix. This project's documented recurring defect is that a rule
written once in a builder is **bypassed by `model_validate`**, which is how durable records are read back.
`reconcile_tier` therefore recomputes `requirement_met` and `unmet_requirement` from the two authoritative
tiers on **every** construction path — construction, `model_validate` of stored JSON, and
`model_copy(update=...)` (which `FrozenSchema` re-validates).

**Under-review is recorded, not fatal.** An under-reviewed case produces a valid object with
`requirement_met=False` and a plain-language `unmet_requirement` naming both tiers, e.g.:

> this subject required a review at tier tier_c_expert_judgment (who is qualified to decide), but the
> review was conducted at tier tier_a_machine_check; the requirement was not met

That makes the discrepancy an inspectable, serialized, immutable fact rather than a silent acceptance or a
crash — and still lets a human escalate a case the assigned tier never covered.

Two anti-forgery properties fall out of recomputation: a stored record whose claimed `requirement_met`
**contradicts** its tiers is **refused**, and a forged `unmet_requirement` note is **overwritten**, not
trusted.

## Regression tests

26 tests in `tests/test_review_tier_reconciliation.py`:

- (a) a review that **meets** the requirement -> `requirement_met=True`, `unmet_requirement=None`;
- (b) a review that does **not** (required C, conducted A) -> `False` plus the explicit note, surviving a
  JSON round-trip;
- (c) the **D cases**, parametrized against the map in both directions — D-conducted never satisfies A/B/C,
  and a D requirement is met only by a D-conducted review;
- (d) the **JSON load path**: a forged `requirement_met` flip is refused in **both** directions, plus
  subject mismatch refused;
- (e) a **repeated/duplicate decision** reconciles identically and deterministically.

## Proof

The implementation was delegated, and the result was **not taken on report**. Independent re-verification:

Direct probes confirmed the non-ordinal map; D-conducted satisfying neither A nor C; C-conducted not
satisfying D; a forged stored record refused with the exact contradiction message;
`model_copy(update=...)` refused; a forged note overwritten; an honest record round-tripping unchanged.

Then mutation on a pristine `/tmp` copy with a verified GREEN baseline, one mutation at a time, reverted
after each:

| Mutation | Result |
|---|---|
| Put `D` into `A`'s satisfiers (breaks non-ordinality) | tests **FAIL** — caught |
| Delete the `requirement_met` contradiction guard | tests **FAIL** — caught |
| Force `requirement_met` True (silent success) | tests **FAIL** — caught |
| Delete the subject-mismatch guard | tests **FAIL** — caught |

## Downstream effects / contract changes

- **New public schema** `TierReconciliation`, plus `tier_satisfies_requirement` and
  `_REQUIREMENT_SATISFIED_BY` (exported in `__all__`).
- `HumanReview` gains **no** new field and loses none; `review_id_for` inputs unchanged; the append-only
  `ReviewHistory` chain is untouched.
- No frozen research artifact, historical result or published metric is affected.

Gate: **499 passed** (was 473), 95.86%, ruff clean, mypy clean, guard ratchet 0 — both new raises are
executed by tests.

---

## #31 — build_evidence_bundle is quadratic and its Iterable contract is a lie

**State:** CLOSED  |  **Opened:** 2026-10-08T12:54:45Z  |  **Closed:** 2026-10-08T13:08:17Z

## State

`PROPOSED` — both defects confirmed by execution; the performance numbers by measurement.

## Summary

`detection/evidence.py::build_evidence_bundle` is the heart of the evidence spine: it snapshots everything behind one finding. It has two defects, both in the same function, and neither is visible by reading it.

1. **Its declared type is a lie.** `detections` and `events` are annotated `Iterable[...]`, but the implementation iterates them *per call*. A generator is a valid `Iterable`, so a legal call silently works for the first finding and then fails for every one after it — with an error that blames the wrong thing.
2. **It is quadratic in the number of findings.** It re-scans all detections and re-indexes all events *for each finding*.

## Defect 1 — generator input fails after the first finding, misleadingly

Passing one shared generator, which the declared `Iterable` type permits:

```
finding 0: built a bundle
finding 1: ValueError: finding has no matching detections to bundle
finding 2: ValueError: finding has no matching detections to bundle
finding 3: ValueError: finding has no matching detections to bundle
```

The detections **do** exist — the iterator was consumed by the first call. The error names the finding, so a caller debugs the finding instead of the iterator. That is the wrong diagnosis handed to the person least likely to guess it.

Two candidate causes in the body:

```python
selected = sorted((d for d in detections if d.detection_id in wanted), ...)
...
events_by_id: dict[UUID, SecurityEvent] = {event.event_id: event for event in events}
```

Both consume their argument on every call, so neither may be an `Iterable` unless it is materialized once.

**Why it is latent but worth fixing now.** The current corpus builder passes tuples, so it does not trip. But streaming a large capture rather than materializing it is exactly what you would do for a 130k-event binetflow — the case milestone 7 ([#11](https://github.com/Lakshmi-Sindhu-P/AegisTrace/issues/11)) needs. The first person to reach for a generator for good reasons hits a confusing failure.

## Defect 2 — O(findings x detections) and O(findings x events)

Measured on real capture 46 (`capture20110815-2.binetflow`), staging the pipeline:

| events | findings | parse | emit | aggregate | **bundle** |
|---|---|---|---|---|---|
| 2,000 | 660 | 0.08s | 0.02s | 0.01s | **0.27s** |
| 8,000 | 2,176 | 0.27s | 0.16s | 0.06s | **4.41s** |
| 16,000 | 4,231 | 0.74s | 0.45s | 0.14s | **19.23s** |

Time grows with the **square** of the finding count while every other stage is roughly linear. Extrapolating to the full 129,833-line capture (~34k findings) gives roughly **21 minutes**, which matches an independent full-capture run that was still going after 20 minutes before being stopped.

The cause is per-finding work over the full inputs:

```python
selected = sorted((d for d in detections if d.detection_id in wanted), ...)   # scans ALL detections
events_by_id = {event.event_id: event for event in events}                    # rebuilds ALL events
```

`events_by_id` is rebuilt from scratch for every finding — for the full capture that is ~130k dict insertions repeated ~34k times. `aggregate_findings` in the same pipeline already builds its index once; this function does not.

## Why this matters for the research, not just for speed

The A/B triage corpus has to be built from real captures. At 21 minutes per capture the pipeline is impractical to iterate on, which is a plausible reason the corpus was only ever built from the tiny 559-byte fixture. A corpus of 4 findings cannot support any evaluation claim, so this performance defect sits directly between milestone 7 and a usable corpus.

## Proposed fix (for review)

1. **Hoist both indexes out of the per-call body.** Build `detections_by_id` and `events_by_id` once and reuse them. This is the same change that makes the function linear.
2. **Resolve the type honestly.** Either require `Sequence[...]` — a deliberate narrowing, since the function needs re-iteration — or materialize once internally. Requiring `Sequence` is the more honest fix and makes the constraint visible at every call site; if a caller genuinely streams, it should materialize explicitly and own that cost.
3. **Fix the error message** so an exhausted or absent input is distinguishable from a finding that legitimately has no matching detections.
4. **Add a scaling test** asserting the cost grows roughly linearly, so the quadratic cannot return unnoticed. A wall-clock threshold is flaky, so assert on *work* — e.g. that the index is built a constant number of times.

## Acceptance criteria

- [ ] `build_evidence_bundle` accepts a generator and produces the same bundles as with a tuple
- [ ] passing one shared generator across many findings either works or fails with a message that identifies the exhausted input, never "finding has no matching detections"
- [ ] the documented parameter type matches the real requirement
- [ ] bundle time grows roughly linearly with finding count, demonstrated on the real capture
- [ ] the full-capture corpus build completes in a time that makes iteration practical
- [ ] a regression test distinguishes absent input from exhausted input
- [ ] the guard ratchet still reports 0 unexecuted guard raises
- [ ] gate green: full suite, ruff, mypy

### Comment — 2026-10-08T12:57:04Z

## Correction to my own proposed fix

**The fix I proposed above is wrong, and I am correcting it before it is implemented.**

I wrote: *"Hoist both indexes out of the per-call body. Build `detections_by_id` and `events_by_id` once and reuse them."*

That does not work. `build_evidence_bundle` is called **once per finding**, so an index built inside the function is still rebuilt on every one of the F calls. The cost stays `O(F x D + F x E)`. **Hoisting within the function cannot fix a quadratic in the number of calls** — the index has to be built once *for all findings*, which means it cannot be owned by the per-finding function at all.

### What actually fixes it

1. An index built once — `detections_by_id` plus `events_by_id` — owned by the caller, not the per-finding function.
2. A **batch** entry point that takes all findings, builds the index once, and returns every bundle. That is the shape the real workload needs: the corpus builder maps over findings.
3. The per-finding function refactored to take the index.

The important lesson is the one this whole round keeps repeating: **I proposed a fix without checking it against the call pattern.** The defect was found by measuring, and the fix was then proposed by reading — and the fix was wrong. The scaling test in the delegated work asserts the index is built a constant number of times regardless of finding count, and that test would have caught the wrong implementation. A work-based test is what makes this class of error visible instead of hiding in a wall-clock number.

### Note on my earlier estimate

Recomputing the exponent from the measured points gives ~2.2-2.3, slightly super-quadratic, because per-finding work also grows with cluster size. Extrapolating to the full capture's ~34k findings gives between roughly **21 and 35 minutes**; the figure in the summary below is the conservative lower bound, and it is consistent with the observed full run still going after 20 minutes.

### Comment — 2026-10-08T12:59:52Z

## Second correction — I overstated the consequence, and the overstatement was mine

In the summary above I wrote:

> At 21 minutes per capture the pipeline is impractical to iterate on, **which is a plausible reason the corpus was only ever built from the tiny 559-byte fixture**.

That inference is wrong, and I am retracting it rather than leaving a convenient story in the record.

**Why it is wrong.** The preregistration's corpus is **20 bundles** (`docs/llm_ab_preregistration.md`, "Complete run: 20 bundles"). A bundle is one finding. Measured on capture 46: **2,000 lines already yields 660 findings**. So 20 bundles needs a slice of roughly **50-80 lines**, which completes instantly even with the quadratic. The performance defect therefore is **not** an obstacle to building the 20-bundle corpus, and it cannot be the reason the corpus does not exist.

**What is actually true**, verified just now:

- No corpus artifact exists anywhere on disk — only `triage/corpus.py`, `scripts/build_triage_corpus.py`, and a test.
- The corpus is registered in **neither** `docs/artifact_manifest.json` nor `docs/experiment_registry.json`.
- The only fixture, `data/fixtures/ctu13/scenario_11.binetflow`, is **5 lines** and yields exactly **4 entries** (`entry_count: 4`, all counts 4). Running the builder with a fixed timestamp gives a stable digest.
- So the frozen protocol's 20-bundle sample plan **cannot be satisfied by the available fixture**, and needs a slice of a real capture. That is ordinary pending work in [#11](https://github.com/Lakshmi-Sindhu-P/AegisTrace/issues/11), not a defect — the preregistration is still `FROZEN_PRE_DATA`, so no run has been invalidated.
- The empty `data/derived` directory in my earlier check was a weak signal and I should not have leaned on it; the `find` over the whole tree is the real evidence.

**So what is the quadratic actually blocking?** Full-capture processing. That is what the detector evaluation, the unknown-label workload, and any per-capture held-out run need — capture 44 alone is 4.7M rows. That is a real impact, and it is the one I should have claimed: **`build_evidence_bundle` makes whole-capture analysis impractical**, not corpus construction.

This is the second time in this issue that I stated a consequence without measuring it, after finding the defect by measuring. The pattern is worth naming: measuring found the bug; reasoning-from-the-bug produced two consecutive wrong claims. Both were caught only by going back to execution.

### Comment — 2026-10-08T13:08:17Z

## DONE — `13c910e`

Both defects are fixed and independently verified. The corrected batch design shipped, not my original wrong proposal.

**What changed** (`src/aegistrace/detection/evidence.py`, `tests/test_evidence_bundle_scaling.py`, `scripts/build_triage_corpus.py`):

- `EvidenceIndex`, a frozen dataclass whose `from_inputs` materializes both inputs **once**.
- `build_evidence_bundles`, a batch entry point that builds one index and shares it across all findings, making the cost O(D + E) **independent of finding count**. This is the shape the real workload needs, since the corpus builder maps over findings.
- `build_evidence_bundle` keeps its signature and behaviour, gaining an optional prebuilt `index`.
- The `selected` lookup is a dict lookup instead of a full scan.
- Absent input and genuine no-match now report **distinct** messages, so an exhausted iterator is no longer misreported as a finding with no detections.

**Measured** on real capture 46 (batch path, identical bundle ids on both paths):

| lines | findings | per-finding | batch |
|---|---|---|---|
| 2,000 | 660 | 0.31s | 0.03s |
| 8,000 | 2,176 | 4.73s | 0.27s |
| 16,000 | 4,231 | 22.99s | **0.45s** |

**The full 129,833-line capture now completes in 16.2 seconds**, producing 129,832 detections and 29,903 bundles. The same command was previously stopped after more than 20 minutes.

**Behaviour preserved:** the 559-byte fixture still yields `entry_count: 4` with the **same digest** `1a86e9dc41927d9d454daf57a38c77a71116cedf15dc24249a0f61a56638e7bc`.

**On the type contract:** I took the third option — keep `Iterable` and materialize once internally, rather than narrowing to `Sequence`. That accepts a single-shot generator, which is what the declared type already promised, so no caller needed a type update. The comment in my issue listed only narrowing or materializing as if they were alternatives to honesty; materializing *is* the honest implementation of `Iterable`.

**The scaling test asserts on WORK, not wall-clock time** — it counts how many times the inputs are iterated and requires that to be constant in the number of findings. A timing threshold would be flaky and, more importantly, would have passed the wrong fix.

**Gate:** 398 passed / 95.48%, ruff clean, mypy clean (49 files), guard ratchet 0, `data/` untouched.

**Follow-up, not a blocker:** `scripts/build_triage_corpus.py` now uses the batch entry point, so whole-capture corpora are practical. Nothing else called the old per-finding path in a loop.

---

## #32 — The 20-bundle sample is set by argument order, but the preregistration attributes it to the corpus

**State:** OPEN  |  **Opened:** 2026-10-08T13:11:11Z  |  **Closed:** —

## State

`PROPOSED` — confirmed by execution. Pre-data, so this is correctable now and would be a protocol violation to change later.

## Problem

The frozen preregistration defines its primary metric over **the corpus**:

> the unweighted arithmetic mean of `TriageComparison.agreement_score` over exactly one comparison per bundle, **for the 20 bundles of a complete run**

and names the corpus as *"the deterministic, label-free corpus from `aegistrace.triage.corpus.build_corpus`"*.

**Nothing connects the two.** `run_independent_triage` selects its sample by **caller order**, not from the corpus, and no code path reads a `TriageCorpus` to decide which bundles to triage.

```python
ordered_bundles = list(bundles)
selected = ordered_bundles[: budget.max_bundles_per_run]   # caller order, no sort
```

The same pattern appears in `src/aegistrace/spine.py:133`. So the identity of "the 20 bundles of a complete run" is fixed by **argument order at the call site**, while the corpus digest is content-addressed and order-independent.

### Measured

Two corpus builds from the same bundle *set* in different orders give a byte-identical digest, as designed:

```
corpus digest stable across input order? True
```

But the sample the run actually selects is **not** stable:

```
first-20 selected from original order == from shuffled order?  False
overlap: 0/20
corpus first-20 == original-order first-20?  False
corpus first-20 == shuffled first-20?        False
```

**Two runs can share a byte-identical `corpus_digest` while triaging completely disjoint bundle sets** — zero bundles in common. The preregistration's primary metric would then be computed over a sample that "the corpus" does not determine.

### The corpus is a terminal artifact

Verified by grep across `src/` and `scripts/`:

- `build_corpus` is called **only** by `scripts/build_triage_corpus.py`, which uses the result **only to print summary counts** (`entry_count`, `event_count`, `detection_count`).
- `CorpusEntry` is **never read** to select, order, or verify anything.
- `run_independent_triage` takes `bundles: Sequence[EvidenceBundle]`; no caller passes corpus order. Both real call sites (`build_triage_corpus.py`, `spine.py`) build bundles directly from findings order.
- `scripts/run_offline_spine_demo.py` does not use the corpus at all — it constructs **synthetic** bundles (`10.0.0.{n}`).

So the corpus is written, digested, and then **never consulted again**.

## Why this matters

This is the same failure shape as [#13](https://github.com/Lakshmi-Sindhu-P/AegisTrace/issues/13)-[#26](https://github.com/Lakshmi-Sindhu-P/AegisTrace/issues/26) and [#29](https://github.com/Lakshmi-Sindhu-P/AegisTrace/issues/29): **a claimed identity that does not determine what actually happened.** The preregistration asserts the result is attributable to a specific pre-registered corpus. As written, it is attributable to whatever order the caller happened to pass.

`build_corpus`'s own docstring makes the gap sharper, because it goes to some trouble to be order-independent:

> Build a triage corpus whose digest does not depend on input ordering.

That property is real and correct. It is simply not used for anything, because the only consumer of ordering — the run's sample selection — does not consult the corpus.

## Scope, stated honestly

- **No result is invalidated.** The run has never executed, spend is zero, and no `TriageAssessment` or `TriageComparison` exists on disk. This is "the protocol as frozen is not executable as written", not "a published number is wrong".
- **It is correctable now and not later.** The preregistration status is `FROZEN_PRE_DATA`. Fixing the link before any model output is seen is legitimate; changing the sampling rule after would be a protocol violation.
- I checked one plausible-but-wrong candidate on the way here, and it is **not** a defect: `tests/test_preregistration.py` hardcodes `PROVIDER_COMMAND = "uv run python scripts/run_independent_triage.py"`, a path that does not exist. That is a synthetic fixture for the validator, not a claim about the repository; the frozen config names `run_offline_spine_demo.py`, which does exist.

## Design question for the owner

Which end should own the sample? Both are defensible and they differ in what a reader can reproduce:

- **(a) The corpus owns it.** `run_independent_triage` takes a `TriageCorpus` (or the corpus's ordered entry ids) and selects the first `max_bundles_per_run` from it, so the digest fully determines the sample. A reproducer rebuilds the corpus and gets the identical 20. Requires the run to be able to resolve a bundle from a `CorpusEntry`.
- **(b) The caller keeps ownership, and the corpus is explicitly declared a pool, not a sample.** Then the preregistration must say the 20 are the first 20 of a named, reproducible ordering, and the run must record which 20 it used — with the link verifiable after the fact.

My recommendation is **(a)**, because it makes the pre-registered artifact the single thing that determines the sample, which is what the preregistration already claims. **(b)** is cheaper but leaves the sample determined by a call site, and the artifact's digest would still not identify the run's inputs.

## Acceptance criteria

- [ ] the set of bundles a run triages is determined by the corpus, not by argument order
- [ ] two runs over the same corpus triage the same bundles regardless of the order bundles are passed
- [ ] the run records which bundles it used, verifiably linked to the corpus digest
- [ ] `corpus.entries` is either genuinely consumed or its role is stated as a pool rather than a sample
- [ ] a test falsifies the shuffle case: shuffling the bundle argument must not change the selected set
- [ ] the frozen preregistration text matches whatever is decided, changed **before** any model output exists
- [ ] guard ratchet still reports 0 unexecuted guard raises
- [ ] gate green: full suite, ruff, mypy

### Comment — 2026-10-08T13:17:15Z

## The defect is FIXED in `66abd10`. One decision remains open.

**Fixed — the order dependence.** Both call sites now sort by `(str(evidence_bundle_id), str(finding_id))` — the same canonical key `build_corpus` already uses — before slicing the budget:

| check | before | after |
|---|---|---|
| `sorted-bundles[:20] == corpus.entries[:20]` | False | **True** |
| sample identical across shuffles | False (overlap 0/20) | **True (20/20)** |

So the selected sample now depends only on the bundle **set**, and when that set is the corpus's, the run's prefix is exactly `corpus.entries[:max_bundles_per_run]`. No schema, field, or signature change.

**Two existing tests had depended on caller-order selection** — `test_assessment_budget_exhaustion_aborts_rather_than_raises` and `test_bundle_overflow_is_enforced_and_recorded` registered recorded responses only for `bundles[0]`. That is direct evidence the bug was load-bearing, not theoretical. I read the diff to confirm only the response fixtures were widened: `run.aborted`, `calls_made == 2`, `len(run.assessments) == 2` and the abort-reason assertions are all untouched.

**Also confirmed:** no quadratic remains in the corpus pipeline. The full 129,833-line capture now profiles as parse 5.2s / `emit_ml_detections` 2.8s / `aggregate_findings` 2.4s / `build_evidence_bundles` 3.4s / `build_corpus` 0.9s — 14.7s total, no dominant stage. Whole-capture corpora are practical, so the 20-bundle plan is reachable from a real capture rather than only from the 5-line fixture.

## Still open — needs you

**Who owns the sample?** The sort removes the order dependence, but it does not make the corpus formally *determine* the sample:

- **(a) The corpus owns it.** The run takes a `TriageCorpus` and resolves bundles from its entries, so the digest fully determines the 20. A reproducer rebuilds the corpus and gets an identical sample. Requires a way to resolve a bundle from a `CorpusEntry`.
- **(b) The caller keeps ownership, and the corpus is declared a POOL, not a sample.** Cheaper, but the corpus digest still would not identify the run's inputs.

My recommendation remains **(a)**, because the preregistration already attributes the metric to the corpus.

**One acceptance criterion is still unmet:** the run does **not** record the identities of the bundles it selected. Today you can verify the sample by re-deriving the sort, but the run itself carries no record of which bundles it used. Under either option above, that should be recorded so the link is checkable after the fact rather than reconstructed.

This remains correctable only while the preregistration is `FROZEN_PRE_DATA`. Nothing has been sent to any provider and no assessment exists on disk.

---

## #33 — TriageComparison's left/right evidence fields do not track the left/right arguments

**State:** OPEN  |  **Opened:** 2026-10-08T13:26:58Z  |  **Closed:** —

## State

`PROPOSED` — confirmed by execution. Minor: no computed metric is currently wrong, and nothing reads these fields yet. Filed because the fix is cheap and the trap is easy to fall into.

## Problem

`compare_assessments(left, right, ...)` re-orders its arguments by **role** before doing anything:

```python
ordered = sorted((left, right), key=_sort_key)   # canonical role order
first, second = ordered
...
left_only_evidence_ids=tuple(sorted(first_cited - second_cited)),
right_only_evidence_ids=tuple(sorted(second_cited - first_cited)),
```

So the returned `left_only_evidence_ids` describes **`roles[0]`** — always `triage_analyst` — and **not** the argument named `left`.

### Executed

```
A) left=analyst, right=adjudicator   -> left_only = analyst's citation
B) left=adjudicator, right=analyst   -> left_only = analyst's citation   (same)
```

Passing the adjudicator as `left` still returns the analyst's unique evidence in `left_only_evidence_ids`. The output field does not track the parameter of the same name.

### Why the re-ordering itself is right

The canonical ordering is deliberate and correct — it is what makes `comparison_id` order-independent (verified: identical across argument order), so the escalation rate is reproducible rather than dependent on call-site style. **The defect is only that the field names contradict that choice**, and nothing documents the convention:

- The `TriageComparison` docstring says nothing about what left and right mean.
- The two fields carry no description.
- No code reads them yet (verified by grep across `src/` and `scripts/`).

### Why it still matters

The preregistration points a reader at exactly these fields when it defines the primary metric:

> `len(shared_evidence_ids) / (len(shared_evidence_ids) + len(left_only_evidence_ids) + len(right_only_evidence_ids))`

The formula is a symmetric sum, so **the value is unaffected and no metric is wrong**. The risk is interpretive: `left_only_evidence_ids` is the natural field for a follow-up question like *"when the two roles diverge, whose evidence is unique?"* — and the name would answer it wrongly. `roles` is stored alongside and always `(triage_analyst, expert_adjudicator)`, so the information is recoverable, but only by inferring an undocumented convention.

This is the same family as [#32](https://github.com/Lakshmi-Sindhu-P/AegisTrace/issues/32): a stored record whose meaning is not pinned down by the field names, where the reader has to reconstruct the convention from the implementation.

## Proposed fix (for review)

1. **Document the convention on the schema fields** — state that left/right mean the canonically first/second role, not argument order, and that `roles` gives the mapping.
2. **Rename the parameters so they cannot mislead** — e.g. `first: AssessmentOutcome, second: AssessmentOutcome`, letting the function impose the canonical order itself. This is the fix that removes the trap rather than documenting it.
3. **Consider a validator** asserting `roles` is in canonical order whenever `left_only`/`right_only` are non-empty, so the convention cannot silently drift.

I lean to (2) over (1): a name that cannot be misread beats a comment explaining why it can be. But (2) touches a public signature, so it needs a decision rather than a guess.

## Acceptance criteria

- [ ] the meaning of `left_only_evidence_ids` / `right_only_evidence_ids` is determinable from the schema alone
- [ ] no parameter name implies an ordering the implementation does not honour
- [ ] `comparison_id` remains independent of argument order (do not regress this)
- [ ] `agreement_score` remains symmetric (do not regress this)
- [ ] a test pins the convention so it cannot drift
- [ ] guard ratchet still reports 0 unexecuted guard raises
- [ ] gate green: full suite, ruff, mypy

## Not a defect (checked and rejected)

I tested two other candidate defects in this module and both were false alarms, recorded here so they are not re-raised:

- **Mutual abstention producing `agreement=True` with `agreement_score=0.0`.** I predicted this, then found it is impossible: the schema enforces `cited_evidence_ids: Field(min_length=1)`, and direct construction with zero citations is refused (`too_short`). So `agreement=True` requires two identical **non-empty** citation sets, which forces `agreement_score > 0`.
- **`agreement` and `agreement_score` disagreeing.** With identical citations but different categories the result is `agreement=False, agreement_score=1.0`. That is correct and intended: the two fields measure different things — disposition agreement versus citation overlap — and only `agreement_score` feeds the preregistered primary metric.

### Comment — 2026-10-08T13:31:00Z

## Partially fixed in `0da5b44` (+ `4412593`) — documentation and drift protection done, rename open

**Done — the convention is now documented on the schema itself.** `TriageComparison`'s docstring states that `left` means `roles[0]` and `right` means `roles[1]` — canonically the triage analyst then the expert adjudicator — and says explicitly that these names do **not** refer to the parameters of `compare_assessments`. Both fields carry a `description` naming the role they belong to, and the function docstring states that its arguments are not positional in the result.

**Done — the convention is now pinned in both directions.** New `tests/test_comparison_field_semantics.py` (5 tests) fails if anyone:
- makes the fields track argument order, **or**
- makes `comparison_id` or `agreement_score` order-dependent.

That second direction matters more than the first: the canonical re-ordering is the property worth protecting, and a naive "fix" for this issue would break it. The test also asserts the convention is discoverable from the schema alone, so the documentation cannot be silently dropped later.

**Still open — fix (2), the rename.** I named the parameters in the docstring rather than renaming them, because renaming `left`/`right` changes a public signature. As stated in the issue I lean toward the rename: a name that cannot be misread beats a comment explaining why it can be. That needs your decision, not my guess.

### A correction to my own process

While writing the change up I put a **placeholder commit hash** into the `MEMORY.md` row *before* the commit existed. I caught it, read the real hash back after committing, and amended the row to `0da5b44`. Worth noting because the same class of error — recording a claimed identity instead of verifying it — is exactly what this issue is about. The governance record must contain the hash that exists, not the one I expected.

### Gate

```
ruff check .          -> All checks passed
mypy                  -> Success, 49 source files
pytest -q             -> 410 passed, coverage 95.56%   (was 405 / 95.53%)
guard ratchet         -> 0 unexecuted guard raises
agent traces          -> 26 valid, 0 invalid
```

---

## #34 — verify_claim checks evidence kind but never whether the cited reference exists

**State:** OPEN  |  **Opened:** 2026-10-08T13:32:30Z  |  **Closed:** —

## State

`PROPOSED` — confirmed by direct execution. Latent, not live: `verify_claim` is re-exported from `aegistrace.verification` but has **no consumer under `src/`**, so this is a guard that is not yet load-bearing. Filed because it is the guard a future claim-generation path will rely on, and because it is the same defect family as [#32](https://github.com/Lakshmi-Sindhu-P/AegisTrace/issues/32) and [#33](https://github.com/Lakshmi-Sindhu-P/AegisTrace/issues/33).

## Problem

`verify_claim` inspects **only** each `EvidenceReference.kind`. The `reference` string is never read:

```python
def _kinds(references): return {reference.kind for reference in references}

def verify_claim(claim: Claim) -> ClaimVerification:   # no bundle, no context
    kinds = _kinds(claim.evidence_references)
    ...                                                     # every rule tests `kind` only
```

So a claim can cite evidence that **does not exist** and still verify at its declared strong type.

### Executed

| declared type | cited reference | verified | effective type |
|---|---|---|---|
| `MODEL_INFERENCE` | `model_score` → `detection://does-not-exist/999` | **True** | `model_inference` |
| `REFERENCE_BACKED_FACT` | `external` → `https://example.invalid/ghost` | **True** | `reference_backed_fact` |
| `DETERMINISTIC_DERIVATION` | `detection` → `totally made up prose` | **True** | `deterministic_derivation` |

The reason string returned for the first row is:

> `"cited evidence supports the declared category (model_inference)"`

That sentence is about the **evidence**. What was actually established is a statement about the evidence's **kind**. Those are different claims, and the record does not distinguish them.

### The signature makes existence uncheckable

`verify_claim(claim: Claim) -> ClaimVerification` accepts no bundle and no resolution context. So this is not a forgotten comparison — **bundle membership cannot be checked by construction**, because the function is never given anything to check against. Contrast `verification/evidence_assertions.py`, which does resolve paths and reports `UNRESOLVED` and `AMBIGUOUS` as distinct violations; that layer has the resolver and this one does not.

### Why it matters

The stated purpose of the taxonomy is to keep statements pinned to the tier that can carry them, and the module docstring promises that a claim citing evidence which "cannot support its declared category" is downgraded rather than waved through. As executed, that holds for **no evidence** and **wrong-kind evidence**, but not for **evidence that does not exist**. A fabricated identifier is accepted at full strength, and `verified=True` reads as though the evidence were checked.

This is the project's recurring vacuous-verification shape: **the check reports success over a scope it does not cover.**

## What this is NOT

- **Not a regression.** The behaviour is original; no rule ever read `reference`.
- **Not the same as #15.** That issue was about *kind* rules (`OBSERVED_FACT` on a `model_score`) and is closed. This is about whether the reference resolves at all, which no rule addresses.
- **Not a claim that any published result is wrong.** No production path generates claims yet, so nothing downstream has consumed a fabricated reference.

## Design choices flagged, not derived

1. **Where should existence be checked?** Options: (a) add an optional resolution context to `verify_claim` so it can resolve references when given one, and record that it could not when not; (b) keep `verify_claim` purely kind-based but rename the output so it cannot be read as an existence check — e.g. a distinct `kind_admissible` field rather than `verified`; (c) leave it and document the limitation prominently. I lean to (a) plus (b): the current `verified=True` is the part that misleads.
2. **Should `verified` become three-valued?** `kind_admissible` / `resolved` / `unresolved` would let a consumer see the difference without reading prose. That is a schema change to `ClaimVerification`.
3. **`docs/evaluation.md:95`** says the verification layer is evaluated mechanically "for identifier existence". I could not tell whether that means the *layer checks* identifier existence or the *study* checks the layer's outputs; the sentence is ambiguous and sits in a section that describes a planned study. Worth pinning down while touching this, but I am **not** claiming the docs promise a capability the code lacks — the reading is genuinely ambiguous.

## Acceptance criteria

- [ ] a claim whose cited reference does not resolve is not reported as `verified=True` at its declared strong type, **or** the output field no longer reads as though the evidence were checked
- [ ] the distinction between "kind is admissible" and "reference resolved" is visible in the record, not only in prose
- [ ] `verify_claim`'s contract states clearly what it does and does not check
- [ ] controls unchanged (no regression): uncited claim → downgraded; wrong-kind → downgraded; explicit `UNKNOWN_INSUFFICIENT_EVIDENCE` → still verified; `AI_INTERPRETATION` on a `model_score` → still verified
- [ ] the number of references is not treated as evidence: citing more fabricated ids must not verify a claim
- [ ] guard ratchet still reports 0 unexecuted guard raises
- [ ] gate green: full suite, ruff, mypy

## Considered and NOT filed as a defect

An independent audit also flagged that `_DERIVATION_KINDS` includes `event`, so `OBSERVED_FACT` and `DETERMINISTIC_DERIVATION` accept **identical** evidence and declaring the stronger type costs nothing. I traced this and it is **not** a defect: it is the deliberate, reviewed outcome of #15, which chose minimum-kind rules and explicitly flagged the alternative ("make the taxonomy *exclusive* rather than minimum-based. That is a larger change and is not proposed here"). Recorded here so it is not re-raised as new.

### Comment — 2026-10-08T13:35:00Z

## Supporting evidence: the resolution capability already exists in this repo

Digging into the neighbouring layer for this issue turned up something that makes fix option (a) much cheaper than it first looked.

`triage/assessment.py` — the model-output boundary — **already resolves cited ids against the bundle** before admitting an assessment:

```python
cited = payload.get("cited_evidence_ids")
if not isinstance(cited, Sequence) or isinstance(cited, (str, bytes)) or not cited:
    reasons.append("assessment cites no evidence; an uncited assessment is not admissible")
else:
    allowed = bundle_evidence_ids(bundle)
    unknown = sorted(str(item) for item in cited if str(item) not in allowed)
    if unknown:
        reasons.append(f"cited evidence not present in the bundle: {', '.join(unknown)}")
```

That is exactly the check `verify_claim` does not perform. It requires a non-empty citation list **and** that every cited id exists in the bundle, and an uncited or non-existent citation makes the whole payload a `FailedAssessment` rather than an admissible record.

So the project does not lack the ability to resolve evidence references — it has the helper (`bundle_evidence_ids`) and a working implementation of the check one module over. `verify_claim` simply receives no bundle, so it cannot call it. That makes **option (a) — accept an optional resolution context — a wiring change using an existing utility, not new infrastructure.**

It also sharpens the asymmetry worth fixing: in `assessment.py` a citation of a non-existent id is *fatal*; in `claims.py` the same fabricated id is *verified*. Two layers, opposite verdicts on the same kind of input.

## Still open

I have deliberately **not** implemented a fix. The shape of the fix is a real choice:

1. optional resolution context on `verify_claim`, recording when it could not resolve;
2. keep the function kind-only but stop calling the result `verified` — a distinct `kind_admissible` field;
3. document the limitation and leave it.

I lean to (1) **plus** (2). Adding resolution without changing the field name would still leave `verified=True` readable as an evidence check in the case where no context was supplied. Changing the field name is a `ClaimVerification` schema change, which is why this is a decision rather than a patch.

One thing I can confirm needs no decision: `verify_claim` has **no consumer under `src/`** (only a re-export from `verification/__init__.py`), so whichever option is chosen, the blast radius today is the contract itself.

### Comment — 2026-10-08T22:33:13Z

**PARTIAL FIX** — commit `0e0e977`. Acceptance criteria 1 (second branch), 3 and 4 met; **criterion 2 is not**, because it needs your decision.

## What was fixed
The defect was in the **record**, not the check. The success path reported:

> `"cited evidence supports the declared category (model_inference)"`

That sentence is about the **evidence**. What had actually been established is a statement about the evidence's **kind**. So a claim citing a fabricated identifier was reported as though the evidence had been checked.

The success path now states what was established and says explicitly that resolution was not checked. The caveat is added **only** where a claim was accepted on kind — a downgraded claim is already unverified, so the note there would be noise and would blur the distinction you asked to make visible.

## What I confirmed rather than assumed
- Your analysis that existence is uncheckable **by construction** is correct: `verify_claim` takes no bundle and no resolver. Not a forgotten comparison.
- The overstating wording was pinned by **no test** and had **no consumer under `src/`** (only `verification/__init__.py` re-exports it). Verified by grep *before* changing it, so no recorded artifact moved.

## What still needs you — this is the actual decision
Your issue flagged it as a design choice and I agree it is one, because both routes change a public contract:

**Option A — add an optional resolution context to `verify_claim`.** It could then resolve references when given a context, and record that it could not when not. Strongest, but changes a public signature and makes the function's guarantee depend on how it was called.

**Option B — keep `verify_claim` purely kind-based, and make the distinction visible in the schema.** `verified: bool` becomes three-valued — `kind_admissible` / `resolved` / `unresolved` — so a consumer can see the difference without reading prose. Changes `ClaimVerification`.

**Option C — do both.** A + B is what your issue leans toward, and I agree: `verified=True` is the part that misleads, and prose in `reasons` is a weak place to put a guarantee.

**My recommendation: C, implemented as A with `verified` renamed to `kind_admissible` plus a separate `resolution` field defaulting to `unresolved`.** That keeps the existing kind rules untouched, makes the scope visible in the record, and lets a caller that has a resolver upgrade the field honestly. It is a breaking change to `ClaimVerification`, which is exactly why I did not take it unilaterally.

## Also worth pinning down (you raised it, I did not resolve it)
`docs/evaluation.md:95` says the verification layer is evaluated mechanically "for identifier existence". I could not tell whether that means the *layer checks* identifier existence or the *study* checks the layer's outputs — the sentence is ambiguous and sits in a section describing a planned study. **I am not claiming the docs promise a capability the code lacks.** If it means the former, that sentence should change; if the latter, it is accurate.

Gate: 445 passed / 95.63%, ruff clean, mypy clean (49 files), guard ratchet 0.

---

## #35 — triage_id omits severity and cited evidence, so distinct assessments can share an identity

**State:** CLOSED  |  **Opened:** 2026-10-08T13:36:16Z  |  **Closed:** 2026-10-08T22:18:19Z

## State

`PROPOSED` — confirmed by execution. **Latent, not live:** unreachable under the frozen protocol, which runs one assessment per role per bundle. Filed because two fields that drive the headline metric are absent from the record's identity, and because the same family has produced three live defects already ([#32](https://github.com/Lakshmi-Sindhu-P/AegisTrace/issues/32), [#33](https://github.com/Lakshmi-Sindhu-P/AegisTrace/issues/33), [#34](https://github.com/Lakshmi-Sindhu-P/AegisTrace/issues/34)).

## Problem

`triage_id_for` derives an assessment's identity from five fields:

```python
triage_id_for(*, role, evidence_bundle_id, input_snapshot_digest, category, summary) -> UUID
```

`severity` and `cited_evidence_ids` are **not** among them. Both of those fields are load-bearing:

- `severity` is one of only two axes the agreement engine compares for a mismatch (`DisagreementReason.SEVERITY_MISMATCH`);
- `cited_evidence_ids` is the *sole* input to `agreement_score`, which is the preregistration's **primary metric**.

So two records can differ in exactly the fields the experiment measures, and still share an identity.

### Executed

```
A: severity=medium  cites=d9083fb4     A.triage_id = ded7e396-404e-580b-aca7-47a1906b7e1b
B: severity=high    cites=700f0eca     B.triage_id = ded7e396-404e-580b-aca7-47a1906b7e1b

A.triage_id == B.triage_id   ->  True
A.model_dump() == B.model_dump()  ->  False      (the records genuinely differ)
```

The narrowest collision needs only one field to differ — same citations, `severity` `medium` vs `high` — and the ids are still identical.

### The internal inconsistency

Executed on a genuine pair, `severity` is treated as a distinguishing property by the engine:

```
analyst(medium) vs adjudicator(high) -> reasons = ['evidence_divergence', 'severity_mismatch']
```

The engine calls these two records **different**. The identity function calls an assessment with a different severity the **same**. One of those two is wrong, and the identity function is the one that omits a field the taxonomy treats as significant.

### The asymmetry worth noticing

`failed_attempt_id_for` **does** content-address its records, via `raw_digest`:

```python
failed_attempt_id_for(*, role, evidence_bundle_id, input_snapshot_digest, raw_digest)
```

So a *rejected* model response is more uniquely identified than an *admitted* one. Two failures with different raw text get different ids; two successful assessments with different severities do not.

### Consequence if reached

- `subject_triage_id` is the review's **only** link to its subject, and `ReviewHistory` enforces `review.subject_triage_id == history.subject_triage_id`. Two distinct assessments sharing an id make that link ambiguous — a review could be recorded against the wrong record.
- `compare_assessments` keys its "cannot compare an assessment with itself" guard on this same identifier.
- `TriageRun` has no uniqueness validator (only `validate_abort_reason`), so duplicate assessment ids are storable without complaint.

## Reachability, stated honestly

Under the frozen preregistration's `max_retries_per_assessment: 1` and one assessment per role per bundle, at most one *successful* assessment exists per `(role, bundle)`, and `role` is in the identity. **I could not construct a live collision through the frozen path.** The exposure is:

- any future retry policy that keeps a second successful assessment for the same role;
- any path that compares two same-role assessments (already refused, but for the wrong stated reason);
- a reviewer keyed by `subject_triage_id` when the underlying assessment is regenerated with a changed severity.

The narrow reading is that this is a **documented** choice — the docstring does say identity comes from those five fields. The finding is that the choice is inconsistent with how `severity` is used two modules away, not that it is undocumented.

## Design choices flagged, not derived

1. **Should `severity` join the identity?** It is a decision axis, so I think yes. This changes every `triage_id`, so it must land **before** any run produces assessments — the same reasoning that justified fixing #26 and #32 before the frozen A/B.
2. **Should the full record be content-addressed?** Including `cited_evidence_ids` (and the raw response digest, matching `failed_attempt_id_for`) would make the identity unforgeable, at the cost of no longer identifying a "slot".
3. **Or declare the identity a *slot* rather than a *record* identity**, and rename/document it as such — then the retry question becomes explicit rather than accidental.

Option 1 is the minimal consistency fix. Option 3 is the honest relabelling if the current behaviour is wanted. I have not implemented any of them, because 1 changes every id and 3 changes the contract's meaning.

## Acceptance criteria

- [ ] either `severity` participates in the assessment identity, or the identity is documented and named as a slot identity rather than a record identity
- [ ] two assessments whose `model_dump()` differs are distinguishable by identity, or the reason they are not is stated in the contract
- [ ] `TriageRun` either rejects duplicate assessment ids or documents that duplicates are meaningful
- [ ] admitted assessments are at least as uniquely identified as failed attempts
- [ ] no regression: one assessment per role per bundle keeps its existing id under whichever option is chosen, or the change is made before any run produces assessments
- [ ] guard ratchet still reports 0 unexecuted guard raises
- [ ] gate green: full suite, ruff, mypy

### Comment — 2026-10-08T13:36:32Z

## Cost of fixing this is low — checked

I looked for anything that would make a change to `triage_id_for` expensive, before asking for a decision on it:

- **no golden ids are pinned anywhere** — a scan of `tests/` for hardcoded UUID literals outside `uuid4()` returns nothing;
- **no test asserts a `triage_id` value** — nothing matches `triage_id ==` or calls `triage_id_for(...)` directly;
- **nothing is keyed by `triage_id`** under `src/`. Its only consumers are `assessment.py:113` (the producer), `agreement.py:38` and `:141` (where it becomes the comparison's `assessment_ids`), and `review/history.py:25` (the subject-match check).

So option 1 (include `severity`) is a one-line change plus tests, with no golden values to rewrite. The cost is not the change — it is the **timing**: it must land before any run produces assessments, which is exactly the situation now. Nothing has been sent to any provider, spend is zero, and no assessment exists on disk.

I am still not implementing it unilaterally, because the underlying question — is `triage_id` a *record* identity or a *slot* identity? — is a contract decision, and the two answers lead to different code:

- **record identity** → add `severity` (and arguably the citations and the raw response digest, matching `failed_attempt_id_for`);
- **slot identity** → keep the current inputs, but rename and document it as a slot, so the retry behaviour is explicit instead of accidental.

Answering "slot" would also mean `TriageRun` needs to say what happens when two assessments occupy one slot.

### Comment — 2026-10-08T22:18:18Z

**RESOLVED** by the identity rule, commit `0e026ab`.

## The rule
`docs/identity_rule.md`: *an identifier is a versioned content address over exactly the fields that constitute the entity's identity — and over nothing else.*

`triage_id_for` omitted `severity` and `cited_evidence_ids`, although the agreement engine already reports `severity_mismatch` and `evidence_divergence` — so it treated as identity-bearing exactly the differences the id ignored. Two assessments differing in severity AND citations produced an identical id (`ded7e396-404e-580b-aca7-47a1906b7e1b`) while their `model_dump()` differed.

The strongest evidence this was an oversight rather than a design: `failed_attempt_id_for` IS content-addressed over `raw_digest`, so a **rejected** assessment was more uniquely identified than an **admitted** one.

## Change
`triage_id_for` now hashes `(role, evidence_bundle_id, input_snapshot_digest, category, summary, severity, sorted(cited_evidence_ids))`. Namespace `triage-assessments/v2`; v1 retained through `triage_id_v1_for`.

`input_snapshot_digest` is deliberately RETAINED: it pins the exact assessor input, which is what mutual blindness depends on.

Citations are sorted, so an assessor's listing order cannot change its identity — that order is not a property of the finding.

## Verification
- Distinctness: severity, citations, category and summary each move the id.
- Stability: identical input gives an identical id.
- Citation order is not identity-bearing.
- An admitted assessment is now at least as well identified as a rejected one.

Gate: 433 passed / 95.62%, ruff clean, mypy clean (49 files), guard ratchet 0.

---

## #36 — SNAPSHOT_FIELDS is derived from EvidenceBundle, so the snapshot allowlist guard cannot fail

**State:** CLOSED  |  **Opened:** 2026-10-08T13:39:58Z  |  **Closed:** 2026-10-08T22:18:44Z

## State

`PROPOSED` — confirmed by execution. The affected guard is in the layer this project calls its **experimental variable**: what the two mutually blind assessors are permitted to see.

## Problem

`SNAPSHOT_FIELDS` exists so a test can pin the set of fields an assessor may observe. Its own comment states the purpose:

```python
#: The complete set of keys an assessor may observe. Kept explicit so a test can assert that the
#: snapshot contains nothing beyond the evidence bundle itself.
SNAPSHOT_FIELDS: frozenset[str] = frozenset(EvidenceBundle.model_fields)
```

It is not explicit. It is **derived from the very thing it is supposed to constrain**, and `input_snapshot` is itself just the model dump:

```python
def input_snapshot(bundle): return bundle.model_dump(mode="json")
```

So the two assertions that are meant to enforce the invariant reduce to tautologies:

| assertion | reduces to |
|---|---|
| `set(snapshot) == set(EvidenceBundle.model_fields)` | `set(model_dump()) == set(model_fields)` — true for any pydantic model |
| `frozenset(EvidenceBundle.model_fields) == SNAPSHOT_FIELDS` | `X == X` — `SNAPSHOT_FIELDS` **is** `frozenset(EvidenceBundle.model_fields)` |

Adding a field to `EvidenceBundle` moves **both** sides of both assertions together. Neither can fail for the case the guard exists to catch.

### Executed

I added one field to the bundle and evaluated every assertion in `tests/test_snapshot_leakage.py`:

```
PASSES  test_snapshot_keys_are_exactly_the_evidence_bundle_fields : set(snapshot)==set(SNAPSHOT_FIELDS)
PASSES    ...its second assert                                  : set(snapshot)==set(model_fields)
PASSES  test_ground_truth_label_stops_at_the_bundle_boundary    : 'SENTINEL-LABEL-BOTNET-C2' absent
PASSES  test_raw_payload_reference_and_paths...                 : 'raw_payload_reference' absent
PASSES                                                          : '.binetflow' absent
PASSES  test_scenario_identity_and_label_field_names...         : 'scenario_id' absent
PASSES                                                          : 'source_label' absent

...and yet the new field SHIPS to BOTH assessors:
  leaked key: 'curator_notes' -> value: 'internal SOC context: see ticket 4417'
  present in the canonical snapshot text? True
```

A full test run reports green while internal SOC context reaches both providers.

## What this is NOT — the existing suite is genuinely good

I want to be precise, because `tests/test_snapshot_leakage.py` is one of the strongest files in the repository and it explicitly documents having caught a previous vacuity:

> "The first version of this file asserted absence directly and was caught being vacuous: the label was already dropped before the bundle, so absence proved nothing."

Its sentinel construction and its `LABEL_SENTINEL in raw` pre-check are correct and I am not impugning them. **The known leak vectors — the research label, the on-disk path, the scenario id — are well covered by value sentinels and by specific field-name string checks.**

The gap is narrower and specific: **the *general* allowlist invariant is not enforced.** A new field escapes if it is (a) not named one of the four pinned strings (`scenario_id`, `source_label`, `raw_payload_reference`, `.binetflow`) and (b) does not carry a sentinel value. `curator_notes` is exactly that, and it is a plausible field to add.

So the correct reading is not "leakage is unguarded" but "**the enumerated leak vectors are guarded; the invariant they are proxies for is not.**" The next person to add a bundle field gets no signal.

## Proposed fix

Make `SNAPSHOT_FIELDS` the literal it claims to be:

```python
SNAPSHOT_FIELDS: frozenset[str] = frozenset({
    "schema_version", "evidence_bundle_id", "bundle_version", "finding_id",
    "detection_ids", "event_summaries", "observed_values", "score_references",
    "feature_versions", "external_findings", "missing_context", "limitations", "created_at",
})
```

With that, adding a field to `EvidenceBundle` fails `set(snapshot) == set(SNAPSHOT_FIELDS)` until someone consciously admits it to the allowlist — which is the documented intent, and turns the guard from a restatement of pydantic's behaviour into a decision point.

I believe this one is unambiguous enough to implement without a design decision: `input_snapshot` does not read the constant, so there is **no runtime behaviour change**; the only consumer is a test; and the resulting test passes today because the constant and the schema currently agree. I will implement it and record the gate here, unless told otherwise.

## Acceptance criteria

- [ ] `SNAPSHOT_FIELDS` is a literal, not a projection of `EvidenceBundle.model_fields`
- [ ] adding a field to `EvidenceBundle` fails at least one test until the allowlist is consciously updated
- [ ] the failing test names the offending field so the fix is obvious
- [ ] no runtime behaviour change: `input_snapshot` and `snapshot_digest` are untouched
- [ ] the existing sentinel and field-name assertions are preserved unchanged
- [ ] a regression test pins the guard by proving it can fail (not merely that it passes)
- [ ] guard ratchet still reports 0 unexecuted guard raises
- [ ] gate green: full suite, ruff, mypy

### Comment — 2026-10-08T22:18:43Z

**RESOLVED** — commit `e7605be` (previous round). Closing it now; it was fixed and verified but the issue was left open, which is itself a bookkeeping defect worth correcting rather than leaving as drift.

## The defect
`SNAPSHOT_FIELDS` existed so a test could pin what the two blind assessors may see — its own comment said so — but it was DEFINED as `frozenset(EvidenceBundle.model_fields)` while `input_snapshot` IS `bundle.model_dump(mode="json")`. Both sides of every assertion therefore moved together, and the second assertion was literally `X == X`.

**Demonstrated, not argued.** Widening a bundle with `curator_notes = "internal SOC context: see ticket 4417"` left all seven assertions in `tests/test_snapshot_leakage.py` passing while the note reached the snapshot.

## Fix
`SNAPSHOT_FIELDS` is now a literal 13-name frozenset. A new field on `EvidenceBundle` fails the guard until a human consciously admits it.

## Verification
Two tests added: `test_the_allowlist_guard_can_actually_fail` asserts the guard FIRES on a widened bundle, and `test_snapshot_fields_is_a_literal_not_a_projection` pins that the constant is not derived. The latter was added because asserting a guard fires is not enough — a guard derived from the thing it guards can be made to fire in a way that proves nothing.

## Honest scope
No runtime behaviour change: `input_snapshot` and `snapshot_digest` never read the constant, and its only consumer is a test. The gap was NARROWER than "leakage is unguarded" — the known vectors (label, path, scenario) were well covered by sentinel values; the general allowlist invariant they proxied for was not. The residual — that the known vectors are still covered only by sentinels and four pinned strings, and that network addresses still reach the snapshot deliberately — is recorded in `MEMORY.md`.

The lesson this produced is now a named class in this project: a guard that cannot fail. That class has since been recorded eleven times, and it is what `docs/identity_rule.md` and the `#35`/`#38`/`#40` work were built to stop repeating.

---

## #37 — Empty-but-valid ingestion input reports a clean success over zero rows (both parsers)

**State:** CLOSED  |  **Opened:** 2026-10-08T13:45:34Z  |  **Closed:** 2026-10-09T03:23:54Z

## State

`PROPOSED` — confirmed by execution against both parsers.

## Problem

A structurally **valid** input file containing **zero data rows** is accepted as a complete, clean success: `rows_seen=0 accepted=0 rejected=0 issues=0`, no refusal, and the CLI exits 0 having written a manifest claiming `record_count=0`.

The parsers correctly refuse a file that is *completely* empty or has no recognisable header. The gap is precisely **valid-structure-but-no-data**: the header proves the file is the right thing, so the parser reports success over an empty scope.

Executed, using each fixture's own real header:

```
CTU13 valid header + 0 data rows:
  rows_seen=0 accepted=0 rejected=0 issues=0
  >>> CLEAN PASS over nothing? True

IoT23 headers only:
  rows_seen=0 accepted=0 rejected=0 issues=0
  >>> CLEAN PASS over nothing? True
```

For contrast, a truly empty file **is** refused (`issues=1`), so the two cases are already distinguished in the code — the distinction is just not applied to "header valid, nothing after it".

Note on method: my first attempt at this probe used a header I typed from memory, which had an extra `DstBytes` column. The parser correctly flagged it `malformed_row` / `unexpected CTU-13 header`, which *looked* like it refuted the finding. It did not — it proved the parser validates headers properly. Re-run with the fixture's actual header (15 columns, ending `SrcBytes,Label`) gives the clean pass above. Recording this because a wrong instrument nearly buried a real defect.

## Why it matters

This is the same family as the recurring **vacuous verification** class in this project: a check reporting success over a scope it does not actually cover. Here the scope is a whole ingestion run.

Downstream consequences, all silent:
- a manifest is written with `record_count=0` and no error;
- the run exits 0, so any pipeline or scheduled job treats an empty capture as a finished one;
- a truncated download, a failed extraction that left the header, or a mis-pointed path produce **no signal** — the run simply appears to have produced nothing to analyze, which is indistinguishable from a capture that genuinely contained no flows.

For a project whose central claim is evidence-grounded defensibility, "we ingested nothing and said nothing" is the wrong default. An ingest that accepts zero records should refuse, or at minimum record an issue.

## Proposed fix

Treat "valid structure, zero data rows" as a refusal, not a success — e.g. an `empty_input` issue alongside the existing `malformed_row` handling, raised when the header is recognised but no data row follows it. Both parsers need it.

I am **not** implementing this unprompted: whether zero-row ingestion should be a hard refusal (raise) or a recorded issue that still permits an empty result is a contract decision with downstream effects on the CLI exit code and the manifest. Filing for the owner's call.

## Acceptance criteria

- [ ] a valid header followed by zero data rows produces a non-empty `issues` for both `parse_ctu13_binetflow` and `parse_iot23_conn_log`
- [ ] `accepted_rows + rejected_rows == rows_seen` still holds, or the deviation is deliberate and documented
- [ ] the CLI does not exit 0 with `record_count=0` without surfacing the condition
- [ ] a regression test pins the zero-row case for both parsers
- [ ] a genuinely empty file stays refused as it is today
- [ ] gate green

## Related

- `#39` — `rejected_rows` over-counts the header issue. Same reporting surface; both should be settled together.

### Comment — 2026-10-09T03:23:54Z

**DONE** — implemented and committed as `e2ba0e7`. Owner decision recorded in `docs/pending_decisions.md`.

## Owner decision (verbatim)

> "Approve Option 1. Zero accepted ingestion records must produce a non-zero exit code, whether the source is empty or all rows are rejected. Preserve diagnostics and rejection reasons. Distinguish this from successful ingestion followed by zero detections or filter matches. Add regression tests. For both changes, verify downstream effects, document contract changes, and preserve frozen research artifacts and historical results."

## Problem -> cause

Both CLIs ended with the identical expression:

```python
return 2 if args.fail_on_rejects and result.report.rejected_rows else 0
```

An empty-but-valid source (header parses, no row rejected, nothing ingested) therefore exited `0`
and was indistinguishable from a completed ingest. The report said `(rows_seen, accepted_rows,
rejected_rows) == (0, 0, 0)` and the process said "success".

## Change

The rule now lives in **one** place — `ingestion.ingestion_exit_reason` / `ingestion_exit_code` in
`src/aegistrace/ingestion/report.py` — and both adapters call it.

That single-definition choice is deliberate, not stylistic: in the immediately preceding commit a
*duplicated* guard carrying a *duplicated* error message made a falsification test vacuous (the test
named one guard, the other raised instead, and deleting the named guard changed nothing). Two CLIs
restating the same rule is the same shape of hazard, so it is structurally prevented rather than
merely checked.

| Case | Before | After |
|---|---|---|
| Empty-but-valid source (0 rows seen) | exit 0 | **exit non-zero**, reason on stderr |
| All rows rejected | exit 0 unless `--fail-on-rejects` | **exit non-zero** regardless of the flag |
| Some accepted, some rejected, no flag | exit 0 | exit 0 (unchanged — a normal, reportable outcome) |
| Some accepted, some rejected, `--fail-on-rejects` | exit 2 | exit 2 (unchanged) |
| Normal ingest | exit 0 | exit 0 (unchanged) |

The zero-accept refusal is **not** gated on `--fail-on-rejects`: no flag should be needed to notice
that nothing was ingested.

**Diagnostics preserved.** The reason is printed to stderr while stdout keeps its existing
machine-readable JSON shape, so no consumer of that summary breaks. The run still writes
`quality_report.json` (carrying the rejection reasons) and `dataset_manifest.json` before exiting
non-zero.

**The carve-out is asserted, not assumed.** The owner explicitly distinguished this from "successful
ingestion followed by zero detections or filter matches". A run that accepted some rows and rejected
others is a *successful* ingest and still exits 0 without the flag; that boundary has its own test,
because a fix that fired on any rejection would be a different and unwanted behaviour.

## Proof

Six new tests across both adapters plus a unit test that the rule has one definition. Each was
mutation-tested on a pristine `/tmp` copy with a verified GREEN baseline, one mutation at a time:

| Mutation | Result |
|---|---|
| Zero-accept branch disabled (old behaviour restored) | tests **FAIL** — caught |
| Rule gated on `--fail-on-rejects` | test **FAILS** — caught |
| Rule fires on any rejection | boundary test **FAILS** — caught |

Verified by execution across all five cases above.

## Downstream effects / contract changes

- The CLI **exit-code contract** changes for the zero-accept case only. Documented in the
  `ingestion_exit_reason` docstring and in this comment.
- No schema, report field, or artifact changed. `rejected_rows` semantics are untouched.
- No frozen research artifact, historical result, or published metric is affected; ingestion outputs
  for real datasets are unchanged because those accept rows.

Gate: 473 passed, 95.82%, ruff clean, mypy clean, guard ratchet 0, all seven governance validators PASS.

---

## #38 — event_id_for ignores row content and raw_checksum, so distinct records collide

**State:** CLOSED  |  **Opened:** 2026-10-08T13:45:35Z  |  **Closed:** 2026-10-08T22:18:15Z

## State

`PROPOSED` — confirmed by execution.

## Problem

CTU-13 event identity does not depend on the record it identifies. `event_id_for` derives the id from five fields only:

```python
identity = json.dumps([source.source_type.value, source.source_dataset, source.scenario_id,
                       source.dataset_version, source.source_event_id], ...)
```

and `source_event_id` is **per-file line numbering**:

```python
source_event_id = f"line-{line_number}"      # ctu13.py:239
```

`SourceRecordRef` carries a `raw_checksum` field, and `event_id_for` **ignores it**. It also ignores every row field.

### Executed

Two genuinely different records — different protocol, label, byte count, addresses and file — at the same line number in the same scenario:

```
A: tcp malicious 1000B  fileA -> 465820a4-d6c9-50fd-86ba-0c20a2a34015
B: udp benign  123456B  fileB -> 465820a4-d6c9-50fd-86ba-0c20a2a34015
COLLIDE = True    records differ = True
```

Because `source_event_id` is `line-N` and not qualified by the source file, ingesting two different binetflow files for the same scenario collapses their line-1 records (and every matching line number) onto one identity.

## Why it matters

`event_id` is the **root of the entire identity chain**:

```
event_id -> detection_id -> finding_id -> evidence_bundle_id -> triage_id -> review_id
```

Every downstream id is derived from this one. A collision here is not a local dedup annoyance; it means two distinct observations are treated as one piece of evidence throughout the spine, and a `TriageAssessment` cannot cite one of them independently of the other.

This is the third instance of one pattern, and it is worth naming: **an identity that does not depend on the content it labels.**
- `#35` — `triage_id_for` omits `severity` and `cited_evidence_ids`
- `#40` — `review_id_for` omits `final_disposition`, `tier`, `notes`, `subject_role`
- this issue — `event_id_for` omits the row and the file checksum

The ids are content-addresses in name only; they are *slot* addresses. `#35` is the shallowest and this is the deepest.

Note the asymmetry that makes this worth fixing rather than tolerating: `SourceRecordRef` **already carries** `raw_checksum`, and ingestion **already computes** it (`IngestionReport.raw_checksum` exists). The material needed to make the identity content-bearing is present and unused.

## Proposed fix

Include a per-file qualifier in the identity — at minimum the `raw_checksum` that is already on `SourceRecordRef` — so that `line-N` is unique within a file rather than within a scenario. Fragments: `event_id_for` signature, whether row content should participate at all, and migration of any persisted ids.

The one design question I would want answered before touching it: **is repeatable-across-re-ingestion the only property required, or is "distinct rows get distinct ids" also required?** The current docstring claims only the former ("repeatable event ID solely from stable source identity"). Both are satisfied by adding the checksum. I have not changed it.

## Acceptance criteria

- [ ] two distinct source records in the same scenario cannot share an `event_id`
- [ ] re-ingesting the *same* file still yields identical `event_id`s (the documented property is preserved)
- [ ] the identity uses material already present on `SourceRecordRef` rather than new plumbing
- [ ] a regression test pins the two-file collision case
- [ ] the docstring states precisely which property is guaranteed
- [ ] gate green

## Related

- `#35`, `#40` — the same identity family.
- All three should be settled **before** the frozen A/B runs, since the corpus is built from these ids.

### Comment — 2026-10-08T22:18:14Z

**RESOLVED** by the identity rule, commit `0e026ab`.

## The rule
`docs/identity_rule.md`: *an identifier is a versioned content address over exactly the fields that constitute the entity's identity — and over nothing else.*

This issue was one of three reports of a single defect. `event_id_for` hashed arrival bookkeeping (`source_event_id` = `line-N`, numbered per file) and omitted content (`raw_checksum`). Two different files of one scenario therefore collided on every matching line.

## Change
`event_id_for` now hashes `(source_type, source_dataset, scenario_id, dataset_version, source_event_id, raw_checksum)`. `SourceRecordRef.raw_checksum` already existed and was already populated at both ingestion call sites, so no new plumbing was needed. Namespace `events/v2`; `events/v1` retained and reachable through `event_id_v1_for`.

## Verification
- Distinctness: two files, same line number, different content → different ids. The v1 helpers still collide, asserting the defect was real rather than assumed.
- **Did the values change, or only the ids?** Checked, because a green suite cannot distinguish them. With the v1 helpers patched into BOTH the parser and the schema validator, all three pinned issue-22 golden digests reproduce exactly (`48435f1e4ad4` / `7411b8bf8cb3` / `7c8a256bc0af`), and the id-free value multisets are byte-identical between v1 and v2.
- The issue-22 digest covered `(event_id, values)` pairs, so it moved with the id scheme and was not testing the property its name claimed. It now also asserts an id-free value digest.
- `SecurityEvent.validate_evidence_identity` already ENFORCED `event_id == event_id_for(source)`. This is why patching only the parser's binding could not forge ids during the investigation — genuine enforcement by construction.

## Frozen research
Untouched: no digest value is pinned anywhere, the Phase-3 artifacts contain zero uuid-shaped ids, and the preregistration is `FROZEN_PRE_DATA` with spend 0.

Gate: 433 passed / 95.62%, ruff clean, mypy clean (49 files), guard ratchet 0.

---

## #39 — rejected_rows counts the header issue, so accepted+rejected != rows_seen

**State:** CLOSED  |  **Opened:** 2026-10-08T13:45:36Z  |  **Closed:** 2026-10-08T22:18:32Z

## State

`PROPOSED` — confirmed by execution. Minor, low severity, but it is a counter that can be read as authoritative.

## Problem

`rejected_rows` counts the header's own issue as a rejected data row, so the natural invariant `accepted_rows + rejected_rows == rows_seen` does not hold when the header is malformed.

### Executed

A CTU-13 file with an invalid header and two data rows:

```
rows_seen=2  accepted=0  rejected=3
accepted + rejected = 3  !=  rows_seen = 2
```

The extra rejection is the header issue itself, which carries `line_number=1` while `rows_seen` counts only data rows. Confirmed in the header-only case too: a *valid* header with no data rows gives `rows_seen=0 rejected=0`, while a *malformed* header with no data rows gives `rows_seen=0 rejected=1`.

So `rejected_rows` is really "rejections plus structural complaints", while `rows_seen` is "data rows".

## Why it matters

Low on its own — a malformed header is already surfaced as an issue, so nothing is hidden. It matters because these counters are the summary a reviewer reads to judge whether an ingest was clean, and a reader who checks the arithmetic finds it does not add up. Any downstream consumer that trusts `accepted + rejected == rows_seen` (accounting, completeness checks, run-to-run diffing) is subtly wrong on exactly the runs that are already unhealthy.

Filing it separately from `#37` because the root cause is different: `#37` is a success reported over an empty scope; this is a miscount in a populated report.

## Proposed fix

Either count header issues in a separate `structural_issues` field, or exclude them from `rejected_rows`. Which one is right depends on what consumers mean by "rejected row", so I am filing rather than choosing.

## Acceptance criteria

- [ ] `accepted_rows + rejected_rows == rows_seen` holds, or the report documents why it cannot
- [ ] structural/header problems remain visible somewhere in the report
- [ ] a regression test pins the malformed-header arithmetic
- [ ] gate green

## Related

- `#37` — the same reporting surface; settle both together.

### Comment — 2026-10-08T22:18:31Z

**CLOSED — the issue was MIS-FRAMED by me, and no defect exists.** Commit `d8d8b00`.

I filed this as an arithmetic over-count ("`accepted_rows + rejected_rows` can exceed `rows_seen`"). That is a true observation about the numbers, but it is not a bug, and my title asserted a defect that does not exist. Recording the correction rather than quietly closing it.

**What is actually the case.** `rejected_rows` is defined as the number of recorded **issues**, not the number of rejected **data rows**. The contract is deliberate and pinned:

- `tests/test_ctu13_ingestion.py::test_invalid_header_and_missing_label_are_rejected` asserts `rejected_rows == 2` for one invalid header plus one data row. A header is not a data row, so under the "rejected data rows" reading the answer would be 1 and the pinned test would fail.
- The CLI depends on it: `return 2 if args.fail_on_rejects and result.report.rejected_rows else 0`. A malformed header **must** count here or `--fail-on-rejects` would exit 0 on an unusable file.

So `accepted_rows + rejected_rows != rows_seen` is the intended behaviour of a field whose name suggests otherwise. The name is the problem, not the arithmetic.

**Change made.** Behaviour is unchanged. The field now carries documentation stating what it counts, that it duplicates `len(issues)`, that the sum may legitimately exceed `rows_seen`, and that renaming it would be a breaking change. Two tests pin both halves: the contract (`rejected_rows == len(issues) == 2` for the malformed-header case, with `rows_seen == 1`) and the self-consistency that DOES hold whenever no structural problem is reported (`(0, 0, 0)` for a header-only file).

**Still open and genuinely yours to decide** (Issue #37, which I deliberately did not touch): whether a malformed header should move out of `rejected_rows` into a separate `structural_issues` field. That changes the CLI exit contract and the manifest, so it is Category B and needs your approval. The alternatives are analysed in `docs/identity_decision_register.md`.

Lesson recorded in `MEMORY.md`: I filed a defect without first checking whether the behaviour was a pinned contract. The measuring instrument — my reading of the field name — was wrong, not the code. This is the ninth time in this project that the instrument rather than the implementation was at fault.

---

## #40 — review_id_for ignores final_disposition and subject_role, so distinct human judgments collide

**State:** CLOSED  |  **Opened:** 2026-10-08T13:45:37Z  |  **Closed:** 2026-10-08T22:18:17Z

## State

`PROPOSED` — confirmed by execution. Second member of the identity family (`#35`, `#38`).

## Problem

`review_id_for` derives a review's identity from four inputs:

```python
def review_id_for(*, subject_triage_id, reviewer_ref, decision, reviewed_at) -> UUID:
```

The `HumanReview` schema has eleven content fields. The identity ignores, among others, **`final_disposition`, `tier`, `notes`, `subject_role`, and `supersedes_review_id`**.

### Executed

Four reviews that differ *only* in an identity-ignored field:

```
A disposition='confirmed'                      id=43dcd757-aa09-5982-b411-91f491d2bd34
B disposition='COMPLETELY DIFFERENT DISPOSITION' id=43dcd757-aa09-5982-b411-91f491d2bd34  COLLIDE=True
C tier='tier_d_insufficient_evidence'          id=43dcd757-aa09-5982-b411-91f491d2bd34  COLLIDE=True
D notes='a totally different note'             id=43dcd757-aa09-5982-b411-91f491d2bd34  COLLIDE=True
records genuinely differ: True
```

Because `ReviewHistory` rejects duplicate ids, this is not merely a confusing hash — it makes **two distinct dispositions at the same instant unrepresentable**. `append_review` refuses the second with `"a review with this identity is already recorded"`, so a reviewer who changes their disposition within the same timestamp cannot record that change as a new history entry, which is precisely what the append-only history exists to allow.

The ignored `final_disposition` and `subject_role` fields are the most consequential: `final_disposition` is the review's actual conclusion, and `subject_role` says **which of the two mutually blind roles** is being reviewed. A review of the analyst's assessment and a review of the adjudicator's assessment, same reviewer, same decision, same time, are one identity.

## Why it matters

`review_id` is the anchor of the human-judgment record — the audit trail of who decided what about which conclusion. Two logically distinct human judgments collapsing to one identity undermines exactly the layer the project relies on to show that a human, not a model, made the call.

This is the same pattern as `#35` and `#38`: **an identity that does not depend on the content it identifies.** `#35` costs a collision among machine assessments; this one costs a collision among human dispositions, so it is worse — the machine layer can be re-run, but a lost human judgment is a lost judgment.

Note the naming trap: `decision` (CONFIRM/REVISE/ESCALATE) *is* in the identity while `final_disposition` (what was actually concluded) is not. The identity covers the *shape* of the judgment, not its *substance*.

## Proposed fix

Include `final_disposition` and `subject_role` at minimum, and consider `tier` and `supersedes_review_id`. `notes` is a judgement call — including free text in an identity makes it a fragile content address, which may not be wanted.

Two decisions I will not make unilaterally:
1. which fields are identity-bearing;
2. whether `reviewed_at` should be in the identity at all, given that including it is what makes same-instant distinct dispositions collide. Dropping the timestamp in favour of a content hash of the conclusion may be the cleaner contract.

## Acceptance criteria

- [ ] two reviews differing only in their conclusion cannot share a `review_id`
- [ ] `subject_role` participates, so the two blind roles cannot collide
- [ ] `append_review` no longer refuses a genuine, distinct disposition as a duplicate
- [ ] the chosen identity fields are documented on `review_id_for`
- [ ] a regression test pins the same-instant distinct-disposition case
- [ ] gate green

## Related

- `#35`, `#38` — the same identity family. All three should be settled before the frozen A/B runs.

### Comment — 2026-10-08T22:18:16Z

**RESOLVED** by the identity rule, commit `0e026ab`.

## The rule
`docs/identity_rule.md`: *an identifier is a versioned content address over exactly the fields that constitute the entity's identity — and over nothing else.*

`review_id_for` hashed `(subject_triage_id, reviewer_ref, decision, reviewed_at)`. It omitted the substance of the judgment (`subject_role`, `final_disposition`, `supersedes_review_id`) and included the recording clock. Four reviews differing only in disposition, tier and notes all produced `43dcd757-aa09-5982-b411-91f491d2bd34`, and two distinct dispositions sharing a timestamp were unrepresentable.

## Change
`review_id_for` now hashes `(subject_triage_id, subject_role, reviewer_ref, decision, final_disposition, supersedes_review_id)`. `reviewed_at` is REMOVED: it records *when* a judgment was written down, not *what* it was. Namespace `reviews/v2`; `reviews/v1` retained and reachable through `review_id_v1_for`. A separate v1 function exists rather than a `version=` flag so a v2 call cannot silently omit a defining field.

Excluded as derived or free text: `tier`, `escalation_state`, `notes`.

## Verification
- Distinctness: changed disposition, changed role, and a different superseded review each change the id.
- Duplicate handling, both directions: a changed mind in the same instant is now recordable as a correction, while a genuine duplicate is still refused.
- `validate_review_coherence` still refuses an id that does not match the record's own fields.
- v1 ids remain reproducible for historical records.

Gate: 433 passed / 95.62%, ruff clean, mypy clean (49 files), guard ratchet 0.

---

## #41 — Dead guard: the FAILED_ASSESSMENT branch in classify_tier is unreachable

**State:** CLOSED  |  **Opened:** 2026-10-08T13:45:38Z  |  **Closed:** 2026-10-08T22:18:34Z

## State

`PROPOSED` — confirmed by reading and by execution.

## Problem

`classify_tier` contains this branch:

```python
elif DisagreementReason.FAILED_ASSESSMENT in comparison.disagreement_reasons:
    tier = ReviewTier.C_EXPERT_JUDGMENT
    reasons.append("an assessor failed, so any conclusion rests on incomplete input")
```

It is **unreachable**. Two branches above it always consume the case:

```python
if abstained:                      ...
elif not admissible:               ...   # line 106
elif len(admissible) == 1:         ...   # line 109
elif DisagreementReason.FAILED_ASSESSMENT in ...:   # line 114  <- dead
```

The reason is in `agreement.py`:

```python
failed = isinstance(first, FailedAssessment) or isinstance(second, FailedAssessment)
if failed:
    reasons.add(DisagreementReason.FAILED_ASSESSMENT)
```

`FAILED_ASSESSMENT` is added **if and only if** at least one side is a `FailedAssessment`, and a failed assessment is never admissible. So whenever `FAILED_ASSESSMENT` is present:
- one side failed → `len(admissible) == 1` → line 109 fires first;
- both sides failed → `admissible` is empty → `not admissible` fires first at line 106.

Reaching line 114 requires `len(admissible) >= 2`, which requires no failed side, which means `FAILED_ASSESSMENT` cannot be in the reasons. Verified by execution: a comparison whose `disagreement_reasons == (FAILED_ASSESSMENT,)` returned tier **C** with the reason `"only one admissible assessment exists; it is unconfirmed by a second role"` — the line-114 message never appears.

## Why it matters

The guard's stated protection — "an assessor failed, so any conclusion rests on incomplete input" — is **not** what fires. The tier that results is the same (C either way), so this is not currently a wrong outcome. What is wrong is that the code contains a rule that reads as an active safety property and is in fact dead, and it carries a *different explanation* than the one a reader gets.

That matters for this project specifically, because the audit trail is a deliverable: the `reasons` tuple is the human-readable justification recorded with the tier. A reader auditing why a given finding landed in Tier C is told "only one admissible assessment exists" when the intended explanation was "an assessor failed". Those are different statements about the evidence.

It also sits badly with the project's own ratchet on unexecuted guard raises, which exists to catch exactly this: protection that never runs.

## Proposed fix

Either delete the dead branch (making the code honest about what it does), or reorder it above `len(admissible) == 1` if the more specific explanation is wanted for the one-side-failed case. The second is probably the intent, since it produces the better audit message.

I have not changed it: which explanation should be recorded is a semantic choice about the audit trail, and this is a governance-adjacent layer.

## Acceptance criteria

- [ ] no branch in `classify_tier` is unreachable across all reachable `(abstained, admissible, disagreement_reasons)` inputs
- [ ] when an assessor failed, the recorded `reasons` says so
- [ ] a regression test drives a one-side-failed comparison and asserts the reason text
- [ ] the guard ratchet stays at 0
- [ ] gate green

### Comment — 2026-10-08T22:18:33Z

**RESOLVED** — commit `d8d8b00`.

## Confirmed unreachable
The branch tested `DisagreementReason.FAILED_ASSESSMENT in comparison.disagreement_reasons`. `compare_assessments` adds that reason only when a side `isinstance(..., FailedAssessment)` — and a `FailedAssessment` is never in the admissible set. So either `not admissible` or `len(admissible) == 1` always fired first. The branch could never change the tier; it could only change the recorded reason text.

Independent confirmation that it had no reachable effect: after removing it, the import of `DisagreementReason` in `tiers.py` became unused (ruff F401). The branch was that symbol's only consumer in the module. And the full suite still passes unchanged, so no test covered it either.

## Why removal is the right fix rather than reordering
The branch read as the rule protecting the case "an assessor failed". It provided no such protection — the case is handled earlier, for a different reason, and the recorded justification therefore blames "only one admissible assessment exists" when the real cause was a failure. Code that claims a safety property it does not provide is the "guard that cannot fail" class this project has now recorded eleven times. Deleting it cannot change any tier: a failed assessor still lands on the generic disagreement path and still reaches Tier C.

## Verification
`test_issue_41_a_failed_assessor_reaches_tier_c_without_the_dead_branch` builds a genuine failed assessor (`cited_evidence_ids=[]`), asserts `FAILED_ASSESSMENT` is in the comparison's disagreement reasons, then pins that `classify_tier` returns `C_EXPERT_JUDGMENT` and that the reason recorded is the surviving wording. It also asserts the removed wording does NOT appear, so if the reason text is ever reinstated that is a deliberate decision rather than a silent drift.

## Left to you
Rewording the reason so it names the failure explicitly is the better message and is a genuine improvement — but it changes what the audit trail says, so it is recorded as an owner decision in `docs/identity_decision_register.md` rather than taken unilaterally.

Gate: 433 passed / 95.62%, ruff clean, mypy clean (49 files), guard ratchet 0.

---

## #42 — model_copy bypasses HumanReview and ReviewHistory validators (latent)

**State:** CLOSED  |  **Opened:** 2026-10-08T13:45:39Z  |  **Closed:** 2026-10-08T22:29:48Z

## State

`PROPOSED` — confirmed by execution. **Latent**: no production path currently exploits it. Filed for the record, not as an active bug.

## Problem

Pydantic v2 does not re-run validators on `model_copy(update=...)`, so every `@model_validator(mode="after")` invariant on `HumanReview` is bypassable by copying a valid instance and overwriting a field.

### Executed

```
direct REVISE without supersedes -> REFUSED (ValidationError)
model_copy -> REVISE             -> decision=revise supersedes=None  NO ERROR
```

A `REVISE` decision is required by the schema to name the review it supersedes. The constructor enforces that; `model_copy` silently produces a `REVISE` with `supersedes_review_id=None`.

The same mechanism defeats `ReviewHistory`'s subject-match validator:

```
history.subject=18fc7b3a-...
review.subject =98e64e5a-...
MISMATCH ACCEPTED = True
```

## Why it is only latent

I checked every `model_copy` call in `src/`:

```
src/aegistrace/features/behavioral.py:235,238   (events/sources, not reviews)
src/aegistrace/features/causal.py:307,310       (events/sources, not reviews)
src/aegistrace/review/history.py:40             (ReviewHistory)
```

- The behavioural/causal uses are on events and sources, not reviews, so no invariant is at stake.
- `history.py:40` is the only review-adjacent use, and `append_review` **does** re-check the invariant manually before it (line 25: `if review.subject_triage_id != history.subject_triage_id: raise ValueError`). So the projection path is defended by hand, not by the schema.

So today nothing breaks. The finding is that the schema invariant is not the guarantee it appears to be: the real guarantee is three manual `raise` statements in `append_review`, and any future code that reaches for `model_copy` — a natural way to build a corrected review — will bypass the schema silently.

This is the same shape as the project's recurring **vacuous verification** class, one level down: an invariant that reports success over a scope it does not cover. Recording it because `#26` showed this project cares about guards that are enforced by construction rather than by convention, and because the fix is cheap now.

## Proposed fix

Options, cheapest first:
1. `model_copy(..., update=...)` has no validation escape hatch, so add a single `HumanReview.revalidate()`-style helper — or simply document on `append_review` that it, not the schema, is the enforcement point.
2. Give `HumanReview` a `model_construct`-free construction path so a corrected review must go through the validator.
3. Prevent the projection: have `append_review` build a fresh `ReviewHistory` from fields rather than `model_copy`, so the validator runs and the manual checks become belt-and-braces.

I would pick 3 plus a test, since it makes the schema the guarantee again and keeps the manual checks as defence in depth. Not implemented: it changes how the append-only chain is constructed, which is core to the audit trail.

## Acceptance criteria

- [ ] a `REVISE` without `supersedes_review_id` cannot exist, by any construction path used in `src/`
- [ ] a review whose subject differs from its history cannot exist, by any construction path used in `src/`
- [ ] regression tests pin both bypasses
- [ ] `append_review`'s manual checks remain, as defence in depth
- [ ] gate green

### Comment — 2026-10-08T22:29:47Z

**RESOLVED** — commit `6bcc805`. Category A, implemented independently as the register recommended (option 3), but **wider than option 3** because the narrower fix would have left the real defect hidden.

## The fix
`FrozenSchema.model_copy` now re-validates whenever fields are replaced. This closes the escape hatch for **every** schema in the project, not for the one call site that was noticed. A copy with no `update` is not re-validated: no field changed, so re-running validators would cost time without adding a guarantee.

`append_review` also now constructs `ReviewHistory` from fields rather than copying it, so `validate_subjects_match` runs and the three manual `raise` statements become defence in depth instead of the only guarantee.

## The issue was wrong that this was latent — it exposed a third instance
The issue said "today nothing breaks". Re-validating immediately broke something: **a third instance of the same class, in the features layer.**

`behavioral.py` built its synthetic leakage-audit event as `event_id = uuid5(last.event_id, "future-audit")`. That does not equal `event_id_for(source)` — precisely what `SecurityEvent.validate_evidence_identity` exists to forbid. The audit event was **schema-invalid** and survived only because the copy skipped validation.

The sharpest part: `causal.py` — the sibling audit helper, written to do the same job — **already derived it correctly** with `event_id_for`. Two helpers disagreed about how to construct an event id and nothing noticed, because the bypass silenced the one mechanism that would have said so. That is the cost of a validator that is not really enforced, made concrete.

## Verification
Re-ran the issue's exact reproduction. All three bypasses now refuse:

```
[1] direct REVISE without supersedes            -> REFUSED (ValidationError)
[2] model_copy -> REVISE                        -> REFUSED (ValidationError)
[3] ReviewHistory subject mismatch via copy     -> REFUSED (ValidationError)
```

And the behaviour that must NOT change is unchanged: plain copies, deep copies, and valid updates all still work.

## Three pre-existing tests were repaired, not weakened
They built deliberately schema-**invalid** events via the bypass (`model_copy(update={"source": ...})` without re-deriving the id). Their fixtures now re-derive the id, so they still exercise the **feature builder's** refusal rather than the event schema's. Assertions untouched. Same repair pattern as issues #30 and #32.

`tests/test_copy_revalidation.py` adds 7 tests, each stating its falsifier — because a guard whose failure mode is untested may be a tautology, which is the class of defect this issue belongs to.

Gate: 440 passed / 95.62%, ruff clean, mypy clean (49 files), guard ratchet 0.

---

## #43 — Schema validators do not enforce builder-side invariants (TriageComparison, feature datasets, SpineRecord)

**State:** CLOSED  |  **Opened:** 2026-10-08T23:13:01Z  |  **Closed:** 2026-10-08T23:15:35Z

## Problem

Four schema classes accept states their own builders refuse. A record can be written through the
builder (which raises), or read back with `model_validate` (which does not), so the guarantee is
enforced only on the write path. This is the same defect class as #42 and the `ReviewHistory`
chain gap closed in `bec8bc5`.

Executed against the real schemas before the fix:

| Schema | Builder rule | Executed result |
|---|---|---|
| `TriageComparison` | `agreement.py:83` — "cannot compare an assessment with itself" | `assessment_ids=[x, x]` **ACCEPTED**, and survived a JSON round-trip |
| `BehavioralFeatureDataset` | `behavioral.py:146` — "require one scenario per dataset" | `scenario_ids=['11','12']` **ACCEPTED**, and survived a JSON round-trip |
| `CausalFeatureDataset` | `causal.py:202` — same | `scenario_ids=['11','12']` **ACCEPTED**, and survived a JSON round-trip |
| `SpineRecord` | `spine.py:91` (`_assert_history_open`) — "the spine must never append a review" | record carrying 1 human review **ACCEPTED** |

Additionally, `TriageComparison` accepted `roles` that could not map `assessment_ids` (2 ids with 1
role; 1 id with 2 roles; duplicate roles), which matters because `left_only_evidence_ids` is
*interpreted* through `roles[0]`.

## Cause

Each invariant was written once, in the builder. `model_validate` never calls a builder, and every
one of these records is read back from a stored artifact rather than rebuilt. The schema therefore
looked like the guarantee while the real guarantee was whichever caller happened to run.

## Why each rule is an existing contract, not a new one

- `SpineRecord`'s own docstring says "an **unreviewed** tier assignment".
- `BehavioralFeatureDataset` and `CausalFeatureDataset` both say "Immutable **scenario-local** ...
  collection", and the builder raises the same rule.
- `compare_assessments` refuses a same-role pair and a repeated identifier, and builds `roles` and
  `assessment_ids` in parallel, so every comparison it produces satisfies both rules.

## Change

- `TriageComparison.validate_roles_map_assessments`: `roles` must map `assessment_ids` one-to-one
  and be distinct; `assessment_ids` must themselves be distinct (checked before the
  unrecorded-`roles` early return).
- `schemas/common.py::require_uniform_scenario`: one shared helper used by both feature datasets.
- `BehavioralFeatureDataset.require_single_scenario`, `CausalFeatureDataset.require_single_scenario`.
- `SpineRecord.require_history_is_open`.

## Removed rather than left dead

`_assert_history_open` was **deleted**. Once `SpineRecord` refuses the state at construction, no
path can produce a record carrying a review, so the helper could never fire — a guard no test can
execute. The guard ratchet (`scripts/report_unexecuted_guard_raises.py`, baseline 0) is what makes
that a hard requirement rather than a judgement call. The schema is now the single guarantee, and it
also covers the read path the helper never saw.

## Verification

- `tests/test_comparison_role_mapping.py` (7 tests): aligned control including unrecorded-`roles`
  and single-assessment shapes; both misalignment directions; same-role pairs; repeated
  `assessment_ids` both with and without roles; JSON-load forgery for both the misalignment and the
  repeat.
- `tests/test_scenario_local_datasets.py` (6 tests): per-family control, empty dataset, mixed
  scenario refused, and mixed dataset forged in stored bytes refused.
- `tests/test_decision_falsification.py::test_spine_refuses_record_with_a_review` rewritten to drive
  the schema through construction, `model_copy(update=...)`, and `model_validate` of forged bytes.
- `tests/test_spine_integration.py::test_spine_raises_if_a_review_were_present` now expects the
  schema's `ValidationError` instead of the removed helper's `RuntimeError`.

Gate: 466 passed (was 452 at the start of this round), 95.80%, ruff clean, mypy clean, guard ratchet
0, all governance validators PASS.

## Method note

Building this round's probes, I wrote four successive fixtures without reading the schema fields
first. Each failed for a reason of my own making — a wrong keyword argument, a missing required
field, then citations that did not exist in the bundle (which silently produced `FailedAssessment`
objects with identical ids). The probe's detail column caught each one; the "REFUSED" results were
my own errors, not the schema's behaviour. The committed tests now assert the offending property
before asserting refusal, so a probe cannot report a pass for the wrong reason.

The guard ratchet then caught a real hole in my own work: I had verified `assessment_ids`
distinctness by ad-hoc probe but never committed a test for it, leaving `triage.py:240` unexecuted.

## Category

A — engineering. Every rule enforced here was already a documented contract of the schema or of its
builder; no identifier meaning, tier semantic, public schema, or research result changes.

### Comment — 2026-10-08T23:15:35Z

DONE. All four gaps closed in `f7db9ef` / `8dd1829`, plus the TriageComparison roles mapping in `8dd1829`.

**Fixed:** `TriageComparison.validate_roles_map_assessments` (roles map assessment_ids one-to-one and are distinct; assessment_ids are distinct, checked before the unrecorded-roles early return), one shared `require_uniform_scenario` helper on both feature datasets, and `SpineRecord.require_history_is_open`.

**Removed:** `_assert_history_open` deleted rather than retained — once the schema refuses the state at construction, no path can produce a record carrying a review, so it was a guard no test could execute. The guard ratchet (baseline 0) makes that a hard requirement.

**Also repaired:** a MEMORY.md defect I introduced in rounds 33-34 — three blank lines terminated the markdown table, orphaning two rows outside it. My earlier checker counted pipe-rows rather than contiguous table membership and reported 74 valid rows. Now 77 contiguous rows, 0 malformed, 0 orphaned.

**Gate:** 466 passed, 95.80%, ruff clean, mypy clean, guard ratchet 0, all 7 governance validators PASS.

**Reusable lesson proposed:** a schema validator is the guarantee only if it runs on every construction path; a rule written once in a builder is bypassed by `model_validate`, which is exactly how stored records are read. Corollary: when a schema begins enforcing a builder-side rule, the builder-side check becomes unreachable and must be deleted, not retained.

---

## #44 — Vacuous test assertions: a test that cannot fail is indistinguishable from one that passes

**State:** CLOSED  |  **Opened:** 2026-10-09T03:24:27Z  |  **Closed:** 2026-10-09T03:24:44Z

**State: DONE** (implemented across commits `bb34c06`, `d5b4549`, `046c69f`).

## Problem

This project's documented recurring defect class is *"a check that reports success over a scope it
does not cover"*. Rounds 34-36 applied that lens to the library and to the schema read path. This
issue applies it **one level up, to the test suite itself**: a vacuous test is indistinguishable
from a passing one.

A four-way read-only audit of all 45 test files produced six CONFIRMED findings and a set of
suspected ones. Confirmed means proven by mutation: delete or disable the thing the test claims to
check, and the test still passes.

## Confirmed findings and fixes

| # | Test | Why it was vacuous | Fix |
|---|---|---|---|
| 1-2 | `tests/test_results_ledger.py` (two tests) | Compared a renderer's output to **itself** (`render(ledger) == render(ledger)`), so a renderer returning a constant passed both | Determinism across a reparse, plus the falsifier: a mutated ledger must render **differently** |
| 3 | `tests/test_features.py` | Compared a parquet schema field to the **same file's** schema field - literally `x == x` | Pins the expected Arrow types explicitly (`pa.float64()`, `pa.string()`) |
| 4 | `tests/test_triage_provider.py` | Re-asserted `provider.descriptor`, the very object the test constructs and passes in (identity comparison, always true) | Removed; the load-bearing `synthetic is True` and digest assertions retained |
| 5 | `src/aegistrace/evaluation/hardening.py` | `alert_volume` **duplicated** `compute_binary_metrics`' threshold guard with the identical message, so the falsification test naming `alert_volume`'s guard passed even when that guard was deleted | Redundant guard **deleted** (behaviour provably identical); the single surviving guard is now the one under test |
| 6 | `tests/test_decision_falsification.py` | Claimed all four machine checks refuse to pass vacuously on an empty assessment set, but pinned only two by name | Pins all four check names and asserts every **assessment-scoped** check fails closed |

Finding 5 is the purest form: the duplicate made the test vacuous, and the honest fix was to delete
the duplicate rather than keep it as defence in depth.

Finding 6 required care in the other direction: `bundle_states_its_own_gaps` legitimately passes on
an empty assessment set, because it checks the **bundle**, not the assessors. A blanket "nothing may
pass" assertion would have been wrong. Only the three assessment-scoped checks are asserted not to
pass.

## Fragile tests hardened

`tests/test_artifact_self_consistency.py`: eight tests accumulated violations inside a loop over
`captures` and then asserted the accumulator was empty - with no guard that `captures` was
non-empty. A truncated or empty artifact was therefore certified **fully self-consistent**. Three of
them assert *inside* the loop, where zero iterations means zero assertions. Added
`_captures(artifact, name)` and applied it to all eight.

`tests/test_claim_verification_scope.py`: three `assert not any(...)` assertions are vacuously true
over an empty list. Each now requires `reasons` to be non-empty first.

`tests/test_snapshot_leakage.py`: deleted a companion assertion whose own comment admitted it is
true by construction. A companion that cannot fail adds a passing test without adding a guarantee.

## Suspected finding CHECKED AND REJECTED

The subset assertions in
`tests/test_identity_rule.py::test_downstream_ids_follow_the_event_identity` were reported as
structurally tautological. They are **weak but genuinely falsifiable**, and were left unchanged.
Proof: mutation injecting a detection id into the bundle that was never emitted makes the test
**FAIL**.

Recording a rejected suspicion matters as much as recording a confirmed one.

## Proof method

Every claim above was proven by mutation on a pristine copy with a **verified GREEN baseline**, one
mutation at a time, reverted after each:

| Mutation | Result |
|---|---|
| Renderer returns a constant | test **FAILS** - caught |
| Feature columns written as `float32` | test **FAILS** - caught |
| The single surviving threshold guard deleted | test **FAILS** - caught |
| `assessors_saw_identical_input` forced to always pass | test **FAILS** - caught |
| **The OLD two-name assertion** vs that last mutation | test **PASSES** - proving it was blind |
| `_load` returns an artifact with `captures: []` | guarded tests **FAIL**; **unguarded (old) tests PASS** |

The last row in each pair is the finding: the pre-existing versions certified a broken system.

## Method note - my own instrument was wrong first

My first mutation harness ran in a `/tmp` copy missing `configs/`, so three of four probes "failed"
with `FileNotFoundError` rather than for the mutation, and I nearly recorded that as the tests
catching it. Rebuilt the copy, verified a green baseline first, then mutated. *The measuring
instrument was wrong, not the code* - the thirteenth occurrence of that pattern in this project, and
the reason the baseline check is now mandatory before any mutation result is trusted.

## Gate

473 passed (was 466), 95.82%, ruff clean, mypy clean, guard ratchet 0, all seven governance
validators PASS.

### Comment — 2026-10-09T03:24:43Z

Closed as DONE. Implementation and proof are in the issue body above; commits `bb34c06`, `d5b4549`, `046c69f`. No open work remains.
