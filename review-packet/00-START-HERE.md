# AegisTrace — Review Packet

**Purpose of this packet.** To let an independent reviewer — human or automated — assess two
things: whether this project's *research contribution* is defensible, and whether the *engineering
work* is original and real rather than narrated.

Everything here is either original work by the author or a verbatim record of how the work was
done. Nothing in this packet is a claim about production use, deployment, security impact, or
commercial traction. **AegisTrace has never been deployed and has processed no real-world
security telemetry.**

---

## 1. What AegisTrace is

AegisTrace is a **defensive AI-security research project**. It is not a product and not a scanner.

Its research question, stated verbatim in `01-PROJECT/README.md`:

> Can a provenance-first, multi-model security system combine deterministic, supervised, anomaly,
> temporal, and reference-backed evidence to generate trustworthy investigation recommendations
> while clearly separating observed facts from inference and enabling a junior reviewer to handle
> basic triage without eliminating expert escalation?

The project's thesis is that the interesting research problem is **not** "can an LLM triage
alerts" — that area is crowded. It is whether **mutual blindness between two independently frozen
assessors**, with their *disagreement itself* as the escalation signal, produces a more trustworthy
triage than a single model. The provider-independent machinery for that experiment is built; the
run itself is deliberately **not** executed (see §6).

The system is built as a chain in which every conclusion must trace back to source evidence:

```text
Versioned telemetry
    -> source adapter -> canonical event + validation
    -> Parquet storage
    -> rules + specialist detectors
    -> deterministic finding + evidence bundle
    -> claim verification (epistemic taxonomy)
    -> independent LLM triage + deterministic adjudication
    -> tiered human review
    -> local investigation instrument
```

The LLM is advisory. It cannot create source evidence, overwrite detector output, or become the
final authority. **Nothing in the system acts on a system under observation.**

---

## 2. Status — what is and is not claimed

Read this before reading anything else. The project's own `docs/results.md` and
`docs/limitations.md` are stricter than this summary.

**Implemented and verified**

| Area | Evidence |
|---|---|
| Ingestion, canonical events, manifests | `src/aegistrace/ingestion/`, `docs/datasets.md` |
| Feature engineering, leakage controls | `src/aegistrace/features/`, `docs/features.md` |
| Deterministic rules + supervised detectors | `src/aegistrace/detection/` |
| Finding aggregation, evidence bundles | `src/aegistrace/detection/findings.py` |
| Claim verification against an epistemic taxonomy | `src/aegistrace/verification/` |
| Triage schemas, assessor isolation, deterministic adjudication | `src/aegistrace/triage/` |
| Tiered human review + append-only review store | `src/aegistrace/review/`, `src/aegistrace/storage/` |
| Local investigation instrument (no JavaScript, loopback only) | `src/aegistrace/ui/` |

**Not implemented, and stated as such inside the project**

- No LLM has ever been run. Nothing has been sent to any provider. Measured spend is **zero**.
- No fusion model. No production deployment. No real-world telemetry.
- Scenario 7 (the sealed final holdout) has **not** been opened.
- The UI's comparison view reports "AI assessment not available" because that is true.

**Measured at the time this packet was built**

```
pytest        600 passed, 96.00% coverage
ruff          All checks passed
mypy          Success: no issues found in 54 source files
guard ratchet 0 unexecuted guard raises (baseline 0)
```

Reproduce with `uv sync --all-groups` then `uv run pytest`, `uv run ruff check .`, `uv run mypy`.
The full gate, including six governance validators, is `.github/workflows/ci.yml`.

---

## 3. How to read this packet

| Folder | What it is | Why a reviewer should care |
|---|---|---|
| `00-START-HERE.md` | This file | Framing and claim boundary |
| `01-PROJECT/` | The complete repository: source, tests, docs, configs, CI, README, `MEMORY.md` | The work itself |
| `02-GOVERNANCE/` | All 44 GitHub issues with comments, 38 agent trace files, full commit history | The *process*: how defects were found, fixed, and proven |
| `03-RESEARCH-INPUTS/` | The landscape scan and the sources behind it | Evidence the gap claim was checked, not assumed |
| `04-AUDIT-SCRIPTS/` | Independent audit probes written to attack the project's own claims | Adversarial self-review |
| `99-INVENTORY.md` | Exactly what was excluded from this packet and how to regenerate it | Completeness and honesty |

**Suggested reading order for an automated reviewer**

1. `01-PROJECT/README.md` — the claim.
2. `01-PROJECT/docs/results.md` — every claim the project makes, its evidence tier, and what it
   does **not** support. Machine-checked against the experiment registry.
