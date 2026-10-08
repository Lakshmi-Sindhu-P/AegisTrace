# AegisTrace results ledger

This ledger states what the AegisTrace project claims, at what evidence tier, and backed by which registered experiment artifact; every number is extracted from an artifact on disk. It is generated from `docs/results_ledger.json` by `scripts/render_results_ledger.py` and is validated against `docs/experiment_registry.json` by `scripts/validate_results_ledger.py`, so a claim cannot drift from its citation without the validator failing.

## Claim index

| Claim | Type | Status |
| --- | --- | --- |
| `claim:stage1-threshold-distance-uncertainty-routing` | DETERMINISTIC_DERIVATION | REFUTED |
| `claim:stage1-model-score-routing-dominates` | DETERMINISTIC_DERIVATION | SUPPORTED |
| `claim:stage2-reviewer-sweep-model-score-best` | DETERMINISTIC_DERIVATION | SUPPORTED |
| `claim:heldout-per-capture-precision-recall-spread` | OBSERVED_FACT | SUPPORTED |
| `claim:recall-ceiling-from-alert-rate-cap` | DETERMINISTIC_DERIVATION | SUPPORTED |
| `claim:unknown-label-rows-dominate-validation-pool` | OBSERVED_FACT | SUPPORTED |
| `claim:unknown-label-rows-excluded-from-labeled-metrics` | OBSERVED_FACT | SUPPORTED |
| `claim:no-real-fatigue-or-automation-bias-model` | UNKNOWN_INSUFFICIENT_EVIDENCE | NOT_CLAIMABLE |
| `claim:hf-false-alarm-rate-time-and-precision` | REFERENCE_BACKED_FACT | SUPPORTED |
| `claim:hf-correct-decision-versus-justification` | REFERENCE_BACKED_FACT | SUPPORTED |
| `claim:hf-no-published-workload-fatigue-threshold` | REFERENCE_BACKED_FACT | UNKNOWN |
| `claim:hf-no-usable-soc-automation-bias-parameter` | REFERENCE_BACKED_FACT | UNKNOWN |

## `claim:stage1-threshold-distance-uncertainty-routing`

**Statement.** Routing alerts by distance from the decision threshold retrieves more true positives than ranking by model score.

**Evidence.**

- Captures[scenario_id=CTU-Malware-Capture-Botnet-49].policies[policy=model_score].budgets[budget=100].true_positives = 100 versus policies[policy=uncertainty] = 8 and policies[policy=random] = 9.
- Captures[scenario_id=CTU-Malware-Capture-Botnet-54].policies[policy=model_score].budgets[budget=100].true_positives = 100 versus policies[policy=uncertainty] = 59 and policies[policy=random] = 60.
- Uncertainty's true-positive count exceeds model_score's at 0 of the 9 tested budgets on each of the six evaluated captures.

**Scope limit.** Refutes only ascending absolute distance from the frozen 0.2 threshold as a routing signal for this random-forest detector on these captures; predictive entropy, ensemble disagreement, and calibration-based uncertainty were not tested.

**Experiments.** `phase3-analyst-outcome-replay-1.0.0`

**Artifacts.** `data/evaluation/phase3_analyst_replay/replay_summary.json`

## `claim:stage1-model-score-routing-dominates`

**Statement.** Ranking alerts by model score retrieves at least as many true positives as threshold-distance uncertainty routing at every tested reviewer budget on all six stage-1 captures.

**Evidence.**

- Capture 46 at budget 100: model_score true_positives = 100, uncertainty = 84; capture 48: model_score = 24, uncertainty = 20; capture 50: model_score = 100, uncertainty = 96.
- Across the six captures, the uncertainty policy beats model_score at 0 of 9 tested budgets per capture.

**Scope limit.** Compares routing of already-computed scores at a fixed reviewer budget on two validation captures and four held-out captures; it is not a study of human cognition and supports no claim about analyst behaviour.

**Experiments.** `phase3-analyst-outcome-replay-1.0.0`

**Artifacts.** `data/evaluation/phase3_analyst_replay/replay_summary.json`

## `claim:stage2-reviewer-sweep-model-score-best`

**Statement.** Across a deterministic sweep of 450 simulated reviewer policies, model score is the best routing policy at every strictness value and every shift budget on every capture.

**Evidence.**

