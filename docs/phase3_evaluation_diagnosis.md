# Phase 3 Evaluation Diagnosis: Cap-Bound Recall and Label Scarcity

**Status:** VALIDATING — read-only diagnostic recorded 2026-10-08. No model, feature, threshold,
frozen policy, or evaluation artifact was changed. This document interprets existing recorded
artifacts; it does not produce a new detector result or a generalization claim.

**Issue:** [Lakshmi-Sindhu-P/AegisTrace#8](https://github.com/Lakshmi-Sindhu-P/AegisTrace/issues/8)

## Summary

The cross-scenario stability pass reported an operating-point recall of roughly 27% and a
68,353-case all-model residual. That result has been read as evidence that the supervised detector is
weak. The recorded artifacts show the binding constraint is the **evaluation policy applied to a
malicious-heavy labeled population**, not model discrimination.

At the frozen policy threshold `0.20`, the balanced Random Forest already achieves 99.5% recall at
99.0% precision on the labeled validation pool. The same model at the stability-selected operating
threshold `0.73` achieves 26.9% recall. The difference is caused by the policy constraint, not by a
change in the model.

## Evidence 1 — The labeled population is malicious-heavy and small

Source: `data/evaluation/phase3_model_stability/stability_summary.json`, `scenario_metadata.validation`.

| Validation capture | Total rows | Labeled | Malicious | Benign | Unknown | Unknown share |
|---|---:|---:|---:|---:|---:|---:|
| CTU-Malware-Capture-Botnet-45 | 1,121,072 | 27,775 | 2,580 | 25,195 | 1,093,297 | 97.5% |
| CTU-Malware-Capture-Botnet-46 | 129,832 | 5,561 | 901 | 4,660 | 124,271 | 95.7% |
| CTU-Malware-Capture-Botnet-51 | 1,309,781 | 122,157 | 106,352 | 15,805 | 1,187,624 | 90.7% |
| CTU-Malware-Capture-Botnet-53 | 325,471 | 9,783 | 2,168 | 7,615 | 315,688 | 97.0% |
| **Total** | **2,886,156** | **165,276** | **112,001** | **53,275** | **2,720,880** | **94.3%** |

Two facts follow. First, the labeled validation subset is 67.8% malicious (`112,001 / 165,276`)
because unknown rows are excluded from supervised metrics and one large capture (51) contributes
106,352 of the 112,001 malicious labels. Real-world traffic has the opposite prevalence. Second,
**94.3% of validation rows have no authoritative label at all**, so even the labeled metrics describe
a small minority of observed flows.

## Evidence 2 — At the frozen threshold the supervised models are strong

Source: `data/evaluation/phase3_model_stability/stability_summary.json`, `model_results.*.fixed_policy_metrics`.

| Model | Threshold | Precision | Recall | TP | FP | FN |
|---|---:|---:|---:|---:|---:|---:|
| Random Forest | 0.20 | 0.9903 | 0.9949 | 111,426 | 1,092 | 575 |
| HistGradientBoosting | 0.20 | 0.9954 | 0.9931 | 111,229 | 511 | 772 |

At the stability-selected operating threshold, the same Random Forest records precision `0.99987` and
recall `0.2685` (TP 30,072, FP 4, FN 81,929).

## Evidence 3 — The workload cap is mathematically a recall ceiling

The recorded operating policy maximizes pooled validation recall subject to
`precision >= 0.95` **and** `alerts_per_1000_labeled_flows <= 200`.

Because the labeled population is 67.8% positive, a cap of 200 alerts per 1,000 labeled flows permits
flagging at most 20% of labeled rows. Even a perfect ranker can therefore capture at most
`20 / 67.8 = 29.5%` of positives. The observed 26.9% is about 91% of that hard ceiling: the model is
near-optimal *given the constraint it was handed*.

At threshold `0.20`, the Random Forest raises 680.8 known alerts per 1,000 labeled flows and is
therefore marked ineligible. The constraint, not the model, forces the threshold upward.

The residual is concentrated accordingly: `residual_error_analysis.by_scenario` records 614 cases in
capture 45, 744 in capture 46, **65,619 in capture 51**, and 1,376 in capture 53. The recorded
disagreement histogram over the 112,001 malicious validation cases shows 68,312 caught by zero
detectors, 24,808 by one, 18,776 by two, and 105 by three at their operating thresholds.

## Evidence 4 — The genuine open uncertainty is unlabeled

The hardening artifact `data/evaluation/phase3_hardening/hardening_summary.json` records 186,269
alerts at the frozen threshold `0.20` across a 455,303-row validation pool. Those rows have no
authoritative class. They are a workload signal, not a false-positive rate, and they are the actual
unresolved question: on the 94.3% of traffic that is unlabeled, the project cannot currently say
whether an alert is a detection or a false alarm.

## Evidence 5 — Measured unknown-label workload at the frozen threshold (2026-10-08)

`scripts/report_phase3_unknown_workload.py` refits the frozen policy on the frozen training captures
(52 and 47) and scores the cached behavioral `1.1.0` artifacts for the four validation captures at the
frozen threshold `0.20`. No threshold search is performed. As a pipeline check, it reproduces the
hardening artifact's alert volume exactly for captures 46+53 (known_alerts `2,600`, unknown_alerts
`183,669`; the hardening artifact records `186,269` total).

