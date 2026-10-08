# Phase 4 Learning Note: Identity, Evidence, and Human Judgment

This note explains the one idea behind issues #35, #38, #39, #40 and #41, in plain language. The
normative rule is [`docs/identity_rule.md`](../identity_rule.md); the per-issue analysis is
[`docs/identity_decision_register.md`](../identity_decision_register.md). Neither is repeated here.

## The idea: a slot address versus a content address

Imagine a hotel. Room 412 is a **slot address** — it tells you where to *find* something. It says
nothing about who is in the room. If the guest changes, the address does not.

A passport number is a **content address** — it is derived from facts about a specific person. Two
different people cannot share one, and the same person keeps theirs.

AegisTrace had built slot addresses and was calling them identities. Every id was derived from
*where a thing sat in a stream* — the row number, the call order — rather than from *what the thing
was*. That works perfectly until two different things occupy the same slot.

## Why that is dangerous in an evidence system, not just untidy

AegisTrace's whole claim is that a conclusion can be traced back to the evidence it rests on. If two
different pieces of evidence can share an identifier, then a citation pointing at that identifier no
longer points at one thing. The traceability claim quietly stops being true while every test still
passes — because the tests were checking that ids *exist*, not that they *distinguish*.

The three concrete failures:

| Issue | What was hashed | What was missed | Result |
|---|---|---|---|
| #38 | `line-N` — the row's position in one file | which file it came from | two different files of one scenario collided on every matching line |
| #40 | who reviewed, and *when* they wrote it down | **what they decided** | four reviews with different conclusions shared one id |
| #35 | the summary sentence | severity and cited evidence | two assessments the engine calls "disagreeing" shared one id |

## The rule, and the test for any field

> An identifier is a versioned content address over exactly the fields that constitute the entity's
> identity — and over nothing else.

To decide whether a field belongs, ask: **if two instances differ only in this field, are they
genuinely different things that a consumer must tell apart?**

- `final_disposition` (what the reviewer decided) → yes, belongs.
- `reviewed_at` (when they typed it) → no. It is **recording bookkeeping**. Two people can reach the
  same conclusion at different times; that does not make it a different conclusion.
- `line-N` (position in the file) → no. It is **arrival bookkeeping**.
- `tier` (computed from the assessments) → no. It is **derived**; deriving it from fields already in
  the hash adds nothing and creates a second source of truth.

Two further subtleties worth internalising:

- **Sort what has no order.** A reviewer listing evidence A, B, C has not made a different finding
  than one listing C, B, A. So citations are sorted before hashing. An ordering that carries no
  meaning must not leak into an identity.
- **Keep what pins the input.** `input_snapshot_digest` looks like bookkeeping but is retained: it
  records the *exact* bytes both blind assessors saw, which is what makes their mutual blindness
  checkable. That is substance, not timestamp.

## The trap this work was really about: vacuous verification

The reason these defects survived a 400-test suite is the most transferable lesson in this note.

A test that checks `id_a != id_b` passes for *any* hash function, including one that ignores
everything. It is a test that cannot fail, and a guard that cannot fail is not a guard. This project
has now recorded that class eleven times.

So the rule comes with four obligations, and **each must be tested in both directions**:

1. **Distinctness** — things that differ get different ids. *And the falsifier:* under the old scheme
   they genuinely collided, so the test asserts the defect was real rather than assumed.
2. **Stability** — the same thing always gets the same id.
3. **Duplicate handling** — a real repeat is refused, *and* a genuine second decision is accepted.
   Widening an identity can break the second half; a changed mind must be recordable as a correction.
4. **Downstream integrity** — every citation still resolves. An id change that silently orphans a
   reference is worse than the collision it fixed.

## Two traps hit while doing this work

Recorded because both are more instructive than the fix.

**The measuring instrument was wrong, not the code — three times in one round.** My first attempt to
prove the old ids reproduced patched only the parser's import binding. `SecurityEvent` has a
validator that *recomputes* the id from the source, so every row failed validation and I got zero
events. The empty result initially looked like evidence. The lesson: when a measurement returns a
surprising answer, suspect the instrument first — this was the ninth occurrence in the project.

**A golden digest can test the wrong thing while looking rigorous.** A pinned digest from issue #22
was named "feature values are unchanged by the ordering fix", but it hashed `(event_id, values)`
pairs — so it moved when the id scheme changed, which has nothing to do with values or ordering. It
was re-captured, and a second id-free assertion was added so it now tests the property in its name.

## How to check whether values changed, not just ids

A green suite cannot tell you this. What can:

1. Patch the *old* identity functions into **every** binding — the producer and any validator.
2. Re-run and confirm the old pinned digests reproduce exactly.
3. Compare the id-free content on both sides.

Done here, all three pinned digests reproduced exactly (`48435f1e4ad4`, `7411b8bf8cb3`,
`7c8a256bc0af`) and the id-free value multisets were byte-identical. That is what licenses the claim
"only the identifiers changed".

## Where the frozen research sits

Changing an id scheme in a research project is a governance question, not just a refactor. Before
touching it, three things were checked and none were assumed: no digest value is pinned in the
preregistration, the Phase-3 artifacts contain zero uuid-shaped ids, and the preregistration is
`FROZEN_PRE_DATA` with zero spend. So no published metric is invalidated. Had any digest been pinned,
the correct action would have been to stop and ask, not to update the constant.

The ordering mattered too: these ids feed the corpus, so they had to be settled *before* the frozen
A/B runs rather than after.

## Interview-level summary

> AegisTrace derived identifiers from a record's position in a stream rather than its content, so
> three different entity types could each mint one id for two genuinely different things — which
> undermines the project's central traceability claim while all tests pass. I generalised the three
> reports into one rule: an identifier is a content address over exactly the defining fields, and
> over nothing else, with arrival bookkeeping, recording timestamps and derived values excluded. I
> versioned the namespaces so historical records stay describable, and proved the change touched only
> identifiers and no feature value by reproducing the old pinned digests through the legacy functions
> with every binding patched. The deeper lesson was that the tests which should have caught this were
> written to pass for any hash function — so each of the four obligations is now tested together with
> its falsifier.
