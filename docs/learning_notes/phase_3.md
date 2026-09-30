# Phase 3 Learning Note: Detection Foundations

## What was built

Phase 3 adds three deliberately small layers:

1. `src/aegistrace/features/network.py` builds a versioned numeric feature vector from CTU-13
   flow fields. It keeps event/scenario/source IDs as metadata and excludes labels and label-like
   fields from the model matrix.
2. `src/aegistrace/detection/rules.py` applies three fixed, evidence-traceable rules: high total
   volume, long-lived high-volume flows, and large ICMP packet bursts. Each result records the
   observed value and threshold. A rule signal is not an incident or proof of compromise.
3. `src/aegistrace/evaluation/baselines.py` fits Logistic Regression and Random Forest with fixed
   parameters and seed 42. Scenario 11 is training, Scenario 5 is validation, and Scenario 7 is
   the held-out test scenario. `Background` and `To-*` rows stay unknown and are excluded from
   supervised fitting and metrics.

## Features

A feature is a measurable input representation used by a detector or model. The baseline uses flow
duration, log-scaled bytes/packets, source bytes, port-role flags, protocol flags, direction flags,
and a compact connection-state length. Missing numeric values become zero plus an explicit missing
indicator. The complete contract, units, rationale, and leakage review are in
[`docs/features.md`](../features.md).

Feature engineering is not the same as “adding every available column.” A small versioned vector
makes it possible to inspect coefficients, compare runs, and diagnose whether a signal comes from
behavior or from an accidental identifier.

### Cross-flow behavioral features

The original vector describes one flow at a time. That representation cannot tell whether a source
host opened 100 connections in the last minute, contacted many destinations, or repeatedly made
short connections. The validation-only improvement study adds those aggregates in feature version
`1.1.0`. They are computed separately per scenario, from prior observed flows only, and include
unknown-label flows as context. The current flow's source/total byte ratio captures traffic
asymmetry; raw addresses, labels, filenames, and scenario IDs remain outside the matrix.

This is a useful modeling lesson: a feature can be technically label-blind and still reflect a
collection environment. Scenario-held-out validation is what tests whether the behavior transfers.

### Causal host/time representation study

Issue #2 adds feature version `1.2.0` without changing `1.1.0`. The new values look farther back in
time (300 seconds), look at short-window diversity (60 seconds), count prior reuse of the current
destination/port, track prior protocol diversity and volume, and encode recency since the previous
source-host flow. “Prior” is the important word: the current row is scored before it is inserted into
the host's state, and a future-event audit checks that earlier vectors do not change.

These features illustrate why representation is different from model complexity. A model can only
learn the distinctions present in its inputs. A longer window may reveal a slow beacon, while
destination reuse may reveal a repeated pattern, but both can also memorize a capture's traffic
shape. The `1.2.0` validation run reduced the union of cases missed by RF/HGB/SVM by 4.9%, yet no
single constrained operating point improved. That is a useful negative result: more context created
some complementary coverage but did not establish a better detector policy.

The study also found a reproducibility lesson. When HGB's operating point was changed to a
zero-alert fallback, the old disagreement and residual sections still described its previous
threshold. Derived evidence must be regenerated whenever a policy changes; otherwise two parts of
one report silently describe different detectors.

### Diagnosing representation changes without overclaiming

Issue #3 adds a useful diagnostic habit: compare the individual malicious cases that changed, not
only the pooled residual count. A `causal_only` case is missed by the old RF/SVM union but caught by
the new representation; a `both_residual` case is missed by both. In this run, the new representation
changed overlap mainly for a Scenario 10/51 slice with very high prior source-connection and
repeated-short counts, one recent destination, and one protocol. The unchanged residuals still
contain many high-rate flows, so the feature family explains only part of the behavior.

This is descriptive evidence, not causal proof. A subgroup can be a property of one capture's
collection conditions rather than a transferable attacker behavior. The correct next step is a
scenario-held-out check of the narrow burst-density hypothesis under the same policy, or a move to
deterministic finding aggregation if more detector complexity is not justified. A lower pooled
residual alone is not a reason to promote a representation or add fusion.

### Reproducibility and uncertainty

Issue #4 adds a small experiment registry rather than a tracking platform. Each run records the
code revision, dataset and feature versions, scenario split, seed, command, artifact digest,
documentation, and claim boundary. This makes it possible to answer “which code and data produced
this number?” without committing raw datasets or generated evaluation tables.

The uncertainty companion uses Wilson score intervals for proportions that can be reconstructed from
recorded confusion counts. The interval around recall, for example, describes uncertainty in the
observed true-positive fraction; it does not make unknown traffic labeled, estimate PR-AUC, or prove
generalization. Because the intervals are aggregate-count summaries rather than independent-event
bootstrap estimates, they improve communication but do not replace scenario-aware validation.

## Precision and recall

For known labels, precision asks: “Of the flows predicted malicious, how many were malicious?”
Recall asks: “Of the malicious-labeled flows, how many did we find?” A detector can have high
precision and terrible recall if it raises very few alerts. The Phase 3 rules show this tradeoff:
they produced almost no false positives on the held-out scenario but found only 1.6% of its known
malicious rows.

## False positives and false negatives

- A false positive is a benign-labeled flow that the detector flags. It costs analyst attention and
  can erode trust.
- A false negative is a malicious-labeled flow that the detector misses. It can hide behavior that
  deserved investigation.

False-positive rate divides false positives by all known benign rows. False-negative rate divides
false negatives by all known malicious rows. Neither metric is meaningful for unknown rows because
there is no authoritative class to compare against.

