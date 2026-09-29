# Threat and Ethical Boundary

**Status:** Phase 0 defensive threat model. Review whenever a new source, network service, LLM provider, or deployment target is introduced.

## Protected Assets

- Integrity of raw and normalized evidence.
- Provenance linking events, transformations, detections, models, prompts, and reviews.
- Dataset and experiment reproducibility.
- API keys, reviewer identity, local paths, and configuration secrets.
- Potentially sensitive IP addresses, credentials, commands, user agents, and Cowrie artifacts.
- Accuracy of public documentation and portfolio claims.

## Trust Boundaries

```text
Third-party files/APIs ──untrusted──> source adapters
Controlled Cowrie      ──untrusted──> local raw store
Normalized records     ──validated──> detectors
Evidence bundle        ──bounded────> external/local LLM
LLM response           ──untrusted──> schema + evidence validator
Validated proposal     ──advisory───> human reviewer
Reviewer decision      ──audited────> final disposition
```

Validation changes the form of data; it does not make the underlying claim true.

## Threats and Mitigations

| Threat | Example | Mitigation |
|---|---|---|
| Malformed or adversarial input | Oversized fields, invalid timestamps, prompt-like commands | Bounded parsing, size limits, schema validation, quarantine, and no execution of source content |
| Prompt injection through telemetry | A command says to ignore instructions or reveal secrets | Delimit evidence as data, use structured fields, fixed system policy, no tools/secrets in the triage context, validate output |
| Evidence tampering | Raw file changes after an experiment | SHA-256 manifests, immutable raw references, code revision and adapter version in runs |
| Provenance loss | A transformed row cannot be traced to its source | Deterministic event IDs and required source/transformation metadata |
| Label leakage | `detailed-label` appears in features | Feature allowlist and tests that reject prohibited columns |
| Cross-split leakage | Near-duplicate flows occur in train and test | Deduplicate before grouped/time/scenario splitting |
| Secret disclosure | API key enters logs or an LLM prompt | Environment-based secrets, redaction, prompt allowlist, secret scanning, no debug payload logging by default |
| Sensitive-data disclosure | Honeypot credentials or public IPs enter Git/screenshots | Local ignored raw storage, synthetic examples, redacted UI, retention policy |
| Unsafe honeypot exposure | Cowrie is reachable from the internet | Localhost binding, isolated Docker network, controlled sessions, no port forwarding |
| LLM overclaim | Output states “compromised” from a scan pattern | Evidence IDs, uncertainty fields, unsupported-claim rules, human review |
| Scanner authority inflation | Upstream “critical” finding becomes confirmed incident | Preserve source claim and confidence; require independent evidence and reviewer disposition |
| Dependency/supply-chain risk | Unpinned packages or container images change | Lock dependencies, pin container digest/version, scan before releases, minimize dependencies |
| Denial of service/cost | Huge input or repeated LLM/API requests | Batch and field limits, caching, budgets, retries with caps, offline test doubles |
| Audit mutation | Reviewer or process overwrites original AI output | Append-only logical records and immutable IDs |
| Misleading public claim | Prototype result presented as operational performance | Resume-evidence ledger and claim review before publication |

## Defensive Operating Rules

- Do not scan, probe, exploit, authenticate against, or collect from systems without explicit authorization.
- Do not generate exploit payloads, malware, persistence, authentication bypasses, or credential-attack automation.
- Do not expose an intentionally vulnerable service to the public internet.
- Use offline datasets, safe synthetic records, localhost, isolated containers, or explicitly controlled systems.
- Treat commands and payloads in telemetry as inert evidence; never execute them.
- Stop and redesign any test whose defensive value does not justify its security risk.

## LLM-Specific Rules

- The evidence package is an allowlist, not a dump of all stored data.
- Source strings are quoted/serialized as untrusted data and never interpolated into system instructions.
- The model receives no filesystem, shell, network, email, or security-tool execution capability for triage.
- Secrets and raw credentials are excluded or redacted before a request leaves the process.
- Provider, model, prompt version, evidence IDs, timestamps, and validation result are stored.
- Model output is a proposal. It cannot alter events, detections, or final disposition.
- Provider retention and privacy terms must be reviewed before sending non-synthetic data.

## Cowrie Containment

Initial Cowrie work is limited to local controlled sessions. The container should run without unnecessary host mounts or privileges, on a dedicated network, with a pinned image. Only required log output is mounted. Internet egress should be disabled when feasible. Downloads and proxy/high-interaction modes are not needed for the initial adapter.

## Incident Response for the Project

If secrets or sensitive raw data are committed or sent to an unintended provider:

1. Stop processing and preserve the relevant audit information without copying the secret further.
2. Revoke or rotate the credential.
3. Remove sensitive data from active artifacts using an approved history-remediation process.
4. Document impact and corrective controls without reproducing the secret.
5. Add a regression check and update project memory if architecture or workflow changes.

## Out of Scope for V1

- Multi-tenant authorization and role-based access.
- Public service hardening or internet-facing deployment.
- Automated response, blocking, quarantine, or remediation.
- Malware detonation and artifact reverse engineering.
- Formal compliance certification.

These exclusions must remain visible in demos and portfolio descriptions.
