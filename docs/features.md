# Phase 3A Feature Specification

**Status:** implemented and validated as `FEATURE_VERSION=1.0.0` for CTU-13 Argus flows.

The feature builder consumes only `Ctu13FlowDetails`. It never reads `ground_truth_label`, raw
labels, filenames, scenario IDs, or source record IDs when constructing the numeric matrix. The
event and scenario IDs remain metadata for traceability and grouped evaluation.

## Feature contract

| Feature(s) | CTU-13 source field(s) | Units / encoding | Missing behavior and rationale | Leakage risk |
|---|---|---|---|---|
| `duration_seconds`, `duration_missing` | `Dur` | seconds; binary indicator | Missing duration becomes 0 plus indicator. Duration describes flow behavior without using labels. | Low; verify timestamps are available before any future time-slice split. |
| `log_total_bytes`, `total_bytes_missing` | `TotBytes` | `log1p(bytes)`; binary indicator | Missing becomes 0 plus indicator. Log compression limits domination by very large flows. | Low; do not use post-event aggregates. |
| `log_packet_count`, `packet_count_missing` | `TotPkts` | `log1p(packets)`; binary indicator | Missing becomes 0 plus indicator. Captures flow volume. | Low. |
| `log_source_bytes`, `source_bytes_missing` | `SrcBytes` | `log1p(bytes)`; binary indicator | Missing becomes 0 plus indicator. Retains Argus source-side semantics. | Low. |
| `src_port_well_known`, `src_port_missing` | `Sport` | binary port `<=1023`; binary indicator | Missing is not treated as well-known. Captures endpoint role hints without using service labels. | Low; port behavior can be environment-specific. |
| `dst_port_well_known`, `dst_port_missing` | `Dport` | binary port `<=1023`; binary indicator | Missing is not treated as well-known. | Low. |
| `dst_port_http` | `Dport` | binary membership in `{80,443,8080}` | Missing maps to 0. Explicit, interpretable service-port hint. | Medium; not a label proxy by itself. |
| `dst_port_dns` | `Dport` | binary membership in `{53}` | Missing maps to 0. Explicit DNS-port hint. | Medium; not a label proxy by itself. |
| `protocol_tcp`, `protocol_udp`, `protocol_icmp`, `protocol_other`, `protocol_missing` | `Proto` | fixed one-hot flags | Unknown protocols use `other`; absent protocol uses `missing`. Prevents unseen categories from changing schema. | Low. |
| `direction_forward`, `direction_reverse`, `direction_bidirectional`, `direction_other`, `direction_missing` | `Dir` | fixed one-hot flags for `->`, `<-`, `<->` | Other Argus directions use `other`; absent uses `missing`. Preserves direction semantics without source labels. | Low. |
| `state_length`, `state_missing` | `State` | character count; binary indicator | Missing state becomes 0 plus indicator. Avoids a high-cardinality state vocabulary in the first baseline. | Low; state is source telemetry, not ground truth. |

The resulting 26-column vector is ordered and versioned in
`src/aegistrace/features/network.py`. Feature Parquet includes event/scenario/source IDs and
ground-truth labels for audit, but `FeatureDataset.matrix()` returns only numeric columns to model
callers. Unknown labels are not relabeled as benign.

## Behavioral feature family (`FEATURE_VERSION=1.1.0`)

**Status:** implemented and validated in the Phase 3 validation-only improvement experiment.

`src/aegistrace/features/behavioral.py` composes the 26 per-flow values with six
scenario-local behavioral values. It is called once per scenario; source hosts are keyed only for
aggregation and their addresses never enter the model matrix. Events are sorted by observed time,
and every aggregate uses prior flows only. Unknown-label rows therefore provide unlabeled context
without becoming supervised examples.

