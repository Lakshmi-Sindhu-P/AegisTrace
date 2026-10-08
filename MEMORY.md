# AegisTrace Project Memory

This file is the durable project memory for AegisTrace. It combines two memory layers:

- **Semantic and procedural memory** records stable project facts, constraints, architecture intent, and working practices.
- **Episodic memory** records dated decisions and changes, with the evidence that supports them.

Read this file before starting any task. Keep statements status-aware and grounded in repository evidence. A design brief can approve intent, but it cannot prove implementation or results.

## Status Model

- **CURRENT / IMPLEMENTED** — supported by code, configuration, documentation, or artifacts in the repository.
- **APPROVED INTENT / DESIGN** — accepted direction that governs future work but is not necessarily built.
- **PLANNED, NOT IMPLEMENTED** — proposed work with no implementation evidence yet.
- **VALIDATED** — implemented behavior supported by recorded tests, experiments, or other reproducible evidence.

Move a capability from `PLANNED` to `IMPLEMENTED` and then to `VALIDATED` only when repository evidence supports the transition. Never infer implementation status from the project brief.

For portfolio claims, also preserve the categories defined by `docs/resume_evidence.md`: `IMPLEMENTED`, `VALIDATED`, `PROTOTYPE`, `PLANNED`, and `NOT CLAIMABLE`.

## Core Architecture

### Current Implemented State

**Status: CURRENT / IMPLEMENTED and VALIDATED — Phase 3 detection and provenance foundations as of 2026-09-29**

- The repository contains governance and Phase 0 documentation plus an installable Python 3.12 package foundation.
- `AGENTS.md` installs the persistent memory protocol for repository-aware coding agents.
- `README.md` and `docs/` now document the charter, architecture, datasets, methodology, evaluation protocol, threat model, limitations, and resume-evidence boundary.
- `pyproject.toml`, `.python-version`, and `uv.lock` establish Python 3.12, `uv`, Pydantic, PyArrow, pytest, Ruff, and mypy.
- `src/aegistrace/` implements strict configuration, application-owned redacting JSON logging, canonical security-event/provenance/detection schemas, dataset manifests, an IoT-23 Zeek adapter that writes typed Parquet and quality artifacts, a separate CTU-13 Argus `.binetflow` adapter with typed source-specific flow details, a versioned CTU-13 feature builder, deterministic rules, and scenario-aware Logistic Regression/Random Forest baseline evaluation.
- `tests/` and safe synthetic fixtures validate deterministic event identity, timestamp/label/schema constraints, manifest consistency, configuration behavior, logging redaction, Zeek parsing, duplicate/malformed handling, Parquet output, and CLI execution.
- CTU-13 Scenarios 11, 5, 7, 47, 53, 45, and 51 are the official third-party artifacts downloaded across Phase 3 baseline and validation work: only CC-BY labeled text-flow files are present under ignored `data/raw/`; no packets or executables were acquired. The stability study uses Scenarios 11 and 47 for training and 5, 12, 4, and 10 (capture IDs 46, 53, 45, and 51) for validation. Scenario 7 is sealed for every post-baseline study and was not loaded, tuned against, or newly scored.
- IoT-23 Capture 34-1 remains pending the source page's authorization requirement; its adapter is implemented and validated against synthetic Zeek fixtures only.
- Canonical event/provenance/detection and dataset-manifest schemas are implemented, including scenario identity and CTU-13 source-specific typed details; finding, evidence-bundle, triage, and review schemas remain planned for their milestones.
- A 26-column `FEATURE_VERSION=1.0.0` feature vector, six-feature scenario-local behavioral extension `1.1.0`, and separate 13-feature causal host/time extension `1.2.0` are implemented. All behavioral/causal aggregates use only prior flows within one scenario and keep unknown rows as context but not supervised examples. The `1.1.0` contract remains unchanged by the `1.2.0` experiment.
- A validation-only improvement runner compares per-flow versus behavioral features, `class_weight=None` versus `balanced`, fixed threshold 0.5, and validation-selected thresholds. It has no final-test argument and records per-scenario metrics, error summaries, checksums, configuration, and threshold trade-offs in ignored `data/evaluation/phase3_improvement/diagnostic.json`.
- A pre-final hardening runner performs one-at-a-time behavioral-group ablations, a future-event temporal-causality audit, raw versus training-only sigmoid calibration assessment, and alert-volume analysis. It refuses sealed Scenario 7 and freezes the validation policy in `configs/phase3_frozen_policy.json`: balanced Random Forest, behavioral `1.1.0`, seed 42, raw scores, threshold 0.20, and existing deterministic rules v1.0.0 retained separately.
- `src/aegistrace/evaluation/model_family.py` and `scripts/run_phase3_model_family_benchmark.py` implement the first post-amendment validation-only model-family benchmark. It compares retained rules, Logistic Regression, shallow Decision Tree, Random Forest, Extra Trees, HistGradientBoosting, practical linear SVM, and a separate Isolation Forest anomaly experiment, with per-case disagreement and an explicit sealed-Scenario-7 guard.
- `scripts/run_phase3_model_stability_cached.py` and `scripts/correct_stability_operating_point.py` implement the cross-scenario RF/HGB/Linear-SVM stability pass over immutable behavioral `1.1.0` Parquet artifacts. `data/evaluation/phase3_model_stability/stability_summary.json` records model-specific score semantics, a validation-only precision/workload threshold policy, four-scenario metrics, alert volumes, SVM unique coverage, and all-model residual errors; Scenario 7 is explicitly excluded.
- `src/aegistrace/features/causal.py` and `scripts/run_phase3_causal_representation.py` implement the validation-only `1.2.0` causal host/time representation study over the same four non-sealed validation scenarios. `scripts/reconcile_phase3_causal_artifact.py` refreshes candidate/reference deltas after derived-reference repairs. The ignored `data/evaluation/phase3_causal_representation/causal_summary.json` records feature lineage, checksums, model-specific thresholds, per-scenario metrics, disagreement, and residual coverage; Scenario 7 is explicitly excluded.
- The prior stability repair now recomputes HGB-derived disagreement/residual sections from recorded case IDs and computes residual reference quantiles once, avoiding an O(n²) diagnostic loop. The repair is recorded in the stability artifact rather than treated as a new detector result.
- `scripts/analyze_phase3_causal_overlap.py` implements the bounded Issue #3 diagnostic over immutable `1.1.0`/`1.2.0` validation case records and Parquet features. It verifies common-feature identity, classifies RF/SVM overlap changes, summarizes subgroup distributions by scenario, records input checksums, and rejects sealed Scenario 7. The ignored `data/evaluation/phase3_causal_overlap/overlap_summary.json` supports a localized Scenario 10/51 burst-density hypothesis but does not promote `1.2.0` or justify fusion/new model complexity.
- `src/aegistrace/schemas/experiments.py` implements strict `ExperimentRun`/artifact lineage schemas. `docs/experiment_registry.json` tracks the current model-family, stability, causal representation, overlap diagnosis, and uncertainty runs; `scripts/validate_experiment_registry.py` checks references and digests, and `scripts/validate_phase3_evidence.py` checks sealed-scenario and known-artifact invariants. `src/aegistrace/evaluation/uncertainty.py` and `scripts/summarize_phase3_uncertainty.py` produce aggregate Wilson intervals without refitting or changing thresholds; PR-AUC uncertainty remains explicitly unestimated.
- `src/aegistrace/schemas/agent_trace.py` implements strict redacted agent-trace and versioned solution-knowledge records. `scripts/validate_agent_trace.py` and `scripts/validate_solution_knowledge.py` validate local JSONL provenance and tracked reusable lessons. `.github/ISSUE_TEMPLATE/` defines structured issue forms for work, human blockers, architecture decisions, and retrospective lessons; no GitHub Actions scheduler or self-modifying governance is enabled.
- `LICENSE` establishes the repository's MIT license. Raw datasets, generated evaluation artifacts, and local agent traces remain excluded by `.gitignore`.
- No LLM or AI-security scanner integration exists.
- Evaluation metrics and reproducible baseline/improvement artifacts exist; the improvement result is limited to four training/validation scenarios and no production or cross-dataset performance result exists.
- No API, dashboard, persistent application database, container stack, or cloud deployment exists.
- `.context/` contains local, gitignored Conductor workspace material; it is not part of the product architecture or durable project evidence.

