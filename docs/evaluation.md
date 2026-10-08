# Evaluation Protocol

**Status:** Phase 3 rules, baseline, validation-only improvement, pre-final hardening, model-family
benchmark, and cross-scenario operating-point validation are implemented. Findings, verification,
dual-LLM comparison, and recommendation evaluations remain approved future work. The historical
results below are reproducible exploratory CTU-13 evidence, not a broad generalization claim.

This document defines what will be measured before models or LLM outputs are available. Metric definitions, corpus sizes, and thresholds will be versioned before the corresponding experiment begins.

## Evaluation Units

- **Event:** one canonical observation.
- **Detection:** one detector's result over one or more events.
- **Finding:** correlated detections and events presented for triage.
- **Triage case:** one immutable evidence bundle plus expected adjudication rubric.
- **Review:** one human decision linked to one triage assessment.

## Detector Experiments

Compare:

1. transparent rules only;
2. statistical baseline only;
3. interpretable ML baseline only;
4. rules plus ML under a deterministic aggregation policy;
5. the smallest justified specialist shortlist (shallow Decision Tree and optionally Extra Trees);
6. an explicitly scoped anomaly-ranking specialist, if its contamination assumptions are defensible;
7. an interpretable fusion model only if disagreement analysis demonstrates complementary errors.

Do not select a final detector solely by F1. Retain the simplest model that meets the research
question's evidence and workload needs. Compare complementary error patterns, scenario stability,
confidence intervals, alert volume, runtime/resource cost, and interpretability. XGBoost,
LightGBM, CatBoost, SVM, KNN, MLPs, autoencoders, clustering, semi-supervised methods, and
temporal neural models are deferred until a smaller controlled benchmark demonstrates a concrete
need.

For labeled data, record per class and macro/weighted where appropriate:

- precision, recall, and F1;
- confusion matrix;
- false-positive and false-negative rates;
- PR-AUC for imbalanced binary ranking;
- ROC-AUC only with an explanation of its limitations;
- score/calibration plots when scores have probabilistic meaning;
- per-scenario and time-slice results.
- model-family stability across repeated seeds or bootstrap resamples;
- alert volume on known and unknown rows, clearly separated from false-positive rates;
- computational cost and memory footprint;
- error overlap, unique detections, and disagreement categories between specialists.

Accuracy may be reported but cannot be the headline metric.

### Split policy

- Define the split before fitting preprocessing or thresholds.
- Deduplicate first.
- Prefer scenario-group holdout for generalization claims.
- Use temporal splits for within-scenario experiments where timestamps support them.
- CTU-13 Phase 3 historical three-scenario baseline (accepted baseline record): Scenario 11 for
  training, Scenario 5 for validation, and Scenario 7 as the untouched test scenario. Each split is a
  complete capture boundary.
- Current validation-only pool used by the improvement, hardening, model-family, stability, and
  causal passes: training captures CTU-Malware-Capture-Botnet-52 and -47; validation captures -46,
  -53, -45, and -51; sealed capture -48 / Scenario 7 remains the untouched final test.
- Fit all preprocessing on the training partition only.
- Keep one untouched final test partition after model selection begins.
- Exclude `unknown` labels from supervised fitting and metrics. Do not convert `Background` or
  `To-*` labels to benign.
- Do not include labels, filenames, scenario IDs, source addresses, or label-derived fields in the
  feature matrix.
- Do not use labels to group findings or prioritize a review queue. Labels may be used only in
  evaluation denominators and error analysis.

### Model-family and disagreement protocol

All model-family, feature, threshold, anomaly-contamination, fusion, and aggregation decisions are
made with training/validation data only. Each specialist emits a separately versioned score and
event-linked evidence. Before any ensemble is considered, calculate pairwise overlap and residual
errors for rules, Logistic Regression, Random Forest, any added tree model, and any anomaly score.
Report unique known malicious detections, unique false positives, scenario-specific changes, and
whether an apparent gain comes from a workload increase.

If complementary errors justify fusion, use an interpretable Logistic Regression meta-model over
out-of-fold detector outputs. Preserve all component outputs, fit the meta-model without leaking
validation labels, select thresholds on validation only, and compare against the strongest single
specialist. A fused score is an investigation-priority recommendation, not a maliciousness fact.