| Capture | Labeled | Malicious | Prevalence | Precision | Recall | PR-AUC | Unknown rows | Unknown alerts | Unknown share |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 46 (Sc5) | 5,561 | 901 | 0.162 | 0.9829 | 0.9578 | 0.982910 | 124,271 | 56,744 | 0.457 |
| 53 (Sc12) | 9,783 | 2,168 | 0.222 | 0.9698 | 0.7703 | 0.946879 | 315,688 | 126,925 | 0.402 |
| 45 (Sc4) | 27,775 | 2,580 | 0.093 | 0.9424 | 0.9888 | 0.995813 | 1,093,297 | 494,069 | 0.452 |
| 51 (Sc10) | 122,157 | 106,352 | 0.871 | 0.9919 | 0.9999 | 0.999950 | 1,187,624 | 512,112 | 0.431 |
| **Pooled** | **165,276** | **112,001** | **0.678** | — | — | — | **2,720,880** | **1,189,850** | **0.437** |

Pooled workload: known_alerts `112,518`; all rows `2,886,156`; all alerts `1,302,368` (45.1% of all
rows).

Two consequences:

1. **Pooled recall hides per-capture variation.** The pooled labeled recall of `0.9949` is dominated
   by capture 51, which supplies 106,352 of the 112,001 positives. Capture 53 (NSIS) recall is
   `0.7703` and capture 46 is `0.9578`. This is the concrete reason every capture is reported
   individually rather than only pooled.
2. **The unlabeled workload is the real problem.** At the frozen threshold the model raises
   `1,189,850` alerts on rows with no authoritative label — 43.7% of all unlabeled traffic. This is a
   workload and uncertainty signal, **not** a false-positive rate, and it is the quantity the
   corrected framing should report.

The generated artifact is `data/evaluation/phase3_unknown_workload/workload_summary.json` (ignored).
No threshold, model, feature, or frozen policy was changed to produce it.

## Interpretation

1. The reported low recall and large residual are artifacts of a labeled-population-relative alert
   cap, not evidence of a weak detector.
2. `alerts_per_1000_labeled_flows` is population-dependent. When the labeled set is mostly positive it
   behaves as a recall ceiling rather than a workload control.
3. Model discrimination is not the current bottleneck. Label scarcity and unlabeled alert workload
   are.

## Recommended reframe (not yet approved as policy)

- Measure the frozen policy threshold on capture-grouped held-out captures, and report every capture
  individually rather than only pooled.
- Report unknown-label alert volume separately and never convert it to a false-positive rate.
- Frame the research contribution around evaluation under label scarcity and uncertainty routing to a
  human, rather than around squeezing detector recall.
- Do not select a future operating threshold under a labeled-population-relative cap without also
  reporting the absolute workload and the labeled prevalence that makes the cap binding.

## Caveats

- This is validation evidence over captures 45, 46, 51, and 53; it is not a held-out or real-world
  generalization claim.
- The deterministic rules detector is separately and genuinely weak (recall `0.0013` at its operating
  point). This diagnosis concerns the supervised models only.
- No threshold, model, feature, artifact, or frozen policy was modified to produce this document.
