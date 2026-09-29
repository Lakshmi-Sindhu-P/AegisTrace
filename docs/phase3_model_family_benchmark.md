# Phase 3 Post-Amendment Model-Family Benchmark

**Status:** `VALIDATED` validation-only experiment implementation and exploratory result. Scenario 7
remains sealed. This benchmark does not select a final detector, implement fusion, or establish an
operational detection claim.

## Scope and controls

The run used the existing behavioral feature family `1.1.0`, scenario-local prior-flow aggregates,
the same leakage controls, and complete scenario boundaries as the accepted improvement study:

| Split | Scenarios | Known rows | Total rows |
|---|---|---:|---:|
| Training | CTU-Malware-Capture-Botnet-52 (11), CTU-Malware-Capture-Botnet-47 (6) | 22,974 | 666,163 |
| Validation | CTU-Malware-Capture-Botnet-46 (5), CTU-Malware-Capture-Botnet-53 (12) | 15,344 | 455,303 |

`Background` and `To-*` rows remain `unknown`. They are excluded from supervised fitting and labeled
metrics, but remain in the validation pool for separate workload analysis. No labels, filenames,
scenario IDs, source labels, or raw addresses enter model matrices. Scenario 7 was not loaded,
inspected, scored, or used for any decision.

Reproducible artifact and command:

```bash
uv run python scripts/run_phase3_model_family_benchmark.py \
  --train data/raw/ctu13/CTU-Malware-Capture-Botnet-52/capture20110818-2.binetflow CTU-Malware-Capture-Botnet-52 \
  --train data/raw/ctu13/CTU-Malware-Capture-Botnet-47/capture20110816.binetflow CTU-Malware-Capture-Botnet-47 \
  --validation data/raw/ctu13/CTU-Malware-Capture-Botnet-46/capture20110815-2.binetflow CTU-Malware-Capture-Botnet-46 \
  --validation data/raw/ctu13/CTU-Malware-Capture-Botnet-53/capture20110819.binetflow CTU-Malware-Capture-Botnet-53 \
  --output-dir data/evaluation/phase3_model_family \
  --ingested-at 2026-09-22T12:00:00Z \
  --created-at 2026-09-22T12:00:00Z \
  --seed 42
```

The full JSON artifact is the ignored local file
`data/evaluation/phase3_model_family/benchmark_summary.json`. It records checksums, feature names,
parameters, thresholds, scenario metrics, runtime, alert volume, and per-case disagreement.

## Candidates

- Existing deterministic rules v1.0.0, retained unchanged.
- Logistic Regression with the existing balanced, standardized baseline configuration.
- Shallow Decision Tree (`max_depth=6`, `min_samples_leaf=20`).
- Existing balanced Random Forest (`200` trees, `max_depth=12`, seed 42).
- Balanced Extra Trees (`200` trees, `max_depth=12`, seed 42).
- HistGradientBoosting with balanced training sample weights.
- A practical linear SVM (`LinearSVC`, balanced class weights). A probability-enabled kernel SVC was
  not practical for this pool; the final SVM uses a training-range-normalized margin and is not a
  calibrated probability.
- Isolation Forest is reported separately. It is fit without labels on known feature rows only and
  scores all validation rows as an anomaly-prioritization signal. It does not create labels.

The frozen validation policy threshold `0.20` is used for comparable classifier workload/error
reporting. Rules retain their native binary threshold. Validation-selected thresholds are reported
as a secondary precision/recall trade-off, not as a post-test choice.

## Fixed validation-policy results

Known-label support is 15,344 flows. Alert counts include unknown rows and therefore are workload
signals, not false-positive counts.

| Detector | Precision | Recall | F1 | PR-AUC | FPR | FNR | FP | FN | Known alerts | All alerts |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Rules (native threshold) | 0.000 | 0.000 | — | 0.200 | 0.001 | 1.000 | 9 | 3,069 | 9 | 221 |
| Logistic Regression | 0.995 | 0.608 | 0.755 | 0.916 | 0.001 | 0.392 | 10 | 1,202 | 1,877 | 132,513 |
| Decision Tree | 0.967 | 0.514 | 0.671 | 0.642 | 0.004 | 0.486 | 54 | 1,491 | 1,632 | 148,626 |
| Random Forest | **0.974** | **0.825** | **0.894** | 0.958 | 0.005 | 0.175 | 67 | 536 | 2,600 | 186,269 |
| Extra Trees | 0.992 | 0.583 | 0.735 | 0.903 | 0.001 | 0.417 | 15 | 1,279 | 1,805 | 161,935 |
| HistGradientBoosting | 0.996 | 0.787 | 0.879 | **0.979** | 0.001 | 0.213 | 9 | 655 | 2,423 | 173,496 |
| Linear SVM margin | 0.201 | 1.000 | 0.334 | 0.951 | 0.995 | 0.000 | 12,219 | 0 | 15,288 | 368,393 |
| Isolation Forest | 0.250 | 0.990 | 0.399 | 0.599 | 0.745 | 0.010 | 9,139 | 30 | 12,178 | 444,160 |

