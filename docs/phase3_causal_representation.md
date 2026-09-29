# Phase 3 causal host/time representation study

**Status:** `VALIDATED` training/validation representation experiment; Scenario 7 remains sealed.

## Question and boundary

Issue [#2](https://github.com/Lakshmi-Sindhu-P/AegisTrace/issues/2) asked whether a richer,
causal host/time representation reduces the malicious validation flows missed by the retained
Random Forest (RF), HistGradientBoosting (HGB), and Linear SVM (SVM). The study uses the same
complete-capture split and operating policy as the corrected `1.1.0` stability reference:

- train: CTU-13 Scenarios 11/52 and 47;
- validation: Scenarios 5/46, 12/53, 4/45, and 10/51;
- Scenario 7/48 is not loaded, scored, tuned, or used for feature selection;
- only authoritative `Normal` and `Botnet` labels enter supervised fitting and metrics;
- `Background` and `To-*` remain unknown and may supply prior context only;
- RF, HGB, and SVM parameters, seed `42`, and validation policy are unchanged.

The reproducibility artifact is the ignored
`data/evaluation/phase3_causal_representation/causal_summary.json`. It records source checksums,
feature names/version, scenario metadata, operating thresholds, per-scenario metrics, disagreement,
and residual cases. The corrected `1.1.0` reference is
`data/evaluation/phase3_model_stability/stability_summary.json`.

## Representation

Feature version `1.2.0` composes all 32 values from `1.1.0` and adds 13 prior-only values:

- 300-second source connection count;
- 60-second destination and destination-port diversity;
- 300-second protocol diversity and destination/port reuse;
- 60-second repeated-short count;
- log prior bytes/packets with observation indicators;
- log time since the previous source-host flow with a first-flow indicator.

The implementation is in `src/aegistrace/features/causal.py`. Source/destination addresses are
aggregation keys only. Events are sorted by observed UTC time, aggregates are updated after the
current vector is produced, mixed-scenario input is rejected, and a future-flow audit verifies that
earlier vectors do not change. No label, filename, scenario identifier, or source label enters the
numeric matrix.

## Operating-point results

The policy maximizes recall subject to validation precision at least `0.95` and at most 200 alerts
per 1,000 known-label flows. Thresholds are selected on each model's own score scale in 0.01
increments; PR-AUC is threshold-independent. HGB has no feasible candidate and therefore uses the
documented zero-alert fallback.

| Model | Reference 1.1.0 threshold | Causal 1.2.0 threshold | Causal precision | Causal recall | Causal F1 | Causal PR-AUC | Causal FPR/FNR | Alerts/1,000 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| RF | 0.73 | 0.65 | 0.9998 | 0.2607 | 0.4135 | 0.999563 | 0.000094 / 0.7393 | 176.7 |
| HGB | 1.00 | 1.00 | — | 0.0000 | — | 0.999695 | 0.000000 / 1.0000 | 0.0 |
| SVM | 0.58 | 0.78 | 1.0000 | 0.2548 | 0.4062 | 0.998941 | 0.000000 / 0.7452 | 172.7 |

The causal deltas versus the corrected `1.1.0` reference are:

| Model | Δ precision | Δ recall | Δ F1 | Δ PR-AUC | Interpretation |
|---|---:|---:|---:|---:|---|
| RF | −0.000038 | −0.0078 | −0.0098 | −0.000026 | Slightly worse ranking/operating recall with fewer alerts. |
| HGB | 0.0000 | 0.0000 | 0.0000 | −0.000044 | Still no workload-feasible operating point. |
| SVM | 0.0000 | −0.0349 | −0.0432 | +0.125364 | Ranking improves substantially, but the constrained operating point catches fewer cases. |

Per-scenario causal operating-point recall was RF `0.7310/0.2064/0.2479/0.3492` and SVM
`0.4841/0.0011/0.2499/0.3298` for Scenarios 4/5/10/12 respectively. HGB recall was zero in all
four scenarios. The large spread is evidence of capture-specific behavior, not a generalization
guarantee.

## Residual and disagreement result

After correcting the stale HGB-derived sections in the prior artifact, the `1.1.0` reference had
68,353 malicious validation cases missed by all three learned models. The `1.2.0` representation
has 64,986 such cases, a reduction of 3,367 cases (4.9%). This is a union-coverage change, not a
single-model win: RF and SVM each catch fewer cases at their new constrained thresholds, but their
overlap decreases and their combined coverage increases from 43,648 to 47,015 malicious cases.

The remaining residuals are concentrated in Scenario 10/51 (62,527 of 64,986). Their median causal
values still show very high prior activity (`2,711` destination reuses and `2,711` prior
300-second source connections), one protocol, one recent destination, and near-zero inter-flow
recency. This representation therefore distinguishes some errors but does not resolve the
capture-specific high-volume ICMP-like subgroup.

## Reference-artifact defect found and repaired

The earlier stability artifact had HGB metrics changed to the zero-alert operating fallback while
its disagreement/residual sections still reflected HGB's old threshold. The repair command
`scripts/correct_stability_operating_point.py` now recomputes those derived sections from the
recorded case IDs and immutable non-sealed Parquet artifacts. The expensive feature-summary helper
was also corrected to compute reference quantiles once instead of sorting the same 112,001-row
lists inside every residual-row loop. The repair records `artifact_repair` in the artifact and does
not load Scenario 7.

## Decision and limitations

The causal extension is implemented and validated as a representation experiment, but it is not a
new frozen detector policy. It does not justify fusion yet: the union gain is modest, dominated by
one validation capture, and the per-model operating trade-off is not better. It also does not
justify a new model family. The next defensible step is a narrower representation audit of the
Scenario 10/51 residual subgroup (with a future-event causality check and scenario-held-out test
design) before reopening Scenario 7. No temporal neural model, semi-supervised method, fusion,
LLM, scheduler, or governance change was implemented.
