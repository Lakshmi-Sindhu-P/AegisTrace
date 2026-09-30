# AegisTrace Architecture

**Status:** Phase 1 contracts, Phase 2 ingestion, Phase 3A versioned features, Phase 3B deterministic rules, and Phase 3C baseline/improvement/hardening evaluation code are implemented and tested. The accepted three-scenario baseline remains historical; the current detector-improvement study uses two training and two validation scenarios while Scenario 7 remains sealed. A validation-frozen Random Forest policy exists for a future one-time final measurement. The multi-model, finding, verification, dual-review, reference-retrieval, and recommendation layers below are approved design, not implemented capability.

## Design Principles

1. Evidence precedes explanation.
2. Raw source meaning and provenance survive normalization.
3. Rules, ML, LLM triage, and human decisions remain separate records.
4. Missing data is explicit; adapters never invent values.
5. Batch and local-first are sufficient until measurements prove otherwise.
6. Every component must be testable without an external LLM or live security service.
7. A detector family earns inclusion through complementary error evidence and reproducible evaluation, not algorithm count.
8. Investigation recommendations are deliberately weaker than incident, compromise, or maliciousness claims.

## System Context

```text
┌──────────────────────────────── Sources ────────────────────────────────┐
│ CTU-13 flows │ IoT-23 Zeek │ controlled Cowrie JSON │ DShield │ scanner JSON │ fixtures │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │ untrusted input
                                v
┌──────────────────── Ingestion and normalization ───────────────────────┐
│ source adapter -> validation -> canonical event -> data-quality report │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │ versioned Parquet
                                v
┌──────────────────── Detection and investigation evidence ──────────────┐
│ feature view -> rules | supervised | anomaly | temporal specialists    │
│ independent outputs -> disagreement analysis -> optional fusion        │
│ detection records -> deterministic finding aggregation -> evidence     │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │ verified, bounded evidence only
                                v
┌────────────────────── Triage, adjudication, and review ────────────────┐
│ verification labels -> LLM A triage + isolated LLM B adjudication      │
│ independent frozen outputs -> deterministic agreement/conflict engine  │
│ evidence + uncertainty -> junior review | expert escalation | abstain  │
└────────────────────────────────────────────────────────────────────────┘
```

## Component Boundaries

| Component | Owns | Must not do |
|---|---|---|
| Source adapter | Parse one source and map source fields | Infer missing source facts or assign new ground truth |
| Validation | Schema, ranges, required fields, data-quality issues | Silently repair ambiguous data |
| Storage | Versioned Parquet datasets and DuckDB query views | Become the source of raw evidence |
| Feature builder | Versioned, leakage-reviewed model inputs | Include labels, scenario names, raw identifiers, or post-event facts as features |
| Detector registry | Record specialist identity, version, score semantics, and resource cost | Treat every candidate algorithm as justified or comparable by default |
| Detector | Immutable detection result linked to event IDs | Overwrite source events or claim final disposition |
| Disagreement analysis | Compare detector outputs and residual errors on validation data | Use Scenario 7 to choose a model, feature, threshold, or ensemble |
| Fusion layer | Combine complementary detector outputs under a frozen, interpretable policy | Turn agreement into ground truth or hide individual detector outputs |
| Finding aggregator | Group related detections and construct evidence references | Add evidence that no detector or source produced |
| Verification layer | Classify claims as observed, derived, reference-backed, inferred, interpreted, or unknown | Upgrade a model score or anomaly into a fact |
| Reference retriever | Attach vetted external references with source, version, and retrieval provenance | Blur external references with telemetry or silently treat them as truth |
| LLM A triage | Structured proposal based on one evidence bundle | Fetch unrestricted context or act as ground truth |
| LLM B adjudication | Independently challenge the same evidence and identify contradictions | See LLM A's conclusion before its own output is frozen |
| Agreement engine | Deterministically compare independently frozen outputs | Ask a third LLM to decide which reviewer is correct by default |
| Human review | Record tier, disposition, notes, and escalation while preserving history | Replace or mutate the original AI result, or imply expert certification from an LLM |
| Recommendation layer | Suggest monitor, gather evidence, review, escalate, or prioritize | Automate blocking, isolation, remediation, or destructive response |
| Evaluation | Reproduce metrics from versioned records | Mix test data into feature/model selection |

## Canonical Entities

The Phase 1 event, provenance, and manifest contracts are immutable Pydantic models in `src/aegistrace/schemas/`; Phase 2 adds CTU-13-specific flow details and scenario identity. Phase 3 adds an immutable detection record for rules and versioned feature records. Finding, evidence-bundle, triage, and review contracts remain designs for their scheduled milestones.

### SourceRecordRef

