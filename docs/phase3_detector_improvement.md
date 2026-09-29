# Phase 3 Detector-Improvement Diagnostic

**Status:** `VALIDATED` implementation and validation-only experiment; not an operational detection
claim. **Date:** 2026-09-21.

## Scope and sealed-test rule

This investigation deliberately did not load, feature-engineer, tune, or score the held-out
Scenario 7 capture. It used complete capture boundaries only:

| Role | CTU-13 scenario | Accepted rows | Known benign | Known malicious | Unknown |
|---|---|---:|---:|---:|---:|
| Training | Botnet-52 (Scenario 11) | 107,251 | 2,709 | 8,164 | 96,378 |
| Training | Botnet-47 (Scenario 6) | 558,912 | 7,471 | 4,630 | 546,811 |
| Validation | Botnet-46 (Scenario 5) | 129,832 | 4,660 | 901 | 124,271 |
| Validation | Botnet-53 (Scenario 12) | 325,471 | 7,615 | 2,168 | 315,688 |

Scenario 47 had seven rejected records (the quality report preserves the issues); Scenario 53 had
zero rejects. Only authoritative `Normal` and `Botnet` rows entered supervised fitting and metrics.
`Background` and `To-*` remained `unknown` and were retained only as unlabeled behavioral context.
The source manifests record the CC-BY terms, URLs, checksums, and acquisition scope. The complete
run configuration, feature names, checksums, class weights, threshold grid, and per-scenario results
are in the ignored artifact
`data/evaluation/phase3_improvement/diagnostic.json`.

## Why the original detector missed malicious flows

The accepted first baseline used only one-flow-at-a-time values: duration, bytes, packets, ports,
protocol, direction, and state length. It could not represent host recurrence, bursts, destination
fan-out, port scanning-like diversity, or repeated short connections. A malicious flow that looked
ordinary in isolation therefore received no contextual signal. The fixed 0.5 policy also hid useful
ranking information when scores were conservative under scenario shift.

The three existing deterministic rules remain the transparent evidence-traceable baseline; this
investigation did not tune them or treat a rule signal as proof of compromise. Their prior Scenario 5
recall was zero, so adding more rule thresholds without contextual state would not address the main
failure mode identified here.

The historical Scenario 5 validation record illustrates the failure: rules had recall 0.000,
Logistic Regression recall 0.0277, and Random Forest recall 0.0067. These values are the prior
accepted baseline, not new measurements on the sealed test. With the expanded training pool but the
same per-flow family, fixed-threshold recall rose to 0.373 (Logistic Regression) and 0.078 (Random
Forest) on the combined validation pool, showing that more scenario coverage helps but does not
solve the representation gap by itself.

## What changed

`src/aegistrace/features/behavioral.py` adds feature version `1.1.0` to the original 26 values:

- prior source-host connection count in 60 seconds;
- prior unique destinations and destination ports in 300 seconds;
- current-flow source-byte / total-byte asymmetry plus a missing indicator; and
- prior short-connection count in 300 seconds (`Dur <= 1s`).

Each scenario is processed independently. Events are ordered by timestamp, aggregates use prior
flows only, raw addresses are keys rather than numeric features, and no label, filename, scenario
ID, or source label enters the model matrix. `src/aegistrace/evaluation/improvement.py` compares
Logistic Regression and Random Forest with `class_weight=None` and `class_weight="balanced"`, a
fixed threshold of 0.5, and a validation-only threshold grid from 0.05 to 0.95. The selected
threshold maximizes validation F1; it is not a final-test choice.

## Validation results

The most useful comparison is the balanced Random Forest, because it had the strongest selected F1:

| Feature family / policy | Threshold | Precision | Recall | F1 | PR-AUC |
|---|---:|---:|---:|---:|---:|
| Per-flow 1.0.0, fixed | 0.50 | 0.941 | 0.078 | 0.143 | 0.817 |
| Behavioral 1.1.0, fixed | 0.50 | 1.000 | 0.519 | 0.683 | 0.958 |
| Behavioral 1.1.0, validation-selected | 0.15 | 0.956 | 0.845 | 0.897 | 0.958 |