### Approved Architectural Intent

**Status: APPROVED INTENT / DESIGN — not implemented**

AegisTrace is intended to use this high-level flow:

```text
CTU-13 | IoT-23 | DShield | Cowrie | AI-security scanner findings | synthetic fixtures
    -> source adapters
    -> canonical security event schema
    -> validation and data-quality checks
    -> normalized event store
    -> feature engineering
    -> deterministic rules + supervised/anomaly/temporal specialists
    -> disagreement analysis -> optional interpretable fusion
    -> deterministic finding aggregation
    -> verification labels + evidence bundle + vetted references
    -> independent structured LLM triage and adjudication
    -> tiered human review and recommendation
    -> evaluation and analytics
    -> audit and provenance records
```

The LLM is subordinate to evidence and is never the authoritative source of truth. Original events, detector outputs, AI results, and human review history must remain traceable and must not be silently overwritten.

The amended target is a provenance-first, multi-model investigation system rather than a single
universal malicious-versus-benign classifier. This is approved design only. A specialist is added
only after a validation hypothesis, complementary error evidence, and workload/interpretability
trade-off justify it. Model agreement is not ground truth; recommendations never automate blocking,
isolation, remediation, or other destructive response.

### Approved Initial Technology Direction

**Status: CURRENT / IMPLEMENTED for the foundation; APPROVED INTENT / DESIGN for data, ML, and application layers**

- Runtime and packaging: Python 3.12 with `uv`, `pyproject.toml`, and a committed lockfile.
- Core: Pydantic, PyArrow/Parquet, and scikit-learn baselines are implemented; Pandas, NumPy, and DuckDB remain approved tools for later milestones (pytest/Ruff/mypy are already dev dependencies).
- Configuration: TOML for non-secret configuration and environment variables for secrets.
- Logging: Python standard-library logging with JSON-formatted structured records initially.
- Application layer, only when needed: FastAPI and Streamlit.
- Initial persistence: Parquet and DuckDB.
- PostgreSQL is deferred until durable review, workflow, audit, user-action, or relational application state justifies it.
- Infrastructure: Docker and Docker Compose where they improve reproducibility or isolation.
- Deployment: local-first. Azure is deferred until the core pipeline works, tests pass, architecture is stable, evaluation exists, and deployment adds demonstrable value.
- Avoid unjustified complexity such as premature microservices, Kafka, Kubernetes, graph/vector databases, multiple clouds, deep learning, or MLflow.

### Approved Repository Shape

**Status: CURRENT / IMPLEMENTED for existing paths; PLANNED, NOT IMPLEMENTED for later milestone paths**

```text
README.md
AGENTS.md
MEMORY.md
LICENSE
pyproject.toml
.env.example
docs/
    project_charter.md
    architecture.md
    datasets.md
    threat_model.md
    methodology.md
    evaluation.md
    phase3_causal_representation.md
    limitations.md
    resume_evidence.md
    roadmap.md
    agent_orchestration.md
    experiment_registry.json
    solution_knowledge.json
    learning_notes/
src/aegistrace/
    ingestion/          (implemented)
    schemas/            (implemented)
    validation/         (PLANNED, NOT IMPLEMENTED - directory absent)
    features/           (implemented)
    detection/          (implemented)
    verification/       (implemented)
    triage/             (implemented)
    review/             (implemented)
    evaluation/         (implemented)
    provenance/         (PLANNED, NOT IMPLEMENTED - directory absent)
    storage/            (PLANNED, NOT IMPLEMENTED - directory absent)
    api/                (PLANNED, NOT IMPLEMENTED - directory absent)
    ui/                 (PLANNED, NOT IMPLEMENTED - directory absent)
data/
    raw/
    interim/
    processed/
    fixtures/
    evaluation/
tests/
notebooks/
scripts/
    __init__.py
    ingest_iot23.py
    ingest_ctu13.py
    run_phase3_baselines.py
    run_phase3_improvement.py
    run_phase3_hardening.py
    run_phase3_model_family_benchmark.py
    run_phase3_model_stability.py
    run_phase3_model_stability_cached.py
    run_phase3_causal_representation.py
    reconcile_phase3_causal_artifact.py
    analyze_phase3_causal_overlap.py
    summarize_phase3_uncertainty.py
    validate_experiment_registry.py
    validate_phase3_evidence.py
    correct_stability_operating_point.py
    validate_agent_trace.py
    validate_solution_knowledge.py
.github/
    ISSUE_TEMPLATE/
configs/
    phase3_frozen_policy.json
```

## Semantic Memory (Domain Facts)

### Project Identity and Research Goal

- **Name:** AegisTrace.
- **Subtitle:** Evidence-Grounded AI Security Triage.
- **Type:** applied AI-security research and engineering project; not a production security product.
- **Primary research question:** Can a provenance-first, multi-model security system combine deterministic, supervised, anomaly, temporal, and reference-backed evidence to generate trustworthy investigation recommendations while clearly separating observed facts from inference and enabling a junior reviewer to handle basic triage without eliminating expert escalation?
- The project should evaluate deterministic rules, supervised/anomaly/temporal detection, finding aggregation, verification, independent LLM triage/adjudication, and human review separately before evaluating combinations.
- Success depends on reproducibility, measurable results, explainability, provenance, security, uncertainty handling, and human oversight—not feature count.

### Security and Ethical Boundary

- AegisTrace is defensive only. It is not an autonomous SOC, prevention system, penetration-testing platform, exploit framework, malware platform, or offensive automation tool.
- Testing is limited to offline datasets, synthetic fixtures, localhost, isolated containers, controlled environments, or software explicitly intended for defensive testing.
- Do not attack or scan unowned infrastructure, expose intentionally vulnerable systems publicly, generate exploit payloads, create persistence, bypass authentication, or perform unauthorized reconnaissance.
- If an approach introduces unnecessary security risk, stop and choose a safer alternative.

### Evidence, Provenance, and Human Oversight

- Preserve source provenance, event IDs, timestamps, transformation versions, detector versions, feature/training-dataset versions, scores, triggered rules, supporting evidence, model/provider and prompt versions, uncertainty, analyst review, and final disposition.
- LLM inputs must be limited evidence packages containing relevant events, rules, ML results, scanner findings, and known context.
- LLM outputs must be structured, cite evidence identifiers, expose uncertainty, and allow `insufficient evidence` rather than forced confidence.
- Claims about malware, exploits, CVEs, attacker intent, compromise, persistence, or exfiltration are unsupported without direct evidence and should be flagged.
- Human reviewers should eventually be able to mark triage as confirmed, partially confirmed, rejected, needs investigation, or insufficient evidence.
- Preserve the original AI result alongside reviewer decisions, notes, timestamps, and final results.
- Never claim planned functionality, fabricated metrics, production use, scale, latency, deployment, users, or security impact. Resume statements must be backed by repository evidence.

### Approved Initial Data-Source Strategy

**Status: CURRENT / IMPLEMENTED for CTU-13 and synthetic fixtures; APPROVED INTENT / DESIGN for remaining sources**

- **IoT-23:** primary labeled baseline for ML development and quantitative evaluation. The approved subset is `CTU-IoT-Malware-Capture-34-1` (first Mirai pipeline), `CTU-IoT-Malware-Capture-8-1` (additional malicious scenario), and `CTU-Honeypot-Capture-4-1` (benign Philips Hue scenario). Do not process the full dataset without a demonstrated need. The Capture 34-1 adapter is implemented and synthetic-fixture validated; the official artifact is not used until authorization is available.
- **CTU-13:** real labeled validation source. The adapter ingests CC-BY bidirectional Argus text-flow files and preserves scenario/source-label provenance; `Background` and `To-*` labels remain unknown under the conservative mapping. The stability pool uses Scenarios 11 and 47 for training plus Scenarios 5, 12, 4, and 10 for validation. Scenario 7 remains the sealed final test from the accepted baseline and is not used for improvement selection, threshold selection, or model comparison.
- **DShield / SANS Internet Storm Center:** recent real-world telemetry for generalization and exploratory analysis. Its unlabeled events are not malicious ground truth; represent label uncertainty explicitly.
- **Cowrie:** controlled local honeypot telemetry for fixtures, demos, schema development, reconstruction, and session analysis. Run only in an isolated/local environment initially.
- **AI-security scanner findings:** eventual vendor-neutral adapter input. Treat scanner output as upstream evidence, never authoritative truth, and do not make AegisTrace depend on one vendor.
- **Synthetic fixtures:** safe, small inputs for schema design, pipeline tests, malformed data, and controlled behavioral scenarios.

