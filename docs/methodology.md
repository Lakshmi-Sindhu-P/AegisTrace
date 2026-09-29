# Research Methodology

**Status:** Phase 0 method plus validated Phase 3 feature/detector implementation. The current
multi-model, finding, verification, and dual-review design is approved intent only. Existing
training/validation results are exploratory and scenario-aware; they are not a broad generalization
claim.

## Study Design

AegisTrace is an incremental engineering case study with quantitative detector evaluation and a
future rubric-based LLM triage evaluation. Each layer is evaluated before it is combined with the
next:

```text
data quality
-> rules
-> supervised and anomaly specialists
-> disagreement analysis
-> optional interpretable fusion
-> deterministic findings and verification
-> independently frozen LLM triage and adjudication
-> human-reviewed recommendations
```

This ordering prevents LLM presentation quality, ensemble complexity, or queue aggregation from
masking an invalid data pipeline or weak detector.

## Working Hypotheses

- H1: Transparent rules will perform well on known behaviors but miss patterns outside their definitions.
- H2: An interpretable ML baseline will find some cases missed by rules but introduce different false positives.
- H3: A bounded evidence package and structured response will reduce unsupported LLM claims compared with an otherwise equivalent ungrounded condition.
- H4: Adding the LLM may improve explanation completeness and category/severity proposals, but it will not improve the underlying detector's event-level performance.
- H5: Explicit abstention and human review will catch a meaningful subset of low-evidence or conflicting cases.
- H6: Detector families that expose complementary residual errors can improve investigation prioritization without making any individual model authoritative.
- H7: Deterministic finding aggregation and claim verification can reduce duplicate reviewer work while preserving event-level provenance.
- H8: Independent AI review will expose some unsupported claims or benign explanations that a single triage pass misses; agreement will not be treated as truth.

These are hypotheses, not findings.

## Current working research question

> Can a provenance-first, multi-model security system combine deterministic, supervised, anomaly, temporal, and reference-backed evidence to generate trustworthy investigation recommendations while clearly separating observed facts from inference and enabling a junior reviewer to handle basic triage without eliminating expert escalation?

The temporal and reference-backed terms describe the approved research direction. They are not claims
that those components are currently implemented.

## Evidence Hierarchy

1. Immutable source records and documented labels/context.
2. Reproducible normalized events and data-quality reports.
3. Versioned detector outputs and features.
4. Deterministically assembled findings and evidence bundles.
5. Structured LLM proposals referencing supplied evidence.
6. Human review decisions and notes.

Later layers can interpret earlier evidence but cannot rewrite it.

## Development and Evaluation Separation

- Use development fixtures and training/validation partitions for implementation and tuning.
- Freeze split definitions, feature versions, rubrics, and prompts before final test evaluation.
- Keep a final scenario/case partition untouched until the method is fixed.
- Version exploratory notebooks, but move reusable transformations and metrics into tested package code.
- Generate documentation tables/figures from artifacts where practical to prevent transcription drift.

## Quantitative Methods

- Summarize missingness, duplicates, distributions, time ranges, class balance, and parse failures before modeling.
- Establish a naive or majority baseline alongside rules and ML.
- Use logistic regression as the first supervised baseline unless target structure demonstrates a better justified starting point.
- Phase 3 uses a fixed 26-column CTU-13 flow feature vector (`FEATURE_VERSION=1.0.0`) with explicit missing indicators. Metadata and labels are kept outside the numeric matrix.
- The accepted historical Phase 3 baseline fits on Scenario 11, checks validation on Scenario 5, and reports final held-out results on Scenario 7. Unknown and directional/background labels are excluded from supervised fitting and metrics, not relabeled as benign.
- The historical baseline uses Logistic Regression with a training-fitted standardizer, balanced class weights, `liblinear`, and `max_iter=1000`, plus Random Forest with balanced class weights, 200 trees, `max_depth=12`, one worker, and seed 42. Its score threshold is fixed at 0.5; no test-driven threshold tuning is performed.
- Use a simple anomaly baseline only when its evaluation question and training contamination assumptions are explicit.
- Report per-class and per-scenario metrics plus error examples.
- Use scenario-aware or temporal splits and prohibit label-derived features.