- headline.model_score_best_at_every_strictness_and_budget_all_captures = true and headline.uncertainty_ever_beats_model_score_any_capture = false.
- The sweep spans 6 captures x 3 routing policies x 5 strictness values x 5 shift budgets = 450 simulated reviewer policies.
- headline.per_capture lists uncertainty_beats_model_score_at = [] for all six captures, i.e. uncertainty strictly beats model_score in 0 of 150 paired (strictness, shift_budget) settings.

**Scope limit.** A simulated reviewer under stated assumptions, not observed human behaviour; the shift budgets and strictness values are free assumptions with no published anchor.

**Experiments.** `phase3-reviewer-simulation-1.0.0`

**Artifacts.** `data/evaluation/phase3_reviewer_simulation/simulation_summary.json`

## `claim:heldout-per-capture-precision-recall-spread`

**Statement.** On the four held-out exam captures the frozen detector's per-capture labeled precision ranges from 0.47 to 1.00 and labeled recall from 0.14 to 1.00.

**Evidence.**

- Capture 48: labeled.precision = 0.8181818181818182, labeled.recall = 0.14285714285714285.
- Capture 50: labeled.precision = 0.9992589868132106, labeled.recall = 0.9986917999643218.
- Capture 49: labeled.precision = 0.4693586698337292, labeled.recall = 0.9675208095315815.
- Capture 54: labeled.precision = 0.9596727060198714, labeled.recall = 0.45151613628977827.

**Scope limit.** A single frozen policy at threshold 0.2 with no threshold search; unknown-label rows are excluded, so these figures describe only the labeled minority of each capture and do not establish operational generalization.

**Experiments.** `phase3-heldout-exam-battery-1.1.0`

**Artifacts.** `data/evaluation/phase3_heldout/heldout_summary.json`

## `claim:recall-ceiling-from-alert-rate-cap`

**Statement.** The 200-alerts-per-1000-labeled-flows workload cap mechanically limits recall to at most about 29.5 percent of positives on the pooled validation labels.

**Evidence.**

- operating_policy.alerts_per_1000_labeled_flows_cap = 200.0.
- model_results.random_forest.fixed_policy_metrics.positive_count = 112001 and .support = 165276, i.e. 67.8 percent labeled prevalence; 0.20 / 0.6776 = 0.2952.
- model_results.random_forest.operating_metrics records recall = 0.2684976026999759 (true_positive = 30072, false_positive = 4, false_negative = 81929) at threshold 0.73, about 91 percent of that ceiling.

**Scope limit.** An arithmetic property of the stated alert-rate cap and this pooled labeled population only; it says nothing about performance on unlabeled traffic or at operating points without that cap.

**Experiments.** `phase3-model-stability-1.1.0`

**Artifacts.** `data/evaluation/phase3_model_stability/stability_summary.json`

## `claim:unknown-label-rows-dominate-validation-pool`

**Statement.** About 94.3 percent of flows across the four validation captures (46, 53, 45, 51) carry no authoritative label.

**Evidence.**

- Summed over the four validation captures: workload.all_rows = 2886156 and workload.unknown_rows = 2720880, a share of 0.94273.
- Per capture unknown_alert_share values are 0.4566149785549324, 0.40205836142013635, 0.4519073957030889, and 0.4312071834183209.

**Scope limit.** A workload and coverage statement only; unlabeled rows are not false positives, and these captures are not a representative sample of real-world traffic.

**Experiments.** `phase3-unknown-workload-1.1.0`

**Artifacts.** `data/evaluation/phase3_unknown_workload/workload_summary.json`

## `claim:unknown-label-rows-excluded-from-labeled-metrics`

**Statement.** Unknown-label rows are scored and reported as a workload signal but excluded from every labeled metric.

**Evidence.**

- replay_summary.methodology_note: unknown-label rows are excluded from every labeled evaluation, never counted as false positives, and reported separately as unknown_rows.
- uncertainty_summary.limitations: 'Unknown Background and To-* rows remain outside supervised denominators.'

**Scope limit.** A reporting-convention statement; it does not establish whether those unlabeled rows are malicious or benign.

**Experiments.** `phase3-analyst-outcome-replay-1.0.0`, `phase3-aggregate-uncertainty-1.0.0`

**Artifacts.** `data/evaluation/phase3_analyst_replay/replay_summary.json`, `data/evaluation/phase3_uncertainty/uncertainty_summary.json`

## `claim:no-real-fatigue-or-automation-bias-model`

**Statement.** The project models real reviewer fatigue and real automation bias.

**Evidence.**

