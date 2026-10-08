# Human-factors evidence for the analyst-outcome program

This note records the external evidence that bounds the assumptions in
[`analyst_outcome_program.md`](analyst_outcome_program.md). It exists because stage 2's reviewer model
is an invented assumption set, and an invented assumption presented without provenance is
indistinguishable from a measured one.

Everything marked `VERIFIED` below was re-fetched and re-read during review rather than taken from a
search summary. One transcription error was caught this way and is recorded rather than quietly
fixed.

**No claim in this note is about AegisTrace's own detector.** These are published results about other
systems, other populations, and other tasks.

## Evidence status vocabulary

- `VERIFIED` — the source was retrieved and the specific number below was read in the source text.
- `REPORTED` — the source was retrieved but the specific number was not independently re-read.
- `ADJACENT` — relevant, no boundable number.
- `LOW CONFIDENCE` — retrieved, but internally inconsistent or from a venue that does not support the
  strength of the claim.

## USABLE — numbers that can bound a simulation parameter

### 1. Layman & Roden, *A Controlled Experiment on the Impact of Intrusion Detection False Alarm Rate on Analyst Performance* (arXiv 2307.07023, 2023) — `VERIFIED`

<https://arxiv.org/abs/2307.07023>

Controlled experiment, two groups (`n = 25` at 50% false-alarm rate, `n = 26` at 86% FAR), 52 alarms
each. Values read directly from the paper's results table:

| Measure | 50% FAR | 86% FAR |
|---|---|---|
| Per-alert time, median | **13.44 s** | **18.76 s** |
| Per-alert time, mean | 13.95 s | 19.25 s |
| Precision (PPV), median | **0.80** | **0.33** |
| Precision (PPV), mean | 0.80 | 0.42 |
| Sensitivity, median | 0.83 | 0.86 |
| Sensitivity, mean | 0.78 | 0.69 |
| Correctness, mean | 0.75 | 0.76 |

The paper's own summary: median precision 47% lower and median time on task 40% slower in the
high-FAR group, with **no significant difference in sensitivity**.

**Correction of record.** An earlier pass reported per-alert times of "15.6 s vs 21.4 s". Those
values appear nowhere in the paper; the 21.79 s figure in the source is a *maximum*, not a median.
The table above is the corrected reading.