3. `01-PROJECT/docs/limitations.md` — the honest boundary.
4. `01-PROJECT/MEMORY.md` — 85 dated episodic entries recording decisions, reversals, and defects
   found in the project's own work. This is the single most informative artefact for judging
   whether the engineering process is genuine.
5. `02-GOVERNANCE/github-issues.md` — 44 issues preserving problem → cause → attempts → failures →
   solution → proof.
6. `01-PROJECT/docs/solution_knowledge.json` — validated reusable lessons only.

---

## 4. What to evaluate

**Originality of the contribution**

- Is "mutual blindness between independently frozen assessors, with disagreement as the escalation
  signal" a genuinely under-explored framing, or is it well covered by existing multi-agent LLM
  triage work? `03-RESEARCH-INPUTS/` contains the sources examined.
- Does the project's distinction between *kind admissibility* and *reference resolution* in claim
  verification add anything beyond standard provenance tracking?
- Is the tiered-review model (who is *qualified* to decide, explicitly **not** a severity and not a
  priority) a meaningful contribution or a re-labelling of existing triage tiers?

**Validity of the engineering**

- Are the tests real? Look for vacuous assertions — a recurring defect class this project
  explicitly hunts (`01-PROJECT/docs/solution_knowledge.json`). Every guard raise is required to be
  covered by a test or a ratchet fails the build.
- Are the frozen research contracts genuinely frozen? See `configs/phase3_frozen_policy.json` and
  `docs/experiment_registry.json`.
- Does the code do what the docs say? The docs are treated as claims that repository evidence must
  support, and stale documentation has repeatedly been treated as a defect.
- Is the append-only review store's guarantee real? See `src/aegistrace/storage/reviews.py` — note
  that it **detects** tampering rather than preventing it, and says so.

**Market validity**

- The project deliberately claims **no** market position. Assess whether the research framing could
  support one, and be sceptical: the honest answer may be that it is a research contribution
  rather than a product.

**Where to be most sceptical**

- `docs/results.md` — check each claim against the artifact named beside it.
- `01-PROJECT/MEMORY.md` — look for claims that later entries correct. There are several, recorded
  rather than hidden. Judge whether that is honesty or churn.
- The absence of an LLM run means the central experiment is **unproven**. Treat that as the largest
  open question, not as a completed result.

---

## 5. How the work was produced (and how to check it)

This project was developed by an AI agent under a written governance protocol
(`01-PROJECT/AGENTS.md`) with the repository owner as the sole decision authority. The protocol
requires that:

- every meaningful action links to an issue and emits a **redacted local trace record**
  (`02-GOVERNANCE/traces/`);
- research contracts are frozen before measurement and never tuned afterwards;
- defects in the project's own verification are treated as first-class issues;
- **no agent may autonomously change security boundaries, sealed-data policy, merge privileges, or
  governance rules.**

`02-GOVERNANCE/` exists so a reviewer can audit that discipline rather than take it on trust.
Judging the *process* is as much the point of this packet as judging the code.

---

## 6. Known open questions — stated plainly

1. **The central experiment has not been run.** `configs/triage_provider_freeze.json` records
   `BLOCKED_HUMAN`: every reachable provider advertises one mirrored catalogue, and the only two
   models verified working are the same family, so a two-assessor run would be one model twice —
   which would refute the independence the experiment rests on. The owner instructed deferral in
   exactly this case.
2. **Four issues await owner decisions** on public-contract or research-rule changes
   (see `02-GOVERNANCE/github-issues.md`: #34, #33, #32, #27).
3. **The claim verifier checks evidence *kind*, not whether a cited reference exists.** This is a
   known, filed, unfixed defect (#34), documented in the module itself. A fabricated identifier
   currently passes at full strength. It is latent because no production path generates claims yet.
4. **No external reference retrieval exists**, so `reference_backed_fact` claims have no live
   source to resolve against.

---

## 7. Data governance notice — read before sharing further

This packet contains **no third-party raw data** and **no raw public IP logs**, in line with the
project's own policy (`01-PROJECT/docs/datasets.md`, "Redistribution and Privacy").

- Excluded: `data/raw/` (2.0 GB of third-party CTU-13 captures) and the IP-bearing processed event
  tables. Both remain local only. See `99-INVENTORY.md`.
- Included: derived **feature** tables and summary JSONs, which contain no network addresses
  (verified by column inspection), plus small committed synthetic fixtures.

If you forward this packet, the derived evaluation artifacts still originate from third-party
datasets and should be handled under whatever terms apply to your review context.

---

## 8. Licence

MIT (`01-PROJECT/LICENSE`). Third-party datasets are **not** redistributed here.
