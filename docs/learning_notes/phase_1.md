# Phase 1 Learning Note

## What We Built

Phase 1 established the executable project foundation:

- a Python 3.12 package installed through a locked `uv` environment;
- strict TOML configuration with three explicit environment overrides;
- application-owned JSON logging with nested sensitive-key redaction;
- an immutable canonical security-event envelope with typed detail variants;
- deterministic UUIDv5 event IDs derived from stable source identity;
- timezone-aware transformation provenance;
- dataset/file manifests with checksums and consistency validation;
- a documentation-safe synthetic network fixture;
- automated tests, coverage enforcement, linting, and strict type checking.

At the Phase 1 baseline no real security telemetry was ingested; Phase 2B later adds a separately
documented CTU-13 validation run without changing the Phase 1 learning objective.

## Why It Exists

Every later detector, feature, finding, and AI assessment depends on stable event identity and trustworthy provenance. Implementing these contracts first prevents each source adapter from inventing its own incompatible shape and gives tests a precise boundary for malformed or incomplete data.

The runtime dependency set contains only Pydantic. Dataframe, storage, and ML packages are deferred until the first pipeline uses them, which keeps the foundation understandable and reduces supply-chain surface.

## Cybersecurity Concept

Evidence integrity requires more than retaining raw logs. An analyst must be able to identify the exact source record, dataset version, transformation, and processing time behind a normalized event. A deterministic event ID makes reprocessing idempotent: the same source identity produces the same canonical identity instead of duplicating evidence.

Sensitive telemetry also changes logging requirements. Keys suggesting passwords, tokens, credentials, or secrets are redacted before structured log serialization. This is a safety layer, not permission to log raw credentials; the primary rule remains not to put secrets in log calls.

## AI/ML Concept

Schema validation is part of ML reliability. Invalid ports, naive timestamps, undocumented labels, or unstable record identity can corrupt features and evaluation long before a model is trained. Dataset manifests provide the dataset version and checksum evidence needed to reproduce an experiment and detect silent data replacement.

## Code to Understand

1. `src/aegistrace/schemas/events.py` — source identity, event details, timestamp normalization, and label invariants.
2. `src/aegistrace/schemas/manifests.py` — dataset snapshot integrity and consistency rules.
3. `src/aegistrace/config.py` — TOML loading and allowlisted environment overrides.
4. `src/aegistrace/logging_config.py` — isolated JSON logger and recursive key redaction.
5. `tests/` — executable examples of accepted and rejected inputs.

## Interview Explanation

> I built the project foundation around evidence integrity before adding detection. Each canonical event is an immutable, versioned Pydantic record with a deterministic UUID derived from its dataset and source-record identity, plus timezone-aware transformation provenance. Dataset manifests bind files to checksums and counts, configuration rejects unknown keys, and JSON logging redacts sensitive fields. The package is reproducible through a locked Python 3.12 environment and validated by tests, linting, and strict static typing.

## Questions for Me

1. Why is a deterministic event ID safer for reprocessing than generating a new random UUID every run?
2. Why does `ground_truth_label=malicious` require a `label_source`?
3. What does a dataset checksum prove, and what does it not prove about label quality?
4. Why does the canonical model use a discriminated detail type instead of putting every source field on one flat model?
5. Why are Pandas, DuckDB, and scikit-learn not installed yet even though they are approved technologies?