Logistic Regression shows the same direction with a smaller gain: per-flow fixed threshold gives
precision 0.982 / recall 0.373 / F1 0.541, while behavioral balanced features give 0.997 / 0.557 /
0.714 at 0.5 and 0.984 / 0.744 / 0.847 at the selected 0.05 threshold. This is why the report
does not treat one model family as universally superior.

The behavioral features improve ranking and operating-point performance over the same expanded
training pool. Selecting 0.15 sacrifices 4.4 percentage points of precision (1.000 to 0.956) but
adds 32.6 points of recall (0.519 to 0.845), reducing false negatives substantially. The balanced
Random Forest selected threshold generalizes in both validation captures:

The same model's threshold trade-off makes the policy choice explicit:

| Threshold | Precision | Recall | F1 | False-positive rate |
|---:|---:|---:|---:|---:|
| 0.05 | 0.877 | 0.899 | 0.888 | 0.0315 |
| 0.10 | 0.907 | 0.873 | 0.890 | 0.0222 |
| 0.15 (selected) | 0.956 | 0.845 | 0.897 | 0.0098 |
| 0.20 | 0.974 | 0.825 | 0.894 | 0.0055 |
| 0.50 | 1.000 | 0.519 | 0.683 | 0.0000 |

| Validation scenario | Precision | Recall | F1 | PR-AUC |
|---|---:|---:|---:|---:|
| Botnet-46 (Scenario 5) | 0.976 | 0.958 | 0.967 | 0.983 |
| Botnet-53 (Scenario 12) | 0.946 | 0.798 | 0.866 | 0.947 |

The gain is not uniform, so this is encouraging validation evidence rather than a broad claim.
Class weighting is a policy trade-off, not a universal fix: for the Random Forest at its selected
threshold, `balanced` gives precision 0.956 / recall 0.845, while `None` gives precision 0.986 /
recall 0.822. Logistic Regression does not show the same class-weight advantage, which is why both
models and both settings remain in the artifact.

For the selected balanced Random Forest, the combined validation confusion matrix is
`[[12,155, 120], [475, 2,594]]` (true-negative, false-positive / false-negative, true-positive),
with a 0.0098 false-positive rate and a 0.1548 false-negative rate. By scenario, Scenario 5 has
`[[4,639, 21], [38, 863]]` with FPR 0.0045 and FNR 0.0422; Scenario 53 has
`[[7,516, 99], [437, 1,731]]` with FPR 0.0130 and FNR 0.2016. These rates use known labels only.

## False-negative / true-positive diagnosis

At the selected behavioral Random Forest threshold, validation false negatives had lower contextual
activity than true positives (means across the combined validation pool):

| Feature | False negatives | True positives |
|---|---:|---:|
| Prior source connections (60s) | 64.5 | 111.6 |
| Prior unique destinations (300s) | 25.6 | 112.7 |
| Prior unique destination ports (300s) | 4.0 | 62.1 |
| Source-traffic asymmetry | 0.294 | 0.614 |
| Prior repeated short connections (300s) | 37.3 | 74.0 |

This supports the representation diagnosis: the improved detector catches malicious behavior that is
embedded in a host's sequence, while residual false negatives often look like isolated or quieter
flows. It does not prove that the aggregates are causal indicators; they may partly reflect capture
conditions.

## Limitations and next steps

The study remains limited to four training/validation scenarios, source annotations, and known-label
denominators. Unknown traffic is not evidence of benign behavior. Scenario 47 has seven rejected
rows, and the aggregate family can encode scenario-specific timing or host behavior even though it
is label-blind. Threshold selection on validation is optimistic until a frozen test is run.

Before reopening the final held-out test, the next defensible steps are:

1. Freeze the feature, model, class-weight, and threshold policy and add more licensed CTU-13
   scenarios for repeated scenario-held-out validation.
2. Run feature ablations and temporal/rolling-origin validation to test whether each aggregate adds
   transferable signal without future context.
3. Check calibration and alert-volume budgets, then pre-register an operating point that reflects
   the false-positive cost.
4. Investigate the residual low-activity false negatives and parse rejects without using any final
   test labels.
5. Only then reopen Scenario 7 once, report it as a final held-out result, and do not tune afterward.

Detection remains a signal for investigation, not proof of compromise or an incident disposition.