| Feature | Source fields / window | Units / missing behavior | Rationale and leakage review |
|---|---|---|---|
| `prior_source_connections_60s` | source address; prior 60 seconds | count, zero for no history | Captures burst/rate behavior. Does not use the current label or future rows. |
| `prior_unique_destinations_300s` | source and destination addresses; prior 300 seconds | cardinality, zero for no history; missing destinations use one explicit unknown bucket | Captures fan-out and host-level exploration without retaining raw addresses. |
| `prior_unique_destination_ports_300s` | source address and destination port; prior 300 seconds | cardinality, missing ports excluded | Captures service/port diversity. |
| `source_traffic_asymmetry` | `SrcBytes` / `TotBytes` for current flow | numeric ratio; zero when unavailable plus missing flag | Describes directionality/response imbalance; no label-derived field. |
| `source_traffic_asymmetry_missing` | same fields | binary indicator | Prevents missingness being silently interpreted as benign. |
| `prior_repeated_short_connections_300s` | source address and `Dur`; prior 300 seconds | count of prior flows with duration `<=1s` | Captures repeated short-lived connection behavior; threshold is documented and deterministic. |

The feature builder rejects mixed-scenario input so histories cannot cross a capture boundary. The
aggregate family can still encode environment-specific host behavior, so it requires scenario-held-
out validation and a leakage review before any final-test claim.

## Why this is an intentionally small baseline

The first feature set is designed for inspection and failure analysis, not maximum predictive
power. It uses flow volume, duration, endpoint-port hints, protocol, direction, and a compact state
summary. It omits raw IP addresses, source labels, filenames, scenario IDs, timestamps as calendar
features, and any feature derived from the target. More features require a new version, leakage
review, tests, and a new experiment record.

## Causal host/time representation (`FEATURE_VERSION=1.2.0`)

**Status:** implemented and validated as a training/validation-only representation experiment;
it is not a production detector policy.

Version `1.2.0` composes the complete `1.1.0` vector unchanged and adds prior-only host/time
features. The extension was introduced separately so the accepted `1.1.0` artifacts remain
reproducible. Events are sorted by observed UTC time inside one scenario; all values below are
computed before the current flow and use the current source host only. Unknown rows can provide
unlabeled context but never enter supervised fitting or metrics.

| Feature(s) | Source fields / window | Units and missing behavior | Rationale and leakage risk |
|---|---|---|---|
| `prior_source_connections_300s` | source host; prior 300 seconds | count, zero when no prior flow | Captures slower beacons and host activity beyond the existing 60-second rate. |
| `prior_unique_destinations_60s` | source/destination; prior 60 seconds | cardinality, zero when empty; missing destination uses an explicit bucket | Captures short-window fan-out without exposing addresses. |
| `prior_unique_destination_ports_60s` | source/destination port; prior 60 seconds | cardinality, missing ports excluded | Captures rapid service/port diversity. |
| `prior_unique_protocols_300s` | source/protocol; prior 300 seconds | cardinality; missing protocol uses an explicit bucket | Captures protocol diversity while avoiding categorical label proxies. |
| `prior_destination_reuse_300s` | source/destination; prior 300 seconds | prior count for the current destination | Distinguishes repeated beacon destinations from first contact; current flow is not counted. |
| `prior_destination_port_reuse_300s` | source/destination port; prior 300 seconds | prior count for the current port, zero if missing | Represents repeated service targeting without using source labels. |
| `prior_short_connections_60s` | source and `Dur`; prior 60 seconds | count of prior `Dur <= 1s` flows | Captures bursty short-connection behavior at a second time scale. |
| `log_prior_total_bytes_300s`, `prior_total_bytes_300s_missing` | `TotBytes`; prior 300 seconds | `log1p(bytes)` plus an indicator when no prior byte total was observed | Adds host-level prior volume without allowing missing totals to look benign. |
| `log_prior_packet_count_300s`, `prior_packet_count_300s_missing` | `TotPkts`; prior 300 seconds | `log1p(packets)` plus an observation indicator | Adds host-level prior packet activity with explicit missingness. |
| `log_seconds_since_prior_source_flow`, `seconds_since_prior_source_flow_missing` | `StartTime`; previous flow for the source host | `log1p(seconds)` plus a first-flow indicator | Represents recency without using absolute timestamps or future rows. |

Raw addresses are aggregation keys only and are never columns in the model matrix. Scenario IDs,
filenames, source labels, and ground-truth labels are metadata only. The implementation and causal
window audit are in `src/aegistrace/features/causal.py`; the validation artifact is the ignored
`data/evaluation/phase3_causal_representation/causal_summary.json`.