| Field | Type | Rule |
|---|---|---|
| `source_type` | enum | `ctu13`, `iot23`, `cowrie`, `dshield`, `external_scanner`, or `synthetic` |
| `source_dataset` | string | Stable dataset/feed/sensor name |
| `scenario_id` | optional string | Stable capture/scenario boundary preserved for leakage-safe grouping |
| `dataset_version` | string | Version or dated snapshot identifier |
| `source_event_id` | string | Upstream ID, or deterministic file/record identity when absent |
| `raw_payload_reference` | string | Relative local reference or durable URI; never embed secrets |
| `raw_checksum` | optional string | SHA-256 where the referenced unit is stable |

### SecurityEvent

| Field group | Required content |
|---|---|
| Identity | `schema_version`, deterministic `event_id`, `SourceRecordRef` |
| Time | UTC `observed_at`, UTC `ingested_at`; preserve source timezone assumptions |
| Classification | normalized `event_type`; optional `ground_truth_label`, `label_source`, and `attack_category` |
| Correlation | optional `session_id` and source-provided correlation identifiers |
| Details | exactly one typed detail payload where applicable: network, CTU-13 flow, authentication, command, HTTP, scanner finding, or generic source fields |
| Provenance | adapter name/version, transformation version, processing timestamp, and quality flags |

`event_id` should be a UUIDv5 derived from a project namespace plus `source_type`, `source_dataset`, `scenario_id`, `dataset_version`, and `source_event_id`. If a source lacks an ID, the adapter must first derive `source_event_id` from an immutable file identity and record position. This makes reprocessing idempotent without treating raw content as globally unique.

`Ctu13FlowDetails` is a source-specific typed payload for Argus fields (direction, state, TOS,
source label, and original source addresses). It is deliberately separate from
`NetworkEventDetails`: both sources share canonical network concepts, but CTU-13's label strings,
MAC-address flows, and Argus semantics must remain visible after normalization.

### Phase 3 feature and detector boundaries

`src/aegistrace/features/network.py` emits `FEATURE_VERSION=1.0.0` with a small numeric feature
vector. Event IDs, scenario IDs, source record IDs, and labels remain metadata and are never passed
to model fitting. Missing numeric values become zero plus an explicit missing indicator; categorical
values use fixed one-hot flags with an `other`/`missing` bucket. `src/aegistrace/detection/rules.py`
contains three fixed predicates (`high_volume_flow`, `long_lived_high_volume_flow`, and
`icmp_packet_burst`) that emit `DetectionResult` records with observed values and thresholds.

`src/aegistrace/features/behavioral.py` composes a version `1.1.0` vector with prior, scenario-local
host aggregates: connection rate, destination and port diversity, traffic asymmetry, and repeated
short connections. It rejects mixed-scenario input and uses only flows observed before the current
flow. `src/aegistrace/evaluation/improvement.py` performs validation-only class-weight and threshold
comparisons; its runner has no final-test argument. `scripts/run_phase3_hardening.py` performs
feature-group ablations, a future-event causality audit, calibration assessment, and alert-volume
analysis, then writes the frozen policy in `configs/phase3_frozen_policy.json`. Neither runner can
load the sealed Scenario 7 identifier.

`src/aegistrace/evaluation/baselines.py` fits Logistic Regression and Random Forest only on known
benign/malicious rows from the train scenario. Validation and test scenarios remain separate, and
unknown labels are excluded from supervised fitting and metrics.

### Amended multi-model detection design

**Status: APPROVED INTENT / DESIGN — not implemented.** The final detector is not assumed to be a
single universal malicious-versus-benign classifier. Candidate specialists run in parallel over the
same provenance-preserving evidence, and their outputs remain separately inspectable. A model family
is included only when it answers a clear question, survives scenario-aware validation, and exposes a
useful error or workload trade-off.

The smallest defensible benchmark is:

- existing deterministic rules as the transparent floor;
- Logistic Regression as a linear, coefficient-interpretable baseline;
- the existing balanced Random Forest as the strongest current supervised prototype;
- one shallow Decision Tree as an interpretability control; and
- Extra Trees only if a low-cost tree-diversity comparison is still informative.

Isolation Forest is an optional exploratory specialist for ranking unusual behavior. It must be
trained under an explicit contamination assumption and evaluated as anomaly prioritization, not as
malicious ground truth. HistGradientBoosting is an optional later tabular benchmark if the smaller
tree comparison leaves a clear unresolved question. XGBoost, LightGBM, CatBoost, SVM, KNN, MLPs,
autoencoders, clustering, and semi-supervised methods are deferred because the current scenario
count, label uncertainty, and interpretability requirements do not yet justify their added
complexity or dependencies.

