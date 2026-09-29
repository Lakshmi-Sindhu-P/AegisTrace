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

## Project Guardrails

- Keep all security work defensive and confined to offline datasets, synthetic fixtures, localhost, isolated containers, controlled environments, or explicitly authorized defensive systems.
- Prefer simple, justified, local-first designs and reproducible results over feature count or resume-driven complexity.
- Keep LLM output structured, evidence-linked, uncertainty-aware, and subordinate to deterministic evidence and human review.
- Build incrementally in the phase order recorded in `MEMORY.md`; do not skip foundations to implement later-stage features.
- Explain meaningful implementation work in a teachable way, including the engineering reason, relevant security and AI/ML concepts, key code, and interview-level summary.