### Phase 3 detector-improvement investigation

The validation-only improvement study adds CTU-13 Scenario 47 to the training pool and Scenario 53
to validation. Scenario 11 remains in training and Scenario 5 remains in validation. Scenario 7 is
sealed: this study does not load it, tune thresholds against it, or report a new result from it.
Training and validation remain complete capture boundaries, and the additional scenarios are recorded
with their source URLs, checksums, row counts, and license note in the experiment artifact.

The `1.1.0` behavioral feature family is computed separately for each capture from prior observed
flows. A host's connection rate, destination and port diversity, repeated short connections, and
current-flow traffic asymmetry are represented as bounded numeric aggregates. Unknown rows may
contribute to the prior-flow context, but only authoritative `Normal` and `Botnet` labels enter
supervised fitting or metrics. No threshold or class-weight choice is selected from the sealed test.

Logistic Regression and Random Forest are evaluated with `class_weight=None` and
`class_weight="balanced"`. A fixed threshold of 0.5 is compared with a grid from 0.05 through 0.95;
the selected threshold maximizes validation F1, breaking ties by recall, precision, then lower
threshold. The complete precision/recall trade-off and per-validation-scenario metrics are retained
in `data/evaluation/phase3_improvement/diagnostic.json` (a gitignored reproducibility artifact).

### Pre-final hardening and policy freeze

Before reopening the final test, the hardening command runs one-at-a-time behavioral feature-group
ablations at the candidate operating point, appends a deterministic future fixture event to verify
that earlier vectors do not change, evaluates raw versus training-only sigmoid calibration, and
reports known-label confusion plus potential all-row alert workload. The final validation policy is
recorded in `configs/phase3_frozen_policy.json`; the full hardening evidence is in the ignored
`data/evaluation/phase3_hardening/hardening_summary.json` artifact. A final held-out execution must
use that policy exactly once, with no post-test tuning.

### Causal representation follow-up

Issue #2 adds a separate `FEATURE_VERSION=1.2.0` representation study. It composes the validated
`1.1.0` behavioral vector with prior-only host/time values at 60- and 300-second windows: slower
source activity, short-window diversity, destination/port reuse, protocol diversity, prior
bytes/packets, and source-flow recency. The implementation rejects mixed-scenario input and audits
that appending a future event cannot change earlier vectors. Raw addresses are aggregation keys only;
labels, filenames, scenario IDs, and source labels remain outside model matrices.

The study refits only the retained RF, HGB, and Linear SVM over the existing complete-capture split
(Scenarios 11/47 train; 5/12/4/10 validation), with the same seed, parameters, score semantics,
precision/workload operating policy, and unknown-label treatment. It reports per-scenario metrics,
PR-AUC, alert volume, disagreement, and residual cases in the ignored
`data/evaluation/phase3_causal_representation/causal_summary.json`. Scenario 7 remains sealed.
The extension is not promoted to a final detector policy unless a later scenario-held-out study
shows stable operational value.

The prior stability artifact also had a derived-evidence defect: HGB's zero-alert correction was not
propagated to disagreement/residual sections. `scripts/correct_stability_operating_point.py`
recomputes those sections from recorded case IDs and non-sealed feature artifacts, and the residual
quantile helper now computes each reference quantile once. This repair is recorded as an artifact
provenance entry rather than treated as a new model result.

### Causal-overlap subgroup diagnosis

Issue #3 adds a read-only diagnostic rather than another detector. It joins the corrected `1.1.0`
and `1.2.0` malicious validation case records by deterministic event ID, verifies that the common
feature values are unchanged, and classifies each case by the RF/SVM union at each version:
candidate-only, reference-only, residual in both, or covered by both. HGB is not used for the
overlap categories because its declared operating point is the zero-alert fallback. The diagnostic
then summarizes prior-only host/time values by category and scenario; labels are used only to select
authoritative malicious cases for error analysis and never enter a model matrix.

