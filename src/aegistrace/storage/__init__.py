"""Durable, append-only storage for human-review history.

This package is the persistence layer the UI was missing. It exists to answer one question: *where
does a human decision actually go?* Until now the answer was "nowhere", and the decision form
refused rather than pretend otherwise.

The approved direction (``MEMORY.md``, ``docs/architecture.md``) is Parquet and DuckDB initially,
with human review beginning in DuckDB for a single local user. This package implements exactly that
and nothing more.

Scope, stated plainly: this is a **single-user, local, single-writer** store. DuckDB is an embedded
analytical database, not a concurrent application server, and nothing here pretends otherwise.
PostgreSQL stays deferred until concurrency or durable multi-process workflow actually requires it.
"""

from __future__ import annotations

__all__: list[str] = []