Temporal neural models are not justified by the current aggregate feature representation. They may
be reconsidered only after additional scenario-separated data and an explicit sequence hypothesis
show that prior-flow aggregates cannot represent the relevant behavior. PCA is appropriate for
diagnostic compression; UMAP/t-SNE are visualization tools, not detector-selection evidence.

Before fusion, the evaluation must measure whether specialists catch different validation cases. If
their errors are substantially redundant, retain the simpler detector. If they are complementary,
start with an interpretable Logistic Regression fusion model over detector outputs and preserve all
component signals. A fused score is an investigation-priority signal, not a ground-truth label.

### Findings, verification, and independent AI review

**Status: APPROVED INTENT / DESIGN — not implemented.** Raw alerts will be grouped into findings by
deterministic host/time/destination/port relationships. Aggregation must preserve every contributing
event ID, detector output, score, rule, and feature version. Research labels may evaluate an
aggregator but may not drive grouping or queue priority.

Before any LLM receives a bundle, a verification layer will tag material statements as
`OBSERVED_FACT`, `DETERMINISTIC_DERIVATION`, `REFERENCE_BACKED_FACT`, `MODEL_INFERENCE`,
`AI_INTERPRETATION`, or `UNKNOWN_INSUFFICIENT_EVIDENCE`. It will check identifiers, counts,
timestamps, provenance, and supported deterministic derivations; it cannot prove semantic truth.

Two isolated AI roles are planned. LLM A proposes a structured triage summary, uncertainty, and next
step. LLM B independently reviews the same underlying evidence for contradictions, benign
explanations, unsupported severity, and expert-escalation needs. LLM B must not see LLM A's conclusion
until both outputs are frozen. A deterministic comparison produces `CORROBORATED`,
`PARTIALLY_CORROBORATED`, `CONTRADICTED`, `INSUFFICIENT_EVIDENCE`, `MODEL_DISAGREEMENT`, or
`EXPERT_REVIEW_REQUIRED`. Agreement is not ground truth, and the temporary LLM reviewer is not a
qualified security professional.

Vetted reference retrieval is a separate provenance-bearing input path for sources such as MITRE
ATT&CK, CISA/KEV, NVD/CVE, Zeek/Cowrie documentation, dataset documentation, and carefully selected
threat-intelligence references. Reference text must remain distinguishable from telemetry and model
inference. The recommendation layer may suggest monitoring, evidence collection, guided review,
expert escalation, or investigation priority; it will not automate blocking or remediation.

### DetectionResult

| Field | Meaning |
|---|---|
| `detection_id` | UUIDv4 record identity |
| `event_ids` | Non-empty stable links to canonical events |
| `detector_type` | `rule`, `statistical`, `ml`, or `external_scanner` |
| `detector_name` / `detector_version` | Reproducible detector identity |
| `severity` | `informational`, `low`, `medium`, `high`, or `critical` |
| `score` | Optional detector-specific numeric score; not assumed comparable across detectors |
| `triggered_rules` | Rule identifiers when applicable |
| `supporting_evidence` | Typed evidence references and observed values |
| `created_at` | UTC processing time |

LLM output is not a detector in V1. It interprets findings; it does not create primary detections.

### Finding

A finding groups one or more detection results that concern related events within a documented correlation rule. It stores `finding_id`, event and detection IDs, aggregation version, proposed severity derived by deterministic policy, status, and timestamps. Aggregation is repeatable and versioned.

The planned aggregation contract is intentionally deterministic and evidence-preserving. It groups
related detections using operational fields such as source host, time window, destinations, ports,
and shared behavior. It never uses a research label, model output from a later stage, or an LLM
conclusion to decide which events belong together.

### EvidenceBundle

An immutable snapshot containing:

- `evidence_bundle_id` and version;
- finding and detection references;
- the minimal relevant event fields;
- observed values that caused rules or models to fire;
- model score and feature-version references;
- external findings with their source and uncertainty;
- explicit missing context and known limitations.

The bundle is a serialized object plus relational references. “Evidence graph” describes the logical relationships; V1 does not require a graph database.

### TriageAssessment

Stores `triage_id`, evidence-bundle version, finding IDs, summary, proposed category/severity, non-probabilistic confidence statement, cited evidence IDs, evidence summary, uncertainties, unsupported-claim flags, next step, provider/model/prompt metadata, raw structured response reference, creation time, and review status.

The schema must accept `insufficient_evidence` as a valid category/outcome. Invalid or uncited output is stored as a failed attempt, not silently coerced into a valid assessment.

The amended design adds a role field (`triage_analyst` or `expert_adjudicator`) and an independent
input snapshot to each future assessment. The comparison record is separate from both assessments
and retains raw structured outputs, validator results, and disagreement reasons.

### HumanReview

