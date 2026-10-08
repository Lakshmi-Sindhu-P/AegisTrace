"""Offline demonstration of the audit spine: evidence -> two stubs -> tier -> open review.

This script proves the plumbing end to end and nothing more. Both assessors are deterministic
mechanical stubs, so the output is **not** a triage result and must never be reported as one. No
network is used and no model is configured; the two providers exist only to exercise the boundary.
The repository's freeze artifact is loaded and passed through unchanged, so its ``BLOCKED_HUMAN``
status governs the run exactly as it would in production.

Only ``--output`` is written.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from aegistrace.detection.evidence import build_evidence_bundle
from aegistrace.detection.findings import aggregate_findings
from aegistrace.detection.ml import emit_ml_detections
from aegistrace.schemas.events import (
    Ctu13FlowDetails,
    EventProvenance,
    SecurityEvent,
    SourceRecordRef,
    SourceType,
    event_id_for,
)
from aegistrace.schemas.findings import EvidenceBundle
from aegistrace.spine import run_spine
from aegistrace.triage.provider import ProviderDescriptor, ProviderKind, StubTriageProvider

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = "data/evaluation/triage_spine/offline_spine_demo.json"
FREEZE_PATH = REPO_ROOT / "configs" / "triage_provider_freeze.json"

WARNING = (
    "SYNTHETIC DEMONSTRATION. The assessors were mechanical stubs, not models. These are not "
    "triage results and must never be reported as such."
)

BASE = datetime(2026, 10, 8, 12, 0, tzinfo=UTC)
CREATED_AT = datetime(2026, 10, 8, 13, 0, tzinfo=UTC)


def _parse_created_at(value: str) -> datetime:
    """Parse a required ISO 8601 timestamp that must carry a timezone, normalized to UTC."""

    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(f"invalid ISO 8601 timestamp: {value}") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise argparse.ArgumentTypeError(f"timestamp must include a timezone: {value}")
    return parsed.astimezone(UTC)


def _event(offset_seconds: float, src_ip: str) -> SecurityEvent:
    observed_at = BASE + timedelta(seconds=offset_seconds)
    source = SourceRecordRef(
        source_type=SourceType.CTU13,
        source_dataset="CTU-13",
        scenario_id="11",
        dataset_version="1.0.0",
        source_event_id=f"{src_ip}@{offset_seconds}",
        raw_payload_reference="data/fixtures/ctu13/scenario_11.binetflow",
    )
    return SecurityEvent(
        event_id=event_id_for(source),
        source=source,
        observed_at=observed_at,
        ingested_at=observed_at,
        event_type="network_flow",
        provenance=EventProvenance(
            adapter_name="test_fixture",
            adapter_version="1.0.0",
            transformation_version="1.0.0",
            processed_at=observed_at,
        ),
        details=Ctu13FlowDetails(
            src_ip=src_ip,
            dst_ip="198.51.100.9",
            dst_port=80,
            protocol="tcp",
            source_label="flow=Background",
        ),
    )


def _bundle(src_ip: str) -> EvidenceBundle:
    events = tuple(_event(offset, src_ip) for offset in (0.0, 10.0, 20.0))
    scores = {event.event_id: 0.95 for event in events}
    detections = emit_ml_detections(
        events,
        scores,
        detector_name="ctu13_phase3_random_forest",
        detector_version="1.0.0",
        model_name="random_forest",
        feature_version="1.1.0",
        threshold=0.2,
        created_at=CREATED_AT,
    )
    finding = aggregate_findings(detections, events, created_at=CREATED_AT)[0]
    return build_evidence_bundle(finding, detections, events, created_at=CREATED_AT)


def _stub_descriptor(name: str, model_id: str) -> ProviderDescriptor:
    return ProviderDescriptor(
        name=name,
        model_id=model_id,
        model_family="offline stub, not a model",
        kind=ProviderKind.OFFLINE_STUB,
        requires_egress=False,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--created-at", required=True, type=_parse_created_at)
    parser.add_argument("--bundles", type=int, default=1)
    args = parser.parse_args()

    if args.bundles < 1:
        parser.error("--bundles must be at least 1")

    freeze = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    bundles = tuple(_bundle(f"10.0.0.{index + 1}") for index in range(args.bundles))

    analyst = StubTriageProvider(
        _stub_descriptor("stub-triage-analyst", "stub-analyst-1"), args.created_at
    )
    adjudicator = StubTriageProvider(
        _stub_descriptor("stub-expert-adjudicator", "stub-adjudicator-1"), args.created_at
    )

    records = run_spine(
        bundles=bundles,
        analyst_provider=analyst,
        adjudicator_provider=adjudicator,
        freeze=freeze,
        created_at=args.created_at,
    )

    rows = [
        {
            "spine_id": str(record.spine_id),
            "evidence_bundle_id": str(record.evidence_bundle_id),
            "finding_id": str(record.finding_id),
            "snapshot_digest": record.snapshot_digest,
            "tier": record.tier.tier.value,
            "machine_checks_passed": all(check.passed for check in record.tier.machine_checks),
            "review_count": len(record.review_history.reviews),
        }
        for record in records
    ]

    summary = {
        "warning": WARNING,
        "providers_configured": False,
        "network_egress": "none",
        "created_at": args.created_at.isoformat(),
        "freeze_version": str(freeze.get("freeze_version", "unknown")),
        "bundle_count": len(bundles),
        "record_count": len(rows),
        "records": rows,
    }

    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = REPO_ROOT / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"{'bundle_id':<38} {'snapshot':<12} {'tier':<32} {'checks':<6} reviews")
    for row in rows:
        checks = "pass" if row["machine_checks_passed"] else "fail"
        print(
            f"{row['evidence_bundle_id']:<38} {row['snapshot_digest'][:12]:<12} "
            f"{row['tier']:<32} {checks:<6} {row['review_count']}"
        )
    print(f"\nwarning: {WARNING}")
    print(f"wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
