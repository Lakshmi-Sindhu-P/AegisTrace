"""The exact input an assessor is allowed to see.

Mutual blindness between the two frozen assessors is the project's experimental variable, so it has
to be enforced somewhere concrete rather than asserted. It is enforced here, by construction:

* :func:`input_snapshot` accepts **only** an :class:`~aegistrace.schemas.findings.EvidenceBundle`.
  There is no parameter through which another assessment, a prior conclusion, a research label, or a
  model score from a later stage could enter. The type signature is the enforcement.
* The snapshot is a canonical, key-sorted JSON rendering, so :func:`snapshot_digest` is stable
  across processes and machines. Two assessors given the same bundle therefore receive
  byte-identical input, which is what makes their disagreement attributable to the assessors rather
  than to the input.

**Scope of this guarantee, stated honestly.** This proves what the project feeds an assessor. It
does not and cannot prove what a third-party provider does with data it receives, nor that a
provider is stateless. Those are provider-governance questions, recorded when a provider is
selected.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from aegistrace.schemas.findings import EvidenceBundle

#: The complete set of keys an assessor may observe. Kept explicit so a test can assert that the
#: snapshot contains nothing beyond the evidence bundle itself.
SNAPSHOT_FIELDS: frozenset[str] = frozenset(EvidenceBundle.model_fields)


def input_snapshot(bundle: EvidenceBundle) -> dict[str, Any]:
    """Return the canonical evidence snapshot an assessor is permitted to receive."""

    return bundle.model_dump(mode="json")


def canonical_snapshot_json(bundle: EvidenceBundle) -> str:
    """Render the snapshot as canonical JSON: sorted keys, no incidental whitespace."""

    return json.dumps(
        input_snapshot(bundle), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )


def snapshot_digest(bundle: EvidenceBundle) -> str:
    """Content-address the snapshot so both assessors provably received identical input."""

    return hashlib.sha256(canonical_snapshot_json(bundle).encode("utf-8")).hexdigest()


def bundle_evidence_ids(bundle: EvidenceBundle) -> frozenset[str]:
    """The identifiers an assessment is allowed to cite, drawn only from the bundle."""

    ids = {str(bundle.finding_id)}
    ids.update(str(detection_id) for detection_id in bundle.detection_ids)
    ids.update(str(summary.event_id) for summary in bundle.event_summaries)
    return frozenset(ids)


__all__ = [
    "SNAPSHOT_FIELDS",
    "bundle_evidence_ids",
    "canonical_snapshot_json",
    "input_snapshot",
    "snapshot_digest",
]
