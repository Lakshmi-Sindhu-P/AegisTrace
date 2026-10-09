# AegisTrace UI — Investigation Bench Architecture

**Document status: APPROVED INTENT / DESIGN.**
**Implementation status: PARTIAL — the shell, the five views and the review-append write path are
implemented; the evidence read layer is still one JSON artifact and the comparison view has no real
data. See "Implementation status" below.**

This document records the approved architectural and interaction direction for the AegisTrace
local user interface. It names the navigation model, the major views, the component boundaries, and
the data dependencies, grounding every statement in types and file paths that exist in the
repository today. It is the design contract that implementation must satisfy. Everything a view
claims to read is a real schema in the repository.

## Implementation status

The shell, the five views and the loopback-only server are now **CURRENT / IMPLEMENTED**. What is
implemented is the *instrument*, not the *data*: the UI reads one artifact the pipeline already
writes and renders it honestly, including the states where it has nothing to show.

| Element | Status |
|---|---|
| `src/aegistrace/ui/` package (read layer + app), `scripts/run_local_ui.py` | **CURRENT / IMPLEMENTED** |
| The five views, the navigation and the loopback-only bind | **CURRENT / IMPLEMENTED** |
| Static HTML/CSS, no JavaScript, no external asset | **CURRENT / IMPLEMENTED** |
| Synthetic marking, artifact-unavailable state, "AI assessment not available" state | **CURRENT / IMPLEMENTED** |
| A durable persistence layer (`storage/`) | **CURRENT / IMPLEMENTED** for human-review history (append-only DuckDB store, optional `storage` extra) |
| The review-append write path | **CURRENT / IMPLEMENTED** — `POST /decision` appends a `HumanReview` when a store path is configured, and refuses visibly when it is not |
| Real (non-synthetic) assessment data for the comparison view | **BLOCKED_HUMAN** (provider freeze) |

Two things the UI deliberately does **not** do, both stated on the pages themselves rather than
left implicit:

1. **It does not save a human decision unless a store is configured.** With a store path, a
   submission is appended durably and the page shows the record re-read from the store. Without one,
   `POST /decision` returns an explicit "NOT recorded" page. A form that silently discarded a human
   decision would be the worst failure an evidence-custody tool could have, so it refuses visibly
   instead. The failure page also distinguishes "nothing was written" from "written but could not be
   read back", because collapsing those two would itself be a false statement.
2. **It never invents an assessment pair.** The comparison view always reports "AI assessment not
   available", because the artifact it reads carries no assessments and no real (non-synthetic) run
   exists.


What this document **is not**: it is not blanket approval to introduce new research claims, new
governance rules, or new confidence measures. It approves an architecture and an interaction
direction only. The UI must not represent anything the repository does not already produce, and it
must never overstate certainty.

---

## 1. Owner approval (quoted contract)

> "I approve Investigation Bench (C) as the primary application shell, with Chain of Custody (A)
> integrated as the persistent evidence/provenance system and Two Witnesses (B) implemented as a
> dedicated AI-assessment comparison view. The primary workflow should be investigator-centered:
> findings → evidence inspection → AI-assessment comparison (when available) → review requirements →
> human decision. Preserve the research-first, provenance-first identity of AegisTrace. Do not
> represent synthetic assessments as real experimental results, and do not fabricate functionality,
> confidence measures, or operational capabilities. Treat this as approval of the architectural and
> interaction direction, not blanket approval to introduce new research claims or alter existing
> governance contracts."

The three directions were defined in `docs/ui_design_directions.md`:
- **Direction C (Investigation Bench)** — the shell: a bundle-centric, analyst-facing instrument
  panel whose uncertainty and score treatment come from `docs/ui_design_directions.md` "Direction C".
- **Direction A (Chain of Custody)** — the provenance spine that the shell integrates as the
  persistent evidence/provenance surface.
- **Direction B (Two Witnesses)** — a dedicated split-pane view comparing two independent
  assessors, hosted inside shell C.

The stack choice remains as previously approved (`docs/ui_design_directions.md`): FastAPI serving
static, local-only HTML, added incrementally and parallel to research. FastAPI is not yet a
dependency; it is introduced only at implementation time.

---

## 2. Hard constraints (approved, apply unconditionally)

