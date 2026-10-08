"""Build a deterministic triage corpus from one CTU-13 binetflow fixture.

The pipeline is deliberately mechanical and label-free: parse the fixture, score every event with
one frozen constant, emit ML detections at a frozen threshold, aggregate them into findings,
snapshot each finding into an evidence bundle, and fingerprint those bundles into a corpus.
No label is read and no model is trained here, so the corpus is reproducible from the fixture
and the constants below alone.

Only ``--output`` is written.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from aegistrace.detection.evidence import build_evidence_bundle
from aegistrace.detection.findings import aggregate_findings
from aegistrace.detection.ml import emit_ml_detections
from aegistrace.ingestion.ctu13 import parse_ctu13_binetflow
from aegistrace.triage.corpus import build_corpus, write_corpus

DEFAULT_FIXTURE = Path("data/fixtures/ctu13/scenario_11.binetflow")
EVENT_SCORE = 0.95
THRESHOLD = 0.2
DETECTOR_NAME = "ctu13_phase3_random_forest"
DETECTOR_VERSION = "1.0.0"
MODEL_NAME = "random_forest"
FEATURE_VERSION = "1.1.0"


def _parse_created_at(value: str) -> datetime:
    """Parse an ISO 8601 timestamp that must carry a timezone, normalized to UTC."""

    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(f"invalid ISO 8601 timestamp: {value}") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise argparse.ArgumentTypeError("--created-at must include a timezone offset")
    return parsed.astimezone(UTC)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--created-at", required=True, type=_parse_created_at)
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--corpus-version", default="1.0.0")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    created_at = args.created_at

    parsed = parse_ctu13_binetflow(
        args.fixture,
        ingested_at=created_at,
        scenario_id=args.fixture.stem,
        raw_reference=args.fixture.as_posix(),
        report_generated_at=created_at,
    )
    events = tuple(parsed.events)
    scores = {event.event_id: EVENT_SCORE for event in events}
    detections = emit_ml_detections(
        events,
        scores,
        detector_name=DETECTOR_NAME,
        detector_version=DETECTOR_VERSION,
        model_name=MODEL_NAME,
        feature_version=FEATURE_VERSION,
        threshold=THRESHOLD,
        created_at=created_at,
    )
    findings = aggregate_findings(detections, events, created_at=created_at)
    bundles = tuple(
        build_evidence_bundle(finding, detections, events, created_at=created_at)
        for finding in findings
    )
    corpus = build_corpus(bundles, created_at=created_at, corpus_version=args.corpus_version)
    write_corpus(corpus, args.output)

    summary = {
        "output": args.output.as_posix(),
        "corpus_version": corpus.corpus_version,
        "corpus_digest": corpus.corpus_digest,
        "entry_count": len(corpus.entries),
        "event_count": sum(entry.event_count for entry in corpus.entries),
        "detection_count": sum(entry.detection_count for entry in corpus.entries),
    }
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