## Class imbalance and PR-AUC

The known labels are uneven across scenarios, and the full corpus is dominated by unknown
Background/To-* traffic. Accuracy could look strong while missing nearly every malicious row.
Precision, recall, F1, confusion counts, error rates, and PR-AUC expose more of that tradeoff.
PR-AUC summarizes ranking quality across thresholds and is usually more informative than ROC-AUC
when the positive class is uncommon, but it does not replace the fixed-threshold confusion matrix.

### Threshold tuning and class weighting

The default threshold of 0.5 is a policy choice, not a law. Lowering it usually finds more
malicious rows (higher recall) while flagging more benign rows (lower precision). In this study the
threshold was selected on validation only by maximum F1; every threshold's precision, recall, F1,
and error rates is retained in the diagnostic artifact. It must not be selected from the sealed
final test.

Class weighting changes the training loss so the minority class matters more. `balanced` is useful
when missing a malicious example is more costly than an extra alert, but it can sacrifice precision.
It does not create new information or repair a weak feature representation.

## Supervised versus unsupervised learning

Supervised learning fits a mapping from inputs to authoritative target labels. Phase 3 uses only
known `benign` and `malicious` labels for this purpose. Unsupervised or anomaly methods do not need
labels, but an anomaly score is not automatically a maliciousness label; evaluating one would
require a separate contamination and threshold methodology. No unsupervised detector was added in
this phase.

## Leakage

Leakage occurs when information unavailable at detection time—or derived from the target—enters a
feature or split. Examples here would be using `ground_truth_label`, raw `Label`, the filename,
scenario ID, or a post-hoc aggregate. The feature builder returns only the ordered numeric vector;
the evaluator groups by scenario before fitting and holds out the test scenario. Standardization
is fit on training rows only.

## Why scenario-aware evaluation matters

Flows from one capture share hosts, tooling, timing, and collection conditions. Randomly mixing rows
from the same capture can let a model memorize those conditions and make a result look better than
it generalizes. Holding out a complete scenario asks a harder and more honest question: does the
baseline transfer to a different capture? The current improvement uses two training and two
validation scenarios, which is still a narrow study, but it is methodologically stronger than a
row-level split.

## What the results prove—and do not prove

The run proves that AegisTrace can build a reproducible, leakage-reviewed feature artifact, emit
evidence-linked deterministic detections, and evaluate two simple supervised baselines across
scenario boundaries. It does not prove that AegisTrace detects compromise, that CTU-13 represents
modern networks, or that either model is suitable for operations. The held-out recall was low, so
the first baseline should be treated as a useful negative result and a foundation for later,
explicitly versioned improvements.

The focused improvement study provides a stronger validation signal without reopening the final
test. With the expanded training pool, the behavioral Random Forest using balanced class weights
achieved validation precision `0.683`, recall `0.519`, and F1 `0.683` at threshold 0.5. Selecting
threshold `0.15` on validation raised recall to `0.845` and F1 to `0.897`, while precision fell to
`0.956`. At that same selected threshold, recall was `0.958` on Scenario 5 and `0.798` on Scenario
53, so the gain appeared on both validation captures but was not uniform. The per-flow Random Forest
at threshold 0.5 reached only `0.078` recall on the same expanded validation pool, supporting the
diagnosis that cross-flow context—not only more rows—matters. These are validation findings, not
final-test or operational claims.

## Pre-final hardening lessons

An ablation removes one feature group at a time while holding the model, split, and threshold fixed.
Here, destination-port diversity was the largest single recall contributor, but no group explained
all of the gain. This is stronger evidence for complementary behavior than simply adding more
columns.

Temporal leakage is a special form of train/test contamination. A prior-window feature may use
flows at or before time `t`, but it must not inspect future rows. The hardening audit appends a future
fixture flow and verifies that every earlier vector remains unchanged.

Calibration asks whether a score behaves like a probability. A Random Forest score of 0.8 is not
automatically an 80% chance of maliciousness. The training-only sigmoid assessment slightly improved
expected calibration error but worsened Brier score, so calibration was deferred and raw scores are
used only for ranking/thresholding.

Alert volume connects model metrics to reviewer workload. At the frozen validation threshold 0.20,
precision is 0.974 and recall is 0.825 on known labels, with 2,600 known-label alerts (169.4 per
1,000 labeled flows). The detector produced 186,269 alerts across all validation rows, most of which
are unknown-label rows; that number is a workload warning, not a measured false-positive count.

## Interview explanation

“I built a small label-blind flow feature set, wrote transparent rules with threshold evidence, and
then added scenario-local host/time aggregates. I compared simple model families with validation-only
operating points across separate CTU-13 captures. Unknown Background and To-* labels stayed unknown.
The causal extension added some union coverage but did not improve a single constrained model, so I
kept the final scenario sealed, repaired an inconsistent derived artifact, and treated the result
as a prototype—not proof of compromise detection.”

## Learning questions

1. Why would a high-precision, low-recall rule be useful in an analyst workflow, and when would it
   be harmful?
2. Which feature in `docs/features.md` would be most likely to leak if it were computed over the
   entire dataset before splitting, and why?
3. Why is a held-out scenario a stronger generalization test than a random row split for this data?
4. Why can a lower threshold improve recall without improving the model's ranking quality (PR-AUC)?
5. Which behavioral aggregate would be most vulnerable to capture-specific host behavior, and what
   additional split would you use to test that risk?
6. Why can a feature extension reduce the union of missed cases while making each individual
   model's recall worse at its own precision/workload threshold?
7. Why must disagreement and residual artifacts be regenerated when an operating threshold changes?
