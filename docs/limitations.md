# Limitations

**Status:** Updated after the Phase 3 validation-only detector-improvement and hardening work plus
the 2026-09-22 architecture amendment. The amended multi-model triage architecture is approved
design, not implemented; no production or broad generalization claim is supported.

## Current Limitations

- The repository contains a tested package foundation, an IoT-23 parser validated against a safe synthetic Zeek fixture, and a CTU-13 adapter validated against five genuine labeled text-flow scenarios used across the baseline and validation-only study.
- No official IoT-23 data has been downloaded or validated; the scenario page states authorization is required.
- Canonical event/provenance and dataset-manifest schemas plus two source adapters and typed Parquet/quality artifacts are implemented. Detection rules and supervised model prototypes exist; findings, prompts, UI, and review workflow are not.
- The current validation-only study uses Scenarios 11 and 47 for training and Scenarios 5 and 53 for validation (1,121,466 accepted rows total, with seven rejected rows in Scenario 47). It remains a small, source-specific cross-scenario result, not real-world generalization.
- CTU-13 timestamps do not carry an explicit timezone in the flow rows. The adapter records and applies the scenario's documented `Europe/Prague` context before converting to UTC; this assumption should be independently rechecked before comparative time analysis.
- CTU-13 labels are source annotations. The adapter intentionally maps `Background` and `To-*` labels to unknown, so coarse label counts are a conservative policy rather than a claim that those flows are benign.
- The original three-scenario baseline remains a historical record. During improvement work, Scenario 7 was sealed and not loaded or tuned against; no new held-out-test claim is made.
- The first 26-feature vector and three deterministic rules produce very low recall on the held-out test scenario. This negative result is evidence about this baseline, not evidence that the underlying data cannot support detection.
- Logistic Regression and Random Forest remain simple supervised prototypes. Validation-only threshold tuning and class-weight comparisons improve recall, but the selected threshold is not validated on the sealed final scenario. Unknown labels are excluded from supervised metrics, so results do not describe the majority of raw flows.
- The behavioral `1.1.0` feature family is a defensible representation of prior host behavior, not proof that the feature family is sufficient. It can encode capture-specific host and timing patterns; repeated scenarios, temporal checks, calibration, and an untouched final test are still required.
- Pre-final hardening found a large potential alert workload on unknown validation rows (186,269 alerts at the frozen threshold across 455,303 total rows). Those rows have no authoritative class, so this is a workload signal rather than a false-positive rate; the policy is not an operational alerting claim.
- Only 5.7% of the 2,886,156 cross-scenario validation rows carry an authoritative label (165,276 known; 2,720,880 unknown). Labeled metrics therefore describe a small, malicious-heavy minority (67.8% positive) of observed traffic and cannot be generalized to the unlabeled majority.
- The stability pass operating-point recall (`0.2685` for Random Forest) is bounded by the `<= 200` alerts-per-1,000-labeled-flows cap applied to that malicious-heavy labeled population, not by model discrimination; at the frozen threshold `0.20` the same model records recall `0.9949` at precision `0.9903`. See [phase3_evaluation_diagnosis.md](phase3_evaluation_diagnosis.md). No operational, workload, or generalization claim follows from either figure.
- Calibration was assessed with a training-only sigmoid wrapper and deferred because the Brier score worsened and the ECE improvement was small. Raw model scores must not be described as calibrated real-world probabilities.
- Rules emit detector signals with observed values and thresholds; a signal is not proof of compromise, an incident, or malicious intent.
- No accuracy, grounding, hallucination, latency, cost, or analyst-effort result exists.
- The amended architecture does not yet have a model-family benchmark, disagreement analysis,
  anomaly specialist, temporal specialist, fusion model, deterministic finding aggregator,
  verification layer, reference retriever, dual-LLM comparison, recommendation layer, or reviewer
  training mode. These are planned capabilities, not current system behavior.
- The current datasets justify a small tabular benchmark but not temporal neural models, deep
  representation learning, large gradient-boosting dependency stacks, or semi-supervised claims.
  Adding algorithms for breadth would increase selection bias and operational complexity without
  answering a demonstrated research question.
- A multi-model design can create duplicate alerts, conflicting scores, and false confidence from
  agreement. Component outputs must remain visible, and fusion is invalid unless complementary
  validation errors are demonstrated.
- Deterministic finding aggregation can reduce queue volume while accidentally hiding distinct
  events. It therefore requires preservation and grouping-stability tests before any workload claim.
- External reference retrieval introduces source freshness, licensing, citation, and retrieval
  failure risks. Reference-backed facts must remain separate from telemetry and model inference.
- Two LLMs can share the same blind spots or agree on an unsupported interpretation. Independent
  prompts and frozen outputs improve the experiment but do not create ground truth or expert
  certification.
- Tier B junior review and Tier C expert review are different capabilities. Until a qualified human
  expert participates, the Expert Adjudicator LLM is only an escalation aid.

## Expected Validity Limits

- IoT-23 captures are from specific devices, malware scenarios, collection conditions, and 2018–2019 traffic. Results will not establish current enterprise-network performance.
- Dataset labels combine analyst judgment and labeling rules and may contain ambiguity or error.
- A few selected scenarios cannot represent the diversity of benign networks or attacks.
- Cowrie controlled sessions are useful for contracts and demonstrations but are not representative of uncontrolled internet behavior.
- DShield data is aggregated/unfiltered reporting with potential false positives and cannot serve as malicious ground truth.
- Synthetic fixtures prove deterministic behavior, not real-world detection validity.
- A shared canonical envelope necessarily omits some source semantics; typed source details reduce but do not remove this tradeoff.
- An evidence citation can prove that the model referenced supplied data, not that its interpretation is correct.
- Rule-based unsupported-claim checks cannot recognize every semantic hallucination.
- A single builder acting as reviewer cannot establish inter-rater reliability or general analyst-effort reduction.
- LLM provider/model updates may reduce repeatability even when the model name is unchanged.
- Local batch performance says nothing about real-time throughput, availability, or production operations.

## Complexity guardrails for the amended design

The smallest defensible sequence is: reproduce the frozen baseline; benchmark only a shallow
interpretability control and one low-cost tree alternative if needed; measure disagreement; add one
anomaly-ranking experiment only if its assumptions are explicit; then consider interpretable fusion.
Findings and verification come before any LLM. Temporal neural models, extensive algorithm catalogs,
third-party boosting libraries, reinforcement learning, and automated response are deferred unless a
new evidence-backed requirement changes the scope.

## Claims Explicitly Not Supported

AegisTrace does not currently support claims of autonomous incident response, production readiness, broad threat detection, zero hallucinations, analyst time savings, cloud scale, real-time processing, enterprise deployment, or security impact.

Each limitation should be linked to an experiment or mitigation before any related public claim changes.
