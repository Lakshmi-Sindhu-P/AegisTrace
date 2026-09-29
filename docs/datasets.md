# Dataset and Telemetry Plan

**Status:** source strategy approved; the IoT-23 adapter remains synthetic-fixture validated only,
while seven openly licensed CTU-13 bidirectional-flow artifacts are recorded locally across baseline
and validation-only experiments.

## Source Roles

| Source | Role | Label status | Earliest milestone |
|---|---|---|---|
| Synthetic fixtures | Contract and failure-path tests | Explicit fixture labels, never evaluation evidence | 1 |
| IoT-23 | Primary network-flow pipeline and labeled baseline experiments | Analyst/rule-derived dataset labels | 2 |
| CTU-13 | First real labeled network-flow validation and second adapter format | Stratosphere manual flow labels; `Background` and `To-*` remain unknown here | 2B |
| Controlled Cowrie JSON | Second heterogeneous source and session reconstruction | Scenario intent documented by the builder; not real-world ground truth | 4 |
| DShield/ISC | Current-ish exploratory and generalization telemetry | Unknown; reports may include false positives | 9 |
| AI-security scanner JSON | Optional upstream evidence adapter | Tool finding, not ground truth | 9+ |

## IoT-23

The official IoT-23 description identifies 20 malware captures and three benign device captures. It provides individual scenario downloads and labeled Zeek `conn.log` flows, which lets this project avoid downloading the full 20+ GB archive. Labels were created through manual analysis and rule-based matching, so they remain documented annotations rather than infallible truth.

Official references:

- [Stratosphere Laboratory IoT-23 dataset page](https://www.stratosphereips.org/datasets-iot23)
- [IoT-23 v1.0.0 DOI record](https://doi.org/10.5281/zenodo.4743746)

### Selected scenarios

1. **First pipeline: `CTU-IoT-Malware-Capture-34-1` (Mirai).** The official summary lists 1,923 benign, 6,706 C&C, 14,394 DDoS, and 122 horizontal-scan flows. This is small enough for local iteration while exercising multiple labels.
2. **Additional malicious scenario: `CTU-IoT-Malware-Capture-8-1` (Hakai).** The official summary lists 2,181 benign and 8,222 C&C flows. It provides a different malware scenario and manageable scale.
3. **Benign scenario: `CTU-Honeypot-Capture-4-1` (Philips Hue).** This supplies traffic from a real benign IoT device according to the dataset documentation.

Before download, the implementation must confirm each current individual-scenario URL, record the retrieval date, and capture checksums. If an individual artifact or terms cannot be verified, stop rather than substituting a similarly named file.

The Capture 34-1 scenario page currently states that authorization from the Stratosphere Lab is required to use its files. The repository therefore contains only a synthetic Zeek fixture and an adapter; it does not contain or fetch the official artifact. Once the owner supplies authorization and the file locally, the documented command can create the real normalized outputs.

### Initial use

- Phase 2 uses only Capture 34-1 to prove parsing, schema validation, data quality, and reproducible Parquet output. The parser and writer are validated against `data/fixtures/iot23/conn.log.labeled`; the real-file step remains pending authorization.
- Phase 3 may use its labels for baseline mechanics, but reports must call this an in-scenario experiment.
- Later evaluation adds Capture 8-1 and the benign capture with scenario-aware splits.
- Label and scenario identifiers are prohibited from the feature matrix.
- Raw packet capture and malware binaries are unnecessary for the initial research question and must not be downloaded.

### Leakage controls

- Do not randomly split individual rows as the only reported evaluation.
- Group by capture and, where possible, connection/session or time window.
- Fit encoders, imputers, scalers, thresholds, and models only on training data.
- Keep `label`, `detailed-label`, scenario name, filenames, and post-hoc analyst fields out of features.
- Report results by scenario and class; later held-out-scenario results are the generalization test.
- Deduplicate before splitting so the same flow cannot appear on both sides.

## CTU-13

CTU-13 is the first genuine third-party dataset used by this repository. The authoritative
Stratosphere description documents thirteen 2011 botnet scenarios, manually labeled flows, and
bidirectional Argus/NetFlow-style text artifacts in each scenario's
`detailed-bidirectional-flow-labels` directory. The Stratosphere dataset overview publishes the
dataset under Creative Commons Attribution (CC-BY); the scenario README also permits use with
attribution. The implementation acquires only the labeled text flow file—never the malware
executable or a packet capture.

Official references:

- [Stratosphere CTU-13 dataset description](https://www.stratosphereips.org/datasets-ctu13)
- [Stratosphere dataset overview and CC-BY statement](https://www.stratosphereips.org/datasets-overview)
- [Authoritative Scenario 11 directory](https://mcfp.felk.cvut.cz/publicDatasets/CTU-Malware-Capture-Botnet-52/)
- [Scenario 11 labeled bidirectional flow file](https://mcfp.felk.cvut.cz/publicDatasets/CTU-Malware-Capture-Botnet-52/detailed-bidirectional-flow-labels/capture20110818-2.binetflow)
- [Scenario 47 labeled bidirectional flow file](https://mcfp.felk.cvut.cz/publicDatasets/CTU-Malware-Capture-Botnet-47/detailed-bidirectional-flow-labels/capture20110816.binetflow)
- [Scenario 53 labeled bidirectional flow file](https://mcfp.felk.cvut.cz/publicDatasets/CTU-Malware-Capture-Botnet-53/detailed-bidirectional-flow-labels/capture20110819.binetflow)
- [Scenario 45 labeled bidirectional flow file](https://mcfp.felk.cvut.cz/publicDatasets/CTU-Malware-Capture-Botnet-45/detailed-bidirectional-flow-labels/capture20110815.binetflow)
- [Scenario 51 labeled bidirectional flow file](https://mcfp.felk.cvut.cz/publicDatasets/CTU-Malware-Capture-Botnet-51/detailed-bidirectional-flow-labels/capture20110818.binetflow)

### First validation slice

- **Scenario:** `CTU-Malware-Capture-Botnet-52` (Scenario 11, RBot), using
  `capture20110818-2.binetflow`.
- **Acquisition:** 14,596,615 bytes; SHA-256
  `cee542d4b5efe4fa1cd59b87ece5aaea9a13d8f0abe56cd07cee31590736428c`.
- **Validation:** 107,251 rows accepted, zero rejected rows, zero duplicate source rows.
- **Coarse label counts:** 8,164 malicious (`From-Botnet*`), 2,709 benign
  (`From-Normal*`), and 96,378 unknown. `Background`, `To-Botnet`, and `To-Normal` are not
  treated as benign or malicious by the adapter.
- **Artifacts:** the ignored local output directory is
  `data/processed/ctu13_scenario_11/` (`events.parquet`, `quality_report.json`, and
  `dataset_manifest.json`). The manifest records the source URL, checksum, scenario, terms,
  adapter/transformation versions, and counts.

### Scenario-aware Phase 3 corpus

To make a supervised baseline evaluation defensible, two additional labeled text-flow scenarios
were acquired from their authoritative per-scenario directories. No packets or executables were
downloaded:

| Split | Scenario | Rows | Known labels used for supervision | SHA-256 |
|---|---|---:|---:|---|
| Train | `CTU-Malware-Capture-Botnet-52` (Scenario 11) | 107,251 | 10,873 | `cee542d4b5efe4fa1cd59b87ece5aaea9a13d8f0abe56cd07cee31590736428c` |
| Validation | `CTU-Malware-Capture-Botnet-46` (Scenario 5) | 129,832 | 5,561 | `ef5c9ed6895d4ca5aec723449dae30054ccd1f6b091713a52ffcb681ff78a02c` |
| Test | `CTU-Malware-Capture-Botnet-48` (Scenario 7) | 114,077 | 1,732 | `df0b5338190b967bd340a0d6c1bb3c34d1bbfb4b7ffa764c2dd26f77f1a26680` |

Unknown rows are retained in normalized artifacts and rule scoring, but excluded from supervised
training and metrics. The test scenario is not used for feature or threshold selection. This is a
single three-scenario experiment, not a claim of broad CTU-13 generalization.

The adapter preserves the raw source label, Argus direction/state/TOS fields, source addresses
(including non-IP MAC addresses), source line identity, scenario identity, and the timezone
assumption (`Europe/Prague`, converted to UTC). Source labels are dataset ground truth annotations;
they are not AegisTrace detections or incident dispositions.

The separate implementation lives in `src/aegistrace/ingestion/ctu13.py` and is intentionally not
a format branch inside the IoT-23 Zeek adapter. The Phase 3 split and model result are explicitly
bounded to the three named scenarios; no broad generalization result is claimed.

### Validation-only detector-improvement corpus

The focused Phase 3 improvement run preserves scenario boundaries while adding Scenario 47 to
training and Scenario 53 to validation. It does not load or tune against the sealed Scenario 7
capture:

| Split | Scenario | Accepted rows | Known labels | Unknown | SHA-256 |
|---|---|---:|---:|---:|---|
| Train | `CTU-Malware-Capture-Botnet-52` (Scenario 11) | 107,251 | 10,873 | 96,378 | `cee542d4b5efe4fa1cd59b87ece5aaea9a13d8f0abe56cd07cee31590736428c` |
| Train | `CTU-Malware-Capture-Botnet-47` (Scenario 6) | 558,912 | 12,101 | 546,811 | `801800eeda9a5a44868b1e3e492f93dc6d52b5d14566c1d8431c9e85d0d2adaa` |
| Validation | `CTU-Malware-Capture-Botnet-46` (Scenario 5) | 129,832 | 5,561 | 124,271 | `ef5c9ed6895d4ca5aec723449dae30054ccd1f6b091713a52ffcb681ff78a02c` |
| Validation | `CTU-Malware-Capture-Botnet-53` (Scenario 12) | 325,471 | 9,783 | 315,688 | `1098f0addacedc321c7baefad63ef0d9a0f26630d0155087d37e8da770dd9f2e` |

Scenario 47 has seven invalid records preserved in its quality report and excluded from the
accepted-row table. Only labeled text flows were acquired; no packet captures or executables were
downloaded. The resulting diagnostic is validation evidence for feature and policy selection, not a
final held-out or production result.

### Cross-scenario model-stability validation corpus

The operating-point stability pass keeps Scenarios 11 and 47 in training and adds two licensed,
scenario-separated validation captures: Scenario 45 (Scenario 4) and Scenario 51 (Scenario 10).
Scenario 7 remains sealed and is not loaded, scored, or used for threshold selection. Supervised
models score only authoritative `Normal`/`Botnet` rows; the larger `Background`/`To-*` population
remains unknown and is not converted to benign ground truth.

| Split | Scenario | Accepted rows | Known labels | Unknown | SHA-256 |
|---|---|---:|---:|---:|---|
| Validation | `CTU-Malware-Capture-Botnet-46` (Scenario 5) | 129,832 | 5,561 | 124,271 | `ef5c9ed6895d4ca5aec723449dae30054ccd1f6b091713a52ffcb681ff78a02c` |
| Validation | `CTU-Malware-Capture-Botnet-53` (Scenario 12) | 325,471 | 9,783 | 315,688 | `1098f0addacedc321c7baefad63ef0d9a0f26630d0155087d37e8da770dd9f2e` |
| Validation | `CTU-Malware-Capture-Botnet-45` (Scenario 4) | 1,121,072 | 27,775 | 1,093,297 | `30353fcffe971e97839ccffaa1675535490420f1ba1f65e5c90f6a815a8ab2c0` |
| Validation | `CTU-Malware-Capture-Botnet-51` (Scenario 10) | 1,309,781 | 122,157 | 1,187,624 | `840a7030d57cb965a4e6e19c61e89b20647a4aefe5608c2da90623710e7cd74f` |

The reproducibility artifact is `data/evaluation/phase3_model_stability/stability_summary.json`;
the cached runner reuses immutable `1.1.0` behavioral Parquet artifacts and records each raw-source
checksum. This is validation evidence for model stability and operating-point selection, not a final
held-out or production result.

## Cowrie

Cowrie is an SSH/Telnet honeypot that emits JSON events. Its official event reference documents shared attributes such as event ID, UTC timestamp, session, source IP, and protocol, plus event-specific authentication, command, and file fields.

Official references:

- [Cowrie documentation](https://docs.cowrie.org/en/stable/README.html)
- [Cowrie output event reference](https://docs.cowrie.org/en/latest/OUTPUT.html)
- [Cowrie Docker guide](https://docs.cowrie.org/en/latest/docker/README.html)

### Initial safety policy

- Run a pinned Cowrie container only on an isolated local Docker network.
- Bind the test service to localhost on a non-privileged port; do not forward a router port or expose it publicly.
- Use only controlled test sessions owned by the builder.
- Do not enable Cowrie's experimental LLM backend; it is unrelated to AegisTrace triage and would confound provenance.
- Treat captured usernames, passwords, IPs, commands, downloads, and session recordings as sensitive.
- Do not commit raw Cowrie logs or downloaded files.

### Controlled cases

- a short benign-looking login/session;
- repeated failed authentication attempts;
- repeated successful test login followed by ordinary commands;
- an unusual command sequence represented only as inert text inside Cowrie;
- multiple related events sharing a session ID;
- malformed and truncated JSON fixtures derived from synthetic values.

Scenario intent is fixture metadata, not proof that an identical real-world sequence is benign or malicious.

## DShield / SANS Internet Storm Center

The official API is best-effort, supports JSON and other formats, can return HTTP 429, requests a contact-bearing custom User-Agent, and says its `sources` data may contain false positives and must not be used as a blocklist.

Official reference: [DShield API documentation](https://isc.sans.edu/api/)

Policy:

- defer automated ingestion until the canonical adapter contract is stable;
- select a narrow, documented endpoint and date window at implementation time;
- set a project contact User-Agent through local configuration, never hard-code personal data;
- honor `Retry-After` and stop polling after repeated errors;
- snapshot the response with retrieval time, request parameters, checksum, and API terms note;
- set `ground_truth_label` to unknown unless an independent, documented adjudication exists;
- do not train a malicious/benign classifier directly from DShield report presence;
- do not expose or recommend source IPs as a blocklist.

## External Scanner Findings

The eventual adapter accepts a documented, vendor-neutral internal representation of scanner JSON. A scanner result is a claim by an upstream tool. Preserve tool name/version, rule ID, severity, target reference, raw finding, and uncertainty; do not map it automatically to confirmed compromise.

No scanner product or schema is selected in Phase 0.

## Dataset Manifest

Every acquired or generated snapshot must record:

```text
dataset_name
dataset_version
source_url_or_generator
selected_scenarios
retrieved_or_generated_at
license_or_terms_note
files
sha256_per_file
record_count
time_range
label_distribution_if_applicable
adapter_version
transformation_version
parent_manifest_id_if_derived
```

Manifests may be committed when they contain no secrets or sensitive local paths. Raw datasets and derived bulk artifacts remain outside Git.

## Data Quality Report

Each ingestion run should emit counts for parsed, accepted, rejected, quarantined, and duplicate records plus missingness, unexpected categories, timestamp range, label distribution, and source-specific warnings. Counts must reconcile or the run fails.

## Redistribution and Privacy

- Link to official sources instead of republishing third-party raw files.
- Confirm source terms at acquisition time and record them in the manifest.
- Never commit credentials, raw public IP logs, honeypot downloads, malware samples, or personal contact data.
- Use documentation-safe synthetic examples in tests and screenshots.
