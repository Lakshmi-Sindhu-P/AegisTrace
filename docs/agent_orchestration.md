# Agent orchestration and provenance protocol

**Status:** `IMPLEMENTED` foundation; autonomous scheduling and self-modifying behavior are not
implemented.

This protocol keeps three records separate:

1. **GitHub Issues** are durable work/problem history.
2. **Local traces** are redacted execution provenance and remain gitignored.
3. **Solution knowledge** contains only reusable, validated engineering lessons; it does not replace
   `MEMORY.md`, Issues, or traces.

## Issue lifecycle

Issue bodies use one of these states:

```text
PROPOSED -> READY -> IN_PROGRESS -> VALIDATING -> DONE
                         |              |
                         v              v
                   BLOCKED_HUMAN    SUPERSEDED
```

`BLOCKED_HUMAN` must state the exact missing decision, permission, or artifact. It does not block
unrelated `READY` issues. Dependencies are explicit issue references; readiness is determined by
state and dependency completion, not by an LLM judgment.

Every meaningful issue preserves the causal chain:

```text
problem -> cause -> attempts -> failures -> solution -> change -> proof
```

The issue links source evidence, trace IDs, code/commit versions, validation commands, PRs, outcome,
and follow-ups. Comments may summarize trace events, but raw traces are never copied into GitHub.

Issue forms live under `.github/ISSUE_TEMPLATE/` and are intentionally structured for deterministic
review. GitHub issue numbers are external identifiers; local traces store the repository-qualified
issue reference and a content digest when an issue snapshot is used as evidence.

## Local execution traces

Trace files are redacted JSONL under ignored local paths. Each record is validated by
`src/aegistrace/schemas/agent_trace.py` and `scripts/validate_agent_trace.py`.

The record links:

```text
issue_ref <-> trace_id/span_id lineage <-> workspace/agent
          <-> branch/commit <-> action/source refs
          <-> validation refs <-> outcome
```

Repository references should include a commit/blob context where available. Commands and artifacts
use SHA-256 digests. External sources include URL, retrieval context, and a digest when material.
Trace records contain concise reason codes and confidence basis, not hidden chain-of-thought, secrets,
or unredacted tool output. Field names are compatible with OpenTelemetry trace/span correlation, but
the project does not install or run an OpenTelemetry stack in this phase.

## Versioned solution knowledge

`docs/solution_knowledge.json` is the tracked store. Its Pydantic model is `SolutionKnowledge` and
its validator is `scripts/validate_solution_knowledge.py`.

Each lesson version must include:

- originating issue and trace;
- applicable code/commit version;
- reusable problem pattern and solution principle;
- validation and evidence references;
- current/superseded status and supersession links.

Before reusing a lesson, compare its applicable code version and assumptions with the current
repository. If drift changes the solution, create or link a new issue and append a new version. Old
versions are never overwritten. Task-specific attempts, failures, and raw evidence stay in Issues
and traces.

## Concurrency and escalation

Independent `READY` issues may use separate Conductor workspaces, branches, and PRs. One shared
workspace is allowed only for one intentionally coupled deliverable. No scheduler claims work in
this foundation; future scheduling can consume the same issue states and linkage fields.

No agent may autonomously change governance, security boundaries, sealed-data policy, merge
privileges, or this protocol. Such changes require a linked issue, proposed diff, tests/evidence,
review, and explicit owner approval.

## Validation commands

```bash
uv run python scripts/validate_agent_trace.py path/to/trace.jsonl
uv run python scripts/validate_solution_knowledge.py docs/solution_knowledge.json
```
