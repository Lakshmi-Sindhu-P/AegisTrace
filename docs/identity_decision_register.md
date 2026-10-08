# AegisTrace Identity Decision Register

**Status: PROPOSED.** Decision record for four open issues. Each entry gives a Category verdict
(**A** = engineering, safe to implement independently · **B** = product/architectural contract ·
**C** = research/governance), a one-sentence justification, and ten numbered sections answering the
same questions so the four can be compared.

Every technical claim below was verified against the live source and the executed evidence in the
issue bodies listed in `README`/GitHub. Measured results are quoted from the issue bodies; my own
engineering judgement is labelled as such.

Referenced contract: `docs/identity_rule.md` — **APPROVED (owner, 2026-10-09)**. It already names
the resolution for the two identity issues (#38, #40). This register confirms that those resolutions
execute the approved rule and does **not** re-open them.

---

## Issue #37 — Empty-but-valid ingestion reports a clean success over zero rows

**Category: B (product/architectural contract).** Whether an empty capture is a hard refusal or a
recorded issue changes the CLI contract and the manifest, and the issue explicitly defers that call
to the owner.

**Analogy.** An assembly line that stamps "0 made, no problems" and flips itself to "done" when the
hopper arrived empty with only a label on it. The line correctly rejects a totally bare hopper, but
it treats "right label, no parts" as a finished shift.

### 1. Current behaviour and the demonstrated failure

A file whose header is structurally valid but contains **zero data rows** is accepted as a clean,
complete success: `rows_seen=0 accepted=0 rejected=0 issues=0`, the CLI exits 0, and a manifest is
written claiming `record_count=0`. Verified in both parsers.

- `src/aegistrace/ingestion/ctu13.py::parse_ctu13_binetflow` builds the header issue only when the
  header does **not** match `_FIELDS` (lines 363–371); a matching header sets `header_valid = True`
  and produces no error, so a valid header followed by no rows yields an empty `issues` tuple.
- `src/aegistrace/ingestion/iot23.py::parse_iot23_conn_log` appends the `missing #fields header`
  issue only when `fields is None` (lines 344–348); a recognised `#fields` header with no data rows
  leaves `issues` empty too.

Executed (issue #37), using each fixture's real header:
`valid CTU-13 header + 0 rows` → `rows_seen=0 accepted=0 rejected=0 issues=0`;
`IoT-23 headers only` → same clean pass. A **truly empty** file is still refused (`issues=1`), so
the two cases are already distinguished in the code — the distinction is just not applied to
"header valid, nothing after it".

Note on method recorded in the issue: the first probe used a header typed from memory with an extra
`DstBytes` column; the parser correctly flagged `unexpected CTU-13 header`. That looked like a
refutation but actually proved header validation works. Re-run with the real 15-column header
(ending `SrcBytes,Label`) gives the clean pass. The real header is confirmed in
`ctu13.py:49–64` (15 columns, last two `SrcBytes`, `Label`).

### 2. Expected behaviour and the relevant existing contracts

The parser is already expected to distinguish real from vacuous scopes: it refuses a truly empty
file. The gap is that "recognised, right-shaped input with nothing inside" is not treated as a
condition at all. The recurring **vacuous verification** class this project guards against (see the
snapshot-allowlist fix, behavioural feature checks) says a check must not report success over a
scope it does not cover. Here the scope is a whole ingestion run.

### 3. Root cause

Neither parser emits any issue on the path where the header is valid but the row loop never runs. In
`parse_ctu13_binetflow` the `header_valid` branch and the `rows_seen += 1` loop are decoupled: a
valid header sets the flag, and zero iterations complete the loop without any "nothing was seen"
test. `parse_iot23_conn_log` is the same with `fields` correctly parsed but no data row consumed.

### 4. Proposed correction

When the header is recognised but no data row follows, emit a non-empty condition — either a hard
refusal (raise) such as an `empty_input` issue alongside the existing `malformed_row` handling, or
at minimum a recorded issue so the manifest and exit code surface it. Both parsers need it. This is
the issue's proposed fix; the raise-vs-recorded-issue choice is the open contract decision.

### 5. Alternative approaches

- **Hard refusal** — raise/exit non-zero (with a distinct `empty_input` issue) when header is valid
  and rows_seen == 0.
- **Recorded-but-permissive** — keep exit 0 but append an `empty_input` issue and set
  `record_count=0` visibly in the manifest, leaving the caller to decide.
- **Ambiguous-size guard** — no change to truthiness, only reclassify so that `0 rows` is never
  reported as "clean".

### 6. Advantages and disadvantages of each

- **Hard refusal:** strongest signal; no pipeline can mistake an empty capture for a finished one.
  Disadvantage: breaks callers that legitimately want to store an empty capture, and changes the CLI
  exit code (a downstream contract change).
- **Recorded-but-permissive:** preserves current exit-code behaviour, surfaces the condition for
  anyone who reads the manifest. Disadvantage: a permissive path keeps a silent path for pipelines
  that only check exit code.
- **Reclassify only:** minimal change, but leaves the "0 result is success" semantics intact, which
  is the very default the issue says is wrong.

### 7. Downstream dependencies and potential breaking changes

Manifest consumers, scheduled runs, and any pipeline keying on exit code. If `#37` becomes a hard
refusal the CLI contract changes; if it only records an issue the manifest gains a field. #39
(`rejected_rows` over-counts the header issue) touches the same reporting surface, so both should be
settled together to avoid two conflicting deltas on the report.

### 8. Research, privacy, and governance implications

None directly. No identity, no model call, no egress. The relevance is data-validity/governance: a
failed extraction or truncated download that leaves the header must not silently count as an
ingested dataset, because AegisTrace's evidence claims would otherwise rest on "we ingested nothing
and said nothing."

### 9. Recommended option and justification

Record an `empty_input` issue (permissive), keeping the exit at 0 only if the manifest unambiguously
carries a non-empty issues list and `registered` `record_count=0`. This preserves the CLI contract
while removing the silent path. Preference for the less disruptive option because the down-stream
consumer signal here (the manifest) already exists; turning it into a hard raise is a bigger
contract change that should be the owner's explicit call.

### 10. Whether owner approval is genuinely required

**Yes.** The issue was filed for the owner's call on raise-vs-record — it changes the CLI exit
contract and the manifest, and is coupled to #39. Implement only after an explicit decision.

---

## Issue #38 — event_id_for ignores row content and raw_checksum; distinct records collide

**Category: B (product/architectural contract).** `event_id` is the root of the whole identity
spine, so this is architectural even though the resolution is already specified in the approved
`identity_rule.md`.

**Analogy.** Two students who wrote completely different essays are both stamped with the same
library catalogue number because the number is derived from "seat 3, row 2" rather than from what
they wrote. The library says there is one essay when there are two.

### 1. Current behaviour and the demonstrated failure

`src/aegistrace/schemas/events.py::event_id_for` derives the id from five fields only:

```python
identity = json.dumps([source.source_type.value, source.source_dataset,
                       source.scenario_id, source.dataset_version, source.source_event_id], ...)
```

`source_event_id` is built in `src/aegistrace/ingestion/ctu13.py:239` as `f"line-{line_number}"` —
per-file line numbering, not qualified by the file. `SourceRecordRef` carries `raw_checksum`
(`events.py:24`) and ingestion already computes it (`ctu13.py:_sha256_file`), but `event_id_for`
ignores it and every row field.

Executed (#38): two genuinely different records — `A: tcp malicious 1000B fileA` and
`B: udp benign 123456B fileB`, different files, at the same line number in the same scenario — both
got `465820a4-d6c9-50fd-86ba-0c20a2a34015`. `COLLIDE = True; records differ = True`. Two different
binetflow files for one scenario collapse their matching-line records onto one identity.

### 2. Expected behaviour and the relevant existing contracts

`event_id` is the root of the spine: `event_id -> detection_id -> finding_id -> evidence_bundle_id
-> triage_id -> review_id` (documented in `docs/identity_rule.md`). The approved rule (R1) requires
that two things the system treats as different have different ids. `SourceRecordRef` already carries
`raw_checksum` (R3-ready: a field-set change takes a new namespace version). The docstring claims
only "repeatable event ID solely from stable source identity"; the issue adds the open question of
whether distinct-rows-get-distinct-ids is also required.

### 3. Root cause

The identity is a **slot address**, not a content address: it hashes a per-file line number
(`line-N`) that is identical across files of the same scenario, and drops the only content-bearing
material already in hand (`raw_checksum`). Two files' first rows share `source_event_id = "line-1"`
and the same `(source_type, source_dataset, scenario_id, dataset_version)`, so they collide.

### 4. Proposed correction

Qualify `line-N` with the per-file `raw_checksum` already on `SourceRecordRef`, so the identity is
unique within a file rather than within a scenario. This satisfies both properties: distinct rows in
distinct files get distinct ids, and re-ingesting the **same** file yields identical ids (the
checksum is stable). Per `identity_rule.md`, move to namespace `events/v2` and state precisely in
the docstring which property is guaranteed. Whether row content itself should participate (beyond
the checksum) is a deliberate, smaller design choice.

### 5. Alternative approaches

- **Add only `raw_checksum`** — the issue's and the approved rule's recommended minimal change.
- **Hash the full serialized row** (all CTU/IoT-23 fields) — strictly content-addressed.
- **Add a per-file qualifier other than the checksum** (e.g. file name) — file-name is arrival
  bookkeeping and less stable than content.
- **Do nothing / tolerate** — keep slot semantics and rely on callers never ingesting two files for
  one scenario.

### 6. Advantages and disadvantages of each

- **Add `raw_checksum` only:** smallest change; material already present; preserves re-ingestion
  stability; collision-free across files. Disadvantage: two identical rows inside one file still
  share an id (they are, by content, the same row).
- **Hash full row:** strongest distinctness. Disadvantage: larger algorithm change, and depends on
  exact formatting/ordering of row serialization, which can wobble across formats.
- **File-name qualifier:** easy but breaks if the same content moves files, and is arrival
  bookkeeping — the very class the rule excludes.
- **Do nothing:** no migration cost but the collision family persists into the frozen corpus.

### 7. Downstream dependencies and potential breaking changes

Because every downstream id is derived from `event_id`, all of `detection_id`, `finding_id`,
`evidence_bundle_id`, `triage_id`, `review_id` change together and stay mutually consistent (per the
approved rule's consequence note). Any persisted `/v1` ids remain explainable because the `/v1`
namespace constant stays in source. No published metric is invalidated (see §8).

### 8. Research, privacy, and governance implications

**Explicitly: changing this id invalidates no published metric.** Verified — `data/evaluation/phase3_analyst_replay/replay_summary.json` and `data/evaluation/phase3_reviewer_simulation/simulation_summary.json` contain **zero** uuid-shaped ids, and `configs/llm_ab_preregistration.json` is `FROZEN_PRE_DATA` with spend 0 and pins no digest value (only prose describing the corpus construction). The frozen A/B protocol describes the corpus by construction, not by digest, and the corpus has never been built or sent. Governance upside: evidence ids now genuinely address the evidence, so trace claims hold.

### 9. Recommended option and justification

Add `raw_checksum` (option 1), per the already-approved `identity_rule.md`, with a `/v2` namespace
and an explicit docstring stating both properties. Engineering judgement: it is the minimal change
that removes the collision class using material already plumbed, and it is contractually settled.

### 10. Whether owner approval is genuinely required

**No — approval already granted.** `identity_rule.md` is approved (owner, 2026-10-09) and already
names this exact resolution. Implementing it executes an approved contract; a fresh approval is not
needed, but the implemented change must satisfy the rule's four verification obligations
(distinctness, stability, duplicate handling, downstream integrity).

---

## Issue #40 — review_id_for ignores final_disposition and subject_role; distinct human judgments collide

**Category: B (product/architectural contract).** `review_id` anchors the human-judgment audit
trail; its field set is contract-level and is already prescribed by the approved `identity_rule.md`.

**Analogy.** Two signed verdicts in the same file folder get the same matter number because the
clerk numbered "decided by Mr X at 9:00 AM", not "decided what". The registry then refuses to file
a second verdict at the same timestamp, so the audit trail loses a real decision.

### 1. Current behaviour and the demonstrated failure

`src/aegistrace/schemas/review.py::review_id_for(*, subject_triage_id, reviewer_ref, decision,
reviewed_at)` derives the id from four inputs. It ignores `final_disposition`, `tier`, `notes`,
`subject_role`, and `supersedes_review_id`. Because `reviewed_at` participates, and because
`ReviewHistory` rejects duplicate ids, **two distinct dispositions at the same instant are
unrepresentable**: `append_review` (`src/aegistrace/review/history.py:39`) refuses the second with
"a review with this identity is already recorded".

Executed (#40): four reviews differing only in `final_disposition` (`confirmed` vs
`COMPLETELY DIFFERENT DISPOSITION`), only `tier`, or only `notes` — all four got id
`43dcd757-aa09-5982-b411-91f491d2bd34`; `records genuinely differ: True`. The ignored
`final_disposition` (the actual conclusion) and `subject_role` (which of the two mutually blind
roles is reviewed) are the most consequential: a review of the analyst vs a review of the
adjudicator, same reviewer/decision/time, are one identity.

### 2. Expected behaviour and the relevant existing contracts

`review_id` anchors the human-judgment record — the audit trail of who decided what about which
conclusion. The approved rule (R2) excludes `reviewed_at` as **recording bookkeeping**, and (R1)
requires `final_disposition`, `subject_role`, and `supersedes_review_id` because the system treats
them as distinguishing a correction or a role. The `HumanReview` schema has two `mode="after"`
validators and a `HumanReview`-`ReviewHistory` subject invariant that depend on this id staying
consistent (see #42).

### 3. Root cause

Same pattern as #38/#35: the identity is a slot address. `reviewed_at` is in the id, so two
distinct conclusions at the same instant collide; `final_disposition` and `subject_role` are omitted
entirely. The naming trap: `decision` (CONFIRM/REVISE/ESCALATE — the *shape*) is in the identity,
while `final_disposition` (the *substance*) is not.

### 4. Proposed correction

Per the approved rule: identity =
`(subject_triage_id, subject_role, reviewer_ref, decision, final_disposition, supersedes_review_id)`.
Drop `reviewed_at`. `tier` and `escalation_state` are excluded as derived (`tier` follows from the
subject via `classify_tier`; `#30` ties `escalation_state` to `decision`). `notes` is excluded as
free text that would make a fragile content address. Namespace `reviews/v2`. This makes distinct
dispositions at the same instant representable.

### 5. Alternative approaches

- **Adopt the approved field set** (subject, role, reviewer, decision, disposition, supersedes).
- **Keep `reviewed_at`** and only add disposition/role — keeps same-instant distinct dispositions
  colliding; rejected by R2.
- **Add `notes`** into the identity — makes the id content-address over prose; rejected by the rule
  as fragile.
- **Add `tier`/`escalation_state`** — both are derived; R2 says derived fields must not be present.

### 6. Advantages and disadvantages of each

- **Approved set:** fixes the actual bug (distinct dispositions at the same instant), follows R1/R2,
  is already owner-specified. Disadvantage: id changes, so any historical `/v1` id must be explained
  via the retained `/v1` namespace (none invalidated — see §8).
- **Keep timestamp:** no improvement to the core collision; same-instant corrections stay
  unrepresentable.
- **Add notes/tier/escalation:** makes the id brittle or redundant; conflicts with the approved rule;
  no functional gain.

### 7. Downstream dependencies and potential breaking changes

`append_review`'s duplicate check and chain-building use `review_id`. The `HumanReview`
`review_id` self-validator (`review.py`) recomputes via `review_id_for`; when the namespace/field
set moves to `/v2`, `review_id_for` and the validator must change together or every constructed
review fails validation. `detection`/`finding`/`triage`/etc. are derived from event ids, so they are
unaffected here; only the review identifier lineage changes.

### 8. Research, privacy, and governance implications

**Explicitly: changing this id invalidates no published metric** — the same verified facts as #38:
the two Phase-3 `*_summary.json` artifacts contain zero uuid-shaped ids, and
`configs/llm_ab_preregistration.json` (`FROZEN_PRE_DATA`, spend 0) pins no digest. Governance
upside is the point of the fix: an audit trail that can represent two distinct human dispositions
is a stronger record of "a human, not a model, made the call".

### 9. Recommended option and justification

Adopt the approved field set. Engineering judgement: it is the only option that removes the
collision at the same timestamp, honours R1 (disposition/role are distinguishing) and R2 (timestamp
is bookkeeping, tier/escalation derived, notes fragile), and is already the owner-approved contract.

### 10. Whether owner approval is genuinely required

**No — approval already granted** via the approved `identity_rule.md`, which specifies this exact
field set. Implement per the rule with `/v2` and satisfy the verification obligations. Fresh
approval is not needed.

---

## Issue #42 — model_copy bypasses HumanReview and ReviewHistory validators (latent)

**Category: A (engineering — safe to implement independently).** It is a defensive hardening of an
existing schema invariant; no product contract or identity-field decision changes, so it does not
need owner sign-off.

**Analogy.** A door lock checks that the tenant is authorised, but the intercom's "send key to the
flat" button hands over the key without running the check. Today nobody uses that button for
humans, but the moment somebody does, an unvetted tenant walks in. You fix the keypath, not the
policy.

### 1. Current behaviour and the demonstrated failure

Pydantic v2 does not re-run validators on `model_copy(update=...)`. Executed (#42):
`HumanReview(decision=REVISE, supersedes=None)` raises `ValidationError` (the
`validate_correction_is_linked` invariant in `review.py` requires a REVISE to name what it
supersedes), but `valid.model_copy(update={"decision": REVISE})` silently produces
`decision=revise supersedes_review_id=None`. Likewise
`ReviewHistory.model_copy(update={"reviews": (foreign,)})` yields a history whose review subject
differs from the history subject (`history.subject=18fc7b3a…`, `review.subject=98e64e5a…`, `MISMATCH
ACCEPTED = True`) — the `validate_subjects_match` validator never runs.

### 2. Expected behaviour and the relevant existing contracts

The schema invariants — every review in a history shares the subject triage id, and a REVISE must
reference its superseded review — are declared as `mode="after"` model validators, i.e. they are
supposed to hold on **every** `HumanReview`/`ReviewHistory` instance by construction. The real
guarantee today is not the schema but `src/aegistrace/review/history.py:25` (manual subject
`raise`) plus the chain checks in `append_review`. This is the same **vacuous verification** shape
the project explicitly guards against (see the behavioural-feature/snapshot fixes): an invariant
that reports success over a scope it does not actually cover.

### 3. Root cause

`model_copy(update=...)` is the documented Pydantic v2 escape hatch from validation. By design it
copies a validated instance and stamps over fields without re-raising validators, so any
`@model_validator(mode="after")` invariant is bypassable by copying a valid instance. Latency
confirmed: grep shows `model_copy` in `src/` only at `features/behavioral.py:235,238`,
`features/causal.py:307,310` (events/sources, not reviews) and `review/history.py:40`
(`ReviewHistory`). `append_review` manually re-checks the subject before the copy, so the projection
path is defended by hand, not by the schema — meaning the schema invariant is weaker than it looks.

### 4. Proposed correction

The issue's preferred option: have `append_review` build a fresh `ReviewHistory` from fields rather
than `model_copy`, so the schema validator runs and the manual checks become belt-and-braces
(defence in depth). Add regression tests pinning both bypasses (REVISE-without-supersedes by any
construction path; review-subject-mismatch by any construction path). Optionally add a
`HumanReview.revalidate()`-style helper as the documented reconstruction path.

### 5. Alternative approaches

1. **Reconstruct instead of `model_copy`** in `append_review` (chosen — issue's option 3).
2. **Document** that `append_review` is the enforcement point, accept the schema gap (cheapest).
3. **Add a revalidation helper** `HumanReview.revalidate()` and route rebuilds through it.
4. **Guard at the type boundary** (`model_construct`-free path) so a corrected review must go
   through the validator.

### 6. Advantages and disadvantages of each

- **Reconstruct:** makes the schema the guarantee again, keeps manuals as defence in depth, small
  diff. Disadvantage: changes how the append-only chain is constructed, which is core to the audit
  trail — must remain behaviour-identical.
- **Document only:** zero code change but leaves a genuine bypass open for the next engineer who
  reaches for `model_copy` (the natural way to build a corrected review).
- **Revalidate helper:** explicit, but requires disciplining all construction sites; the helper is
  easy to forget.
- **Type-boundary guard:** the strongest, but the most invasive; heavier than the latent bug
  warrants today.

### 7. Downstream dependencies and potential breaking changes

`append_review`'s three manual `raise`s (subject mismatch, duplicate id, chain/supersede rules) must
be preserved. The switch from `model_copy` to direct construction must produce an objectively
identical `ReviewHistory`; the schema's `review_id` self-validator will also run, so review
construction must remain self-consistent (relevant if #40 changes `review_id_for` — do #40 and #42
together to avoid a transient mismatch).

### 8. Research, privacy, and governance implications

None by itself — it is latent and no production path currently exploits it. Relevance is the same
governance theme: AegisTrace's claim depends on invariants being enforced **by construction, not by
convention** (explicitly valued in #26). Hardening this keeps the audit-trail invariant genuinely
structural, so it underpins the #40 fix rather than undermining it.

### 9. Recommended option and justification

Reconstruct `ReviewHistory` from fields in `append_review` (option 1), with regression tests and the
manual checks retained. Engineering judgement: it closes the bypass at the one real construction site
(option 1) with a small diff and no contract change, and it is the cheap fix while the latent
window is still truly open — the issue flags that it "should be settled before" broader changes.

### 10. Whether owner approval is genuinely required

**No.** Category A: it is internal defensive hardening with no product or identity-field decision. An
engineer can implement it independently with tests; no owner sign-off is needed, though it should
be sequenced with #40 since the two touch adjacent code.

---

## Category summary

| Issue | Category | One-line justification | Owner approval required? |
|---|---|---|---|
| **#37** empty ingestion | **B** | Changes the CLI/exit/manifest contract and is explicitly deferred to the owner | **Yes** |
| **#38** event identity | **B** | Root of the identity spine; resolution already specified in the approved `identity_rule.md` | No (already approved via rule) |
| **#40** review identity | **B** | Anchors the human-judgment audit trail; already prescribed by the approved rule | No (already approved via rule) |
| **#42** validator bypass | **A** | Defensive hardening of an existing invariant; no contract decision | No |