### Canonical Concepts

**Status: CURRENT / IMPLEMENTED for event, provenance, manifest, detection, finding, evidence-bundle, claim, triage-assessment, and human-review contracts; PLANNED, NOT IMPLEMENTED for the triage run itself and the minimal local review UI**

- The implemented canonical event uses a strict, immutable, versioned envelope plus discriminated network, CTU-13 flow, authentication, command, HTTP, or generic details. It retains deterministic UUIDv5 identity, source/dataset/scenario references, UTC event and ingestion times, optional correlation, labels and label source, raw reference/checksum, adapter/transformation versions, and quality flags. Missing values remain explicit; extra fields and naive timestamps are rejected.
- A benign or malicious ground-truth label requires `label_source`; unknown labels cannot carry an attack category. Credentials are deliberately excluded from authentication details.
- The implemented dataset manifest requires relative file references, SHA-256 checksums, versioned transformations, record counts, UTC times, and internally consistent label counts/time ranges.
- The implemented detection result links one detector signal to an event ID and retains detector type/name/version, severity, score, triggered rules, observed-value evidence, a UTC creation time, and a note that a signal is not an incident disposition.
- LLM output is triage over a finding/evidence bundle, not a primary detector in V1.
- An AI triage record should link findings and evidence, preserve the structured assessment, confidence and uncertainty, unsupported-claim checks, model/provider/prompt metadata, creation time, and human review status.
- The intended aggregation chain is `event -> detection -> finding -> evidence bundle` with multiple detectors able to support one finding.
- The implemented finding contract groups related detections by source host and observed-time gap using operational fields only, and never reads a research label, a later-stage model score, or an LLM conclusion. The implemented evidence bundle snapshots finding and detection references, minimal event fields, observed values, per-model score references with their feature versions, and explicit missing context and limitations. The implemented claim contract enforces the epistemic taxonomy and reports an uncited statement as `UNKNOWN_INSUFFICIENT_EVIDENCE` rather than accepting it.
- Evidence relationships use typed references and DuckDB/Parquet records in V1; no graph database is approved.

### Amended detection and review direction

**Status: APPROVED INTENT / DESIGN for downstream investigation layers; bounded detector benchmark
and stability evidence are implemented below**

- The bounded detector benchmark is implemented: rules, Logistic Regression, the current balanced Random Forest, a shallow Decision Tree, Extra Trees, HistGradientBoosting, Linear SVM, and a separate Isolation Forest anomaly-prioritization experiment. Unknown rows remain unknown.
- HistGradientBoosting and Linear SVM have now been evaluated as bounded validation baselines. XGBoost, LightGBM, CatBoost, KNN, MLPs, autoencoders, clustering, semi-supervised learning, and temporal neural models remain deferred until a representation hypothesis and additional evidence justify them.
- Model-family selection requires cross-scenario metrics, confidence intervals, alert volume, computational cost, interpretability, and residual disagreement analysis. Fusion is permitted only when component errors are complementary; an interpretable Logistic Regression meta-model is the default candidate.
- Planned findings group detections using operational evidence (host, time, destinations, ports, shared behavior), preserve all event/detector IDs, and never use research labels for grouping or queue priority.
- Planned verification labels material claims as `OBSERVED_FACT`, `DETERMINISTIC_DERIVATION`, `REFERENCE_BACKED_FACT`, `MODEL_INFERENCE`, `AI_INTERPRETATION`, or `UNKNOWN_INSUFFICIENT_EVIDENCE`.
- Planned LLM A triage and LLM B adjudication receive the same underlying evidence but are frozen independently; B must not see A's conclusion before comparison. A deterministic engine records corroboration, contradiction, disagreement, insufficient evidence, or expert escalation. Neither AI role is ground truth or equivalent to a qualified expert.

### Definition of a Strong V1

**Status: APPROVED INTENT / DESIGN — entirely unimplemented at baseline**

V1 requires at least two data sources, a canonical event schema, validation and provenance, feature
engineering, deterministic rules, a justified detector benchmark, quantitative evaluation,
deterministic findings and evidence bundles, verification labels, independently evaluated structured
AI triage/adjudication, a tiered human-review workflow, AI evaluation, a local dashboard, documented
limitations, reproducible execution, tests, architecture documentation, and a polished README. A
multi-model ensemble, temporal model, or cloud deployment is optional and must be justified by
evidence; none is currently implemented.

## Procedural Memory (Workflows/Coding Styles)

### Task Startup and Memory Maintenance

1. Read `MEMORY.md` before inspecting or changing the project.
2. Inspect the repository and distinguish current evidence from approved intent.
3. State material assumptions and do not reconstruct missing facts.
4. After architectural, dependency, schema, workflow, or project-status changes, update the relevant semantic/procedural section in the same change.
5. Add a concise dated episodic entry for major decisions, reversals, milestone transitions, and validated results. Include evidence paths or commands where practical.
6. Do not use episodic entries as a running activity log; omit routine edits and minor fixes.
7. When code and memory disagree, verify the code and artifacts, correct stale memory, and record a major correction if it changes project understanding.

### Delivery Sequence

- Begin with Phase 0: charter, problem statement, scope/non-goals, research questions, architecture, ethical boundary, dataset plan, technology choices, risks, assumptions, milestones, and learning curriculum.
- Do not build the entire application at once. Progress through data foundations, one IoT-23 pipeline, detection baselines, additional sources, finding aggregation, LLM triage, AI evaluation, human review UI, optional scanner adapters, and final portfolio material.
- Do not add ML before the first ingestion/normalization pipeline is reproducible and understood.
- For supervised CTU-13 experiments, fit only on authoritative benign/malicious labels, retain unknown rows for audit/rule scoring, group splits by scenario, and record checksums, feature version, seed, threshold, and model parameters.
- Feature builders must keep labels, filenames, scenario IDs, source labels, and obvious label proxies out of numeric model matrices. Any material feature change requires a new version, leakage review, tests, and experiment artifact.
- Cross-flow features must be computed per scenario from prior observations only; host keys may support aggregation but raw addresses remain outside model matrices. Thresholds and class weights must be selected on training/validation data only while the final test is sealed.
- New feature families must preserve prior version contracts, document source fields/units/missingness/leakage, pass a future-event audit, and compare against the same scenario-aware operating policy before any promotion. A representation gain in union coverage does not by itself justify fusion or a new model family.
- For representation diagnostics, reconcile predictions by deterministic event ID before interpreting pooled residual changes. Compare candidate-only, reference-only, shared-residual, and shared-coverage groups by scenario and prior-only feature distributions; treat a localized subgroup hypothesis as descriptive until a scenario-held-out check supports transfer.
- Before reopening a sealed final test, run ablations, future-event causality checks, calibration and alert-volume analysis, then freeze model/features/threshold/class weighting/calibration/rules/checksums in a tracked policy artifact. Do not tune after final-test observation.
- Before architecture freeze, reproduce the frozen policy, benchmark only justified simple model families, measure disagreement and stability, test an anomaly ranking specialist only if its assumptions are explicit, and consider interpretable fusion only when errors are complementary. This entire sequence excludes sealed Scenario 7.
- For operating-point comparisons, never assume a shared numeric threshold has shared meaning across model score scales. Record score production, normalization, threshold-selection policy, PR-AUC, per-scenario workload, unique coverage, and residual errors. A higher ranking metric alone is not operational evidence.
- When a policy correction changes an operating threshold, regenerate all derived disagreement/residual sections from immutable case IDs; do not patch only the headline metric. Keep diagnostic summaries linear in the number of cases (compute reference quantiles once).
- Add deterministic alert-to-finding aggregation and claim verification before any LLM receives evidence. Preserve event-level provenance and allow unknown/insufficient-evidence outcomes.
- Keep LLM A and LLM B inputs independent until both outputs are frozen; compare them deterministically and never use agreement as ground truth. Distinguish machine-verifiable checks, guided junior review, expert review, and insufficient evidence.
- Do not add LLM triage before findings and evidence bundles exist.
- Do not add cloud deployment merely for resume value.