| Constraint | Requirement | Repository origin / enforcement |
|---|---|---|
| Localhost-only | Binds `127.0.0.1`; no external requests, no telemetry, no CDN; all assets ship local. | Approved in `docs/ui_design_directions.md` "Shared commitments". |
| Read-only over evidence | The UI never writes detection data, never re-ranks, never auto-acts. The single write path is appending a `HumanReview`, which is append-only. | Enforced by the `ReviewHistory` schema (`src/aegistrace/schemas/review.py`, `validate_chain_is_linear`, `validate_subjects_match`), by `SpineRecord.require_history_is_open` (`src/aegistrace/spine.py`), and by the append-only `ReviewStore` (`src/aegistrace/storage/reviews.py`), which has no mutation code path. |
| Honest certainty | Nothing renders as more certain than it is. Abstention, missing context and limitations are displayed as content, never hidden in a tooltip. Uncertainty is shown as a band/interval, never a bare confidence percentage. Every score carries its model name because scores are not comparable across models. | `TriageCategory.INSUFFICIENT_EVIDENCE`, `EvidenceBundle.missing_context`/`limitations`, `TriageAssessment.confidence_statement` and `uncertainties`, `ScoreReference.model_name`. |
| Accessible by default | WCAG 2.2 AA contrast floor; visible focus states; full keyboard operation; semantic HTML; no information conveyed by animation alone. | Approved in `docs/ui_design_directions.md` "Shared commitments". |
| Colour never alone | Severity and disagreement always carry text and/or shape in addition to colour. | Approved in `docs/ui_design_directions.md` "Shared commitments". |
| Never represent synthetic as real | The UI must visibly mark synthetic (offline stand-in) assessments and must never present them as real experimental results. | `ProviderResponse.synthetic`, `TriageRun.synthetic`, `SpineRecord.synthetic` (see Section 8). |
| No new claims | No new research claims, no new governance rules, no new confidence measures. | Owner approval contract; `AGENTS.md` governance guardrails. |

### The single write path, stated exactly

The only state-changing operation the UI performs is appending a `HumanReview` to a review history.
That operation is **append-only** and is enforced at three levels:

1. `ReviewHistory` (`src/aegistrace/schemas/review.py`) enforces a single linear chain: every review
   shares the subject's `subject_triage_id`; a later review must supersede the most recent review;
   duplicate identifiers are rejected. A correction is a *new* review that points back via
   `supersedes_review_id`; nothing is overwritten.
2. `SpineRecord.require_history_is_open` (`src/aegistrace/spine.py`) guarantees a spine record
   always reaches a human with an **empty** review history awaiting review — it raises if a record
   carries any review. This is the schema-level guarantee that no autonomous component (including
   any UI the spine would not pass through) can write a review. Because a spine record's embedded
   history is therefore *always* empty, reviews are stored in the separate store below rather than
   written back into the spine artifact.
3. `ReviewStore` (`src/aegistrace/storage/reviews.py`) is where a review actually goes. It issues
   only `CREATE`, `INSERT` and `SELECT`, so no mutation code path exists; `review_id` is the primary
   key, so a duplicate is refused by the database as well as by the schema; and every read
   reconstructs a `ReviewHistory`, so a hand-edited database fails loudly on read instead of
   presenting a forged lineage as authoritative. It also journals each subject's expected head and
   count at every append, so a *truncated* chain — which is shorter but still internally valid — is
   detected. The honest limit: DuckDB does not make a table immutable, so a user with the `duckdb`
   CLI can still issue `UPDATE`/`DELETE`; that is **detected**, not prevented. Preventing it is what
   PostgreSQL with restricted roles would buy, and PostgreSQL stays deferred.

The append itself is executed through `append_review` in `src/aegistrace/review/history.py`, which
re-validates the chain before producing the new `ReviewHistory`. The repository's central invariant —
the spine never acts — means the UI appends a review on the human's behalf; the UI never decides a
tier, never classifies, and never scores.

---

## 3. Navigation model (proposed)

Investigator-centered shell (Direction C), five steps. Every step is a real read surface over
already-computed artifacts; "→" is the intended route, not a forced gate (a step may be skipped
when its input is absent).