### Findings and verification evaluation

The planned aggregation study measures duplicate alert reduction, grouping precision against
research labels only as an analysis aid, event/detection/evidence preservation, group stability
under small time-window changes, and reviewer workload proxies. It must never use research labels to
form groups or prioritize alerts.

The verification layer is evaluated mechanically for identifier existence, count/timestamp
consistency, provenance links, claim-type labels, and unsupported deterministic derivations. It is
not reported as proof of semantic correctness.

### Scenario 7 gate

Scenario 7 is the final held-out capture. It is excluded from feature selection, model-family
comparison, threshold tuning, hyperparameter tuning, anomaly selection, temporal-model selection,
fusion/stacking design, aggregation design, and architecture selection. After the detector or
fusion policy, feature version, rules, threshold, class weighting, and checksums are frozen, Scenario
7 may be opened exactly once for a final measurement. The result must be accepted whether favorable
or unfavorable, and no post-test tuning is permitted.

## LLM Triage Corpus

The versioned curated set should include:

- clearly benign evidence;
- clearly malicious evidence supported by labels/detectors;
- ambiguous behavior;
- incomplete evidence;
- conflicting rules and ML outputs;
- tempting but unsupported malware/CVE/intent claims;
- invalid or missing evidence references;
- prompt-injection-like strings inside telemetry;
- edge cases with null or source-specific fields.

Each case needs evidence IDs, a reviewer-authored expected claim boundary, acceptable categories/severities, required uncertainties, prohibited claims, and rationale. The rubric is frozen before evaluating candidate prompts/models.

## LLM Metrics

| Metric | Planned definition |
|---|---|
| Evidence-reference validity | Fraction of cited IDs present in the supplied bundle |
| Evidence-grounding rate | Fraction of material claims supported by cited supplied evidence under human rubric |
| Unsupported-claim rate | Unsupported material claims divided by material claims |
| Required-uncertainty recall | Required uncertainties mentioned divided by those in the case rubric |
| Category/severity agreement | Agreement with allowed adjudicated labels; report confusion, not only a scalar |
| Insufficient-evidence behavior | Appropriate abstentions and inappropriate abstentions reported separately |
| Explanation completeness | Rubric items covered without adding unsupported claims |
| Human override rate | Fraction of proposals changed, with reason taxonomy; case-study only for one reviewer |
| Latency and cost | Measured per case if a paid/remote provider is used |

LLM self-reported confidence is not treated as a calibrated probability unless empirical calibration supports that interpretation.

## Comparative Conditions

Evaluate the same frozen cases under:

```text
rules only
ML only
rules + ML
rules + ML + LLM
rules + ML + LLM + human review
```

The comparison must not imply that prose output improves detection metrics. LLM contribution is assessed on triage classification, evidence use, uncertainty, completeness, and review outcomes.

The amended AI evaluation adds two independently frozen roles:

- **LLM A — triage analyst:** summarizes the bounded evidence, states uncertainty, and recommends a
  next investigative step.
- **LLM B — expert adjudicator:** receives the same underlying evidence without LLM A's conclusion,
  challenges unsupported claims and severity, identifies plausible benign explanations, and decides
  whether escalation is warranted.

Compare the two outputs deterministically after both are frozen. Use the states `CORROBORATED`,
`PARTIALLY_CORROBORATED`, `CONTRADICTED`, `INSUFFICIENT_EVIDENCE`, `MODEL_DISAGREEMENT`, and
`EXPERT_REVIEW_REQUIRED`. Agreement is not ground truth. LLM B is an independent review aid and
cannot substitute for a qualified expert.

## Reproducibility Record

Every run records code revision, dataset manifest, split artifact, feature version, detector/model version, hyperparameters, random seeds, prompt version, model/provider identifier, raw structured outputs, validator version, metric code version, and environment lockfile.

The Phase 3 command is:

```bash
uv run python scripts/run_phase3_baselines.py \
  --train data/raw/ctu13/CTU-Malware-Capture-Botnet-52/capture20110818-2.binetflow \
  --validation data/raw/ctu13/CTU-Malware-Capture-Botnet-46/capture20110815-2.binetflow \
  --test data/raw/ctu13/CTU-Malware-Capture-Botnet-48/capture20110816-2.binetflow \
  --train-scenario CTU-Malware-Capture-Botnet-52 \
  --validation-scenario CTU-Malware-Capture-Botnet-46 \
  --test-scenario CTU-Malware-Capture-Botnet-48 \
  --output-dir data/evaluation/phase3_baselines \
  --ingested-at 2026-09-21T02:00:00Z \
  --created-at 2026-09-21T02:00:00Z \
  --seed 42
```

## Reporting Rules

- Include class counts and uncertainty intervals where sample size permits.
- Publish failure examples and disagreement categories, not only aggregate metrics.
- Separate validation/tuning results from untouched test results.
- Label exploratory analyses as exploratory.
- Do not compare runs whose corpus or rubric changed without explaining the version change.
- Report missing/failed LLM responses in the denominator rather than silently dropping them.
- Never fabricate results or include placeholder numbers that could be mistaken for measurements.

## Phase 3 exploratory results

The table below is the previously accepted baseline record. It is retained as historical evidence;
the held-out Scenario 7 capture is sealed for the detector-improvement investigation. No new Scenario
7 feature, threshold, hyperparameter, or metric is produced by that investigation.

The ignored local artifact `data/evaluation/phase3_baselines/experiment_summary.json` records the
full run, feature version, checksums, parameters, predictions, and metrics. All values below are
from known labels only; unknown rows remain in the source artifacts but are excluded from these
denominators.

| Model | Split | Support | Precision | Recall | F1 | False-positive rate | False-negative rate | PR-AUC |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Rules | Scenario 5 validation | 5,561 | 0.000 | 0.000 | — | 0.0013 | 1.0000 | 0.1620 |
| Rules | Scenario 7 test | 1,732 | 1.000 | 0.0159 | 0.0313 | 0.0000 | 0.9841 | 0.0517 |
| Logistic Regression | Scenario 5 validation | 5,561 | 0.694 | 0.0277 | 0.0534 | 0.0024 | 0.9723 | 0.3377 |
| Logistic Regression | Scenario 7 test | 1,732 | 1.000 | 0.0159 | 0.0313 | 0.0000 | 0.9841 | 0.0633 |
| Random Forest | Scenario 5 validation | 5,561 | 0.188 | 0.0067 | 0.0129 | 0.0056 | 0.9933 | 0.5608 |
| Random Forest | Scenario 7 test | 1,732 | 0.333 | 0.0794 | 0.1282 | 0.0060 | 0.9206 | 0.2071 |

Confusion-matrix counts, seed, parameters, and train-scenario metrics are in the JSON artifact.
These results show that the first small feature set and fixed rules have very low recall on the
held-out scenario. They are implementation evidence and a useful negative result, not evidence of
effective detection or compromise classification.

## Phase 3 validation-only detector improvement

The improvement command is intentionally test-free:

```bash
uv run python scripts/run_phase3_improvement.py \
  --train data/raw/ctu13/CTU-Malware-Capture-Botnet-52/capture20110818-2.binetflow CTU-Malware-Capture-Botnet-52 \
  --train data/raw/ctu13/CTU-Malware-Capture-Botnet-47/capture20110816.binetflow CTU-Malware-Capture-Botnet-47 \
  --validation data/raw/ctu13/CTU-Malware-Capture-Botnet-46/capture20110815-2.binetflow CTU-Malware-Capture-Botnet-46 \
  --validation data/raw/ctu13/CTU-Malware-Capture-Botnet-53/capture20110819.binetflow CTU-Malware-Capture-Botnet-53 \
  --output-dir data/evaluation/phase3_improvement \
  --ingested-at 2026-09-21T15:00:00Z --created-at 2026-09-21T15:00:00Z --seed 42
```

Scenario 47 is added to training and Scenario 53 to validation; Scenario 11 and Scenario 5 retain
their earlier roles. The run compares the original per-flow `1.0.0` family with the scenario-local
behavioral `1.1.0` family, both class-weight choices, fixed threshold 0.5, and validation-selected
thresholds. Metrics are calculated only on known labels. Per-scenario metrics and every threshold
trade-off are stored in the ignored JSON artifact; see [phase3_detector_improvement.md](phase3_detector_improvement.md)
for the short interpretation.

