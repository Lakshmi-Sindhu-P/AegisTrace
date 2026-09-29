# Phase 2 Learning Note

## What We Built

Phase 2 adds a defensive batch adapter for labeled IoT-23 Zeek connection logs. It:

- parses Zeek directives, tab-separated fields, missing markers, and row shape;
- maps network-flow records into canonical `SecurityEvent` objects;
- preserves source IDs, raw-file references, SHA-256, dataset version, and transformation provenance;
- normalizes labels into benign, malicious, or unknown while preserving the detailed label as attack category;
- writes a stable typed Parquet table;
- emits a sanitized data-quality report and a repeatable dataset manifest;
- counts malformed, invalid, duplicate, missing, and labeled records;
- exposes a reproducible CLI without downloading pcaps or binaries.

The official Capture 34-1 file was not downloaded because its source page requires authorization. The implementation is validated against a safe synthetic fixture with the same Zeek shape.

## Why It Exists

This is the first boundary between external telemetry and AegisTrace’s internal evidence model. Keeping parsing, validation, quality accounting, and storage together makes it possible to inspect the dataset before features or detectors hide its problems.

The adapter deliberately does not assign a new security verdict. It maps the source’s documented label into a coarse field and preserves the source’s detailed label; later evaluation can decide how those labels should be used.

## Cybersecurity Concept

Zeek connection logs are network-flow summaries, not packet captures and not complete incident narratives. A row can show endpoints, ports, protocol, duration, bytes, packets, state, and source labels, but it cannot by itself prove attacker intent or compromise. The pipeline keeps that distinction visible.

Duplicate detection is also an evidence-integrity control. If the same stable source event appears twice, silently counting it twice can distort rates, class balance, and later model evaluation.

## AI/Data Concept

Data quality is part of the model. The pipeline records missingness and label distributions before any feature engineering. It writes an explicit Parquet schema so a later reader does not infer incompatible types from an unlucky sample. The raw checksum and manifest make it possible to distinguish a changed dataset from a changed transformation.

## Code to Understand

1. `src/aegistrace/ingestion/iot23.py` — parser, label mapping, quality report, Parquet writer, and CLI.
2. `src/aegistrace/ingestion/report.py` — sanitized parse issues and quality counts.
3. `tests/test_iot23_ingestion.py` — accepted rows, malformed input, duplicates, output artifacts, and CLI behavior.
4. `data/fixtures/iot23/conn.log.labeled` — safe synthetic Zeek-shaped input.
5. `docs/datasets.md` — acquisition authorization and provenance policy.

## Interview Explanation

> I built a batch adapter for labeled Zeek connection logs that treats ingestion as an evidence boundary. It parses directives and missing markers, maps flows into typed canonical events, derives repeatable identities, preserves the raw checksum and source labels, and writes a fixed Parquet schema plus quality report and dataset manifest. The adapter is validated with synthetic data, while the official scenario remains pending authorization, so I do not claim real-data results yet.

## Questions for Me

1. Why is a Zeek flow not equivalent to a packet capture or a confirmed incident?
2. Why preserve both the coarse label and the detailed source label?
3. Why should a malformed-row report never include the raw invalid token?
4. What does duplicate source identity do to evaluation metrics?
5. Why does the pipeline require an explicit `--ingested-at` timestamp?
