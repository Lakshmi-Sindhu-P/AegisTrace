# Phase 3 cross-scenario model stability and operating-point validation

**Status:** `VALIDATED` validation experiment; Scenario 7 remains sealed.

This pass evaluates only retained deterministic rules, Random Forest (RF),
HistGradientBoosting (HGB), and Linear SVM. It adds licensed CTU-13 Scenarios 4
and 10 (capture IDs 45 and 51) to the validation pool. Training remains Scenario
11 plus Scenario 47; validation is Scenarios 5, 12, 4, and 10. No Scenario 7
file was loaded, scored, or used for feature, threshold, or model selection.

The reproducibility artifact is
`data/evaluation/phase3_model_stability/stability_summary.json`. It records raw
checksums, immutable behavioral-feature artifacts, feature version `1.1.0`, seed
42, model parameters, score semantics, threshold trade-offs, per-scenario
metrics, disagreement cases, residual analysis, and the later HGB-derived
artifact repair provenance.

## Score and threshold semantics

The earlier shared numeric `0.20` comparison was a within-model diagnostic, not
an assertion that `0.20` means the same evidence across models:

- RF and HGB use `predict_proba(X)[:, 1]`. These are positive-class ranking/
  probability-like scores, not assumed calibrated probabilities. A threshold is
  a model-specific score cutoff.
- Linear SVM uses `LinearSVC.decision_function(X)`. Its signed margin is
  min-max normalized using training margins only, producing a `[0, 1]` ranking
  score. It is not a probability; its threshold is a normalized-margin cutoff.
- Isolation Forest is separate and unsupervised. It negates
  `decision_function` (higher means more anomalous), then min-max normalizes
  using training anomaly scores only. Its cutoff prioritizes anomalies; it does
  not create malicious ground truth, and unknown traffic stays unknown.
- Rules emit a binary trigger score (`1.0` when a fixed evidence-traceable rule
  fires, otherwise `0.0`) at native threshold `0.5`.

For RF, HGB, and SVM, the pooled validation operating policy was fixed before
comparison: maximize recall subject to precision at least `0.95` and at most
`200` alerts per 1,000 authoritative labeled flows. Unknown rows were excluded
from fitting, precision/recall/PR-AUC, and constraints; their population is
reported separately and never treated as benign. Candidate thresholds were
searched in `0.01` increments on each model's own score scale. PR-AUC is
threshold-independent and is computed once from the full labeled score ranking.

## Pooled validation result

| Detector | PR-AUC | Operating threshold | Precision | Recall | F1 | FPR | FNR | Labeled alerts/1,000 | Policy result |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Random Forest | 0.999589 | 0.73 | 0.9999 | 0.2685 | 0.4233 | 0.000075 | 0.7315 | 182.0 | Constraint satisfied |
| HistGradientBoosting | 0.999738 | 1.00 | — | 0.0000 | — | 0.000000 | 1.0000 | 0.0 | No candidate satisfied both constraints; workload-first zero-alert fallback |
| Linear SVM | 0.873577 | 0.58 | 1.0000 | 0.2898 | 0.4494 | 0.000000 | 0.7102 | 196.4 | Constraint satisfied |

HGB has the highest ranking metric, but its score mass is concentrated above the
workload-constrained operating region: no `0.01` candidate met both constraints.
The zero-alert fallback is explicitly marked as infeasible for precision and is
not an operational success. RF and SVM satisfy the defined workload constraint;
SVM's modest pooled recall advantage is not stable across scenarios.

The retained rules remain the interpretability control rather than a tuned competitor. At their
native binary threshold `0.5` they achieve pooled precision `0.7087`, recall `0.0013`, F1 `0.0026`,
PR-AUC `0.677701`, and 1.25 labeled alerts per 1,000; their predicates remain evidence-traceable
and do not imply that an alert is an incident.

## Per-scenario operating-point metrics

The following rows use each model's pooled validation-derived threshold. Alert
volume is labeled-flow volume; unknown rows are not scored by supervised models.

| Scenario | Model | Precision | Recall | F1 | PR-AUC | FPR | FNR | Alerts/1,000 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 4 (45) | RF | 1.0000 | 0.7620 | 0.8649 | 0.995813 | 0.000000 | 0.2380 | 70.8 |
| 10 (51) | RF | 0.9999 | 0.2615 | 0.4145 | 0.999950 | 0.000253 | 0.7385 | 227.7 |
| 5 (46) | RF | 1.0000 | 0.1743 | 0.2968 | 0.982910 | 0.000000 | 0.8257 | 28.2 |
| 12 (53) | RF | 1.0000 | 0.0655 | 0.1229 | 0.946879 | 0.000000 | 0.9345 | 14.5 |
| 4 (45) | HGB | — | 0.0000 | — | 0.992162 | 0.000000 | 1.0000 | 0.0 |
| 10 (51) | HGB | — | 0.0000 | — | 0.999935 | 0.000000 | 1.0000 | 0.0 |
| 5 (46) | HGB | — | 0.0000 | — | 0.990665 | 0.000000 | 1.0000 | 0.0 |
| 12 (53) | HGB | — | 0.0000 | — | 0.975250 | 0.000000 | 1.0000 | 0.0 |
| 4 (45) | SVM | 1.0000 | 0.2756 | 0.4321 | 0.977602 | 0.000000 | 0.7244 | 25.6 |
| 10 (51) | SVM | 1.0000 | 0.2917 | 0.4517 | 0.943874 | 0.000000 | 0.7083 | 254.0 |
| 5 (46) | SVM | — | 0.0000 | — | 0.969927 | 0.000000 | 1.0000 | 0.0 |
| 12 (53) | SVM | 1.0000 | 0.3316 | 0.4981 | 0.945748 | 0.000000 | 0.6684 | 73.5 |

The fixed `0.20` diagnostic remains available in the artifact for historical
comparison. On that non-equivalent shared cutoff, HGB has precision `0.9954`,
recall `0.9931`, and PR-AUC `0.999738`; RF has precision `0.9903`, recall
`0.9949`, and PR-AUC `0.999589`. Those results do not replace operating-point
validation because their workload is about 681 and 676 alerts per 1,000 labeled
flows respectively.

## SVM unique coverage and residual errors

After the HGB operating-point correction, SVM uniquely catches 13,576 malicious
cases missed by RF and HGB: 12,926 in Scenario 10 (12.15%), 650 in Scenario 12
(29.98%), and none in Scenarios 4 or 5. The coverage remains scenario-dependent.
The unique cases are descriptively enriched for low prior activity (52.3% at or
below the pooled malicious first quartile), low destination diversity (95.2%),
and low port diversity (95.1%). Their protocol mix is 95.2% ICMP, 0.2% TCP, and
4.6% UDP, so this is not evidence of a stable SVM specialist.

The corrected reference has 68,353 malicious validation cases missed by all three
learned models: 614 in Scenario 4, 744 in Scenario 5, 65,619 in Scenario 10,
and 1,376 in Scenario 12. This differs from the earlier 3,192 headline because
the earlier artifact mixed HGB's old disagreement threshold with its corrected
zero-alert operating metrics. The repair is recorded in the artifact's
`artifact_repair` section. The residual cases are dominated by short flows,
very high prior host activity, low destination/port diversity, and mixed
TCP/UDP/ICMP traffic. These are behavioral representation gaps, not evidence
that the flows are benign.

## Decision

The pass does not justify fusion: SVM's unique coverage is scenario-dependent,
and HGB has no workload-compliant operating point. It supports a bounded
representation audit before any new model family. No fusion, temporal model,
semi-supervised method, deep learning, or LLM was implemented.