The pre-final hardening report is [phase3_detector_hardening.md](phase3_detector_hardening.md). It
records feature ablations, the temporal-causality audit, calibration decision, alert-volume table,
and the frozen validation policy in `configs/phase3_frozen_policy.json`. Scenario 7 remains sealed.

## Post-amendment model-family benchmark

The validation-only benchmark is documented in
[phase3_model_family_benchmark.md](phase3_model_family_benchmark.md). Its ignored artifact is
`data/evaluation/phase3_model_family/benchmark_summary.json` and its runner has training/validation
arguments only; Scenario 7 is explicitly rejected.

The benchmark compares the retained rules, Logistic Regression, shallow Decision Tree, Random
Forest, Extra Trees, HistGradientBoosting, and a practical linear SVM. Isolation Forest is reported
separately as an anomaly-prioritization experiment. All supervised metrics use authoritative known
labels only. Unknown rows remain unknown and contribute only to separate workload counts.

Results are reported at the frozen classifier threshold `0.20` plus validation-selected threshold
trade-offs. They include precision, recall, F1, PR-AUC, FPR/FNR, confusion counts, per-scenario
stability, fit runtime, interpretability notes, alert volume, and per-malicious-case disagreement.
The disagreement result does not justify fusion yet: SVM contributes 30 unique malicious cases at a
very high false-positive cost, while other learned families have no unique catches at the shared
operating point. Isolation Forest has no unique malicious coverage at that point and a large alert
workload. The completed follow-up stability pass is documented below; it supersedes the recommendation
for another model-family comparison without opening Scenario 7.

## Cross-scenario operating-point validation

The stability artifact is `data/evaluation/phase3_model_stability/stability_summary.json`, generated
by `scripts/run_phase3_model_stability_cached.py`; the report is
[phase3_model_stability.md](phase3_model_stability.md). It adds licensed Scenarios 4 and 10 to the
validation pool while retaining Scenarios 5 and 12, with Scenarios 11 and 47 as training data.
Scenario 7 remains sealed. The pass reports threshold-independent PR-AUC and per-scenario
precision, recall, F1, FPR/FNR, and labeled alert volume.

The operating policy is identical for RF, HGB, and SVM: maximize validation recall subject to
precision >= 0.95 and <= 200 alerts per 1,000 labeled flows. Each threshold is searched on its own
score scale; unknown rows are not supervised labels or policy denominators. RF selected `0.73` and
was the strongest compliant standalone detector (pooled PR-AUC `0.999589`, recall `0.2685`). HGB
had higher PR-AUC (`0.999738`) but no feasible threshold under both constraints; its explicit
zero-alert fallback is not an operational success. SVM selected `0.58`, but its unique malicious
coverage was 13,576 cases in only two of four scenarios.

After correcting the HGB-derived disagreement sections, residual analysis found 68,353 malicious
cases missed by all three models, concentrated in Scenario 10/51 and enriched for short,
low-destination/port-diversity mixed-protocol flows. This supports a representation study with
richer temporal/host context before any fusion; no fusion or new model family was added.

### Corrected interpretation of the operating-point recall (2026-10-08)

The `0.2685` operating-point recall above must be read together with the population and policy that
produced it. See [phase3_evaluation_diagnosis.md](phase3_evaluation_diagnosis.md) and Issue #8.

- The pooled labeled validation subset is 67.8% malicious (112,001 of 165,276) because unknown rows
  are excluded and capture 51 alone contributes 106,352 malicious labels. Only 5.7% of the 2,886,156
  validation rows carry an authoritative label.
- At the frozen threshold `0.20`, the balanced Random Forest records precision `0.9903` and recall
  `0.9949` (TP 111,426, FP 1,092, FN 575); HistGradientBoosting records precision `0.9954` and recall
  `0.9931`. These settings are excluded only because they exceed the workload cap.
- Because the labeled population is 67.8% positive, the `<= 200` alerts-per-1,000-labeled-flows cap
  permits flagging at most 20% of labeled rows and therefore caps recall at `20 / 67.8 = 29.5%` even
  for a perfect ranker. The recorded `0.2685` is about 91% of that ceiling.
- `alerts_per_1000_labeled_flows` is population-dependent and behaves as a recall ceiling when the
  labeled set is mostly positive. Future operating-point reports must state the labeled prevalence and
  the absolute alert volume alongside the ratio.
