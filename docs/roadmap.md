# AegisTrace Staged Roadmap

**Status:** Revised 2026-09-30 after the causal representation study, stability-artifact repair,
Issue #3 overlap-subgroup diagnosis, and Issue #4 reproducibility hardening.
Scenario 7 remains sealed. This roadmap distinguishes repository evidence from approved future
intent; a design entry is not an implementation claim.

## Current state

| Stage | Status | Evidence and boundary |
|---|---|---|
| Phase 0 — charter, safety, architecture, methodology | `VALIDATED` | Core documentation, claim ledger, and memory protocol are present. The architecture is now amended with a multi-model investigation target, but the new layers remain design. |
| Phase 1 — package and data contracts | `VALIDATED` | Python 3.12/`uv`, configuration, redacting logs, canonical events, manifests, fixtures, tests, Ruff, and mypy. |
| Phase 2 — ingestion foundations | `VALIDATED` | IoT-23 Zeek adapter is fixture-validated; CTU-13 Argus adapter has checksum-backed Scenario 11 validation and typed Parquet/quality artifacts. Official IoT-23 Capture 34-1 remains authorization-gated. |
| Phase 3A/B — features and deterministic rules | `VALIDATED` | Feature versions `1.0.0` and behavioral `1.1.0`; three evidence-traceable rules; labels and scenario metadata excluded from model matrices. |
| Phase 3C — supervised baseline, improvement, hardening | `VALIDATED` / `PROTOTYPE` | Logistic Regression and balanced Random Forest experiments use Scenarios 11/47 for training and 5/53 for validation. The frozen validation policy is ready for one controlled final measurement; Scenario 7 has not been reopened. |
| Phase 3D — model-family, stability, and representation studies | `VALIDATED` / `PROTOTYPE` | The model-family benchmark, corrected four-scenario RF/HGB/SVM operating-point pass, causal `1.2.0` representation study, bounded Issue #3 overlap-subgroup diagnosis, and Issue #4 reproducibility hardening are complete. RF remains the strongest compliant standalone result; HGB has ranking value but no workload-compliant point; causal context modestly improves union coverage without improving any single operating point. Scenario 7 remains sealed. |

## Post-amendment sequence and current gate

These experiments use training and validation data only. They must not open Scenario 7.

1. **Reproduce the frozen reference.** Completed in the model-family artifact; checksums, feature
   version, seed, threshold, and scenario boundaries are recorded.
2. **Small model-family benchmark.** Completed. Results include precision, recall, F1, PR-AUC,
   FPR/FNR, per-scenario stability, alert volume, fit runtime, interpretability, and disagreement.
3. **Optional anomaly ranking.** Completed as a separate Isolation Forest experiment with explicit
   contamination semantics. Unknown rows remain unknown; workload is reported separately.
4. **Disagreement analysis.** Completed. Unique coverage was narrow and did not justify fusion.
5. **Fusion decision.** Deferred. Do not train a meta-model until more scenario/split evidence shows
   useful complementary coverage at an acceptable workload.
6. **Stability follow-up.** Completed with licensed Scenarios 4 and 10. The residual gap is short,
   low-activity, low-diversity mixed-protocol traffic; this is a representation hypothesis, not a
   reason to add another model family.
7. **Representation study.** Completed as feature version `1.2.0`. It reduced all-three residuals
   by 4.9% through lower RF/SVM overlap, but no individual operating point improved and the gain
   was dominated by Scenario 10/51. Do not promote it to a frozen policy or reopen Scenario 7.
8. **Residual-overlap diagnosis.** Completed as Issue #3 without refitting or opening Scenario 7.
   The Scenario 10/51 gain is localized to a high-rate, repeated-short, low-destination-diversity
   subgroup, while substantial similarly shaped residuals remain. The hypothesis is not a policy
   promotion or causal proof.
9. **Next gate.** Either test this narrow burst-density hypothesis on a scenario-held-out,
   non-sealed capture with the frozen operating policy, or stop detector expansion and begin
   deterministic finding aggregation. Do not promote `1.2.0`, add fusion, or add a model family
   without new evidence.
10. **Evidence hardening.** Completed as Issue #4: diagnostic helper tests, a tracked experiment
    registry, digest and sealed-scenario validators, and aggregate Wilson uncertainty summaries.
    These controls improve reproducibility only; they do not alter detector outputs or policy.
11. **Product layer.** After the next research gate, implement deterministic finding/evidence
    aggregation if detector expansion remains unjustified. Preserve event-level provenance and
    unknown/insufficient-evidence outcomes.

The completed benchmark does not alter the frozen policy or open Scenario 7. Before any final-test
run, freeze the detector/fusion policy, feature and rule versions, aggregation version, thresholds,
checksums, and code/environment identifiers. Only then may Scenario 7 be opened once for the final
held-out measurement. The result is accepted whether favorable or unfavorable, with no post-test
tuning.

## Later staged research

| Stage | Status | Smallest defensible objective |
|---|---|---|
| Findings and evidence bundles | `PLANNED` | Produce immutable investigation units that retain every contributing event, detector output, score, rule, and limitation. |
| Reference-backed verification | `PLANNED` | Retrieve vetted MITRE/CISA/NVD/Zeek/Cowrie/dataset references with explicit source and retrieval provenance. |
| LLM A triage | `PLANNED` | Summarize bounded evidence, uncertainty, and next step in structured output. |
| LLM B adjudication | `PLANNED` | Independently challenge the same evidence without seeing LLM A; freeze both outputs before comparison. |
| Agreement/conflict engine | `PLANNED` | Deterministically label corroboration, contradiction, insufficient evidence, disagreement, and escalation. |
| Tiered human review | `PLANNED` | Separate machine-verifiable checks, guided junior review, expert review, and insufficient-evidence outcomes. |
| Reviewer training mode | `PLANNED` | Teach basic triage using trusted references and feedback without implying expert certification. |
| Local review UI | `PLANNED` | Surface evidence, model inference, uncertainty, AI comparison, and immutable review history. |

## Optional research, only if evidence justifies it

- Temporal/host-context representation work only after the residual hypothesis is specified and
  evaluated with the same scenario boundaries. A temporal model is not yet justified.
- Semi-supervised or positive-unlabeled learning only after unknown-label assumptions and a separate
  evaluation design are defensible.
- PCA for diagnostic compression and UMAP/t-SNE for visualization, never as standalone detector
  selection evidence.
- Additional sources such as authorized IoT-23, controlled Cowrie, DShield, or scanner JSON only
  when provenance, licensing, and the research question justify them.

## Deferred or rejected for now

XGBoost, LightGBM, CatBoost, KNN, MLPs, autoencoders, clustering, reinforcement learning,
Kafka/Kubernetes, graph databases, cloud deployment, and automated blocking/remediation are not part
of the next sequence. They add complexity or risk without a demonstrated requirement. No LLM work
begins before findings, evidence bundles, verification, and the evaluation corpus exist.
