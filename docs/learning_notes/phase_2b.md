# Phase 2B Learning Note: CTU-13 Real-Data Validation

## What was actually validated

On 2026-09-21, AegisTrace ingested the authoritative CTU-13 Scenario 11
(`CTU-Malware-Capture-Botnet-52`) `capture20110818-2.binetflow` artifact. The file contained
107,251 labeled bidirectional flow records. All 107,251 rows were accepted, with no malformed or
duplicate source rows. The run produced typed Parquet, a quality report, and a dataset manifest;
the raw file checksum and source URL are recorded in the manifest. Re-ingestion derives the same
event IDs from the scenario, dataset version, and source line identity.

This validates ingestion, provenance, schema mapping, quality accounting, and reproducible local
artifacts against one genuine dataset. It does not validate a detector, machine-learning model,
LLM, incident classifier, or production workflow.

## NetFlow/Argus-style flow data

An Argus-style bidirectional flow is a summary of traffic observed between two endpoints over a
flow interval. It records fields such as start time, duration, protocol, direction, endpoint
addresses and ports, state, packet count, total bytes, source bytes, and a source label. It is
not a packet payload and cannot answer every application-level question. Bidirectionality means
the record summarizes both directions of the conversation while retaining a source-side view of
bytes and endpoints.

## Difference from Zeek connection logs

Zeek `conn.log` records a Zeek connection observation with Zeek's UID, connection state, history,
service, originator/responder byte and packet fields, and optional tunnel metadata. CTU-13's
Argus text flow has different field names and semantics: its `Dir`, `State`, `TotPkts`, `TotBytes`,
`SrcBytes`, and TOS fields come from Argus, and some non-IP flows use MAC addresses. AegisTrace
maps shared concepts into the canonical event envelope, while keeping the complete source label,
Argus fields, and non-IP source addresses in `Ctu13FlowDetails`. The CTU-13 adapter is a separate
module rather than a format branch inside the IoT-23 Zeek adapter.

## CTU-13 labels and the safe mapping

The dataset documentation describes three broad traffic classes: Botnet traffic from infected
hosts, Normal traffic from verified normal hosts, and Background traffic whose purpose is not
known with certainty. Scenario labels are more detailed strings, including `From-Botnet-*`,
`From-Normal-*`, `Background-*`, and `To-*` labels. The adapter therefore maps only
`From-Botnet*` (or an exact `Botnet`) to a malicious ground-truth label and only `From-Normal*`
(or an exact `Normal`) to benign. `Background`, `To-Botnet`, `To-Normal`, and other directional
labels remain unknown. “Unknown” is a deliberate evidence-preserving outcome, not a missing
implementation.

These are authoritative dataset annotations, not AegisTrace inference. The adapter stores the
raw source label and its provenance so later evaluation can choose a more specific policy without
rewriting the original annotation.

## Why scenario identity survives normalization

The scenario is a capture-level boundary. If it were discarded, later random row splitting could
place near-identical behavior from one capture in both training and test data, producing leakage.
Every canonical CTU-13 event therefore carries `scenario_id`, and the manifest records the selected
scenario. A future evaluator can group by scenario before choosing a split; Phase 2B does not make
that final split.

## Interview explanation

“I used a small real CTU-13 labeled bidirectional-flow file to test whether my canonical event
model was coupled to Zeek. I built a separate Argus adapter, preserved source labels and scenario
identity, retained non-IP source addresses, emitted typed Parquet plus a checksum-backed quality
report and manifest, and made Background/To-* labels unknown rather than silently benign. The
validation proves provenance and normalization on real data; it does not claim detection or ML
performance.”
