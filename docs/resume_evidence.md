# Resume Evidence Ledger

This file governs portfolio and resume claims. Update it only from repository evidence.

## IMPLEMENTED

- Defined and documented the AegisTrace research problem, scope, non-goals, defensive boundary, architecture, source strategy, evaluation protocol, risks, and phased milestone plan.
- Established a repository-level persistent memory and claim-governance protocol in `AGENTS.md` and `MEMORY.md`.
- Pre-registered leakage controls, detector/LLM evaluation categories, and evidence-grounding requirements before implementation or experimentation.
- Built a Python 3.12 package foundation with a locked `uv` environment, strict Pydantic event/provenance and dataset-manifest contracts, deterministic UUIDv5 event identity, typed TOML configuration, redacting JSON logs, and documentation-safe fixtures.
- Implemented and fixture-tested an IoT-23 labeled Zeek `conn.log` adapter that emits validated canonical events, typed Parquet, a data-quality report, and a dataset manifest without downloading raw pcaps or binaries.
- Implemented a separate CTU-13 Argus `.binetflow` adapter that preserves scenario identity, source labels, source checksums, source-specific typed fields, and timezone assumptions while emitting canonical events, typed Parquet, a quality report, and a manifest. Phase 3 acquired three labeled text-flow artifacts; no packets or executables were downloaded.
- Implemented a versioned, leakage-reviewed 26-column CTU-13 flow feature builder with explicit missing indicators and typed feature Parquet output.
- Implemented a versioned `1.1.0` scenario-local behavioral feature family for prior host connection rate, destination/port diversity, traffic asymmetry, and repeated short connections, with unknown-label context retained but excluded from supervised fitting.
- Implemented three deterministic evidence-traceable flow rules and immutable event-linked detection records that preserve observed values and thresholds.
- Implemented a validation-only improvement runner that compares per-flow and behavioral features, Logistic Regression and Random Forest class weighting, fixed thresholds, and validation-selected thresholds without a test-split argument.
- Implemented a pre-final hardening runner with behavioral feature ablation, temporal-causality audit, training-only calibration assessment, alert-volume analysis, a sealed-scenario guard, and a versioned validation policy artifact.
- Implemented a validation-only model-family benchmark runner covering retained rules, Logistic Regression, shallow Decision Tree, Random Forest, Extra Trees, HistGradientBoosting, a practical linear SVM, and a separately reported Isolation Forest anomaly experiment, with explicit Scenario 7 rejection and per-case disagreement output.
- Implemented a cached, validation-only cross-scenario stability runner for Random Forest, HistGradientBoosting, Linear SVM, and retained rules. It records model-specific score semantics, validation-derived operating thresholds, per-scenario metrics/alert volumes, SVM unique-case analysis, and all-model residual errors without opening sealed Scenario 7.

These are bounded ingestion and detection-foundation accomplishments, not a production security-detection platform.

## VALIDATED

