# Triage Provider Boundary

**Status: IMPLEMENTED (offline boundary only) — no provider is configured, and no data has been
sent anywhere.**

## What the boundary is

The boundary is the two modules that stand between an evidence bundle and anything that could
produce an assessment:

- `src/aegistrace/triage/provider.py` — the provider contract (`ProviderKind`,
  `ProviderDescriptor`, `ProviderRequest`, `ProviderResponse`, the `TriageProvider` protocol) and
  the only two providers that exist: `RecordedTriageProvider` (deterministic replay of already
  captured text) and `StubTriageProvider` (mechanical text derived from the request alone).
- `src/aegistrace/triage/run.py` — `run_independent_triage`, the orchestrator that refuses remote
  providers, builds the snapshot once per bundle, sends the identical snapshot to both roles,
  admits assessments through the existing `build_assessment`, compares them with the existing
  `compare_assessments`, and enforces the freeze budget.

The boundary does not replace the existing isolation and admission contracts; it composes them.
It imports no HTTP, socket, or LLM client, and it adds no credential path.

## Why egress is blocked in code, not by convention

The governing principle is that **AegisTrace must not send anything anywhere without human
interference**. A convention ("do not call the API yet") is a statement about the current
intention of whoever is editing the repository; it does not survive a later refactor, a copied
snippet, or an automated agent. AegisTrace therefore makes the current state executable:

1. **No transport exists.** Neither new module imports `requests`, `httpx`, `aiohttp`, `urllib`,
   `http.client`, `socket`, `openai`, `anthropic`, or `litellm`. A regression test
   (`test_boundary_modules_cannot_open_a_network_connection`) scans the two modules' import lines
   and fails if such an import appears. There is no client object to misuse.
2. **Contradictory descriptors are unrepresentable.** `ProviderDescriptor` rejects a `REMOTE`
   descriptor with `requires_egress=False`, and rejects any `OFFLINE_*` descriptor with
   `requires_egress=True`.
3. **Offline output is permanently synthetic.** `ProviderResponse` forces `synthetic=True` for any
   response whose descriptor is not `REMOTE`, so a recorded or stub response cannot be presented
   as a real model's assessment. `StubTriageProvider` additionally requires a `model_id` beginning
   with `stub-` and `stub` in `model_family`, so it cannot be named like a real model.
4. **Replay cannot invent an answer.** `RecordedTriageProvider` is keyed by
   `(role, snapshot_digest)`; a missing key raises an error that names the role and the digest
   rather than returning empty or fabricated text.

## Exact refusal behaviour

`assert_provider_permitted(descriptor, freeze_status)` returns normally when
`descriptor.requires_egress` is `False`. When it is `True` and the observed status is not in
`APPROVED_EGRESS_FREEZE_STATUSES` — currently only `APPROVED`, `EGRESS_APPROVED`,
`HUMAN_APPROVED` — it raises `PermissionError`. `BLOCKED_HUMAN` is deliberately absent from that
allowlist. The message names the provider, the model, and the observed status, e.g.:

```text
provider 'remote-llm-provider' (model 'remote-model-v1') requires network egress, but freeze
status 'BLOCKED_HUMAN' is not an approved egress status (APPROVED, EGRESS_APPROVED,
HUMAN_APPROVED); refusing to run it
```

`run_independent_triage` calls this for **both** providers before it reads the budget, builds a
snapshot, or constructs a request. The refusal is a raised error, not a warning, and it is
test-covered (`test_remote_provider_is_refused_under_blocked_human`,
`test_assert_provider_permitted_refuses_and_allows`); the test also proves the remote provider's
`complete` is never reached.

Two other conditions are recorded as an abort on the returned `TriageRun` rather than raised,
because they are ordinary outcomes of a bounded run, not governance refusals:

- **Budget exhaustion.** Exceeding `max_bundles_per_run`, `max_assessments_per_run`, or
  `max_total_calls` stops the run and records an `abort_reason`.
- **Snapshot-digest mismatch.** If either response reports a digest other than the one built from
  the bundle, the run aborts before assessment or comparison, because comparing two different
  inputs would measure the inputs rather than the assessors.

## Current configuration and data status

- `configs/triage_provider_freeze.json` has `status: "BLOCKED_HUMAN"` and
  `transport_status: "NOT IMPLEMENTED - no client exists"`.
- **No provider is configured.** The two roles are marked `UNSET - pending owner approval`, and
  the assessor-independence requirement is `NOT ESTABLISHED`.
- **No data has been sent anywhere.** `measured_spend` is `0`. Both implemented providers are
  offline; a run using them produces `synthetic=True` output that must not be treated as a model's
  assessment.
- Enabling egress requires a human to approve a provider, a credential path, and an approved
  freeze status. That is a governance decision this boundary is built to force, not to pre-empt.
