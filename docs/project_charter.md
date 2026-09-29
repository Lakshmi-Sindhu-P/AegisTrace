# AegisTrace Project Charter

**Status:** Phase 0 design baseline amended on 2026-09-22 after Phase 3 hardening. The amended
multi-model investigation architecture is approved intent; no new capability is implemented by this
document.

## Problem Statement

Security analysts often need to connect raw telemetry, detector outputs, and incomplete context before deciding whether an event deserves investigation. Rules are transparent but narrow; supervised models can miss unfamiliar behavior; anomaly models can surface unusual behavior but are hard to interpret; LLMs can summarize evidence but may invent confident security conclusions.

AegisTrace will test a constrained alternative: run justified deterministic, supervised, anomaly, temporal, and reference-backed specialists; analyze disagreement before optional interpretable fusion; aggregate alerts into provenance-preserving findings; verify claim types; ask two isolated AI roles for structured, uncertainty-aware assessments; and require tiered human review. Every stage must preserve enough provenance to reconstruct why a recommendation was produced.

The project is successful only if its claims are measurable and reproducible. A fluent AI explanation is not evidence of correct triage.

## Objectives

1. Normalize heterogeneous defensive telemetry without erasing source-specific meaning.
2. Preserve source, transformation, detector, model, prompt, and review provenance.
3. Establish transparent rule and statistical/ML baselines before adding anomaly, temporal, or LLM layers.
4. Measure when detector specialists agree or disagree and analyze their failure modes before any fusion.
5. Aggregate related detections into findings without losing event-level provenance or using research labels for queue priority.
6. Verify whether claims are observed facts, deterministic derivations, reference-backed facts, model inference, AI interpretation, or unknown.
7. Determine whether independent evidence-constrained AI roles improve triage completeness or escalation quality without increasing unsupported claims.
8. Make uncertainty and `insufficient_evidence` first-class outcomes and preserve original AI output and human decisions as auditable history.
9. Produce a local, reproducible portfolio artifact whose claims match repository evidence.

## Non-Goals

AegisTrace is not:

- an autonomous SOC or final decision-maker;
- a production intrusion-detection or prevention system;
- a penetration-testing, reconnaissance, exploitation, malware, or credential-attack tool;
- a real-time, high-throughput streaming platform in V1;
- a threat-intelligence blocklist;
- a replacement for source-specific forensic tools;
- a benchmark claiming broad operational generalization from a few datasets;
- a reason to introduce microservices, Kafka, Kubernetes, a graph database, or multiple clouds without measured need.

## Research Questions

### Primary

Can a provenance-first, multi-model security system combine deterministic, supervised, anomaly,
temporal, and reference-backed evidence to generate trustworthy investigation recommendations while
clearly separating observed facts from inference and enabling a junior reviewer to handle basic
triage without eliminating expert escalation?

### Secondary

1. How accurately do transparent rules and simple supervised specialists detect known suspicious patterns across scenarios?
2. Does an anomaly-ranking specialist surface useful unknown or unusual behavior without being mislabeled as maliciousness?
3. Where do detector families disagree, and are their residual errors complementary enough to justify fusion?
4. Can deterministic aggregation reduce duplicate reviewer work while preserving event and evidence provenance?
5. Does verification correctly separate observed facts, derivations, references, model inference, AI interpretation, and unknowns?
6. Does an explicit, bounded evidence package reduce unsupported AI claims?
7. How often do independent AI roles corroborate, contradict, or appropriately abstain?
8. How often and why does a junior or expert reviewer override a recommendation?
9. Does AI assistance improve triage completeness or time without reducing reliability?
10. How well calibrated are detector scores and AI confidence statements?

No research question is answered until the evaluation protocol and results are committed as reproducible artifacts.

## Scope and Success Criteria

### V1 includes

- at least two source adapters, initially IoT-23 and controlled Cowrie JSON;
- a versioned canonical event envelope with source-specific typed details;
- validation, explicit null handling, deduplication, and provenance;
- Parquet storage queried through DuckDB;
- deterministic rules, a statistical baseline, and one interpretable ML baseline;
- finding aggregation and immutable evidence bundles;
- schema-validated LLM triage with evidence references and unsupported-claim checks;
- immutable AI results plus human review decisions;
- comparative detector/LLM/human evaluation;
- a minimal local review UI, documented limitations, tests, and reproducible commands.

### V1 succeeds when

- a new checkout can reproduce the documented pipeline from versioned inputs or safe fixtures;
- integration tests trace one record from raw input through review without losing provenance;
- detector and AI metrics are generated by scripts, not copied into prose;
- evaluation splits prevent obvious capture or temporal leakage;
- every displayed conclusion links to its supporting evidence;
- unsupported claims and uncertainty are visible to the reviewer;
- the repository clearly separates implemented, validated, planned, and non-claimable work.

Cloud deployment and scanner integrations are optional after V1 and are not success criteria.

## Assumptions

