# Phase 3 Held-Out Design: Practice Pool and Sealed Exam

**Status:** PROPOSED — design recorded 2026-10-08. Not executed. No capture has been acquired, no
model fitted, and no exam capture opened. This document defines the split and protocol; it makes no
result claim.

**Context:** the corrected interpretation in
[phase3_evaluation_diagnosis.md](phase3_evaluation_diagnosis.md) shows the recorded operating-point
recall was bounded by a labeled-population-relative alert cap, not by model quality. The held-out
measurement below replaces that framing: measure the frozen threshold on untouched captures, and
report the unknown-label workload separately.

## Split principle

- The unit of splitting is the **whole capture**, never the row. Flows from the same host and time
  window are near-duplicates; random row splits leak and inflate scores. This matches the split policy
  already recorded in [evaluation.md](evaluation.md).
- Two pools: a **practice pool** for iteration and a **sealed exam pool** opened once, with no tuning
  afterward.
- Report **every capture individually**. Never report only a pooled average.
- Report **unknown-label alert volume separately** and never convert it into a false-positive rate.

## Frozen policy under test (unchanged)

`configs/phase3_frozen_policy.json`: balanced Random Forest, behavioral feature version `1.1.0`,
seed 42, raw scores, threshold `0.20`, deterministic rules retained separately.

| Role | Capture | Scenario | Family | Rows | Known | Source |
|---|---|---:|---|---:|---:|---|
| Train | 52 | 11 | RBot | 107,251 | 10,873 | `docs/datasets.md` (family confirmed) |
| Train | 47 | 6 | RBot | 558,912 | 12,101 | `docs/datasets.md` |
| Validation | 46 | 5 | RBot | 129,832 | 5,561 | `docs/datasets.md` |
| Validation | 53 | 12 | NSIS | 325,471 | 9,783 | `docs/datasets.md` |
| Validation | 45 | 4 | RBot | 1,121,072 | 27,775 | `docs/datasets.md` |
| Validation | 51 | 10 | RBot | 1,309,781 | 122,157 | `docs/datasets.md` |
| Historical sealed | 48 | 7 | RBot | 114,077 | 1,732 | `docs/datasets.md` |

The frozen training pool is RBot-family, so "same family" below means RBot.

## Candidate exam captures (unused, verified present, CC-BY)

Availability, filenames, and sizes were verified from the public
`CTU-Malware-Capture-Botnet-N/detailed-bidirectional-flow-labels/` listings on 2026-10-08; families are
as reported by that remote README inventory and are **not independently re-verified** here.

| Capture | Scenario | Family | Labeled file | Size | Proposed role |
|---|---|---:|---|---:|---|
| 44 | 3 | RBot | `capture20110812.binetflow` | 610 MB | **Same-family exam** |
| 50 | 9 | Neris | `capture20110817.binetflow` | 273 MB | **Different-family exam** |
| 49 | 8 | Murlo | `capture20110816-3.binetflow` | 385 MB | **Different-family exam** |
| 54 | 13 | Virut | `capture20110815-3.binetflow` | 251 MB | **Different-family exam** |
| 42 | 1 | Neris | `capture20110810.binetflow` | 369 MB | Spare (different-family replicate) |
| 43 | 2 | Neris | `capture20110811.binetflow` | 236 MB | Spare (different-family replicate) |

All six are CC-BY (Garcia, Sebastian / Malware Capture Facility Project), matching how the existing
captures are treated. Total acquisition is approximately 2.1 GB of labeled text flows.

## Proposed exam set

- **Same-family (1 test):** capture 44 (RBot). Tests whether the learned RBot pattern transfers to an
  unseen RBot capture.
- **Different-family (3 tests):** captures 50 (Neris), 49 (Murlo), 54 (Virut). Tests cross-family
  generality. These are the families not already present in the validation pool (which has RBot and
  NSIS).
- **Optional spares:** 42 and 43 (Neris) if a second replicate is wanted; this would make six tests.
- **Focused minimum:** 4 tests (44, 50, 49, 54), roughly 1.5 GB.

## Measurement protocol (per exam capture)

1. Fit the frozen policy on the frozen training captures only (52 and 47), features `1.1.0`, seed 42.
   No exam data is used for fitting, feature selection, or threshold choice.
2. Score the exam capture at the frozen threshold `0.20`. **No threshold search.**
3. Report, per capture:
   - labeled precision, recall, F1, PR-AUC, and confusion counts, with the labeled prevalence stated;
   - the implied mechanical recall ceiling from the labeled prevalence and any cap, for context;
   - unknown-label alert count and share, labeled explicitly as an unscored workload;
   - runtime and resource cost.
4. After any exam result is observed, do not tune, refit, change features, or adjust the threshold.
   A second exam capture may be opened only under the same frozen policy.
5. Record source checksums, feature version, seed, model parameters, threshold, code revision, and
   the environment lockfile in the run artifact and experiment registry.

## Why not random 80/20 or 75/25 row splits

The ratio is reasonable; the unit is not. Splitting rows randomly places near-duplicate flows from the
same host and time window on both sides of the split, so the model is tested on siblings of its
training data. Whole-capture holdout is the grouped form of the same idea and is already the recorded
policy. A within-capture temporal split (early traffic for fitting, later traffic for scoring) is a
valid secondary check where timestamps support it.

## Open decisions

- Acquire all six captures (≈2.1 GB) or the focused four (≈1.5 GB)?
- Keep Scenario 7 / capture 48 reserved for the historical baseline's one-time final measurement, or
  supersede that reservation with this exam set? Both cannot be the "one untouched test."
- Confirm the exam captures are treated as opened-once before any result is inspected.