- The genuine unresolved uncertainty is the unlabeled majority: 186,269 alerts at the frozen
  threshold across a 455,303-row pool have no authoritative class and must not be reported as false
  positives.

This interpretation does not change the recorded thresholds, metrics, or artifacts. It changes what
the recall figure may be claimed to mean. The frozen policy remains in place; a capture-grouped
held-out measurement at the frozen threshold, reporting unknown-label workload separately, is the
recommended next step and is not yet run.

## Causal host/time representation study

Issue #2 evaluates feature version `1.2.0` with the same RF/HGB/SVM families and operating policy.
The artifact is `data/evaluation/phase3_causal_representation/causal_summary.json`, generated by
`scripts/run_phase3_causal_representation.py`; the interpretation is in
[phase3_causal_representation.md](phase3_causal_representation.md). The extension adds prior-only
60/300-second host activity, diversity, reuse, protocol, prior-volume, and recency values. It does
not use Scenario 7.

Compared with the corrected `1.1.0` reference, pooled causal PR-AUC was RF `0.999563`, HGB
`0.999695`, and SVM `0.998941`. At validation-derived precision/workload operating points, RF
recall was `0.2607`, HGB remained a zero-alert fallback with recall `0.0000`, and SVM recall was
`0.2548`. The causal family reduced all-three residual malicious cases from `68,353` to `64,986`
(4.9%) through lower model overlap, but no individual model improved its constrained recall. The
gain is dominated by Scenario 10/51 and is not sufficient evidence for fusion or a new model
family. The next experiment should audit that residual subgroup with another scenario-held-out
representation hypothesis.

During this pass, a stale-reference defect was corrected: the earlier HGB zero-alert correction
had not propagated to disagreement/residual sections. The repaired artifact records the provenance
of this correction; the quantile helper now avoids repeated O(n) sorting inside residual-row loops.

## Causal-overlap subgroup diagnosis

Issue #3 follows the representation result without refitting or opening Scenario 7. The read-only
`scripts/analyze_phase3_causal_overlap.py` audit compares the corrected `1.1.0` stability case
records with `1.2.0` causal case records and verifies that all common feature values are unchanged.
It classifies 112,001 authoritative malicious validation cases by the RF/SVM union at each frozen
operating point, then summarizes prior-only causal features by category and validation capture.

The categories are `causal_only` (10,564), `reference_only` (7,197), `both_residual` (57,789),
and `both_union` (36,451). The net gain of 3,367 union-covered cases is concentrated in capture 51
(Scenario 10), where candidate-only cases have median 60-second source and repeated-short counts
of 6,106 versus 2,777 in the unchanged residual group, while both groups have median one unique
destination and one protocol. The bounded interpretation is a localized burst-density hypothesis,
not a causal proof: large high-rate residuals remain, and capture 53 has a different diversity
profile. The result does not promote `1.2.0`, justify fusion, or justify a new model family.

The full category counts, transition matrix, feature summaries, input checksums, and sealed-scenario
guard are in `data/evaluation/phase3_causal_overlap/overlap_summary.json`; the diagnostic report is
[phase3_causal_overlap.md](phase3_causal_overlap.md). Any follow-up must test this narrower
hypothesis with a scenario-held-out non-sealed capture or move to deterministic finding aggregation;
Scenario 7 remains sealed.

## Reproducibility and uncertainty artifacts

The tracked [experiment registry](experiment_registry.json) is the canonical index for the current
Phase 3 runs. It links each run to its code revision, scenario split, feature versions, command,
machine-readable artifact digest, documentation, and claim boundary. Run
`uv run python scripts/validate_experiment_registry.py docs/experiment_registry.json --require-artifacts`
when the ignored evaluation artifacts are available locally. Run
`uv run python scripts/validate_phase3_evidence.py` for the additional sealed-scenario and known-
artifact consistency checks.

`data/evaluation/phase3_uncertainty/uncertainty_summary.json` contains 95% Wilson score intervals
for proportions recoverable from the recorded confusion counts. These intervals are useful for
communicating uncertainty around the validation operating points, but they are not bootstrap
confidence intervals over independent events and do not estimate PR-AUC uncertainty. No threshold,
model, or policy decision was changed by this artifact.