- The first user and reviewer is the project builder; multi-user auth and concurrency are out of scope.
- Batch processing is sufficient for V1; no streaming system is required.
- Raw third-party datasets remain outside Git and can be reacquired from documented sources.
- A laptop-scale subset is sufficient to validate the architecture and methods.
- IoT-23 labels are useful research annotations, not unquestionable operational truth.
- Cowrie data is produced only through controlled, local sessions during early development.
- DShield availability and response shapes may change; its adapter must fail safely and cache provenance.
- One provider-neutral LLM interface is sufficient; provider choice is deferred until the evidence pipeline and evaluation corpus exist.
- Human-review measurements from one reviewer are case-study evidence, not population-level claims.

## Major Risks and Controls

| Risk | Why it matters | Required control |
|---|---|---|
| Capture leakage | Randomly splitting correlated flows can produce misleading ML results. | Group by scenario/session and prefer temporal or held-out-scenario evaluation. |
| Label leakage | Dataset labels or source names may accidentally become features. | Maintain an explicit feature allowlist and test excluded columns. |
| Dataset bias | IoT-23 represents specific devices, years, malware families, and labeling rules. | Report per-scenario results and do not claim general SOC performance. |
| Schema dilution | One wide table can become mostly nulls and erase source semantics. | Use a common envelope plus typed source details; measure missingness. |
| LLM hallucination | Fluent output can add unsupported compromise or intent claims. | Require evidence IDs, structured output, `insufficient_evidence`, and post-generation validation. |
| Confidence misuse | LLM confidence text is not a calibrated probability. | Store it separately from detector scores and evaluate calibration empirically. |
| Unlabeled telemetry misuse | DShield reports can include false positives. | Use for exploration/generalization only; ground-truth label remains unknown. |
| Honeypot exposure | Public Cowrie deployment can attract real attacks and sensitive data. | Bind locally, isolate in Docker, use controlled sessions, and never expose it during initial phases. |
| Sensitive logs | IPs, credentials, commands, and downloaded files may be sensitive. | Keep raw data out of Git, minimize retention, redact displays, and document handling. |
| Resume inflation | Planned or prototype work can be presented as validated. | Maintain `docs/resume_evidence.md` and generate claims only from evidence. |
| Scope expansion | Four sources, ML, LLMs, UI, and cloud can overwhelm a portfolio project. | Implement one vertical slice at a time with exit criteria. |

## Milestone Plan

| Milestone | Deliverable | Exit evidence |
|---|---|---|
| 0. Charter | Coherent scope, architecture, dataset, safety, evaluation, and learning docs | Phase 0 documents agree; critique addressed; memory updated |
| 1. Foundation | Python package, locked environment, config, logs, schemas, fixtures, tests | Clean install and test command; schema unit tests |
| 2. First pipeline | IoT-23 Capture 34-1 labeled flow parser to Parquet | Reproducible command, manifest, data-quality report, schema tests |
| 3. Detection baseline | Rules, statistical baseline, Logistic Regression, Random Forest, and behavioral features | Versioned metrics, error analysis, leakage checks, and frozen validation policy |
| 4. Model-family study | Small justified tabular benchmark, optional anomaly ranking, disagreement analysis, and optional interpretable fusion | Scenario-aware validation, confidence intervals, alert volume, cost, and retained/rejected-model rationale |
| 5. Findings and verification | Deterministic aggregation, immutable evidence bundles, and claim-type verification | Event/detection/evidence preservation and grouping-stability integration tests |
| 6. Reference-backed AI review | Vetted reference retrieval, LLM A triage, independently isolated LLM B adjudication, deterministic comparison | Evidence-ID checks, frozen independent outputs, disagreement taxonomy, and unsupported-claim evaluation |
| 7. Human review and training | Tiered junior/expert review, insufficient-evidence path, and optional reviewer-training mode | Original outputs preserved, escalation state recorded, and case-study review metrics |
| 8. Review UI | Minimal local Streamlit reviewer workflow | Evidence, inference, uncertainty, AI comparison, and review history visible |
| 9. Optional adapters | Authorized IoT-23, controlled Cowrie, DShield exploration, and vendor-neutral scanner JSON | Safe failure behavior; no ground-truth inflation or vendor lock-in |
| 10. Portfolio | Polished narrative, diagrams, demo, limitations, and claim audit | Every public claim maps to repository evidence |

## Learning Curriculum

| Milestone | Security concepts | AI/data concepts | Builder should be able to explain |
|---|---|---|---|
| 0 | Triage, evidence, provenance, threat boundaries | Research validity and falsifiable questions | Why an LLM cannot be the detector or authority |
| 1 | Event identity and chain of custody | Schemas, validation, deterministic processing | How provenance survives transformations |
| 2 | Network flows, Zeek connection records, labels | Missingness, distributions, data quality | What one IoT-23 row means and what its label does not prove |
| 3 | Signatures, anomaly detection, false positives/negatives | Class imbalance, splits, baseline models | Precision/recall tradeoffs and leakage prevention |
| 4 | Honeypot sessions and authentication events | Heterogeneous adapters and typed unions | Why one canonical table should not erase source semantics |
| 5 | Alert correlation and evidence sufficiency | Entity relationships and deterministic aggregation | Difference between event, detection, finding, and evidence |
| 6 | Analyst triage and uncertainty | Structured generation and validation | Why citations to evidence IDs constrain but do not guarantee truth |
| 7 | Adjudication and error taxonomies | Calibration and comparative evaluation | What the experiment can and cannot conclude |
| 8 | Human oversight and audit history | Workflow state | Why original AI output must be immutable |
| 10 | Responsible security communication | Reproducibility and claim governance | A defensible 60-second project explanation |