### Engineering Style

- Prefer the simplest justified technology and clear system boundaries.
- Use type hints, focused modules, meaningful docstrings, centralized configuration, explicit error handling, structured logging, and deterministic behavior where possible.
- Avoid giant files, magic numbers, unexplained abstractions, dependency bloat, premature services, and unnecessary async or scalability machinery.
- Preserve raw inputs or references; version transformations, features, datasets, detectors, models, prompts, and experiments.
- Never silently replace training data. Record dataset name/version, download date, source URL, record count, and checksum where practical.
- Use a simple structured experiment registry first; add MLflow only if a demonstrated need emerges.
- Validate every local trace and solution-knowledge file with the repository validators before using it
  as evidence. Keep issue history, trace history, and reusable lessons separate and linked by stable
  references.
- Register every validated Phase 3 run in `docs/experiment_registry.json` with a code revision,
  split, seed, command, artifact digest, documentation, and claim boundary. Treat the registry as
  lineage metadata only; it must not schedule work or mutate governance. Run the registry and known-
  artifact validators before relying on generated metrics.

### Testing and Evaluation

- Test happy paths, malformed inputs, missing/null fields, unexpected source values, duplicates, model-output validation, and provenance preservation.
- Add integration coverage for `raw event -> normalized event -> detection -> finding -> triage` as those stages become implemented.
- For labeled ML data, report accuracy, precision, recall, F1, confusion matrix, false-positive/negative rates, and ROC-AUC or PR-AUC where appropriate. Do not rely on accuracy alone for imbalanced data.
- Evaluate LLM triage with curated benign, malicious, ambiguous, incomplete, conflicting, misleading, and edge-case examples.
- Track evidence-grounding, unsupported claims, severity/category agreement, human overrides, completeness, uncertainty calibration, and detector/LLM disagreement.
- Record rules-only, ML-only, rules+ML, rules+ML+LLM, and human-reviewed comparisons where supported. Never invent missing measurements.

### Teaching and Handoff

After each meaningful implementation step, explain what was built, why it exists, the relevant security and AI/ML concepts, the key files/functions to understand, and a 30–60 second interview explanation. Ask 3–5 comprehension questions when the work introduces foundational concepts.

## Episodic Memory (Key Decisions Log)

