# Phase 0 Learning Note

## What We Built

We turned the broad AegisTrace idea into a bounded research and engineering design. The repository now defines the question, non-goals, defensive boundary, source roles, architecture, canonical entities, evaluation plan, leakage controls, milestones, known limitations, and rules for honest portfolio claims.

No application code or experimental result exists yet.

## Why It Exists

Without a charter, the project could become a collection of impressive-sounding integrations with no defensible research result. Phase 0 makes later choices testable: each layer has an input, output, responsibility, failure behavior, and evidence requirement.

The self-critique also removed premature complexity. A common event envelope plus typed source details replaces a giant universal table; an evidence bundle replaces a graph database; IoT-23 and controlled Cowrie become the first two adapters; DShield and cloud work are deferred.

## Cybersecurity Concept

Security triage is the process of deciding which observations deserve investigation and why. An event is not automatically an incident. A rule firing, anomaly score, scanner finding, or LLM statement is a claim that must be supported and reviewed.

Provenance is the chain connecting a conclusion to its source record and every transformation between them. Preserving that chain lets an analyst reproduce the result, inspect errors, and distinguish evidence from interpretation.

## AI/ML Concept

Evaluation design must prevent data leakage. Network flows from one capture can share hosts, time patterns, and collection artifacts. Randomly placing related rows in both training and test data can make a model look generalizable when it has learned capture-specific shortcuts.

The LLM is evaluated separately from detection. It may improve categorization, completeness, or explanation, but it cannot retroactively improve whether a detector found the right events. Evidence-reference validity can be checked automatically; whether a security claim is truly supported still needs a rubric and human judgment.

## Files to Understand

1. `docs/project_charter.md` — the project contract, critique, milestones, and learning plan.
2. `docs/architecture.md` — component boundaries and the planned entity model.
3. `docs/datasets.md` — why each source exists and how leakage and label uncertainty are controlled.
4. `docs/evaluation.md` — the pre-results measurement protocol.
5. `docs/threat_model.md` — how telemetry, LLM input, honeypot data, and secrets are contained.
6. `docs/resume_evidence.md` — the boundary between completed work and future claims.

## Interview Explanation

> AegisTrace is a defensive research project testing whether an LLM can improve security triage without becoming the source of truth. I designed it as a provenance-first batch pipeline: source adapters create validated canonical events, transparent rules and an interpretable ML baseline create detections, related detections become findings with immutable evidence bundles, and only then does an LLM produce a structured advisory assessment for human review. The evaluation separates detector quality from LLM grounding and uses scenario-aware splits to avoid overstating results from correlated network data.

## Questions for Me

1. Why would a random row split within one IoT-23 capture produce misleading ML results?
2. What is the difference between an event, a detection, a finding, and an evidence bundle?
3. Why is DShield useful for exploration but unsuitable as automatic malicious ground truth?
4. What can evidence-ID validation prove about an LLM response, and what can it not prove?
5. Why did the design defer FastAPI, PostgreSQL, Azure, and a graph database?