| Step | Name | Reads | Shows when data is present | What it can and cannot show when data is missing |
|---|---|---|---|---|
| 1 | Findings | `Finding`, `EvidenceBundle`, `FindingStatus`, `DetectionSeverity` | A bundle-centric working tray of evidence bundles (the unit of work is an evidence bundle, not an alert row). | When no bundles exist: an explicit empty tray stating no evidence bundles are available. It **can** show a bundle even if triage has not run. It **cannot** show a severity that is not on the bundle's `proposed_severity`. |
| 2 | Evidence inspection | `EvidenceBundle`, `EventSummary`, `DetectionEvidence`, `ScoreReference`, `EvidenceReference`, `Claim`/`ClaimVerification`; `SecurityEvent` at the bottom of the chain | Direction A provenance spine: the bundle's ancestry down to raw source records, digest always visible, each claim as a numbered exhibit | When the chain is incomplete (e.g. no raw event store), it shows the gap as a labelled missing slot ("not established"), never blank space. It **cannot** fabricate ancestry the bundle does not reference. |
| 3 | AI-assessment comparison | `TriageAssessment`, `TriageComparison`, `AssessorRole`, `DisagreementReason`, `ProviderMetadata`, `RawResponseReference` | Direction B split pane: both assessors with the shared evidence rail, disagreement marked physically, disagreement as escalation signal | **"when available" is the operative phrase.** If no admissible assessment pair and comparison exist, the view shows an explicit "AI assessment not available" state (abstention or absence), and the workflow proceeds without it. It **cannot** fabricate an assessment pair from an aborted run or a single-side failure. |
| 4 | Review requirements | `TierAssignment`, `ReviewTier`, `MachineCheck`, `ReviewHistory`, `HumanReview` | The tier's reasons and machine checks, plus the current review state | If a tier assignment is absent it displays that; it **cannot** run `classify_tier` itself. |
| 5 | Human decision | `HumanReview`, `ReviewHistory`, `ReviewTier`, `ReviewDecision`, `EscalationState` | The reviewer's disposition form and the append-only review history | The destination of the single write path. If the subject was already resolved, the history is shown and a correction supersedes the last entry. The UI **cannot** auto-decide; only a human submits. |

No forced gating: failing (or missing) AI comparison at step 3 must not block steps 4–5, and step 4
renders even when a comparison is absent. The workflow's integrity comes from what it *refuses* to
render as present, not from imposing a linear gate.

---

## 4. Major views (proposed)

Each view's "reads" are exact repository schema types. All views are pure rendering over
already-computed artifacts unless noted otherwise; the single exception (the write path) is in
Section 5.

### 4.1 Findings — Investigation Bench tray
- **Purpose.** The primary working surface: a specimen-tray of evidence bundles for sustained
  investigative use (Direction C).
- **Reads.** `Finding`, `EvidenceBundle`, `FindingStatus` (`OPEN`/`TRIAGED`/`DISMISSED`/`ESCALATED`),
  `DetectionSeverity` (`INFORMATIONAL`/`LOW`/`MEDIUM`/`HIGH`/`CRITICAL` — all five; a tray that
  rendered only the top four would silently drop a valid severity).
- **Displays.** Evidence bundles keyed by `EvidenceBundle.evidence_bundle_id` and `Finding.finding_id`;
  window (`Finding.window_start`/`window_end`), source host, `proposed_severity`, status.
- **Empty / abstention state.** No bundles → an explicit "no evidence bundles available" tray. A
  bundle with `missing_context`/`limitations` shows those as content.

### 4.2 Evidence inspection — Chain of Custody provenance spine
- **Purpose.** The persistent evidence/provenance system (Direction A) inside the shell: each claim
  is a numbered exhibit; selecting an exhibit re-roots the spine onto its evidence.
- **Reads.** `EvidenceBundle`, `EventSummary`, `DetectionEvidence`, `ScoreReference`, `EvidenceReference`,
  `Claim`, `ClaimVerification`, and at the bottom of the chain `SecurityEvent` (`src/aegistrace/schemas/events.py`).
- **Displays.** Bundle ancestry down to raw source records; the SHA-256 `snapshot_digest` always
  visible (`src/aegistrace/spine.py`); each score with its `ScoreReference.model_name`.
- **Empty / abstention state.** A missing segment is a labelled slot ("not established"), never
  blank space. Uncertainty from `EvidenceBundle.missing_context` and `limitations` is rendered inline.