**Bounds:** per-alert handling time (#1), triage precision and escalation rate (#2), and decision
behaviour under uncertainty (#5).

**Limitation that must travel with any use:** participants were computing-major students performing a
lab classification task. They are **not** professional analysts and the task is not a SOC workflow.
This study can bound a *sensitivity analysis*, not a claim about analyst performance.

### 2. Moosmann, Pekaric & Apruzzese, *Can SOC Operators Explain their Decisions while Triaging Alarms? A Real-World Study* (arXiv 2604.22001, DIMVA'26) — `VERIFIED`

<https://arxiv.org/abs/2604.22001>

Real-SOC field study, `n = 12`, real alarms raised in the operators' own SOC, preceded by a systematic
literature review of 257 documents. Decisions were correct in **83%** of cases, but only **39%** of
the explanations reflected the actual root cause.

**Bounds:** decision quality versus decision *justification* (#5). This is the most directly relevant
source for AegisTrace's own claim-verification design: it is published evidence that a correct
decision and a correct stated reason are different things, and that the second is much rarer.

**Limitation:** small `n`, single SOC, preprint accepted to DIMVA'26.

### 3. *Human–AI Collaboration in Security Operations: Measuring Alert Trust, Automation Bias, and Analyst Upskilling* (IJCTECE 8(5), 2025) — `LOW CONFIDENCE`

<https://doi.org/10.15680/ijctece.2025.0805010>

Reports false-alert acceptance of 22% / 12% / 29% at 70% / 85% / 95% stated AI accuracy, and mean
trust 4.1 / 5.6 / 5.9 on a 7-point scale.

**Do not bound anything on this source alone.** Its methods are written in the future tense
("participants will include 40–50") while reporting results, which is internally inconsistent, and the
venue is low-tier. It is listed so that the gap below is accurate — not as evidence.

## ADJACENT — relevant, no boundable number

These establish that the problems are real and studied. None yields a parameter.

- **Alahmadi et al., "99% False Positives" (USENIX Security 2022)** — <https://www.usenix.org/conference/usenixsecurity22/presentation/alahmadi> — survey plus interviews confirming false-positive volume and analyst desensitisation; no time or threshold figure.
- **"Automation Bias and Complacency in Security Operation Centers" (Computers, MDPI 2024)** — <https://doi.org/10.3390/computers13070165> — scoping review (599→48 articles) producing guidelines only.
- **"Matched and Mismatched SOCs" (ACM CCS 2019)** — <https://doi.org/10.1145/3319535.3354239> — 18 interviews; manager/analyst disagreement, no effect sizes.
- **"A Field Study of the Alert Investigation Process of Tier-1 Analysts" (USEC 2025)** — <https://doi.org/10.14722/usec.2025.23034> — 5+4 analysts, 400+36 investigations; process variance only.
- **"Alert Alchemy: SOC Workflows and Decisions in the Management of NIDS Rules" (ACM CCS 2023)** — <https://doi.org/10.1145/3576915.3616581> — 17 MSSP interviews; qualitative factors only.
- **"Human Performance in Security Operations: Burnout, Well-Being and Flow State" (WOSoC 2025)** — <https://doi.org/10.14722/wosoc.2025.23002> — `n = 19`; 31–36% met criteria for high burnout. Quantifies well-being, **not** a performance-degradation threshold.
- **"Alert Fatigue in Security Operations Centres: Research Challenges and Opportunities" (ACM Computing Surveys 2025)** — <https://doi.org/10.1145/3723158> — review naming four causes; no threshold.
- **"Bending the Automation Bias Curve" (arXiv 2306.16507, 2023)** — rigorous, preregistered, `n = 9000` across 9 countries, with effect sizes — **but** a general-population task-identification experiment, not SOC alert triage.

## THE GAPS — these must be declared free assumptions, not presented as evidence-backed

1. **Workload / fatigue threshold (quantity #3) — NO usable source.** No retrieved study reports how
   many alerts per shift precede performance degradation. The closest work (source 1) varies
   false-alarm *rate*, not alerts-per-shift *volume*, and reports no degradation onset point. Any
   shift-budget parameter in a simulation is a **free assumption**.
2. **SOC-specific automation bias / over-reliance (quantity #4) — effectively no usable source.** The
   only SOC-specific numbers come from source 3, which is unreliable on its own face. The rigorous
   study (last item above) is not SOC triage. Any over-reliance parameter is a **free assumption**.

## How this constrains AegisTrace's program

- The reviewer simulation's shift budgets and strictness values remain **invented**, and the
  simulation must keep saying so. Source 1 bounds per-alert *time*, not alerts per shift.
- Source 1 supports a sensitivity analysis over false-alarm rate, which the sweep already varies via
  strictness. It does **not** justify any particular strictness as realistic.
- Source 2 is the strongest external motivation for AegisTrace's own separation of a *decision* from
  its *stated justification* — the exact distinction the `Claim` / `ClaimVerification` contracts
  encode.
- Because gaps 1 and 2 are unfilled, no AegisTrace result may claim to model real reviewer load or
  real over-reliance. This is a boundary on the research contribution, not a defect to be papered
  over.

## Verification method

Sources 1 and 2 were fetched directly and their numbers read from the source tables rather than from
search summaries. The first pass over source 1 contained an incorrect time-on-task pair, which the
re-read corrected. A control fetch during this review returned empty, which was diagnosed as broken
network egress from the review shell rather than missing sources — the "not found" result was
discarded once a known-good identifier behaved identically.
