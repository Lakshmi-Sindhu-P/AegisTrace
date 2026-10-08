# Learning Map

A single place to orient. This file is an **index with a reading order**, not a summary — every
concept lives in exactly one document, and this map points at it. If you find yourself reading the
same explanation twice, one of the two is a duplicate that should be removed.

## How to use this

Read top to bottom if you are new to the project. Jump to a row if you need one concept. The
**Status** column uses the project's vocabulary and is the honest one: `CURRENT / IMPLEMENTED` means
code and tests exist; `APPROVED INTENT / DESIGN` means it is agreed but not built; `PLANNED, NOT
IMPLEMENTED` means it is written down and nothing more; `VALIDATED` means it produced a result.

## The problem, and the shape of the answer

| Concept | Where it lives | Status |
|---|---|---|
| Why the project exists, scope, and non-goals | [`project_charter.md`](project_charter.md) | APPROVED INTENT / DESIGN |
| What an attacker can and cannot do here | [`threat_model.md`](threat_model.md) | CURRENT / IMPLEMENTED |
| What the project claims, at what evidence tier, and what each claim does NOT support | [`results.md`](results.md) (rendered from [`results_ledger.json`](results_ledger.json)) | CURRENT / IMPLEMENTED |
| Known limits, stated rather than discovered later | [`limitations.md`](limitations.md) | CURRENT / IMPLEMENTED |
| Phase order and what is next | [`roadmap.md`](roadmap.md) | CURRENT / IMPLEMENTED |

## The technical spine, in dependency order

Each layer may only trust the one above it. This ordering is the project's central safety property:
a conclusion can never be stronger than the evidence beneath it.

| Layer | Concept | Where it lives | Status |
|---|---|---|---|
| 1 | Raw datasets, and why labels are handled the way they are | [`datasets.md`](datasets.md) | CURRENT / IMPLEMENTED |
| 2 | **Identity: how evidence, AI assessments and human decisions are named** | [`identity_rule.md`](identity_rule.md) | CURRENT / IMPLEMENTED |
| 3 | Features: what a detector may see, and what must stay out | [`features.md`](features.md) | CURRENT / IMPLEMENTED |
| 4 | Detectors and their frozen policy | [`phase3_detector_hardening.md`](phase3_detector_hardening.md), [`methodology.md`](methodology.md) | VALIDATED |
| 5 | Findings, evidence bundles, and claim verification | [`architecture.md`](architecture.md) | CURRENT / IMPLEMENTED |
| 6 | Analyst-outcome evidence program (stages 1-3) | [`analyst_outcome_program.md`](analyst_outcome_program.md) | VALIDATED (stage 1 REFUTED) |
| 7 | LLM triage: the provider boundary, egress gate, and the frozen A/B protocol | [`triage_provider_boundary.md`](triage_provider_boundary.md), [`llm_ab_preregistration.md`](llm_ab_preregistration.md) | APPROVED INTENT / DESIGN — `BLOCKED_HUMAN` |
| 8 | Tiered human review and the append-only history | [`architecture.md`](architecture.md) | CURRENT / IMPLEMENTED |
| 9 | Local review UI | [`ui_design_directions.md`](ui_design_directions.md) | DESIGN PROPOSED — awaiting owner choice |

## Decisions still open, and where the analysis is

Do not re-litigate these from memory; the analysis is written down.

| Item | Where the full analysis is |
|---|---|
| The ten-field register for #37, #38, #40, #42, with autonomy category per issue | [`identity_decision_register.md`](identity_decision_register.md) |
| UI direction — three options, none approved | [`ui_design_directions.md`](ui_design_directions.md) |
| What `HumanReview.tier` means (required vs conducted) | Issue #30 |
| Which end owns the triage sample | Issue #32 |
| Whether an empty-but-valid ingest refuses or records | Issue #37 |
| Making the validator bypass impossible by construction | Issue #42 |

## Teaching notes, by phase

Longer explanations, written to be read once and understood. Each is self-contained.

| Note | Covers |
|---|---|
| [`phase_0.md`](learning_notes/phase_0.md) | Foundations and environment |
| [`phase_1.md`](learning_notes/phase_1.md) | Ingestion and canonical events |
| [`phase_2.md`](learning_notes/phase_2.md) | Feature engineering |
| [`phase_2b.md`](learning_notes/phase_2b.md) | Detector baselines and evaluation discipline |
| [`phase_3.md`](learning_notes/phase_3.md) | Detection foundations, behavioral and causal features |
| [`phase_4.md`](learning_notes/phase_4.md) | Identity: slot addresses vs content addresses, and vacuous verification |

## The recurring defect class, in one place

The single most useful thing to know about this codebase: its worst defects have not been wrong
arithmetic, they have been **checks that cannot fail** — a guard derived from the thing it guards, a
test that passes for any implementation, an identity that ignores its content.

It has been recorded eleven times: issues #13-#19, #20, #21, #23, #24, #29, #32, #33, #34, #35, #36.
The concrete instance that names the pattern is `SNAPSHOT_FIELDS`, which was *defined* as a
projection of the class it was supposed to police, so both sides of every assertion moved together.

Two habits follow, and they are expected in every change:

1. **Every guard needs a test that makes it fail.** A guard whose failure mode is untested may be a
   tautology.
2. **Every property needs its falsifier.** Asserting "these two ids differ" proves nothing unless you
   also assert that the old scheme made them collide.

The corollary, learned repeatedly and expensively: when a measurement returns a surprising answer,
suspect the instrument before the code. That has been the actual fault **nine times** — including
three separate occasions in the round that produced `phase_4.md`, where a partial monkeypatch, a
mis-typed CSV header, and a table-scanning script each produced a confident, wrong result.

## Verification and how to reproduce a claim

| Need | Where |
|---|---|
| How to run the suite, lint, types, and the guard ratchet | [`../MEMORY.md`](../MEMORY.md), "Testing and Evaluation" |
| Which experiment produced which artifact, and its digest | [`experiment_registry.json`](experiment_registry.json) |
| Whether a committed artifact still matches its recorded digest | [`artifact_manifest.json`](artifact_manifest.json) |
| What each metric means and its stated scope | [`evaluation.md`](evaluation.md) |
