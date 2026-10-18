# Review Packet — committed copy

This directory holds the **non-repository content** of the AegisTrace review packet so that it is
version-controlled and diffable. The built, self-contained packet that can be handed to a reviewer
or an analysis agent is `AegisTrace-Review-Packet.zip` (3.0 MB).

Read [`00-START-HERE.md`](00-START-HERE.md) first — it is the reviewer briefing, and it is
byte-identical to the copy inside the zip.

## Why this is not the whole packet

The built packet bundles a frozen copy of the repository as `01-PROJECT/`. Here that copy would be
redundant: this repository **is** that content, at the commit the packet was built from
(`2ccac9a`). So this directory holds only the packet's additions.

Three further things present in the built packet are deliberately **not** committed here:

| Not committed | Why |
|---|---|
| `02-GOVERNANCE/traces/` (38 records) | `.gitignore` declares this material *"Local agent execution provenance (redacted, machine-readable, **never committed**)"*. Committing it would change a stated data-handling rule, which `AGENTS.md` reserves to the owner. |
| `02-GOVERNANCE/issue-notes/` | Same origin (`.context/`), same rule. |
| `03-RESEARCH-INPUTS/*.pdf`, `*.html` | Downloaded third-party documents (a NIST publication, publisher pages). Committing payloads rather than links conflicts with the redistribution policy in `docs/datasets.md`. The original analysis that cites them — `aegistrace-landscape-scan.md` — **is** committed. |

## Not in git at all

`AegisTrace-Evidence-Archive.zip` (734 MB — 29 Parquet feature tables and 16 summary JSONs) exceeds
GitHub's 100 MB per-file limit and is a build output rather than review material. Its SHA-256 and
size are recorded in `LOCAL-ARTIFACTS.sha256` so it can be verified without being stored. It is a
reproducibility aid; the readable result evidence it backs is committed in the packet zip and in
`docs/`.

## Contents

```
README.md                     this file
00-START-HERE.md              reviewer briefing: what AegisTrace claims, what it does not
99-INVENTORY.md               every packet exclusion, with its size and regeneration command
MANIFEST.sha256               SHA-256 of every file in this directory
LOCAL-ARTIFACTS.sha256        SHA-256 + size of the local build outputs not stored in git
AegisTrace-Review-Packet.zip  the built packet (self-contained, includes 01-PROJECT/)
02-GOVERNANCE/
  github-issues.md            all 44 issues with bodies and comments (309 KB)
  github-issues.json          the same, machine-readable
  git-history.txt             full commit history with messages and per-commit file stats
03-RESEARCH-INPUTS/
  aegistrace-landscape-scan.md
04-AUDIT-SCRIPTS/
  audit_negatives.py          probe that still runs against the current tree
  audit_probe.py              historical probe, pinned to a superseded commit (see its docstring)
```

## Rebuilding the packet

The packet is assembled from this repository plus the local `.context/` provenance tree. The
generator is deliberately not committed because it reads `.context/`, which must not be committed;
the build is a short sequence of `rsync` and `zip` steps described in
[`99-INVENTORY.md`](99-INVENTORY.md).

Verify this directory with:

```bash
shasum -a 256 -c MANIFEST.sha256
```