The bounded narrow hypothesis evaluated by the analysis script is that the Scenario 10/51 overlap change is a high-rate,
repeated-short, low-destination-diversity subgroup. It is marked supported only when the
candidate-only median 60-second connection and repeated-short counts are at least 1.5 times the
unchanged residual median, the destination-diversity ratio is at most 1.25, and at least 100
candidate-only cases are present. These thresholds are diagnostic criteria, not a new operating
policy. A local support result cannot establish causality or justify feature promotion; it must be
checked on a future scenario-held-out non-sealed capture.

Detailed metrics and split rules are in [evaluation.md](evaluation.md).

## Staged model-family and fusion methodology

The next experiments remain training/validation-only and must not open Scenario 7. The benchmark
will use complete scenario boundaries, the existing `1.1.0` behavioral features, authoritative
`Normal`/`Botnet` labels for supervised metrics, and explicit treatment of all other labels as
unknown. Every candidate records precision, recall, F1, PR-AUC, FPR, FNR, per-scenario results,
alert volume, runtime/resource cost, confidence intervals, and residual error categories.

The smallest defensible sequence is:

1. Reproduce the frozen Random Forest and Logistic Regression references.
2. Add a shallow Decision Tree interpretability control and, only if useful, Extra Trees as a
   low-cost tree-diversity comparison. Do not broaden the algorithm list without a hypothesis.
3. Add one Isolation Forest experiment only as unknown/anomaly prioritization, with contamination
   assumptions documented and no conversion of unknown rows to benign labels.
4. Compare event-level predictions and errors across rules, supervised models, and anomaly scores.
   Measure overlap, unique true positives, unique false positives, and per-scenario stability.
5. If complementary behavior is demonstrated, fit an interpretable Logistic Regression fusion model
   using out-of-fold training outputs and validation-only threshold selection. Preserve all component
   outputs and compare the fusion against the best single specialist.
6. Add deterministic finding aggregation and evaluate duplicate reduction, evidence preservation,
   grouping stability, and reviewer workload on training/validation cases only.

Temporal models, deep learning, semi-supervised learning, and large gradient-boosting libraries are
not first-line experiments. They require a demonstrated limitation in the simpler shortlist,
additional scenario-separated data, and a specific sequence or label-assumption hypothesis. PCA may
support diagnostics; UMAP/t-SNE may support visualization, but neither is detector evidence.

Fusion or architecture selection is invalid if it uses Scenario 7, test-derived thresholds, or
post-hoc model selection after final-test observation. The final held-out measurement is one frozen
execution, accepted whether favorable or unfavorable.

### Cross-scenario operating-point stability pass

The follow-up stability pass is complete and remains validation-only. It keeps Scenarios 11 and 47
for training and validates on Scenarios 5, 12, 4, and 10. The newly added Scenario 45 and Scenario
51 flow files are CC-BY licensed artifacts; Scenario 7 is sealed and was not loaded. The run is
reproducible from `scripts/run_phase3_model_stability_cached.py` and
`data/evaluation/phase3_model_stability/stability_summary.json`.

Scores are not interchangeable: RF and HGB use their own `predict_proba(X)[:, 1]` scores; Linear
SVM uses a training-range-normalized `LinearSVC.decision_function` margin; Isolation Forest is a
separate unsupervised ranking score made by negating and training-range-normalizing its decision
function; and rules emit binary scores. The shared `0.20` comparison is therefore diagnostic only.

For RF, HGB, and SVM, the predeclared operating policy maximizes pooled validation recall subject
to precision >= 0.95 and <= 200 alerts per 1,000 authoritative labeled rows. Thresholds are searched
in 0.01 increments on each model's own score scale. Unknown rows remain unknown and are excluded
from fitting, metrics, and policy constraints. PR-AUC is calculated from the full labeled ranking
and is threshold-independent. HGB had the highest PR-AUC (`0.999738`) but no threshold met both
constraints; its explicit workload-first fallback produced zero alerts and zero recall. RF was the
strongest compliant standalone detector (PR-AUC `0.999589`, recall `0.2685` at threshold `0.73`),
while SVM was compliant but lower-ranking and unstable across scenarios.