Stores an immutable link to the original triage assessment or AI-comparison record, reviewer tier,
reviewer decision, notes, review time, escalation state, and final disposition. Tier A machine checks
verify evidence mechanics; Tier B supports guided junior review; Tier C requires genuine expert
judgment; Tier D records insufficient evidence. Corrections create new review history rather than
overwriting earlier records.

### DatasetManifest and ExperimentRun

- `DatasetManifest`: dataset/version, acquisition time, official source, selected scenarios, file checksums, counts, license/terms note, and transformation lineage.
- `ExperimentRun`: experiment ID, code revision, dataset/feature/model versions, split policy, hyperparameters, metrics artifact references, timestamp, and notes. The tracked `docs/experiment_registry.json` now implements a small registry for validated Phase 3 runs; it is evidence metadata, not a scheduler or experiment orchestrator.

Future experiment records must also retain detector-family comparison, disagreement taxonomy,
confidence intervals, alert volume, runtime/resource cost, and the reason a specialist was retained
or rejected. Fusion and architecture choices are selected only on training/validation data.

## Persistence

- Raw third-party data stays outside Git under ignored local storage.
- Normalized immutable event partitions and feature tables use Parquet.
- DuckDB provides local queries and relational views over Parquet.
- Small manifests, configs, prompts, and evaluation cases are versioned in Git when licensing and sensitivity permit.
- Human review can begin in DuckDB for a single local user. PostgreSQL is considered only when concurrency or durable application workflows require it.

## Technology Choices

| Decision | Choice | Status | Reason |
|---|---|---|---|
| Runtime | Python 3.12 | Implemented | Mature data/ML compatibility and long support window |
| Environment/package tool | `uv` with `pyproject.toml` and lockfile | Implemented | Reproducible setup with one project manifest |
| Validation | Pydantic | Implemented for event/provenance/manifest contracts | Typed, versionable boundary models |
| Data frames/storage | PyArrow/Parquet now; Pandas and DuckDB later | PyArrow implemented in Phase 2; others planned | Typed local batch artifacts first, analysis/query tools when used |
| ML | scikit-learn | Implemented for Phase 3 baselines | Logistic Regression and Random Forest with fixed seed and scenario-held-out evaluation |
| Model-family benchmark | scikit-learn first | Approved design | Keep the shortlist small; add a specialist only for a validated hypothesis and complementary error evidence |
| Anomaly detection | Deferred Isolation Forest experiment | Approved design | Treat output as anomaly prioritization, never automatic maliciousness |
| Testing | pytest, Ruff, mypy | Implemented | Runtime contracts, style, and static type checks |
| Configuration | TOML plus explicit environment overrides | Implemented | Avoid an extra YAML or dotenv dependency and keep secrets out of files |
| Logging | Python logging with redacting JSON records | Implemented | Machine-readable context with minimal dependencies |
| UI | Streamlit | Deferred | Suitable for a single-user local review prototype |
| API | FastAPI | Deferred | Add only for a real external consumer |

## Planned Repository Boundaries

```text
src/aegistrace/
    ingestion/     # source adapter protocol and implementations
    schemas/       # canonical and source-detail models
    validation/    # quality checks and reports
    features/      # versioned feature builders
    detection/     # rule, statistical, and ML detectors
    triage/        # findings, evidence bundles, LLM interface, validators
    evaluation/    # split policies, metrics, experiment records
    provenance/    # manifests and lineage utilities
    storage/       # Parquet/DuckDB repositories
    ui/            # deferred Streamlit entry point
```

`api/` will not be created until an API consumer exists. Empty folders will not be committed merely to match a diagram.

## Failure Behavior

- Malformed records are quarantined with source reference and validation errors; a batch reports counts and can fail on configured thresholds.
- Duplicate deterministic event IDs are reported and resolved by explicit policy, never silently appended.
- Missing optional fields stay null with quality flags; required identity/provenance failures reject the record.
- DShield rate limiting honors `Retry-After`, stops repeated requests, and uses cached snapshots where permitted.
- An unavailable LLM does not block detection or evidence creation; triage remains pending.
- Invalid LLM output is retained with validation errors and cannot enter human review as a valid assessment.
- A reviewer correction appends history and never mutates source, detection, or original AI records.

## Architectural Decisions Deferred by Design

- LLM provider/model and prompt transport until Milestone 6.
- API and PostgreSQL until a concrete multi-process or external-client requirement.
- Azure until local reproducibility and evaluation are validated.
- Scanner formats until at least one representative, legally usable JSON fixture is available.
- Multi-model fusion, stacking, anomaly selection, and temporal modeling until the staged benchmark demonstrates a need.
- Reference retrieval and the two-LLM comparison until findings, evidence bundles, verification labels, and evaluation cases exist.
- Automated response actions indefinitely unless the project scope is explicitly changed and separately governed.
