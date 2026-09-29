# Phase 3 causal-overlap subgroup diagnosis

**Status:** `VALIDATED` bounded diagnostic; Scenario 7 remains sealed.

## Question and boundary

Issue [#3](https://github.com/Lakshmi-Sindhu-P/AegisTrace/issues/3) follows the accepted
Issue [#2](https://github.com/Lakshmi-Sindhu-P/AegisTrace/issues/2) result. It asks why the
`1.2.0` representation changed Random Forest (RF) / Linear SVM (SVM) overlap mostly in
CTU-Malware-Capture-Botnet-51 (Scenario 10), while many malicious residuals remained.

This pass is descriptive: it does not refit a model, tune a threshold, promote `1.2.0`, or
introduce fusion or another model family. It compares the corrected `1.1.0` stability artifact
with the `1.2.0` causal artifact over the existing training/validation boundary:

- training: Scenarios 11/47;
- validation: Scenarios 5/12/4/10 (capture IDs 46/53/45/51);
- Scenario 7 (capture 48) was rejected by the diagnostic and was not loaded;
- authoritative malicious validation cases were used only to describe detector disagreement;
  `Background` and `To-*` remained unknown and were not converted to ground truth.

The reproducible command is:

```bash
uv run python scripts/analyze_phase3_causal_overlap.py \
  --created-at 2026-09-29T03:15:00Z
```

The ignored artifact is
`data/evaluation/phase3_causal_overlap/overlap_summary.json`. It records input checksums,
feature versions, category definitions, transition counts, scenario counts, feature summaries,
and the bounded hypothesis decision.

## Deterministic case categories

For every malicious event present in both artifacts, the category compares the RF/SVM union at
each version. HGB is intentionally not used to define this overlap question because Issue #2's
operating policy leaves it at its explicit zero-alert fallback.

| Category | Definition | Count |
|---|---|---:|
| `causal_only` | missed by the `1.1.0` RF/SVM union, caught by `1.2.0` | 10,564 |
| `reference_only` | caught by `1.1.0`, missed by `1.2.0` | 7,197 |
| `both_residual` | missed by both unions | 57,789 |
| `both_union` | caught by both unions | 36,451 |
| **Total** | authoritative malicious validation cases | **112,001** |

The net union change is therefore `10,564 - 7,197 = 3,367` cases, matching Issue #2's
reduction in all-three residuals. That arithmetic is a reconciliation of recorded predictions,
not a new performance claim.

The change is concentrated in capture 51 (Scenario 10):

| Validation capture | `causal_only` | `reference_only` | `both_residual` | `both_union` |
|---|---:|---:|---:|---:|
| 45 (Scenario 4) | 8 | 39 | 606 | 1,927 |
| 46 (Scenario 5) | 33 | 4 | 711 | 153 |
| 51 (Scenario 10) | 10,234 | 7,142 | 55,385 | 33,591 |
| 53 (Scenario 12) | 289 | 12 | 1,087 | 780 |

The RF/SVM overlap transitions also show that the reduction is not simply “both models improved”:
RF gained 10,965 and lost 11,840 cases; SVM gained 1,590 and lost 5,504. Many transitions move
between shared, RF-only, and SVM-only coverage rather than changing the residual union.

## Structural comparison

The diagnostic verifies that all `1.1.0` common features are byte-for-byte unchanged in the
`1.2.0` Parquet rows. It then summarizes the prior-only causal values for each category. In the
capture-51 subgroup, `causal_only` cases have:

- median prior source connections in 60 seconds of `6,106`, versus `2,777` for `both_residual`;
- median prior short connections in 60 seconds of `6,106`, versus `2,777`;
- median 60-second unique destinations of `1` in both groups;
- median time since the prior source flow of approximately `0.0011` versus `0.0022` in the
  representation's log-seconds scale;
- one prior protocol at the median in both groups.

Thus the changed cases are a high-rate, repeated-short, low-destination-diversity slice of the
Scenario 10 traffic. The unchanged residuals are not simply low-activity traffic: they contain a
large, similarly low-diversity, high-rate population at a lower median rate. The new aggregates
therefore separate part of the burst-density range but do not identify a distinct malicious
mechanism or explain the residual subgroup completely.

## Narrower hypothesis decision

The bounded narrower hypothesis evaluated by the analysis script was:

> Within Scenario 10/51, `1.2.0` candidate-only cases are at least 1.5× as bursty by the median
> 60-second source-connection and repeated-short counts, while being no more than 1.25× as
> destination-diverse than unchanged RF/SVM residuals.

The observed ratios are `2.125×`, `2.125×`, and `1.0×`, respectively, with 10,234 candidate-only
cases. The hypothesis is therefore **supported locally** as a description of where the overlap
changed. It is not a causal proof, does not generalize beyond one capture, and does not justify a
new feature policy. Capture 53 has a different mix (candidate-only cases are more destination-
diverse), which is a warning against treating the Scenario 10 pattern as universal.

## Conclusion and next step

Issue #2's conclusion is preserved: `1.2.0` is not promoted to the final policy, and the evidence
does not justify fusion, a new model family, an LLM layer, or orchestration changes. The bounded
diagnostic supports one narrower representation hypothesis—burst density at 60 seconds within
the Scenario 10/51 traffic shape—but also shows that substantial high-rate residuals remain.

The next defensible research step is one scenario-held-out test of this narrow burst-density
hypothesis using an already licensed non-sealed scenario or a newly licensed scenario, with the
same frozen operating policy and no Scenario 7 access. If that test is not justified by available
data, proceed to deterministic finding aggregation rather than adding model complexity.

Limitations: categories depend on frozen thresholds; feature summaries are observational and
cannot establish causality; one validation capture cannot support a generalization claim; unknown
rows are not evaluated as benign; and no operational or incident-detection claim follows.
