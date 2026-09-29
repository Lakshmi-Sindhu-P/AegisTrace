# Phase 3 Pre-Final Detector Hardening

**Status:** `VALIDATED` validation hardening and policy freeze. Scenario 7 remains sealed and was not
loaded, inspected, scored, or used for any choice. The hardening run used the existing Scenario 11/47
training artifacts and Scenario 5/53 validation artifacts only.

## Frozen scope and policy

The frozen validation policy is recorded in
[`configs/phase3_frozen_policy.json`](../configs/phase3_frozen_policy.json) and the complete run is
in the ignored artifact
`data/evaluation/phase3_hardening/hardening_summary.json`:

```bash
uv run python scripts/run_phase3_hardening.py \
  --output-dir data/evaluation/phase3_hardening \
  --policy-path configs/phase3_frozen_policy.json \
  --created-at 2026-09-21T16:15:00Z
```

| Field | Frozen value |
|---|---|
| Model | Random Forest |
| Feature version | `1.1.0` behavioral prior-window features |
| Training scenarios | CTU-Malware-Capture-Botnet-52 (11), CTU-Malware-Capture-Botnet-47 (6) |
| Validation scenarios | CTU-Malware-Capture-Botnet-46 (5), CTU-Malware-Capture-Botnet-53 (12) |
| Class weighting | `balanced` |
| Preprocessing | none |
| Hyperparameters | 200 trees, `max_depth=12`, `n_jobs=1`, seed 42 |
| Calibration | none; calibration assessed and deferred |
| Threshold | `0.20` |
| Rules | Existing deterministic rules v1.0.0 retained separately |

Threshold `0.20` was selected after validation-only workload review. Compared with the previous
candidate `0.15`, it gives nearly identical F1 while improving precision and reducing alerts. It is a
validation policy, not an operational probability claim, and must not be changed after reopening the
sealed final scenario.

## Feature ablation

All rows below use the same balanced Random Forest, training pool, validation pool, and frozen
threshold `0.20`. Each group is removed one at a time; PR-AUC is threshold-independent.

| Feature set | Precision | Recall | F1 | PR-AUC |
|---|---:|---:|---:|---:|
| All behavioral features | 0.974 | 0.825 | 0.894 | 0.958 |
| Without connection rate | 0.957 | 0.831 | 0.889 | 0.947 |
| Without destination diversity | 0.985 | 0.750 | 0.852 | 0.920 |
| Without destination-port diversity | 0.988 | 0.644 | 0.779 | 0.952 |
| Without repeated short connections | 0.987 | 0.756 | 0.856 | 0.906 |
| Without traffic asymmetry | 0.915 | 0.836 | 0.874 | 0.961 |

Destination-port diversity is the largest single recall contributor (recall falls 18.2 points when
removed). Destination diversity and repeated-short-connection features also contribute materially.
Connection rate is complementary but modest at this operating point. Traffic asymmetry mainly
supports precision: removing it slightly raises recall but sacrifices 5.9 points of precision. No
single group is an obvious label proxy; the gains are distributed across defensible behavioral
signals, although capture-specific behavior remains a validity risk.

## Temporal-leakage audit

The builder sorts by `observed_at`, computes the current vector before inserting the current flow into
state, and prunes histories by fixed prior windows. The executable audit appends a deterministic future
flow one second after the latest fixture event (inside the 300-second window) and compares every
earlier vector. The audit passed:

```text
temporal_audit.passed = true
fixture = data/fixtures/ctu13/scenario_11.binetflow
```

Unit coverage also checks that prior-window values remain unchanged when a future event is appended.
Same-timestamp flows use a deterministic event-ID tie-breaker; a future temporal split should still
use complete time boundaries where possible.

## Calibration

Calibration was measured on known validation labels only. The sigmoid wrapper was fit with three-fold
cross-validation inside the training pool, not on validation labels.

| Scores | Brier score | Expected calibration error |
|---|---:|---:|
| Raw Random Forest | 0.0710 | 0.1012 |
| Training-only sigmoid calibration | 0.0799 | 0.0988 |

Sigmoid calibration slightly reduces ECE but worsens Brier score and changes score semantics without
improving the research objective. Calibration is therefore deferred; the frozen policy uses raw model
scores only for ranking and thresholding. A score of `0.80` must not be described as an 80% real-world
probability.

## Alert-volume trade-off

The validation denominator contains 15,344 known labeled flows and 455,303 total flows. Counts in the
`all validation alerts` column include unknown-label rows, so they measure potential reviewer workload
but cannot be converted into false-positive counts.

| Threshold | Precision | Recall | F1 | FP | FN | Known alerts | Alerts / 1,000 labeled | All validation alerts |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.05 | 0.877 | 0.899 | 0.888 | 387 | 310 | 3,146 | 205.0 | 350,901 |
| 0.10 | 0.907 | 0.873 | 0.890 | 273 | 391 | 2,951 | 192.3 | 246,979 |
| 0.15 | 0.956 | 0.845 | 0.897 | 120 | 475 | 2,714 | 176.9 | 213,380 |
| **0.20 frozen** | **0.974** | **0.825** | **0.894** | **67** | **536** | **2,600** | **169.4** | **186,269** |
| 0.30 | 0.996 | 0.717 | 0.834 | 9 | 867 | 2,211 | 144.1 | 157,653 |
| 0.50 | 1.000 | 0.519 | 0.683 | 0 | 1,476 | 1,593 | 103.8 | 116,679 |

At the frozen threshold the combined confusion matrix is `[[12,208, 67], [536, 2,533]]`, with FPR
0.0055 and FNR 0.1746. Scenario 5 validation is precision 0.983 / recall 0.958 / F1 0.970; Scenario
53 is precision 0.970 / recall 0.770 / F1 0.859. The workload remains high on raw validation rows,
which is why this is a research policy freeze rather than an operational alerting claim.

## Release-gate decision

The hardening gate passes for a controlled, one-time reopening of Scenario 7: temporal causality
passed, ablation found no obvious invalid proxy, the threshold trade-off is explicit, and the run is
reproducible from versioned checksums and a frozen policy. Scenario 7 was not reopened in this pass.

Before any final-test run, the next action must be a separate, explicitly authorized execution of the
frozen policy exactly once. No threshold, feature, calibration, or hyperparameter changes may be made
after seeing that result. The high unknown-row alert volume, limited scenario count, seven rejected
Scenario 47 rows, and source-label uncertainty remain limitations. Detection remains an investigation
signal, not proof of compromise or an incident disposition.