| Date | Status | Decision or event | Evidence / rationale |
|---|---|---|---|
| 2026-09-19 | CURRENT / IMPLEMENTED | Established `MEMORY.md` as the project’s durable semantic, procedural, and episodic memory. | Repository file `MEMORY.md`. |
| 2026-09-19 | CURRENT / IMPLEMENTED | Recorded the baseline as an empty initial implementation with no established application stack or validated capability. | Repository inspection showed no tracked application files, manifests, data, tests, or artifacts before this file. |
| 2026-09-19 | CURRENT / IMPLEMENTED | Installed the repository-level agent protocol requiring tasks to read and maintain project memory. | Repository file `AGENTS.md`. |
| 2026-09-19 | CURRENT / IMPLEMENTED | Completed the Phase 0 documentation baseline: charter, architecture, dataset plan, threat model, methodology, evaluation protocol, limitations, and claim ledger. | `README.md` and `docs/`. No application capability is claimed. |
| 2026-09-19 | APPROVED INTENT / DESIGN | Adopted evidence-grounded, defensive-only, human-reviewed AI security triage as the governing project direction. | Project brief supplied by the repository owner. |
| 2026-09-19 | APPROVED INTENT / DESIGN | Approved a local-first Python data/ML direction using Parquet and DuckDB initially; deferred PostgreSQL, cloud deployment, and complex infrastructure until justified. | Project brief, sections 9, 24, and 28. |
| 2026-09-19 | APPROVED INTENT / DESIGN | Approved the initial source strategy: subsetted IoT-23 baseline, uncertain DShield telemetry, isolated Cowrie data, synthetic fixtures, and vendor-neutral scanner adapters. | Project brief, section 7. |
| 2026-09-19 | APPROVED INTENT / DESIGN | Required separate evaluation of rules, ML, LLM triage, and human-reviewed combinations; LLM conclusions remain subordinate to evidence. | Project brief, sections 15–18 and Phase 7. |
| 2026-09-19 | APPROVED INTENT / DESIGN | Narrowed the initial vertical slice to IoT-23 Capture 34-1, selected Capture 8-1 and benign Capture 4-1 for later scenario-aware evaluation, and chose controlled Cowrie as V1's second source. | `docs/project_charter.md` and `docs/datasets.md`. |
| 2026-09-19 | APPROVED INTENT / DESIGN | Selected Python 3.12, `uv`, TOML/environment configuration, standard-library structured logging, and a canonical envelope with typed source details and deterministic event IDs. | `docs/architecture.md`. |
| 2026-09-19 | APPROVED INTENT / DESIGN | Deferred DShield automation, FastAPI, PostgreSQL, Azure, scanner adapters, and graph storage until concrete evidence justifies them. | Phase 0 design critique in `docs/project_charter.md`. |
| 2026-09-20 | VALIDATED | Completed the Phase 1 foundation: locked Python package, strict config, redacting JSON logs, canonical event/provenance schemas, dataset manifests, fixture, and automated checks. | `uv run pytest`: 22 passed with 97.57% coverage; `uv run ruff check .` and `uv run mypy`: passed. |
| 2026-09-21 | VALIDATED | Implemented the IoT-23 Zeek adapter and typed Parquet/report/manifest writer; validated parsing, malformed/duplicate handling, output artifacts, and CLI against a safe synthetic fixture. | `uv run pytest`: 31 passed with 94.65% coverage; Ruff, mypy, `uv lock --check`, and `uv sync --check --all-groups` passed. |
| 2026-09-21 | APPROVED INTENT / DESIGN | Deferred official Capture 34-1 ingestion until authorization is available, based on the scenario page's explicit authorization notice. | Official scenario page README; see `docs/datasets.md`. |
| 2026-09-21 | VALIDATED | Completed Phase 2B with a separate CTU-13 Argus `.binetflow` adapter and typed `Ctu13FlowDetails`; ingested Scenario 11's genuine CC-BY text-flow artifact with stable scenario-aware IDs, source checksum, source-label provenance, Parquet, manifest, and quality report. | `uv run pytest`: 39 passed with 93.67% coverage; Ruff and mypy passed; real run accepted 107,251/107,251 rows with zero rejects/duplicates. Raw checksum `cee542d4b5efe4fa1cd59b87ece5aaea9a13d8f0abe56cd07cee31590736428c`; artifacts in ignored `data/processed/ctu13_scenario_11/`; learning note `docs/learning_notes/phase_2b.md`. |
| 2026-09-21 | VALIDATED | Completed Phase 3 detection foundations: added a 26-column versioned CTU-13 feature vector, three evidence-traceable deterministic rules, immutable detection records, and Logistic Regression/Random Forest baselines using Scenario 11 train, Scenario 5 validation, and Scenario 7 test splits. | `uv run pytest`: 46 passed with 93.07% coverage; Ruff, mypy, lock, and sync checks passed. Run artifact `data/evaluation/phase3_baselines/experiment_summary.json` records checksums (`cee542d4...6428c`, `ef5c9ed6...78a02c`, `df0b5338...a26680`), feature version `1.0.0`, seed 42, parameters, confusion counts, and metrics. Held-out test recall was 0.0159 for rules/Logistic Regression and 0.0794 for Random Forest; results are exploratory and not a broad detection claim. A second fixed-parameter run produced byte-identical experiment summary and feature Parquet hashes. |
| 2026-09-21 | VALIDATED | Ran a focused, validation-only detector-improvement investigation without loading or tuning against sealed Scenario 7. Added CC-BY Scenario 47 to training and Scenario 53 to validation; added six prior-flow, scenario-local behavioral features (`1.1.0`), class-weight comparisons, and validation-only threshold selection. | `scripts/run_phase3_improvement.py`; source checksums `801800ee...d2adaa` and `1098f0ad...dd9f2e`; quality reports in `data/processed/ctu13_scenario_6/` and `_12/`; diagnostic artifact `data/evaluation/phase3_improvement/diagnostic.json`; diagnostic report `docs/phase3_detector_improvement.md`. Balanced Random Forest behavioral features improved combined validation recall from 0.519 at threshold 0.5 to 0.845 at validation-selected threshold 0.15, with precision 0.956 and F1 0.897; both validation scenarios improved, but no final-test or operational claim is made. `uv run pytest`: 51 passed, 91.62% coverage; Ruff and mypy passed. |
| 2026-09-21 | VALIDATED | Completed the pre-final hardening pass without loading or using sealed Scenario 7. Ablations found destination-port diversity the largest single recall contributor, the future-event causality audit passed, training-only sigmoid calibration was deferred after a worse Brier score, and alert-volume trade-offs supported freezing threshold 0.20 rather than 0.15. | `scripts/run_phase3_hardening.py`; report `docs/phase3_detector_hardening.md`; tracked policy `configs/phase3_frozen_policy.json`; ignored artifact `data/evaluation/phase3_hardening/hardening_summary.json`. Frozen policy: balanced Random Forest, behavioral `1.1.0`, seed 42, raw scores, threshold 0.20, Scenario 11/47 training, Scenario 5/53 validation, existing rules v1.0.0 retained separately. It is methodologically ready for one controlled final measurement but not an operational alerting claim. |
| 2026-09-22 | APPROVED INTENT / DESIGN | Amended the target from a single malicious-vs-benign classifier to a provenance-first, multi-model investigation system with specialist detectors, disagreement analysis, optional interpretable fusion, deterministic findings, verification labels, vetted references, two independently frozen AI roles, tiered review, and non-destructive recommendations. | `docs/architecture.md`, `docs/methodology.md`, `docs/evaluation.md`, `docs/roadmap.md`, `docs/project_charter.md`, `docs/limitations.md`, and `docs/resume_evidence.md`. Existing Phase 3 work remains valid; Scenario 7 was not opened. |
| 2026-09-22 | VALIDATED | Completed the first post-amendment model-family benchmark without opening Scenario 7. At the frozen validation operating point, Random Forest retained the strongest F1/recall, HistGradientBoosting had the best PR-AUC, linear SVM added 30 unique malicious cases only at a very high false-positive cost, and Isolation Forest added no unique malicious coverage while producing a large workload. | Runner `scripts/run_phase3_model_family_benchmark.py`; module `src/aegistrace/evaluation/model_family.py`; artifact `data/evaluation/phase3_model_family/benchmark_summary.json`; report `docs/phase3_model_family_benchmark.md`. The result supports no fusion or additional detector-family complexity yet; more scenario/split stability analysis is recommended. |
| 2026-09-23 | VALIDATED | Completed the cross-scenario RF/HGB/Linear-SVM operating-point stability pass without opening Scenario 7. Added licensed Scenarios 45 and 51 to validation, documented model-specific score scales, and selected thresholds only on pooled validation labels under precision >= 0.95 and <= 200 alerts per 1,000 labeled flows. | Runner `scripts/run_phase3_model_stability_cached.py`; correction/provenance helper `scripts/correct_stability_operating_point.py`; artifact `data/evaluation/phase3_model_stability/stability_summary.json`; report `docs/phase3_model_stability.md`. RF is the strongest compliant standalone result (PR-AUC 0.999589); HGB has higher PR-AUC (0.999738) but no feasible operating point under both constraints; SVM uniquely catches 13,576 malicious cases in only two of four scenarios. All three miss 68,353 short/low-activity/low-diversity mixed-protocol cases. No fusion or new model family is justified; a representation-focused temporal/host-context study is next. |
| 2026-09-29 | VALIDATED | Implemented the approved Option-A issue/trace/lesson foundation. Added strict trace and solution-knowledge schemas/validators, explicit local trace ignores, structured GitHub issue forms and lifecycle documentation, and an MIT license. | `AGENTS.md`, `.gitignore`, `.github/ISSUE_TEMPLATE/`, `src/aegistrace/schemas/agent_trace.py`, `scripts/validate_agent_trace.py`, `scripts/validate_solution_knowledge.py`, `docs/agent_orchestration.md`, `docs/solution_knowledge.json`, `LICENSE`; `uv run pytest`: 60 passed with 91.95% coverage; Ruff and mypy passed. No scheduler, OTel stack, or self-modifying governance was added. |
| 2026-09-29 | VALIDATED | Completed Issue #2's causal host/time representation study without opening Scenario 7. Added feature version `1.2.0` with prior-only 60/300-second activity, diversity, reuse, protocol, volume, and recency values; refit only RF/HGB/SVM under the existing validation-only precision/workload policy; recorded scenario-aware metrics, disagreement, checksums, and residuals; and promoted one reusable lesson about regenerating derived evidence after policy changes. | `src/aegistrace/features/causal.py`, `scripts/run_phase3_causal_representation.py`, `scripts/reconcile_phase3_causal_artifact.py`, `docs/phase3_causal_representation.md`, `docs/solution_knowledge.json`, `data/evaluation/phase3_causal_representation/causal_summary.json` (ignored), and Issue #2. The all-three residual fell from 68,353 to 64,986 (4.9%) through lower RF/SVM overlap, but no single operating point improved; no fusion/new model family is justified. A stale HGB-derived disagreement artifact was repaired by `scripts/correct_stability_operating_point.py`, with an O(n²) residual quantile loop fixed to compute reference quantiles once. `uv run pytest`: 61 passed with 90.20% coverage; Ruff and mypy passed. |
| 2026-09-29 | VALIDATED | Completed Issue #3's bounded causal-overlap diagnosis without refitting or opening Scenario 7. Deterministic case reconciliation found 10,564 candidate-only, 7,197 reference-only, 57,789 shared residual, and 36,451 shared-coverage malicious validation cases; 10,234 candidate-only cases were in Scenario 10/51. Their median 60-second source/repeated-short counts were 2.125x the unchanged residual subgroup with equal median destination diversity, supporting one localized burst-density hypothesis but not causal proof, `1.2.0` promotion, fusion, or a new model family. | Issue #3; `scripts/analyze_phase3_causal_overlap.py`; `docs/phase3_causal_overlap.md`; ignored `data/evaluation/phase3_causal_overlap/overlap_summary.json`; common-feature identity checks; Scenario 7 sealed guard. The next gate is one scenario-held-out non-sealed test of the narrow hypothesis or deterministic finding aggregation. |
| 2026-09-30 | VALIDATED | Completed Issue #4 reproducibility hardening without changing detector outputs, thresholds, model families, or Scenario 7 status. Added tests for overlap categorization and sealed-scenario rejection, a tracked five-run experiment registry with digest validation, known-artifact consistency checks, and aggregate Wilson intervals for recorded confusion counts. | Issue #4; `src/aegistrace/schemas/experiments.py`, `src/aegistrace/evaluation/uncertainty.py`, `docs/experiment_registry.json`, `scripts/validate_experiment_registry.py`, `scripts/validate_phase3_evidence.py`, `scripts/summarize_phase3_uncertainty.py`, and new tests. PR-AUC uncertainty remains unestimated; independent scenario-held-out testing and deterministic finding aggregation remain planned. |
| 2026-10-08 | CURRENT / IMPLEMENTED | Corrected post-repair documentation drift: `MEMORY.md` and `docs/evaluation.md` now state SVM unique coverage of 13,576 and an all-three residual of 68,353, matching the repaired stability artifact; also removed the non-existent `docker-compose.yml` and `artifacts/` paths from the repository-shape block. | `data/evaluation/phase3_model_stability/stability_summary.json` (`.svm_unique_coverage.total_unique_cases` = 13,576; `.residual_error_analysis.total_cases` = 68,353) and `docs/methodology.md` (lines 222-224); reason: post-repair documentation drift. |
| 2026-10-08 | VALIDATING | Diagnosed that the Phase 3 stability operating-point recall (~27%) and the 68,353 all-model residual are bounded by the evaluation policy, not by model quality. The pooled labeled validation subset is 67.8% malicious (112,001 / 165,276) and only 5.7% of the 2,886,156 validation rows are labeled; the `<= 200` alerts-per-1,000-labeled-flows cap therefore permits flagging at most 20% of labeled rows and caps recall at ~29.5% even for a perfect ranker. At the frozen threshold `0.20` the balanced Random Forest records recall `0.9949` at precision `0.9903` (HistGradientBoosting `0.9931` / `0.9954`); both are excluded only because they exceed the cap. The genuine unresolved uncertainty is the unlabeled majority, not detector discrimination. | Issue #8; `docs/phase3_evaluation_diagnosis.md`; `data/evaluation/phase3_model_stability/stability_summary.json` (`scenario_metadata.validation`, `model_results.*.fixed_policy_metrics`, `operating_policy`, `residual_error_analysis.by_scenario`); `data/evaluation/phase3_hardening/hardening_summary.json` alert volume. Read-only: no threshold, model, feature, artifact, or frozen policy was changed. |
| 2026-10-08 | CURRENT / IMPLEMENTED | Completed a bounded research-landscape scan for the research-contribution goal, in two passes (OpenAlex index, then direct page/PDF/arXiv/Semantic Scholar fetches). Finding: "evidence-grounded LLM-assisted SOC investigation" is already an occupied area — closest prior art is *CORTEX* (arXiv:2510.00311, multi-agent LLM alert triage where agents **collaborate** over shared evidence) and *PROVSEEK* (arXiv:2508.21323, provenance plus multi-agent LLM forensics). The sharpest defensible gap is the **ablation, not the architecture**: no security-triage work was found that treats *mutual blindness between frozen assessors* as the experimental variable, with disagreement itself as the escalation signal. Secondary gaps: claim-level observed-vs-inferred separation, analyst-decision outcomes, and evaluation rigor. The need is peer-reviewed (ACM Computing Surveys 2025, https://doi.org/10.1145/3723158) and standards-acknowledged (NIST SP 800-61r3). | `docs/research_landscape.md`; retrieval 2026-10-08. Commercial landscape is now covered at vendor-page level (Microsoft, Google, Palo Alto, CrowdStrike, Dropzone, Prophet, Torq) with vendor metrics labelled unverified. Cautionary: arXiv:2511.15755 was withdrawn by its author after a code audit found the multi-agent arm's action list was a source constant — do not cite its numbers. Closest prior art was assessed from abstracts, not full texts; the scan is not a systematic review. |
| 2026-10-08 | CURRENT / IMPLEMENTED | Acquired the focused four held-out exam captures with SHA-256 checksums recorded: 44 (RBot, 639,643,247 B), 50 (Neris, 285,841,002 B), 49 (Murlo, 403,955,463 B), 54 (Virut, 262,668,288 B). Capture 48 is already local. Added `scripts/run_phase3_heldout_battery.py`, which builds each exam capture's behavioral `1.1.0` features (cacheable, `--features-only` for per-capture parallelism), fits the frozen policy on captures 52/47, and scores at the frozen threshold with no threshold search. Feature building for the battery is running; **no exam result exists yet**. | `docs/phase3_heldout_design.md` acquisition table; `scripts/run_phase3_heldout_battery.py`. Raw captures are gitignored. Known cost: the behavioral builder recomputes prior-window counts per event, so large captures (44 has 4,710,639 rows) take tens of minutes each. |
| 2026-10-08 | VALIDATED | Fixed a superlinear prior-window computation in the behavioral `1.1.0` feature builder that blocked the held-out exam captures. `prior_connections` scanned the host's whole 300s window on every event (O(F^2) for a host with F flows in one window); it now reads an O(1) mirror deque of the 60s window. Semantic equivalence proven by rebuilding two cached captures from raw and comparing all 32 features plus the label column against the frozen artifacts (46: 129,832 rows identical; 53: 325,471 rows identical). | Issue #9; `src/aegistrace/features/behavioral.py`; `tests/test_features.py::test_behavioral_prior_connection_count_expires_at_sixty_seconds`; `scripts/run_phase3_heldout_battery.py`. Performance fix only: no feature value, threshold, model, or frozen policy changed, and no held-out data was consumed. Gate: 71 passed / 90.59% coverage; ruff and mypy clean. |
| 2026-10-08 | VALIDATED | Ran the frozen-policy held-out exam battery (no threshold search) on four of the five approved captures; capture 44 was deferred because its working set exceeds the 16 GB host memory and it thrashed swap. Result: within training families the policy transfers almost perfectly (50 Neris: precision `0.9993`, recall `0.9987`), but unseen families degrade non-uniformly — 49 (Murlo) recall `0.9675` at precision `0.4694` (precision collapse), 54 (Virut) precision `0.9597` at recall `0.4515` (recall collapse). Unknown-label alert share `33.6%`-`43.1%` on every capture, consistent with the validation pool's `43.7%`. Capture 48's recall `0.1429` rests on only 63 malicious labeled rows and is not a stable estimate. | Issue #6; `scripts/run_phase3_heldout_battery.py`; `data/evaluation/phase3_heldout/heldout_summary.json` (ignored); `docs/phase3_heldout_design.md` Results section. Also required the O(1) prior-window fix (Issue #9) and a memory-lean runner path. No threshold, model, feature, or frozen policy changed, and no tuning followed the result. |
| 2026-10-08 | VALIDATED | Measured the unknown-label alert workload at the frozen threshold for the four-capture validation pool. At threshold `0.20` the frozen balanced Random Forest records pooled labeled recall `0.9949` at precision `0.9903` but raises `1,189,850` alerts on `2,720,880` unlabeled rows (43.7% of unlabeled traffic; `1,302,368` alerts across all `2,886,156` rows). Pooled recall is dominated by capture 51 (`106,352` of `112,001` positives, recall `0.9999`); capture 53 (NSIS) recall is `0.7703` and capture 46 is `0.9578`, which is the concrete reason for per-capture reporting. The script reproduces the hardening artifact's alert volume exactly (captures 46+53: known_alerts `2,600`, unknown_alerts `183,669`; recorded total `186,269`). | `scripts/report_phase3_unknown_workload.py`; `data/evaluation/phase3_unknown_workload/workload_summary.json` (ignored); `docs/phase3_evaluation_diagnosis.md` Evidence 5; Issue #8. Read-only: no threshold, model, feature, artifact, or frozen policy changed. |
| 2026-10-08 | APPROVED INTENT / DESIGN | Approved the analyst-outcome evidence program after concluding that no live analyst study is available. Stages, in order: (1) decision-theoretic replay on already-held labels, (2) deterministic reviewer simulation, (3) secondary analysis of published human-factors data. The one available external expert is reserved for independent verification of the *completed* method, not as a source of study data, so the project must exhaust its own options first. | `docs/analyst_outcome_program.md`; Issue #10. Boundaries: Stages 1-3 may not claim human decision quality, analyst behaviour, over-reliance, automation bias, or real SOC outcomes. No detector policy, threshold, feature, or frozen artifact changed. |
| 2026-10-09 | CURRENT / IMPLEMENTED | Added the consolidated results ledger, the project's first single place that states what it claims, at what evidence tier, backed by which registered artifact, and what each claim does NOT support. `docs/results_ledger.json` holds 12 claims (8 SUPPORTED, 1 REFUTED, 1 NOT_CLAIMABLE, 2 UNKNOWN) across the existing claim taxonomy, plus 8 explicit non-claims and 5 evidence gaps; `docs/results.md` is rendered from it. Crucially the ledger is machine-checked: `scripts/validate_results_ledger.py` fails if a claim names an experiment absent from the registry, cites an artifact not registered to a referenced experiment, has no scope limit, or is SUPPORTED with no evidence. Two honesty properties are enforced rather than promised: every claim must carry a non-empty scope limit, and an artifact-backed claim must name the registered run that produced it. Discovered while building it that the held-out exam battery and the unknown-label workload run were never registered, so both are now registered as `phase3-heldout-exam-battery-1.1.0` and `phase3-unknown-workload-1.1.0`, taking the registry to 9 runs. | Issues #10, #12; `docs/results_ledger.json`, `docs/results.md`, `scripts/validate_results_ledger.py`, `scripts/render_results_ledger.py`, `tests/test_results_ledger.py`, `docs/experiment_registry.json`. Registry digests are sha256 of the artifact's RAW BYTES, not of canonical JSON. Gate: 200 passed / 92.48%; ruff clean; mypy clean (48 files); registry 9 runs / 0 missing artifacts. |
| 2026-10-09 | CURRENT / IMPLEMENTED | Made the evaluation artifacts self-checking. The summary and headline blocks inside each artifact restate what the raw per-capture records show, and nothing verified that a summary agreed with its own numbers - the most damaging defect a research artifact can have, and one that would otherwise have passed silently. `tests/test_artifact_self_consistency.py` now recomputes each summary claim from the raw records rather than reading the summary for it: Stage 1 has no uncertainty policy beating model_score on true positives at any capture or budget, Stage 2 has uncertainty strictly beating model_score at 0 of 150 paired (strictness, shift_budget) settings, the Stage 2 headline block matches recomputation exactly, all internal arithmetic holds, and held-out confusion matrices re-derive precision and recall to under 1e-9. All assertions held - no summary disagrees with its own data. | Issue #10; `tests/test_artifact_self_consistency.py`. The reviewer simulation deliberately omits the ORACLE policy and documents why in `sweep_axes.oracle_excluded` (it reads ground-truth labels and is not an achievable reviewer policy); the test requires replay to carry all four policies and the simulation to carry every policy it declares, so a silent drop still fails. |
| 2026-10-09 | CURRENT / IMPLEMENTED | Wired the full audit spine end to end for the first time. Until now the triage layer and the human-review layer were built and tested separately and nothing connected them. `src/aegistrace/spine.py` now carries one finding from evidence bundle through two independent assessors, the deterministic agreement engine, tier classification, and an open review history, returning a frozen `SpineRecord` per bundle. It calls `run_independent_triage` once for the whole run rather than once per bundle, matches bundles to their comparison and assessments by `evidence_bundle_id`, and derives `spine_id` deterministically by uuid5 so identical runs produce identical ids. The spine CANNOT act: it has no `append_review` import, no path that constructs a review, and it raises `RuntimeError` if a history is ever found populated, which a test proves by making `new_history` return a populated history. Verified independently by running it and confirming the review count is zero. | Issue #11; `src/aegistrace/spine.py`, `scripts/run_offline_spine_demo.py`, `tests/test_spine_integration.py`, `docs/triage_provider_boundary.md`. The demo artifact `data/evaluation/triage_spine/offline_spine_demo.json` is a SYNTHETIC demonstration using mechanical stub assessors and carries that warning in the artifact itself; it is not a triage result and `providers_configured` is false with `network_egress` none. Gate: 172 passed / 92.48%; ruff clean; mypy clean (48 files). |
| 2026-10-08 | CURRENT / IMPLEMENTED | Added the triage provider boundary, which makes the human egress gate a property of the code rather than a promise in a document. `src/aegistrace/triage/provider.py` defines `ProviderDescriptor`, `ProviderRequest`, `ProviderResponse`, and a `TriageProvider` protocol, plus two offline providers (recorded replay and a clearly-labelled stub). `src/aegistrace/triage/run.py` defines `assert_provider_permitted`, which raises `PermissionError` for any descriptor requiring egress unless the freeze artifact's status is in `APPROVED_EGRESS_FREEZE_STATUSES` (a small allowlist that deliberately excludes `BLOCKED_HUMAN`), and `run_independent_triage`, which sends the byte-identical snapshot digest to both roles and aborts rather than compares on a digest mismatch. Verified directly: a remote descriptor is refused under the repo's `BLOCKED_HUMAN` status, an offline descriptor is permitted, and a remote descriptor is permitted only once the status is approved, so the gate opens and closes with the human decision. No network-capable import exists anywhere in the new code. | Issue #11; `src/aegistrace/triage/provider.py`, `src/aegistrace/triage/run.py`, `tests/test_triage_provider.py`, `docs/triage_provider_boundary.md`. Gate: 161 passed / 91.98%; ruff clean; mypy clean (47 files). No provider is configured and nothing has been sent anywhere; measured spend remains zero. |
| 2026-10-08 | CURRENT / IMPLEMENTED | Converted the one-off manual egress audit into a permanent, non-vacuous test invariant. `tests/test_snapshot_leakage.py` writes unique sentinel tokens into the raw input events and asserts they survive into neither the evidence bundle nor the provider snapshot, so the test fails if a leak is reintroduced rather than passing because no fixture happened to contain a label. The first version of this file was caught being vacuous: it asserted the label was absent from the snapshot, but the label is already dropped before the bundle is built, so the assertion proved nothing. The suite now also pins the fact that network addresses DO reach the snapshot, so stripping them later is a deliberate decision rather than a silent change. | `tests/test_snapshot_leakage.py`, 9 tests; supports the egress audit recorded in `configs/triage_provider_freeze.json`. |
| 2026-10-08 | VALIDATED | Milestone 6 stage 2 completed and corroborates stage 1. A deterministic reviewer-policy sweep (work the queue in routing order up to a shift budget; escalate iff score >= strictness) covered 75 policies per capture and 450 overall across six captures. Uncertainty beats model_score at equal (strictness, shift budget) in 0 of 6 captures, so the stage 1 refutation is not an artifact of one retrieval rule; model_score is the best routing at every strictness and every budget on every capture, and random again beats uncertainty on capture 49 (15 vs 10). The reviewer is a stated policy, not a person, and the shift budgets and strictness values are free assumptions with no published anchor. | Issue #10; `src/aegistrace/evaluation/reviewer_simulation.py`, `scripts/run_reviewer_simulation.py`, `tests/test_reviewer_simulation.py`, `docs/analyst_outcome_program.md`, `docs/experiment_registry.json` (run `phase3-reviewer-simulation-1.0.0`), artifact `data/evaluation/phase3_reviewer_simulation/simulation_summary.json` digest `88120f046ad0b9c836828cde1e9c9b6a47a9e362a05255165925fc735ceda4ef`. Metric convention: `false_escalation_rate` is false escalations over escalations, not over reviewer load. |
| 2026-10-08 | VALIDATED | Stage 3 evidence base established as `docs/human_factors_evidence.md`. Three sources carry usable numbers, two were re-fetched and read from source tables during review, and the review caught a transcription error: per-alert time in the IDS false-alarm experiment is a median of 13.44 s versus 18.76 s (mean 13.95 vs 19.25), not the "15.6 s vs 21.4 s" first reported, while its precision medians (0.80 vs 0.33) are correct. Two quantities have NO usable published source and must stay explicit free assumptions: alerts-per-shift workload thresholds, and SOC-specific automation bias. A control fetch returning empty was diagnosed as broken network egress in the review shell rather than missing sources, and that spurious "not found" result was discarded. | `docs/human_factors_evidence.md`; verified sources arXiv 2307.07023 and arXiv 2604.22001 (DIMVA'26); the low-confidence automation-bias source is listed only so the gap statement is accurate. |
| 2026-10-08 | VALIDATED | Milestone 6 stage 1 complete and its hypothesis REFUTED. A deterministic decision-theoretic replay asked whether routing alerts by uncertainty reaches more true positives than routing by model score at a fixed reviewer budget. It does not: uncertainty loses on all six captures, and on captures 49 (Murlo) and 54 (Virut) it retrieves fewer true positives at budget 100 than a random queue (8 vs 9, and 59 vs 60). Boundary-adjacent alerts skew benign on these captures, so threshold distance is anti-correlated with maliciousness at the top of the queue. This refutes threshold-distance uncertainty as a routing signal for this detector on these captures; it does not refute predictive entropy, ensemble disagreement, or calibration-based uncertainty, which were untested. No tuning followed the result. | Issue #10; `src/aegistrace/evaluation/analyst_replay.py`, `scripts/run_analyst_outcome_replay.py`, `tests/test_analyst_replay.py`, `docs/analyst_outcome_program.md`, `docs/experiment_registry.json` (run `phase3-analyst-outcome-replay-1.0.0`), artifact `data/evaluation/phase3_analyst_replay/replay_summary.json` digest `1d00ec29273207958d3a48d0c63b8b1a69fcc8e5d3375c342a2c59169a956abe`. Gate: 123 passed / 91.73% coverage; ruff clean; mypy clean (44 files). Each capture is evaluated separately and unknown-label rows are excluded from every metric. |
| 2026-10-08 | CURRENT / IMPLEMENTED | Added the deterministic, provider-independent half of Milestone 8: immutable `HumanReview`/`ReviewHistory` contracts, deterministic review-tier assignment with Tier A evidence-mechanics machine checks, and an append-only history. Tier is a claim about who is qualified to decide rather than a severity; disagreement escalates to expert judgement, mutual abstention is recorded as Tier D, and a failing machine check can raise a tier but never lower one. Corrections supersede the latest review rather than overwriting it, and a `REVISE` decision cannot even be constructed without a supersession link. The minimal local review UI remains unstarted. | Issue #12; `src/aegistrace/schemas/review.py`, `src/aegistrace/review/tiers.py`, `src/aegistrace/review/history.py`, `tests/test_review.py`; `docs/architecture.md`, `src/aegistrace/schemas/__init__.py`. Gate: 112 passed / 91.96% coverage; ruff clean; mypy clean (43 source files); experiment-registry, solution-knowledge, Phase 3 evidence, and agent-trace validators pass. Trace `.context/traces/phase4-review-layer.jsonl` (4 records) validates. |
| 2026-10-08 | CURRENT / IMPLEMENTED | Implemented the Milestone 5 deterministic finding and evidence spine in the branch, with no LLM, fusion, UI, or detector-policy change. ML outputs are emitted as evidence-linked `DetectionResult` records that keep each model's own score scale; findings aggregate detections by source host and observed-time gap using operational fields only; evidence bundles snapshot provenance plus explicit missing context and limitations; and a claim-verification layer enforces the epistemic taxonomy, downgrading an uncited claim to `UNKNOWN_INSUFFICIENT_EVIDENCE` instead of accepting it. | Issue #7; `src/aegistrace/schemas/findings.py`, `src/aegistrace/detection/ml.py`, `src/aegistrace/detection/findings.py`, `src/aegistrace/detection/evidence.py`, `src/aegistrace/verification/claims.py`, `tests/test_findings.py`; `docs/architecture.md`. Gate: 80 passed / 90.85% coverage; ruff clean; mypy clean (33 source files); registry, solution-knowledge, Phase 3 evidence, and agent-trace validators pass. Grouping is asserted identical for any window in the open interval between the largest within-burst and smallest between-burst gap. |
| 2026-10-08 | CURRENT / IMPLEMENTED | Added the provider-independent half of Milestone 7: immutable triage assessment and comparison contracts, assessor-input isolation, single-point assessment admission, a deterministic agreement engine, and a deterministic label-free triage corpus. An uncited assessment is unrepresentable in the schema, a malformed provider response is preserved as a failed attempt rather than coerced into a valid one, and the agreement engine records disagreement without ever picking a winner. Provider selection was deliberately not made. | Issue #11; `src/aegistrace/schemas/triage.py`, `src/aegistrace/triage/snapshot.py`, `src/aegistrace/triage/assessment.py`, `src/aegistrace/triage/agreement.py`, `src/aegistrace/triage/corpus.py`, `scripts/build_triage_corpus.py`, `tests/test_triage.py`, `tests/test_triage_corpus.py`; `docs/architecture.md`. Gate: 100 passed / 91.66% coverage; ruff clean; mypy clean (39 files). Corpus digest `031050e3feda3dd652604f6fb002bd21e7fbb3e3128196f525c1fa4f2881329f` reproduces byte-identically across runs and is order-independent. |
| 2026-10-08 | CURRENT / IMPLEMENTED | Established that subagent delegation in this environment must be routed to the `opencode-go-2` provider. Every delegation routed to `opencode-go` failed immediately with no output and an empty working tree, across all five advertised models and eight attempts, which is consistent with that provider's exhausted quota rather than a model defect; the first delegation routed to `opencode-go-2` completed successfully and its output was independently reproduced. | Verified empirically; `list_subagent_models` shows both providers advertise the same five models (`space-bunny-free`, `mimo-v2.6-flash`, `longcat-2.5-preview-free`, `deepseek-v4.1-flash`, `deepseek-v4-flash`), each supporting `low`/`high`/`max` reasoning effort. The working tree was confirmed clean after every failure, so no partial work was lost or duplicated; the affected milestones were implemented directly in the main session. |

### Open Decisions

- No LLM provider or model has been selected. As of 2026-10-08 this is `BLOCKED_HUMAN` on two conditions recorded in `configs/triage_provider_freeze.json`: the repository has no LLM client and no credential path (`config.py:68` supports only non-secret settings), and no available model pairing provides assessor independence because every reachable provider advertises one mirrored catalog and the only two models verified working are the same family. Nothing has been sent to any provider and measured spend is zero. The frozen detector policy was not modified.
- The minimal local review UI is `DESIGN PROPOSED`, not approved: three directions are in `docs/ui_design_directions.md` (Chain of Custody, Two Witnesses, Investigation Bench). FastAPI plus static HTML is the approved stack, to be added incrementally and parallel to research. No UI implementation may begin until the owner selects a direction.
- Official IoT-23 Capture 34-1 authorization and the resulting acquisition manifest are not yet available.
- CTU-13 Phase 3 stability validation covers Scenarios 11 and 47 for training plus 5, 12, 4, and 10 for validation; Scenario 7 is sealed. The frozen policy remains ready for one controlled final measurement, but this pass does not authorize reopening Scenario 7.
- The model-family, stability, causal representation, Issue #3 overlap diagnosis, and Issue #4 reproducibility hardening are complete. Fusion remains deferred because no single constrained operating point improved, the union gain is dominated by Scenario 10/51, and HGB has no workload-compliant operating point. A scenario-held-out non-sealed test of the localized burst-density hypothesis or deterministic finding aggregation should precede any final-policy decision; do not reopen Scenario 7 without a frozen policy and explicit gate.
- The Option-A provenance foundation is complete. Initial tracking issues should be used on the next real AegisTrace change before any scheduler, automatic issue mutation, full OTel stack, or self-improvement automation is proposed.
- DShield endpoint/window, scanner schema, and any need for FastAPI, PostgreSQL, or Azure remain deferred to their documented milestones.
- The Phase 3 evaluation diagnosis (Issue #8) reframe is APPROVED as policy (2026-10-08 by the owner): measure the frozen threshold on capture-grouped held-out captures and report unknown-label workload separately, instead of selecting thresholds under a labeled-population-relative cap. Recorded in `docs/phase3_evaluation_diagnosis.md`; no threshold, artifact, or frozen policy was changed by it.
- The Phase 3 held-out design (`docs/phase3_heldout_design.md`) is APPROVED (2026-10-08): acquire the focused four exam captures 44 (RBot), 50 (Neris), 49 (Murlo), and 54 (Virut), and include capture 48 (RBot) from local storage as a fifth exam capture, measured once as a battery at the frozen threshold `0.20` with unknown-label workload reported separately and every capture reported individually. Capture 48 was previously opened for the historical baseline (feature `1.0.0`), so it carries the label "previously opened for the historical baseline; held out from the current frozen policy"; including it consumes the one-time Scenario 7 opening and retires it from any future fresh-test role. No tuning may follow any battery result. The battery has since run (Issue #6, closed): four of five captures measured at the frozen threshold with no threshold search, and capture 44 was not measured because its working set exceeds the 16 GB host memory. Results and interpretation are in `docs/phase3_heldout_design.md`.
- The analyst-outcome evidence program (`docs/analyst_outcome_program.md`) is APPROVED (2026-10-08 by the owner): pursue analyst-decision evidence in order — (1) decision-theoretic replay on already-held labels, (2) deterministic reviewer simulation, (3) secondary analysis of published human-factors data — before involving any external expert. A live analyst study is not available, so the external expert is reserved for independent verification of the completed method, not as a source of study data. Stages 1-3 may not claim human decision quality, analyst behaviour, or real SOC outcomes. Stage 1 has since run (Issue #10) and REFUTED its hypothesis: routing by threshold-distance uncertainty reached fewer true positives than routing by model score on all six captures, and on captures 49 and 54 it did not beat a random queue. The artifact reproduces byte-for-byte. Stage 2 must therefore treat `model_score` as the incumbent baseline to beat, and the refutation is scoped to threshold-distance uncertainty only - predictive entropy, ensemble disagreement, and calibration-based uncertainty remain untested.
- No open item above should be treated as decided until it is explicitly approved and logged here.