The fixed threshold is not equally meaningful for the normalized SVM margin or anomaly score. Their
validation-selected operating points are therefore also retained in the artifact: SVM threshold
`0.35` gives precision `0.992`, recall `0.785`, F1 `0.876`; Isolation Forest threshold `0.45` gives
precision `0.497`, recall `0.730`, F1 `0.592`. These are validation trade-offs, not calibrated
probabilities or final-test choices.

## Cross-scenario stability

The same fixed threshold was applied separately to both validation scenarios:

| Detector | Scenario 5 recall / F1 | Scenario 53 recall / F1 |
|---|---:|---:|
| Logistic Regression | 0.475 / 0.643 | 0.664 / 0.796 |
| Decision Tree | 0.307 / 0.460 | 0.600 / 0.744 |
| Random Forest | **0.958 / 0.970** | **0.770 / 0.859** |
| Extra Trees | 0.422 / 0.589 | 0.650 / 0.787 |
| HistGradientBoosting | 0.958 / 0.976 | 0.715 / 0.833 |
| Linear SVM margin | 1.000 / 0.280 | 1.000 / 0.364 |
| Isolation Forest | 0.999 / 0.328 | 0.987 / 0.439 |

Every learned family changes materially between the two captures. The consistent Scenario 53 drop
is evidence of capture-specific behavior or representation limits, not justification by itself for a
temporal neural model.

Fit runtimes were recorded in the artifact (parsing and full validation scoring are not included):
Logistic Regression 1.42 s, Decision Tree 0.05 s, Random Forest 1.24 s, Extra Trees 0.64 s,
HistGradientBoosting 2.15 s, Linear SVM 0.08 s, and Isolation Forest 0.15 s on this environment.

## Per-case disagreement

The analysis covers all 3,069 known malicious validation cases at the fixed operating points. The
number of detectors catching each case was:

| Detectors catching a malicious case | Cases |
|---:|---:|
| 1 | 30 |
| 2 | 458 |
| 3 | 184 |
| 4 | 463 |
| 5 | 153 |
| 6 | 292 |
| 7 | 1,489 |

There were no malicious cases missed by every detector. Unique coverage was narrow:

- Linear SVM uniquely caught 30 cases at the fixed `0.20` margin threshold.
- No other model family uniquely caught a malicious case.
- The deterministic rules were the only detector to miss 1,489 cases that every learned/anomaly
  family caught.
- No learned family had a unique-miss set under this operating-point comparison.

The SVM's 30 unique cases came with 12,219 known false positives at the same threshold, so they do
not justify adding it to a fusion policy yet. Isolation Forest also provided no unique malicious
coverage at this operating point while producing 9,139 known false positives and 431,982 unknown-row
alerts.

## Recommendation

**Recommendation: no fusion or additional model-family complexity yet.** The benchmark does not show
enough useful complementary coverage to justify a fusion layer: Random Forest and
HistGradientBoosting overlap heavily, SVM's unique cases are too costly at the shared operating
point, and Isolation Forest is an anomaly/workload signal rather than a practical maliciousness
specialist here. Semi-supervised learning has not demonstrated value because unknown rows were used
only for workload accounting. Temporal models are not justified yet; the Scenario 53 degradation
should first be investigated with more licensed scenarios, repeated scenario/temporal validation,
and residual error analysis.

The next experiment should therefore be a data/split stability study—not an architecture expansion:
add appropriately licensed scenarios, repeat scenario-held-out evaluation, and examine whether the
same malicious behavior remains low-activity or capture-specific. Revisit fusion or temporal models
only if that study demonstrates a concrete, reproducible gap.

Detection remains an investigation signal, not proof of compromise or an incident disposition.