- simulation_disclaimer: 'This is a simulated reviewer under stated assumptions. It is not observed human behaviour and is not evidence about analyst decision quality, over-reliance, trust calibration, or automation bias.'
- reviewer_model.assumption_note: 'The reviewer is an explicit policy, not a human model. These are stated assumptions and are not calibrated to, or validated against, observed analysts.'

**Scope limit.** No SOC-specific fatigue or over-reliance measurement exists anywhere in the project, so no AegisTrace result may claim to model real reviewer load or real automation bias.

**Experiments.** `phase3-reviewer-simulation-1.0.0`

**Artifacts.** `data/evaluation/phase3_reviewer_simulation/simulation_summary.json`

## `claim:hf-false-alarm-rate-time-and-precision`

**Statement.** Published controlled-experiment evidence shows a higher intrusion-detection false-alarm rate slows per-alert triage and lowers precision without changing sensitivity.

**Evidence.**

- docs/human_factors_evidence.md source 1, Layman & Roden, arXiv 2307.07023 (2023), VERIFIED: median per-alert time 13.44 s at 50 percent FAR versus 18.76 s at 86 percent FAR; median precision 0.80 versus 0.33; no significant difference in sensitivity.

**Scope limit.** Participants were computing-major students in a lab classification task, not professional analysts and not a SOC workflow, so this bounds a sensitivity analysis and not analyst performance.

**Experiments.** _(none cited)_

**Artifacts.** _(none cited)_

## `claim:hf-correct-decision-versus-justification`

**Statement.** Published field evidence shows SOC operators' decisions are far more often correct than the explanations they give for those decisions.

**Evidence.**

- docs/human_factors_evidence.md source 2, Moosmann, Pekaric & Apruzzese, arXiv 2604.22001 (DIMVA'26), VERIFIED: real-SOC field study with n = 12; decisions were correct in 83 percent of cases but only 39 percent of explanations reflected the actual root cause.

**Scope limit.** Small n and a single SOC; it motivates separating a decision from its stated justification but does not establish a general rate.

**Experiments.** _(none cited)_

**Artifacts.** _(none cited)_

## `claim:hf-no-published-workload-fatigue-threshold`

**Statement.** No retrieved study reports the number of alerts per shift at which analyst performance begins to degrade.

**Evidence.**

- docs/human_factors_evidence.md, THE GAPS item 1: 'No retrieved study reports how many alerts per shift precede performance degradation.' Any shift-budget parameter is therefore a free assumption.

**Scope limit.** An absence-of-evidence finding over the reviewed literature, not proof that no such study exists.

**Experiments.** _(none cited)_

**Artifacts.** _(none cited)_

## `claim:hf-no-usable-soc-automation-bias-parameter`

**Statement.** There is no usable published SOC-specific automation-bias or over-reliance parameter to calibrate a simulation against.

**Evidence.**

- docs/human_factors_evidence.md, THE GAPS item 2: 'SOC-specific automation bias / over-reliance (quantity #4) - effectively no usable source.' The rigorous study listed, arXiv 2306.16507, is a general-population task-identification experiment rather than SOC alert triage.

**Scope limit.** Absence of a usable SOC-specific parameter; it does not deny that automation bias exists, only that this project can quantify it.

**Experiments.** _(none cited)_

**Artifacts.** _(none cited)_

## Non-claims

- AegisTrace is not a SOC product, an IDS, or a deployable detector; all evaluation here is offline and research-grade.
- Output of the stub-assessor triage spine is not a triage result and carries no detection-quality claim.
- No claim is made about analyst behaviour, over-reliance, trust calibration, or automation bias.
- No claim is made that uncertainty routing is ineffective in general; only ascending threshold-distance uncertainty was tested.
- No pooled cross-capture, cross-population, or operational-generalization claim is made; captures are reported individually.
- No claim is made about the quality of the roughly 94.3 percent of validation rows that have no authoritative label.
- The sealed capture 48 result is not independent external validation.
- The model-family and causal-representation runs are prototypes, not a frozen final detector.

## Evidence gaps

- No SOC-specific workload or fatigue threshold exists in the reviewed literature, so every shift-budget value is a free assumption.
- No usable SOC-specific automation-bias measurement exists, so over-reliance cannot be calibrated against evidence.
- About 94.3 percent of validation flows have no authoritative label, so their true quality is unresolved.
- PR-AUC uncertainty is not estimated; the uncertainty run covers aggregate confusion-count proportions only.
- No observed human analyst data of any kind was collected for this project.