### 4.3 AI-assessment comparison — Two Witnesses
- **Purpose.** A dedicated comparison view making the mutual-blindness experiment legible
  (Direction B). Disagreement is the hero state, not an error.
- **Reads.** Two `TriageAssessment` records (roles `TRIAGE_ANALYST` and `EXPERT_ADJUDICATOR`),
  `TriageComparison`, `AssessorRole`, `DisagreementReason`, `ProviderMetadata`, `RawResponseReference`.
- **Displays.** Both assessors citing into a shared rail; `shared_evidence_ids`,
  `left_only_evidence_ids`, `right_only_evidence_ids`; `disagreement_reasons`;
  `agreement_score`; `escalation_recommended`. Each side is labelled with its role name, not with
  "real/synthetic correctness".
- **Empty / abstention state.** No admissible pair + comparison → an explicit "AI assessment not
  available" card. Mutual abstention (`INSUFFICIENT_EVIDENCE`) renders as an "insufficient
  evidence" card. `TriageCategory.INSUFFICIENT_EVIDENCE` is a valid category, not a failure
  (`src/aegistrace/schemas/triage.py`).

### 4.4 Review requirements
- **Purpose.** Show *who is qualified to decide* and why.
- **Reads.** `TierAssignment`, `ReviewTier`, `MachineCheck`, `ReviewHistory`, `HumanReview`.
- **Displays.** The tier string with `TierAssignment.reasons` (always present —
  `min_length=1`) and `machine_checks`. A tier is an assertion about reviewer qualification
  (`ReviewTier` in `src/aegistrace/schemas/review.py`), never a severity.
- **Empty / abstention state.** If no `TierAssignment` artifact exists, the view states that it is
  absent; it does **not** compute one.

### 4.5 Human decision
- **Purpose.** The single write-path surface.
- **Reads.** `ReviewHistory`, `HumanReview`, `ReviewTier`, `ReviewDecision`, `EscalationState`.
- **Displays.** The current (last) review and the full linear chain.
- **Write.** Appends a `HumanReview` (Section 2, Section 5). The UI cannot auto-submit.

---

## 5. Component boundaries (proposed)

The UI is a **thin, read-mostly renderer**. Its components fall into three classes:

| Class | Components | Behaviour | Calls into the library? |
|---|---|---|---|
| Pure rendering over computed artifacts | Findings tray, provenance spine, comparison pane, tier display, review history display | Reads already-computed records and renders them. Performs **no detection, no scoring, no tier classification**. | **No.** It may format/aggregate for display but never computes a finding, an assessment, a comparison, a tier, or a score. |
| Display-only utilities | Uncertainty band/interval renderer, severity/disagreement glyph (always text+shape+colour), synthetic badge | Render existing fields honestly. | No. |
| The single write path | Human-decision form → `append_review` | Takes a human's form input and appends a `HumanReview`. | **Yes — the only library call.** It invokes `append_review` (`src/aegistrace/review/history.py`); the `ReviewHistory` and `SpineRecord` schemas enforce append-only semantics and the open-history invariant. |

The boundary rule, stated plainly: **the UI performs no detection, no scoring, and no tier
classification of its own.** Those are library responsibilities performed upstream
(and, in the case of tier assignment, by `classify_tier` at `src/aegistrace/review/tiers.py`, never
by the UI). The UI renders what exists and appends one thing humans write.

The `synthetic` flag is read and rendered (Section 8), never recomputed: the flag is forced onto the
record by the provider boundary (`src/aegistrace/triage/provider.py`) and propagated to the run and
the spine record.

---

## 6. Data dependencies (proposed)

Each view maps to the record type(s) it consumes. "Exists today" means the schema/module is
implemented in the repository now; it does not mean the UI reads a durable store for it, because the
UI reads one JSON artifact for evidence and only the human-review history has a durable store
(Section 7).

