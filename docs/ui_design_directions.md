# AegisTrace UI — Design Directions for Approval

**Status: PROPOSED — awaiting owner approval. No implementation may begin until one direction is chosen.**

Stack is already approved: FastAPI + static HTML, added incrementally and **parallel to research so it
never blocks it**. FastAPI is a new dependency; it is introduced only at implementation time.

## What this interface must not be

A generic cybersecurity dashboard: dark background, red/amber/green severity chips, a table of alerts,
a world map with attack arcs, a big number that says "threats blocked". That vocabulary implies
certainty and autonomous action, which is precisely what AegisTrace refuses to claim. It would
misrepresent the project.

## What it must embody

Five properties, all of which come from the research design rather than from taste:

| Property | Where it already exists in the system |
|---|---|
| Evidence provenance | `EvidenceReference`, `raw_payload_reference`, SHA-256 digests |
| Investigative traceability | `SecurityEvent` → `DetectionResult` → `Finding` → `EvidenceBundle` → `TriageAssessment` → `HumanReview` |
| Uncertainty | `UNKNOWN_INSUFFICIENT_EVIDENCE`, `MissingContext`, `limitations`, `FailedAssessment` |
| Independent verification | two mutually blind assessors; `TriageComparison`; disagreement as signal |
| Human judgment | `ReviewTier`, `HumanReview`, append-only `ReviewHistory` |

A useful test for any visual decision: **does this make it harder to overstate what is known?**

---

## Direction A — Chain of Custody

**Concept.** The interface is an evidence ledger. It reads like a case file or a lab notebook: each
claim is a numbered exhibit, and every exhibit carries its ancestry in the margin.

**Visual language.** Warm paper neutrals, not black. Hairline rules and generous margins. Deliberately
low-saturation so that the single accent colour — reserved for *"a human decision is required"* —
carries real weight. No severity colour at all.

**Typography.** A serif for prose and claim statements (Source Serif or Newsreader) so claims read as
assertions under scrutiny; a monospace for every identifier, digest, and timestamp (IBM Plex Mono);
a neutral sans for chrome only.

**Layout.** A numbered exhibit list is the primary surface. A persistent left rail is the *provenance
spine*: selecting an exhibit expands its full ancestry down to raw source records. Uncertainty is a
visible labelled slot — "not established" — never blank space.

**Signature interaction.** Select any claim and the spine re-roots to its evidence. The digest is
always visible, so a reader can verify nothing was silently altered.

**Optimises** credibility and auditability; ideal for the human-review and write-up workflow.
**Risks** feeling slow and archival for triage throughput.

---

## Direction B — Two Witnesses

**Concept.** Independence is the research variable, so it becomes the layout. Two assessors face each
other across a shared evidence rail, like a deposition transcript.

**Visual language.** Cool neutral ground; two voices distinguished by typographic texture rather than
competing colours. Divergence is marked on the rail between them, so disagreement has a physical
location on screen.

**Typography.** A humanist sans for interface (Inter); monospace for citations; each assessor rendered
at a distinguished weight/style so the two voices are never visually merged.

**Layout.** Split pane. Both assessors cite into the same central rail, and citations that both used
are shared anchors. Shared evidence collapses; contested evidence expands.

**Signature interaction.** Disagreement is the hero state, not an error. Where the assessors diverge,
the rail marks it and the case is promoted to Tier C; mutual abstention renders as an explicit
"insufficient evidence" card rather than an empty result.

**Optimises** the project's central claim and makes the A/B experiment legible; strongest research UI.
**Risks** narrow value when assessors agree, which will be most rows.

---

## Direction C — Investigation Bench

**Concept.** An instrument panel for an analyst: a working surface with a specimen tray, built for
sustained investigative use rather than for reporting.

**Visual language.** Light technical grid, dense but unhurried spacing, tabular numerals everywhere so
columns can be compared by eye. A persistent "tray" along the bottom holds the working set.

**Typography.** A grotesque for interface (Inter or Söhne); a tabular monospace (JetBrains Mono) for
all numerics so digits align.

**Layout.** Bundle-centric rather than alert-centric. The unit of work is an evidence bundle, not a
row in an alert table. Detail opens in place rather than in a modal, preserving context.

**Signature interaction.** Uncertainty renders as an interval or band rather than a point estimate
wherever a score is shown, and every score carries its model name because scores are not comparable
across models. Nothing is ever displayed as a bare confidence percentage.

**Optimises** daily investigative throughput and honest uncertainty display.
**Risks** closest of the three to conventional tooling; identity comes mostly from the uncertainty
treatment.

---

## Shared commitments (whichever is chosen)

- **Localhost-only.** Binds `127.0.0.1`; no external requests, no telemetry, no CDN. All assets local.
- **Read-only over evidence.** The UI never writes to detection data, never re-ranks, never auto-acts.
  The only write path is a `HumanReview`, which is append-only.
- **Never red/green alone.** Severity and disagreement are always encoded with text or shape as well
  as colour, so the interface survives colour-vision deficiency and greyscale printing.
- **WCAG 2.2 AA contrast** as a floor, visible focus states, full keyboard operation, semantic HTML.
- **Nothing renders as more certain than it is.** Abstention, missing context, and limitations are
  displayed as content, not hidden in a tooltip.
- **Accessible by default.** No motion required to understand state; no information conveyed by
  animation alone.

## Recommendation

**Direction B for the triage/comparison view** (it is the research contribution made visible) with
**Direction A's provenance spine adopted throughout** (it is the trust mechanism). Direction C's
tabular numerics and uncertainty bands are worth taking as techniques regardless of which shell wins.

If one shell must be chosen for a genuinely minimal first increment, I would build **A**, because the
provenance spine is load-bearing for every other view and the ledger metaphor cannot mislead.

## Open question for the owner

Which direction, or which combination? I will not finalise the visual direction without your approval,
and I will not begin implementation until you choose.
