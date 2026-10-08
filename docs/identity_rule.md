# The AegisTrace Identity Rule

**Status: APPROVED (owner, 2026-10-09). Applies to every identifier AegisTrace derives from content.**

## The rule

> An identifier is a **versioned content address over exactly the fields that constitute the
> entity's identity — and over nothing else.**

A field **belongs** in an identity when two instances that differ in that field are genuinely two
different things, and a consumer must be able to tell them apart.

A field **does not belong** when it is any of these three:

| Excluded kind | Meaning | Example |
|---|---|---|
| **Arrival bookkeeping** | where the record sat in the input, its position in a list, call order | `line-42` as the *only* thing distinguishing two flows |
| **Recording bookkeeping** | when something was observed, ingested, processed, or written down | `reviewed_at` |
| **Derived** | recomputable from fields already in the identity | `snapshot_digest` given the bundle id |

### Corollaries

- **R1 — Nothing that must be distinguished may be absent.** If the system treats two things as
  different, their identities must differ. A comparison engine that reports `severity_mismatch`
  treats severity as distinguishing; the identity must agree.
- **R2 — Nothing that is bookkeeping or derived may be present.** Including it creates collisions
  that have nothing to do with the entity, and it makes an id change for reasons the entity did not.
- **R3 — Changing the field set changes the algorithm, so it takes a new version.** Every identity
  kind already uses a versioned `uuid5` namespace (`/v1`, `/v2`, …). A change to the field set
  introduces `/v2`; `/v1` stays describable so historical records remain interpretable.

### Why this rule exists

AegisTrace's central claim is that a conclusion can be traced back to the evidence that supports it.
That claim rests on identifiers. An identifier that does not depend on the thing it identifies looks
like a content address but behaves as a **slot address** — a name for a *position*, not for a
*thing*. Two distinct observations then share one name, and the trace stops being a trace.

This was found three times independently (`#35`, `#38`, `#40`), which is what makes it a rule rather
than a bug fix.

---

## Application to the three identity kinds

### 1. Evidence — network events (`#38`)

`event_id_for` hashes `(source_type, source_dataset, scenario_id, dataset_version, source_event_id)`.

`source_event_id` is built as `f"line-{line_number}"` — **arrival bookkeeping**, and per-file. Two
different records in two different files of the same scenario therefore share an identity:

```text
A: tcp malicious 1000B  fileA -> 465820a4-d6c9-50fd-86ba-0c20a2a34015
B: udp benign  123456B  fileB -> 465820a4-d6c9-50fd-86ba-0c20a2a34015
```

`SourceRecordRef` **already carries** `raw_checksum`, and ingestion already computes it. The material
needed to make the identity content-bearing is present and was unused.

**Resolution.** Include `raw_checksum`, which qualifies `line-N` to *the file it was read from*.
Both properties now hold: re-ingesting the same file yields the same ids (the checksum is stable),
and different files cannot collide. Namespace `events/v2`.

### 2. AI assessments (`#35`)

`triage_id_for` hashes `(role, evidence_bundle_id, input_snapshot_digest, category, summary)`.

It omits `severity` and `cited_evidence_ids`. The agreement engine emits `severity_mismatch` and
`evidence_divergence`, so the system **already treats both as distinguishing** — R1.

The asymmetry is the sharpest evidence that this is an oversight rather than a choice:
`failed_attempt_id_for` **is** content-addressed over `raw_digest`, so a *rejected* assessment is
more uniquely identified than an *admitted* one.

**Resolution.** Add `severity` and `cited_evidence_ids` (sorted, so citation order cannot matter).
Namespace `triage-assessments/v2`. `input_snapshot_digest` is retained deliberately: it is the exact
input the assessor saw, and recording it is load-bearing for mutual blindness even though it is
derivable from the bundle.

### 3. Human review decisions (`#40`)

`review_id_for` hashes `(subject_triage_id, reviewer_ref, decision, reviewed_at)`.

`reviewed_at` is **recording bookkeeping** — R2 — and it is what makes two distinct dispositions at
the same instant collide. Omitted: `final_disposition` (the actual conclusion), `subject_role`
(which of the two mutually blind roles is being reviewed), `supersedes_review_id` (what the
correction corrects). All three are defining — R1.

Note the naming trap: `decision` (CONFIRM / REVISE / ESCALATE) is in the identity while
`final_disposition` (what was actually concluded) is not. The identity covered the *shape* of the
judgment, not its *substance*.

**Resolution.** Identity = `(subject_triage_id, subject_role, reviewer_ref, decision,
final_disposition, supersedes_review_id)`. `reviewed_at` is dropped. `tier` and `escalation_state`
are excluded as derived — `tier` follows from the subject via `classify_tier`, and `#30` ties
`escalation_state` to `decision`. `notes` is excluded as free text, which would make a fragile
content address out of prose. Namespace `reviews/v2`.

---

## Consequences of the change

- **No published metric is invalidated.** Verified: no `corpus_digest` *value* is pinned in any
  config or doc (only prose describing it), and the Phase-3 artifacts
  `data/evaluation/phase3_analyst_replay/replay_summary.json` and
  `data/evaluation/phase3_reviewer_simulation/simulation_summary.json` contain **zero** uuid-shaped
  ids. `configs/llm_ab_preregistration.json` is `FROZEN_PRE_DATA` with spend 0 and pins no digest.
- **The frozen A/B protocol is untouched.** It describes the corpus as "the deterministic label-free
  corpus built by `build_corpus` over the frozen evidence bundles" — a construction, not a digest.
  The corpus will have different ids after this change, and it had never been built or sent.
- **Historical records stay interpretable.** The `/v1` namespace constants remain in the source, so a
  pre-change id can still be explained by naming the version that produced it.
- **Downstream ids follow automatically.** `detection_id`, `finding_id`, `evidence_bundle_id`,
  `triage_id`, `comparison_id` and `review_id` are all derived, so they change together and stay
  mutually consistent.

## Verification obligations

Any change under this rule must demonstrate all four:

1. **Distinctness** — two instances differing in a defining field get different ids.
2. **Stability** — re-deriving from identical input gives identical ids, across processes.
3. **Duplicate handling** — recording the same thing twice is detected as a duplicate, not silently
   merged; and a genuine second decision is *not* rejected as one.
4. **Downstream integrity** — every reference in the spine still resolves to the object it names.

## Rules for future work

- Before adding a field to an identity, ask: *if two instances differ only here, are they two
  things?* If no, do not add it.
- Before removing one, check nothing must distinguish on it.
- Never reuse a namespace version for a changed field set.
- Never make an identity depend on input order, list position, or wall-clock time.