| View | Source of truth (schema type) | Module | Exists today? |
|---|---|---|---|
| Findings tray | `Finding`, `EvidenceBundle` | `src/aegistrace/schemas/findings.py` | Yes (schema). Produceable via aggregation found in the repo (findings aggregation implemented per `MEMORY.md`). |
| Provenance spine | `EvidenceBundle`, `EventSummary`, `DetectionEvidence`, `ScoreReference`, `EvidenceReference`, `Claim`, `ClaimVerification`, `SecurityEvent` | `src/aegistrace/schemas/findings.py`, `src/aegistrace/schemas/events.py`, `src/aegistrace/detection/evidence.py`, `src/aegistrace/verification/claims.py` | Yes for the schemas and claim verification module. A durable event store is **not** implemented (see 7). |
| AI comparison | `TriageAssessment`, `TriageComparison`, `AssessorRole`, `DisagreementReason`, `ProviderMetadata`, `RawResponseReference` | `src/aegistrace/schemas/triage.py`, `src/aegistrace/triage/agreement.py` (agreement engine), `src/aegistrace/spine.py` | Schemas/engine: Yes. Real non-synthetic assessment data: **not yet** (firewall — see 7). |
| Review requirements | `TierAssignment`, `ReviewTier`, `MachineCheck` | `src/aegistrace/schemas/review.py`, `src/aegistrace/review/tiers.py` | Yes (schema + `classify_tier`). |
| Human decision | `HumanReview`, `ReviewHistory` | `src/aegistrace/schemas/review.py`, `src/aegistrace/review/history.py`, `src/aegistrace/storage/reviews.py` | Yes — schema, append-only helper, **and** a durable append-only store (`ReviewStore`). |
| Top-level page/run identity | `SpineRecord` (fields: `spine_id`, `snapshot_digest`, `triage_run`, `comparison`, `tier`, `review_history`, `synthetic`) | `src/aegistrace/spine.py` | Yes (schema + `run_spine`). |
| Egress/boundary truth | `ProviderDescriptor`, `ProviderResponse.synthetic`, freeze artifact | `src/aegistrace/triage/provider.py`, `configs/triage_provider_freeze.json` | Yes. Freeze status is `BLOCKED_HUMAN` and assessor independence is `NOT ESTABLISHED`. |

None of these dependencies is a network dependency. All reads are over local, already-computed
records; binding is `127.0.0.1` only.

---

## 7. "Not yet available" (the repository does not yet produce/contain these)

The UI would want the following, but they do not exist in the repository today. The document names
them so implementation never fabricates them:

1. **A durable evidence read layer.** The human-review history now has a durable store
   (`src/aegistrace/storage/reviews.py`, append-only, DuckDB, optional `storage` extra), but there is
   still no durable store for *evidence*: the UI reads a **JSON artifact the pipeline already wrote**,
   via `src/aegistrace/ui/artifacts.py`. A store-backed evidence read layer remains
   `PLANNED, NOT IMPLEMENTED`, and PostgreSQL stays deferred. The `ui/` package, the FastAPI
   dependency and the `storage/` package all exist as optional extras.
2. **Real (non-synthetic) independent assessment data.** `configs/triage_provider_freeze.json` is
   `BLOCKED_HUMAN`; assessor independence is `NOT ESTABLISHED`; there is no LLM client or credential
   path, and no network-capable import exists in the provider boundary
   (`src/aegistrace/triage/provider.py`). Only offline recorded-replay and stub providers can run
   today, and those are synthetic by construction. The AI-comparison view can therefore only ever
   show synthetic assessments until the freeze is resolved by a human.
3. **A raw-event store serving the provenance spine's bottom.** `SecurityEvent` is a real schema,
   and ingestion adapters exist, but a durable event store usable by a UI is planned, not built.
4. **A numeric confidence measure to band.** There is no numeric confidence percentage in the
   schemas; uncertainty is carried as free text (`TriageAssessment.confidence_statement`,
   `TriageAssessment.uncertainties`, `EvidenceBundle.missing_context`/`limitations`). How the UI
   renders an "interval/band" for confidence is therefore `not determined from the repository` —
   there is no numeric measure to band. The band requirement applies to scores (e.g.
   `ScoreReference.model_score`, `TriageComparison.agreement_score`), each always labelled with its
   model/scale; it must not invent a numeric confidence the schemas do not provide.
5. **Ground-truth labels.** The snapshot deliberately excludes ground-truth labels
   (`configs/triage_provider_freeze.json`, prohibited payloads; `src/aegistrace/schemas/events.py`
   keeps `GroundTruthLabel` off the bundle / snapshot path). The UI must treat them as unavailable
   evidence, never as a value it may display as an assessment basis.
