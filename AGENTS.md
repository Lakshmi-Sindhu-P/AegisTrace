# AegisTrace Agent Instructions

AegisTrace is an evidence-grounded, defensive AI-security research project.

## Persistent Memory Protocol

At the start of every task, before planning, editing, or evaluating the project:

1. Locate and read the repository-root `MEMORY.md` completely.
2. Inspect the relevant repository evidence and reconcile it with `MEMORY.md`.
3. Maintain a strict distinction between `CURRENT / IMPLEMENTED`, `APPROVED INTENT / DESIGN`, `PLANNED, NOT IMPLEMENTED`, and `VALIDATED`.
4. Never infer that a capability is implemented merely because it appears in a prompt, plan, or design document.

While working:

- Follow the architecture, security boundaries, evidence-grounding rules, coding practices, and workflows recorded in `MEMORY.md`.
- Treat code, tests, configuration, datasets, and reproducible artifacts as implementation evidence.
- Treat LLM conclusions and external scanner findings as supporting evidence, never authoritative truth.
- Preserve provenance, uncertainty, original AI outputs, and human-review history.
- Never fabricate metrics, capabilities, deployment status, scale, security impact, or portfolio claims.

Update `MEMORY.md` in the same change whenever work materially changes:

- architecture or component boundaries;
- dependencies or technology choices;
- canonical schemas or public interfaces;
- data-source strategy;
- detection, ML, LLM, or evaluation methodology;
- security or ethical constraints;
- development workflows; or
- milestone implementation or validation status.

For major decisions, reversals, milestone transitions, and validated results, add a concise dated entry to `Episodic Memory (Key Decisions Log)`. Include supporting file paths, tests, experiment artifacts, or commands where practical. Do not log routine edits or use episodic memory as a general activity log.

Promote functionality from `PLANNED` to `IMPLEMENTED` and then to `VALIDATED` only when repository evidence supports the transition. If `MEMORY.md` conflicts with verified repository state, repository evidence wins: correct the stale memory and log the correction when it materially changes project understanding.

Before completing a task:

1. Decide whether the work created durable architectural or procedural knowledge.
2. Update `MEMORY.md` when required.
3. Verify that documentation and portfolio claims match actual evidence.
4. Report unresolved conflicts between project intent and implementation.

## Issue, Trace, and Reusable-Lesson Protocol

GitHub Issues are the durable history for planned work and meaningful problems. Use an issue for
material bugs, failures, blockers, regressions, architectural decisions, follow-ups, and approved
work. The issue must preserve enough history to reconstruct:

```text
problem -> cause -> attempts -> failures -> solution -> change -> proof
```

Use these issue states in the issue body and status comments:

- `PROPOSED` — scoped but not approved to run.
- `READY` — approved and dependency-free (or dependencies satisfied).
- `IN_PROGRESS` — actively owned by one workspace/branch.
- `BLOCKED_HUMAN` — exact human input, permission, or decision is required; unrelated `READY`
  issues remain runnable.
- `VALIDATING` — implementation is complete and evidence is being checked.
- `DONE` — validation, commits/PRs, outcome, and follow-ups are recorded.
- `SUPERSEDED` — replaced by a linked issue or solution version; history is retained.

Every meaningful action must link to an issue and emit a redacted local trace record. A trace must
link the issue, trace/span lineage, Conductor workspace and agent/session, branch and commit/code
version, action, source references, validation, outcome, and approval state. Use content digests for
commands and artifacts; never store secrets or unredacted tool output. Record concise reason codes
and confidence basis, not hidden chain-of-thought.

Deterministic source references must identify repository paths with commit/blob context, commands
with their environment and result, external URLs with retrieval time and content digest, and linked
issue/PR identifiers. A model-generated suggestion is a hypothesis until supported by repository
evidence, tests, or an authoritative source.

Reusable lessons belong in the versioned solution-knowledge store, not in place of `MEMORY.md`,
Issues, or traces. A lesson is admitted only when it is generalizable and validated. Each lesson
version must link its originating issue and trace, applicable code/commit version, problem pattern,
solution principle, validation evidence, and supersession links. Revalidate a prior lesson against
current code before reuse. If drift changes its applicability, create/link a new issue and append a
new version; never overwrite an old version.

No agent may autonomously change `AGENTS.md`, security boundaries, sealed-data policy, merge
privileges, issue/trace rules, or other high-impact governance. Such changes require a linked issue,
proposed diff, evidence/tests, review, and explicit owner approval. Retrospectives may propose
improvement issues but may not promote their own lessons without that review.

Independent `READY` issues may run concurrently in isolated Conductor workspaces, branches, and
PRs. Use one shared workspace only for one intentionally coupled deliverable. A future scheduler may
consume the same states and linkage fields, but no autonomous scheduler is enabled by this protocol.

## Project Guardrails

- Keep all security work defensive and confined to offline datasets, synthetic fixtures, localhost, isolated containers, controlled environments, or explicitly authorized defensive systems.
- Prefer simple, justified, local-first designs and reproducible results over feature count or resume-driven complexity.
- Keep LLM output structured, evidence-linked, uncertainty-aware, and subordinate to deterministic evidence and human review.
- Build incrementally in the phase order recorded in `MEMORY.md`; do not skip foundations to implement later-stage features.
- Explain meaningful implementation work in a teachable way, including the engineering reason, relevant security and AI/ML concepts, key code, and interview-level summary.
