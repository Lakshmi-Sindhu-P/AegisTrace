# Phase 3 Held-Out Design: Practice Pool and Sealed Exam

**Status:** APPROVED 2026-10-08 by the repository owner. Acquisition of the focused four exam
captures (44, 50, 49, 54) is in progress; no model has been fitted and no exam capture has been
scored. This document defines the split and protocol; it makes no result claim.

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

## Approved exam battery

Five captures, opened once as a battery:

- **Same-family (2 tests):** captures 44 and 48 (both RBot). Tests whether the learned RBot pattern
  transfers to unseen RBot captures.
- **Different-family (3 tests):** captures 50 (Neris), 49 (Murlo), 54 (Virut). Tests cross-family
  generality. These are the families not already present in the validation pool (which has RBot and
  NSIS).
- **Acquisition:** completed 2026-10-08 for the focused four (raw files are ignored and not
  committed). Source: `https://mcfp.felk.cvut.cz/publicDatasets/CTU-Malware-Capture-Botnet-<n>/detailed-bidirectional-flow-labels/`.

  | Capture | Family | File | Bytes | SHA-256 |
  |---|---|---|---:|---|
  | 44 (Sc3) | RBot | `capture20110812.binetflow` | 639,643,247 | `0ebcd1df082bb5f85f8254c3857b02fdbb597c9b2ee7c50f908cc24ca92c0054` |
  | 50 (Sc9) | Neris | `capture20110817.binetflow` | 285,841,002 | `c8de257b6207ec3624467da62e91841073256fbdad5434db5eb5667588178bab` |
  | 49 (Sc8) | Murlo | `capture20110816-3.binetflow` | 403,955,463 | `c3884b629e152e3144c2d7250d01939c199fa8a135a88f0c775ee3be0237f01f` |
  | 54 (Sc13) | Virut | `capture20110815-3.binetflow` | 262,668,288 | `d1d8aaea885870c64615261bd78ebf569e7d5b41adab2a6f3008702f4ded4503` |

  Capture 48 is already local.
- **Spares:** 42 and 43 (Neris) if a further replicate is wanted.

### Capture 48 status (important)

Capture 48 is **not pristine**. It was already opened once as the test scenario of the historical
three-scenario baseline, and its metrics are recorded in [evaluation.md](evaluation.md) (Rules,
Logistic Regression, and Random Forest at feature version `1.0.0`). It has, however, never been used
to select the **current** frozen policy (feature `1.1.0`, balanced Random Forest, threshold `0.20`,
training captures 52 and 47).

Including 48 in this battery is therefore defensible only under the honest label
**"previously opened for the historical baseline; held out from the current frozen policy."** It
consumes the one-time Scenario 7 opening recorded in the gate section of [evaluation.md](evaluation.md),
and it retires 48 from any future fresh-test role. No tuning may follow any battery result.

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

## Resolved decisions (2026-10-08)

- **Scope:** acquire the focused four (44, 50, 49, 54) and use capture 48 from local storage. The
  remaining unused captures (42, 43) stay available as spares.
- **Capture 48:** included in the battery under the "previously opened for the historical baseline"
  label above; this consumes the one-time Scenario 7 opening.
- **Opened once:** the battery is opened once, together, at the frozen policy, with no tuning after
  any result.