6. **Any UI code or dependency.** No HTML/CSS/JS, no FastAPI dependency, no `ui/`/`api`/`storage`
   package (verified: absent from the tree).

---

## 8. Marking synthetic assessments (specific, required)

The code distinguishes synthetic from real through a validated `synthetic` flag. The UI must render
that flag, and must do so as a permanent, visible part of the assessment surface — never as a
tooltip, never dismissible:

- `ProviderResponse.synthetic` (`src/aegistrace/triage/provider.py`): the raw-response flag. The
  provider boundary **forces** `synthetic=True` on any response from a non-`REMOTE` descriptor,
  so an offline stub or recorded-replay response can never claim `synthetic=False`.
- `TriageRun.synthetic` (`src/aegistrace/triage/run.py`): a run is synthetic if either descriptor is
  offline, even if it aborts before a response.
- `SpineRecord.synthetic` (`src/aegistrace/spine.py`): propagated onto the spine record.

Required UI treatment:
- Wherever an assessment, a comparison, or a spine record whose `synthetic == True` is shown, a
  persistent inline marker must label it **synthetic (offline stand-in — not an experimental
  result)**.
- The AI-comparison view must not present a synthetic pair as a real experimental result, and must
  not let a synthetic badge be hidden behind an interaction.
- The badge must carry text and shape, not colour alone (colour-blind / greyscale-safe).

This is a display requirement over an existing, validated field; it is not a new confidence measure
and not a new governance rule.

---

## 9. Status vocabulary

| Item | Status |
|---|---|
| This document | **APPROVED INTENT / DESIGN** (owner approval quoted in Section 1) |
| Investigation Bench (C) as shell | **CURRENT / IMPLEMENTED** (shell, navigation, five views) |
| Chain of Custody (A) as evidence/provenance system | **CURRENT / IMPLEMENTED** (provenance view; reads one artifact) |
| Two Witnesses (B) as dedicated comparison view | **CURRENT / IMPLEMENTED as an absence state** — the view exists and correctly reports "not available"; its real content is **BLOCKED_HUMAN** |
| Five-step investigator workflow | **CURRENT / IMPLEMENTED** (navigation order) |
| The five views, navigation, component boundaries in Sections 3–5 | **CURRENT / IMPLEMENTED** |
| FastAPI / static-HTML stack | **CURRENT / IMPLEMENTED**, as an optional `ui` extra so the library never needs a server |
| Loopback-only bind (`127.0.0.1`) | **CURRENT / IMPLEMENTED and VERIFIED** — no `--host` flag exists, and a live run served loopback while refusing the LAN address |
| Durable persistence layer (`storage/`) | **CURRENT / IMPLEMENTED** for human-review history (append-only DuckDB store, optional `storage` extra). A durable store for **evidence** remains **PLANNED, NOT IMPLEMENTED** — the UI reads a JSON file |
| The review-append write path | **CURRENT / IMPLEMENTED** — `POST /decision` appends a `HumanReview` when a store path is configured, and returns an explicit "NOT recorded" page when it is not |
| Underlying schemas the views read | **CURRENT / IMPLEMENTED** (per `MEMORY.md`) |
| Provider boundary, egress refusal, `synthetic` enforcement | **CURRENT / IMPLEMENTED and VALIDATED** (per `MEMORY.md` and `src/aegistrace/triage/provider.py`) |
| Real non-synthetic triage run | **BLOCKED_HUMAN** / **NOT ESTABLISHED** (freeze artifact), so **PLANNED, NOT IMPLEMENTED** |

---

## 10. Items marked "not determined from the repository"

The following could not be established from the repository and are stated as such rather than
guessed:
- The exact durable data source a UI would read **evidence** from; the human-review store now exists
  (`src/aegistrace/storage/reviews.py`), but no durable evidence store does, so how evidence records
  become available to the UI beyond the one JSON artifact is still not determined.
- A numeric confidence measure to band as uncertainty (the schemas carry text, not a numeric
  confidence); the band requirement applies to scores, not to an invented confidence number.
- Whether `Claim`/`ClaimVerification` artifacts are produced for the evidence spine on the same
  record path the UI would consume; the schemas and verification module exist, but a coupled
  production UI-ready artifact feed is not implemented.