## Design Challenge

The original concept is valuable but too broad if treated as one build step.

1. **The proposed wide canonical schema risks becoming a null-heavy universal record.** A shared envelope plus typed network, authentication, command, and external-finding details preserves meaning more cleanly.
2. **An “evidence graph” is premature.** V1 needs stable typed references and bundles, not a graph database or graph algorithms. Relational links in DuckDB are enough.
3. **DShield is a poor second supervised source.** Its API warns that reports can contain false positives. It belongs in exploratory/generalization work, not training ground truth.
4. **Random row splits would overstate model quality.** Flows from the same scenario share hosts, time windows, and collection conditions. Initial within-scenario results are pipeline checks, not generalization evidence.
5. **Human override rate from one builder is weak evidence.** It can describe a case study but cannot support claims about analyst populations or labor savings.
6. **LLM prose quality is not a research outcome.** Grounding and unsupported-claim rubrics must be defined before viewing outputs to reduce cherry-picking.
7. **FastAPI plus Streamlit is unnecessary initially.** The local UI can call an application/service layer directly; add an API only when a real external client exists.
8. **Four source types in early milestones would obscure whether the first pipeline is correct.** The first vertical slice should use one small IoT-23 scenario and fixtures.
9. **Deep learning, cloud deployment, live honeypot exposure, and scanner integrations are resume-driven unless later evidence justifies them.** They remain deferred.

## Revised Recommended Phase-0 Design

The approved implementation sequence is:

1. Build a batch-only local package with Python 3.12 and `uv`; use `pyproject.toml` plus a committed lockfile.
2. Use TOML for non-secret configuration, environment variables for secrets, and standard-library structured logging before adding logging frameworks.
3. Model a versioned canonical event envelope with discriminated source details rather than a single flat universal record.
4. Make event identity deterministic from source, dataset version, and source record identity; preserve raw references and checksums.
5. Start with synthetic fixtures, then parse only IoT-23 `CTU-IoT-Malware-Capture-34-1` labeled connection logs.
6. Treat the first scenario as a pipeline and baseline experiment, not proof of generalization.
7. Add `CTU-IoT-Malware-Capture-8-1` and benign `CTU-Honeypot-Capture-4-1` for later scenario-aware evaluation.
8. Use Cowrie JSON as the second canonical source, generated through controlled localhost sessions in isolated Docker.
9. Implement rule/statistical/logistic-regression baselines before any LLM work.
10. Represent evidence as immutable bundles with typed references in files/tables; do not introduce a graph database.
11. Add a provider-neutral LLM interface only after findings and the evaluation rubric exist.
12. Add Streamlit after review-state requirements are implemented; defer FastAPI, PostgreSQL, Azure, DShield automation, and scanner adapters until a measured need appears.

This revision keeps the research question intact while making each claim independently testable.

## Phase 3 amendment and architecture-freeze sequence

The prior Phase 3 work remains valid and is not discarded. Before any final architecture decision,
follow the constrained sequence in the [staged roadmap](roadmap.md): reproduce the frozen
validation policy; benchmark only justified simple specialists; measure disagreement; add an
interpretable fusion model only if errors are complementary; implement deterministic findings and
verification; and freeze all policy artifacts before the one-time Scenario 7 measurement. Do not
begin LLM implementation before findings, evidence bundles, verification, and the evaluation corpus
exist.

## Phase 0 Exit Criteria

- [x] Problem, objectives, non-goals, and research questions are explicit.
- [x] Architecture and canonical entities have documented boundaries.
- [x] Initial scenarios, source roles, and data-governance rules are selected.
- [x] Security and ethical boundaries are documented.
- [x] Evaluation measures and leakage risks are defined before experiments.
- [x] Milestones and learning outcomes are sequenced.
- [x] The design has been challenged and narrowed.
- [x] Portfolio claims are separated from plans.
- [ ] The owner has reviewed any remaining open questions before their milestone begins.

## Deferred Decisions

These do not block Phase 1:

- LLM provider and model: decide during Milestone 6 using cost, structured-output support, reproducibility, privacy, and evaluation needs.
- DShield endpoint selection and sampling window: decide during Milestone 9 after the adapter contract exists.
- PostgreSQL or FastAPI: add only if multi-process durable workflow state or an external client makes the need concrete.
- Cloud deployment: reconsider after V1 evaluation and local reproducibility are complete.