After the HGB zero-alert correction, SVM uniquely caught 13,576 malicious validation cases, but
only in two of four scenarios (0 in Scenarios 4 and 5), so this is not stable complementary
coverage. The corrected all-three residual is 68,353 cases, concentrated in Scenario 10/51 and
dominated by short, low-diversity mixed-protocol flows. The evidence supports the bounded causal
representation study in `docs/phase3_causal_representation.md`, not fusion or another model family
yet. Full per-scenario metrics, alert volumes, subgroup summaries, and residual counts are in
`docs/phase3_model_stability.md`, `docs/phase3_causal_representation.md`, and their JSON artifacts.

### Post-amendment model-family benchmark result

The first post-amendment benchmark was executed with `scripts/run_phase3_model_family_benchmark.py`
on the existing Scenario 11/47 training pool and Scenario 5/53 validation pool. It preserved
behavioral feature version `1.1.0`, the frozen Random Forest configuration, the deterministic rules,
unknown-label treatment, and the sealed Scenario 7 boundary. The full result is in
[phase3_model_family_benchmark.md](phase3_model_family_benchmark.md) and the reproducibility artifact
is `data/evaluation/phase3_model_family/benchmark_summary.json`.

The SVM candidate uses a practical linear margin (`LinearSVC`) with training-range score
normalization; a probability-enabled kernel SVC was not computationally practical for this pool.
Isolation Forest is a separate unlabeled ranking experiment fit on known feature rows without
passing labels to the estimator. Unknown validation rows remain unknown and are scored only for
separate workload analysis.

At the frozen `0.20` operating point, Random Forest retained the strongest F1 (`0.894`) and recall
(`0.825`); HistGradientBoosting had the best PR-AUC (`0.979`) but slightly lower recall. The
per-case disagreement analysis found 30 malicious cases unique to SVM and 1,489 cases missed only
by the deterministic rules; no other family added unique malicious coverage at that operating point.
Isolation Forest produced high recall but substantial false positives and unknown-row workload. The
result supports no fusion or additional model-family complexity yet. More licensed scenarios and
repeated scenario/temporal stability analysis should precede any temporal, semi-supervised, or
fusion experiment.

## LLM Methods

- Build the evaluation corpus and claim-boundary rubric before selecting or tuning a model.
- Compare a bounded evidence condition against a controlled less-grounded condition only if both use the same cases and output schema.
- Require machine-valid structured output and evidence identifiers.
- Retain failed requests, invalid responses, abstentions, and validator failures in denominators.
- Use deterministic settings where supported and record provider-side parameters.
- Separate automatic checks (schema and evidence-ID validity) from human semantic adjudication.
- Keep LLM A's triage prompt/output isolated from LLM B's independent adjudication prompt/output
  until both are frozen. Compare them with a deterministic agreement/conflict engine rather than a
  third LLM by default.
- Label every material claim as observed fact, deterministic derivation, reference-backed fact,
  model inference, AI interpretation, or unknown/insufficient evidence.
- Treat external reference retrieval as separately versioned evidence with source and retrieval
  provenance; it cannot upgrade telemetry or a model score into ground truth.

## Human Review Methods

The initial reviewer is the builder. Review records should use a fixed decision taxonomy and reason codes. Where feasible, blind the reviewer to experimental condition during rubric scoring. Report this as a single-reviewer case study and do not claim population-level analyst behavior. A second independent reviewer is a future improvement, not a V1 dependency.

Future review evaluation distinguishes Tier A machine-verifiable checks, Tier B guided junior review,
Tier C expert security review, and Tier D insufficient evidence. Until a qualified expert is
available, LLM B is an escalation aid and independent second opinion, not equivalent to Tier C.

## Reproducibility

Each result must identify the code revision, locked environment, dataset manifest/checksums, split version, feature version, model or prompt version, seed where applicable, and command used. Large raw data stays outside Git; manifests and safe small fixtures make the lineage inspectable.

## Change Control

Any material post-results change to labels, splits, metrics, rubrics, features, prompts, or exclusion rules creates a new version and is disclosed. Exploratory changes cannot be relabeled as pre-registered confirmatory results.
