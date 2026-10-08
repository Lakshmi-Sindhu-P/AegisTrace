"""Deterministic, label-free triage corpora over evidence bundles.

A triage corpus is the frozen input set for triage. It records only what a bundle *contains*
(identity, snapshot digest, and size), so a corpus can be rebuilt from the same bundles and compare
byte-identical across processes and machines. It deliberately has no field through which a
``GroundTruthLabel`` or any model output could enter: the corpus is evidence about evidence, and
mixing a research label into it would make the corpus unfalsifiable as a record.

Determinism rests on two rules:

* ``build_corpus`` sorts its entries, so shuffling the input bundles yields the same digest.
* ``corpus_digest`` hashes canonical JSON (sorted keys, compact separators) over the corpus version
  and the entries' content, excluding ``created_at``, which is provenance rather than content.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from uuid import UUID

from pydantic import Field, field_validator

from aegistrace.schemas.common import FrozenSchema, SchemaVersion, Sha256, normalize_utc
from aegistrace.schemas.findings import EvidenceBundle
from aegistrace.triage.snapshot import snapshot_digest

CORPUS_SCHEMA_VERSION = "1.0.0"
CORPUS_VERSION = "1.0.0"


class CorpusEntry(FrozenSchema):
    """One bundle's content-addressed fingerprint inside a triage corpus."""

    evidence_bundle_id: UUID
    finding_id: UUID
    snapshot_digest: Sha256
    event_count: int = Field(ge=0)
    detection_count: int = Field(ge=0)


class TriageCorpus(FrozenSchema):
    """An immutable, order-independent set of bundle fingerprints for triage."""

    schema_version: SchemaVersion = CORPUS_SCHEMA_VERSION
    corpus_version: SchemaVersion
    corpus_digest: Sha256
    created_at: datetime
    entries: tuple[CorpusEntry, ...] = Field(min_length=1)

    @field_validator("created_at")
    @classmethod
    def normalize_created_at(cls, value: datetime) -> datetime:
        return normalize_utc(value)


def _corpus_digest(corpus_version: str, entries: tuple[CorpusEntry, ...]) -> str:
    """Hash the corpus version and entry content as canonical JSON."""

    payload = {
        "corpus_version": corpus_version,
        "entries": [entry.model_dump(mode="json") for entry in entries],
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_corpus(
    bundles: Iterable[EvidenceBundle],
    *,
    created_at: datetime,
    corpus_version: str = CORPUS_VERSION,
) -> TriageCorpus:
    """Build a triage corpus whose digest does not depend on input ordering.

    Raises ``ValueError`` when ``bundles`` is empty, because an empty corpus would silently claim
    that a triage run had no input rather than that it was never built.
    """

    ordered = sorted(
        bundles,
        key=lambda bundle: (str(bundle.evidence_bundle_id), str(bundle.finding_id)),
    )
    if not ordered:
        raise ValueError("cannot build a triage corpus from an empty bundle sequence")

    entries = tuple(
        CorpusEntry(
            evidence_bundle_id=bundle.evidence_bundle_id,
            finding_id=bundle.finding_id,
            snapshot_digest=snapshot_digest(bundle),
            event_count=len(bundle.event_summaries),
            detection_count=len(bundle.detection_ids),
        )
        for bundle in ordered
    )
    return TriageCorpus(
        corpus_version=corpus_version,
        corpus_digest=_corpus_digest(corpus_version, entries),
        created_at=created_at,
        entries=entries,
    )


def write_corpus(corpus: TriageCorpus, path: str | Path) -> Path:
    """Write a corpus as canonical JSON, creating the parent directory when needed."""

    destination = Path(path)
    canonical = json.dumps(
        corpus.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(canonical + "\n", encoding="utf-8")
    return destination


__all__ = [
    "CORPUS_SCHEMA_VERSION",
    "CORPUS_VERSION",
    "CorpusEntry",
    "TriageCorpus",
    "build_corpus",
    "write_corpus",
]