- The Phase 1 foundation passes 22 automated tests with 97.57% branch-aware coverage, Ruff linting, and strict mypy type checking as of 2026-09-20.
- The Phase 2 parser/writer foundation passes 31 automated tests with 94.65% branch-aware coverage, Ruff linting, strict mypy type checking, and lockfile checks as of 2026-09-21.
- Phase 2B real-data validation accepted all 107,251 rows from CTU-13 Scenario 11 with zero rejected or duplicate source rows; the checksum-backed manifest and quality report are reproducible from the documented command.
- Phase 3 baseline execution passed across three scenario-separated CTU-13 files: 107,251 train rows, 129,832 validation rows, and 114,077 test rows, with unknown labels excluded from supervised metrics and checksums, feature version, and seed recorded in the experiment artifact.
- Added and checksum-recorded CTU-13 Scenario 47 (558,912 accepted rows, 7 rejected rows) and Scenario 53 (325,471 accepted rows, zero rejected rows) under the documented CC-BY labeled-flow source; the validation-only run used Scenarios 11/47 for training and 5/53 for validation.
- Validation-only detector improvement was reproducibly executed with feature versions `1.0.0` and `1.1.0`, class-weight variants, a fixed threshold, a validation threshold grid, and per-scenario metrics in the ignored diagnostic artifact. This validates the experiment implementation and the measured validation result, not operational effectiveness.
- Pre-final hardening passed the future-event causality audit, measured complementary feature-group contributions, assessed calibration, and froze `configs/phase3_frozen_policy.json` at validation threshold 0.20. This is ready for one controlled final measurement but does not establish operational alert quality.
- The post-amendment model-family benchmark reproduced the four-scenario training/validation boundary and recorded model parameters, checksums, metrics, alert volume, fit runtime, per-scenario stability, and malicious-case disagreement in `data/evaluation/phase3_model_family/benchmark_summary.json`. This validates the experiment implementation and exploratory validation result, not a final detector or operational capability.
- The cross-scenario stability pass reproduced four validation scenarios with licensed source checksums and behavioral feature version `1.1.0` in `data/evaluation/phase3_model_stability/stability_summary.json`. Under a validation-only precision/workload policy, Random Forest was the strongest compliant standalone result; HGB's higher PR-AUC had no feasible operating point; SVM's unique coverage was unstable. This validates methodology and bounded validation evidence, not operational effectiveness.

This validates the implemented software contracts and utilities only. It is not security-detection or research-result validation.

## PROTOTYPE

- Logistic Regression and Random Forest supervised baselines plus behavioral-feature variants trained on two CTU-13 scenarios and evaluated on two separate validation scenarios. The improvement is a prototype validation result; the sealed final scenario has not been reopened.
- The model-family benchmark and stability pass are prototype comparative results: RF is strongest under the declared workload constraint, HGB is a ranking-only result under that constraint, and SVM does not provide stable complementary coverage. The 3,192-case residual points to a temporal/host representation gap. No fusion policy or production detector is claimed.

## PLANNED

- Provenance-first multi-model investigation architecture: justified specialist benchmark,
  disagreement analysis, optional interpretable fusion, deterministic findings, verification labels,
  vetted references, independent AI review, tiered human review, and non-destructive recommendations.
- Authorized real IoT-23 Capture 34-1 ingestion and Cowrie adapter.
- Parquet/DuckDB normalized storage.
- Causal temporal/host representation study and any resulting repeat of the sealed validation protocol.
- Deterministic alert aggregation into provenance-preserving investigation findings.
- Verification labels, vetted reference retrieval, and a deterministic AI agreement/conflict engine.
- Independent LLM A triage and LLM B adjudication, followed by tiered human review and reviewer-training mode.
- Findings and evidence bundles.
- Structured evidence-grounded LLM triage and validator.
- Human-review workflow and Streamlit dashboard.
- Comparative evaluation and final portfolio report.

## NOT CLAIMABLE

- Operational detector performance, despite the recorded exploratory and validation-only metrics. The study is a small CTU-13 experiment, thresholds were selected on validation, and the final scenario remains sealed.
- Reduced analyst effort or human override rate.
- Broad real-dataset coverage or cross-dataset generalization. The improvement study uses four named training/validation scenarios and keeps the final scenario sealed; IoT-23 remains synthetic-fixture validated only.
- Real-time, production, cloud, or enterprise deployment.
- Operational security impact, users, scale, latency, or cost.
- Autonomous SOC, detection, response, remediation, or prevention capabilities.
- A multi-model ensemble, anomaly detector, temporal model, fusion model, or dual-LLM adjudication
  system; the amendment is approved design only until code and evaluation evidence exist.
- Claims that two AI reviewers agreeing establishes truth or that an LLM is equivalent to an expert
  security reviewer.

## Claim Review Checklist

Before publishing a claim:

1. Link it to code, tests, a dataset manifest, experiment artifact, screenshot, or reproducible command.
2. Use the narrowest accurate status: implemented, prototype, or validated.
3. Include dataset and evaluation scope when stating a metric.
4. State material limitations and avoid implying production use.
5. Move unsupported ideas to `PLANNED` or `NOT CLAIMABLE`.
