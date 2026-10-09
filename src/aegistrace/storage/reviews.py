"""A durable, append-only store for human-review history, backed by DuckDB.

Why this module exists
----------------------
The local UI could present a decision form but had nowhere to put a decision. It refused rather
than silently discarding one. This module is the place decisions go.

The one property everything here serves is **append-only**. A correction must extend the record,
never rewrite it, so the history shows what was believed and when - not merely the latest answer. A
review that could be edited in place would destroy the only thing an evidence-custody record is for.

How append-only is enforced, and its honest limits
--------------------------------------------------
Three mechanisms, in descending order of strength:

1. **No mutation code path exists.** This module issues only ``CREATE``, ``INSERT`` and ``SELECT``.
   There is no function that updates or deletes a review, so no caller can ask for one. A test
   asserts this by inspecting the module's SQL rather than trusting the sentence you are reading.
2. **``review_id`` is the primary key.** A duplicate review cannot be inserted even if the caller
   bypasses the Python-level check, because the database refuses it.
3. **Every read revalidates the whole chain.** ``load_history`` reconstructs a
   :class:`~aegistrace.schemas.review.ReviewHistory`, whose ``model_validator`` re-checks that the
   chain is linear, that no identity repeats, and that every review shares one subject. A database
   edited by hand, or by a future version with a bug, therefore fails loudly on read instead of
   presenting a forked lineage as authoritative.

The limit, stated rather than glossed: DuckDB itself does not make a table immutable. A user with
the ``duckdb`` CLI can still issue ``UPDATE``/``DELETE`` against the file. Mechanism 3 is what
catches that - the tampering does not go unnoticed, it just cannot be *prevented* by an embedded
analytical database. Preventing it is what PostgreSQL with restricted roles would buy, and that is
deferred until it is genuinely needed.

The write/read symmetry matters
-------------------------------
The project's most recurring defect has been a guarantee enforced on the **write** path (a helper)
but bypassed on the **read** path (``model_validate`` of stored data). The repair everywhere has
been to move the guarantee onto the schema so both paths get it. This module follows that: appends
go through :func:`~aegistrace.review.history.append_review` *and* the resulting history is
constructed from fields, so the schema's validators run; reads construct the schema directly, so the
same validators run again. The store adds a uniqueness constraint and an ordering column, and
contributes no new rule of its own that the schema does not already enforce.
"""

from __future__ import annotations

import contextlib
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from aegistrace.review.history import append_review
from aegistrace.schemas.review import HumanReview, ReviewHistory

#: Table and sequence names. Module-level so tests and migrations refer to one spelling.
REVIEW_TABLE = "human_review"
REVIEW_SEQUENCE = "human_review_sequence"
HEAD_JOURNAL_TABLE = "review_head_journal"
HEAD_JOURNAL_SEQUENCE = "review_head_sequence"

#: Columns written by :meth:`ReviewStore.append_review`, in schema order. The sequence column is
#: deliberately excluded: it is arrival bookkeeping, not part of the review, and it is exactly the
#: kind of field the identity rule excludes from an entity's identity.
_COLUMNS: tuple[str, ...] = (
    "schema_version",
    "review_id",
    "subject_triage_id",
    "subject_role",
    "reviewer_ref",
    "tier",
    "decision",
    "notes",
    "reviewed_at",
    "escalation_state",
    "final_disposition",
    "supersedes_review_id",
)

_CREATE_TABLE = f"""
CREATE TABLE IF NOT EXISTS {REVIEW_TABLE} (
    sequence            BIGINT PRIMARY KEY,
    schema_version      VARCHAR NOT NULL,
    review_id           VARCHAR NOT NULL UNIQUE,
    subject_triage_id   VARCHAR NOT NULL,
    subject_role        VARCHAR NOT NULL,
    reviewer_ref        VARCHAR NOT NULL,
    tier                VARCHAR NOT NULL,
    decision            VARCHAR NOT NULL,
    notes               VARCHAR NOT NULL,
    reviewed_at         VARCHAR NOT NULL,
    escalation_state    VARCHAR NOT NULL,
    final_disposition   VARCHAR NOT NULL,
    supersedes_review_id VARCHAR
)
"""

#: ``reviewed_at`` is stored as an ISO-8601 **string**, not as a DuckDB timestamp, and the reason is
#: a defect this module's own read path caught on its first run. DuckDB's ``TIMESTAMP`` is
#: timezone-naive, so a UTC-aware ``reviewed_at`` came back naive and the schema rejected it
#: ("timestamp must include a timezone"). ``TIMESTAMPTZ`` is the obvious alternative but DuckDB
#: requires the ``pytz`` package to read it, which would add a dependency to preserve a value we can
#: already round-trip exactly. The string form is the schema's own canonical serialization, parsed
#: back by the same field validator that produced it, so no conversion and no dependency is
#: introduced. The cost is that time-range queries need a cast; that is a fair trade for exactness.
_EXPECTED_TYPES: dict[str, str] = {
    "sequence": "BIGINT",
    "schema_version": "VARCHAR",
    "review_id": "VARCHAR",
    "subject_triage_id": "VARCHAR",
    "subject_role": "VARCHAR",
    "reviewer_ref": "VARCHAR",
    "tier": "VARCHAR",
    "decision": "VARCHAR",
    "notes": "VARCHAR",
    "reviewed_at": "VARCHAR",
    "escalation_state": "VARCHAR",
    "final_disposition": "VARCHAR",
    "supersedes_review_id": "VARCHAR",
}

_CREATE_SEQUENCE = f"CREATE SEQUENCE IF NOT EXISTS {REVIEW_SEQUENCE} START 1"

#: An append-only journal of each subject's current head. Written once per append, never updated.
#:
#: Why it exists: the chain validators check the *shape* of a history, not its *completeness*. A
#: two-review chain with its newest row deleted is a one-review chain, and a one-review chain whose
#: single entry supersedes nothing is perfectly valid - so deleting the newest row left a shorter
#: history that validated cleanly. Recording the expected head and count at each append makes that
#: deletion visible: the journal still says two reviews, the table shows one, and the mismatch is
#: refused. This gap was found by probing the store, not by reasoning about it.
#:
#: The residual, stated rather than hidden: an editor who rewrites the journal consistently with the
#: reviews can still defeat this, and one who rewrites the whole database defeats it entirely.
#: Detecting that needs an anchor outside the database - a signed manifest, or a database whose
#: roles forbid writes. DuckDB offers neither, so this is detection of accidental or partial
#: corruption plus the common tampering case, not a cryptographic guarantee.
_CREATE_HEAD_JOURNAL = f"""
CREATE TABLE IF NOT EXISTS {HEAD_JOURNAL_TABLE} (
    sequence            BIGINT PRIMARY KEY,
    subject_triage_id   VARCHAR NOT NULL,
    head_review_id      VARCHAR NOT NULL,
    review_count        BIGINT NOT NULL
)
"""

_EXPECTED_HEAD_TYPES: dict[str, str] = {
    "sequence": "BIGINT",
    "subject_triage_id": "VARCHAR",
    "head_review_id": "VARCHAR",
    "review_count": "BIGINT",
}


class ReviewStoreError(RuntimeError):
    """Raised when the store cannot be opened, read, or appended to.

    One error type for every failure, so a caller that catches it catches all of them. A caller
    must never be able to tell "the store is fine and this subject has no reviews" from "the store
    is broken" by receiving an empty history for both - the first is an empty history, the second
    is this exception.
    """


class ReviewStore:
    """An append-only DuckDB-backed store of human-review history.

    Open with :meth:`open`, use as a context manager, and treat the instance as a connection to one
    local database file. One writer at a time: this is a single-user local store by design.
    """

    def __init__(self, path: Path, connection: Any) -> None:
        self._path = path
        self._connection = connection

    # -- lifecycle ---------------------------------------------------------------------------

    @classmethod
    def open(cls, path: str | Path) -> ReviewStore:
        """Open (creating if absent) the review store at ``path``.

        The **parent directory must already exist**. DuckDB will happily create a database file at a
        mistyped path, which would silently start an empty store and make "no reviews yet"
        indistinguishable from "you pointed me at the wrong place" - the same class of defect as an
        artifact read that reports success over a file it never found. Requiring the directory makes
        that mistake a loud failure.
        """

        resolved = Path(path).expanduser().resolve()
        if not resolved.parent.is_dir():
            raise ReviewStoreError(
                f"review store directory does not exist: {resolved.parent}. "
                f"Create it first; refusing to start an empty store at a mistyped path."
            )

        try:
            import duckdb
        except ModuleNotFoundError as error:  # exercised by patching the import, see the tests
            raise ReviewStoreError(
                "the storage extra is not installed; install it with: pip install -e '.[storage]'"
            ) from error

        # ``connection`` is bound to None before the try so the failure handlers below can never
        # reference an unbound name. ``duckdb.connect`` is itself inside the try and is the most
        # likely step to fail (a path that is a directory, an unreadable file, a corrupt database),
        # and calling ``connection.close()`` in the handler for that case used to raise
        # ``UnboundLocalError`` - which masked the real cause AND escaped the single error type this
        # module promises. A caller catching ``ReviewStoreError`` saw an ``UnboundLocalError``
        # instead. Found by probing, not by reading.
        connection: Any = None
        try:
            connection = duckdb.connect(str(resolved))
            connection.execute(_CREATE_TABLE)
            connection.execute(_CREATE_HEAD_JOURNAL)
            connection.execute(_CREATE_SEQUENCE)
            connection.execute(f"CREATE SEQUENCE IF NOT EXISTS {HEAD_JOURNAL_SEQUENCE} START 1")
            cls._require_expected_schema(connection, resolved)
        except ReviewStoreError:
            if connection is not None:
                connection.close()
            raise
        except Exception as error:  # duckdb raises its own error hierarchy
            if connection is not None:
                connection.close()
            raise ReviewStoreError(
                f"could not open the review store at {resolved}: {error}"
            ) from error
        return cls(resolved, connection)

    @staticmethod
    def _require_expected_schema(connection: Any, resolved: Path) -> None:
        """Refuse to use a table whose shape is not the one this module writes.

        ``CREATE TABLE IF NOT EXISTS`` silently does nothing when a table of that name already
        exists, so a store created by an earlier version of this module would be used as though it
        matched. Reading it back through the current column list would then mis-assign fields - a
        wrong answer rather than an error, which is the failure mode this project treats as the
        worst kind. Comparing the actual types turns that into a loud refusal.
        """

        for table, expected in (
            (REVIEW_TABLE, _EXPECTED_TYPES),
            (HEAD_JOURNAL_TABLE, _EXPECTED_HEAD_TYPES),
        ):
            described = {
                str(row[0]): str(row[1]).upper()
                for row in connection.execute(f"DESCRIBE {table}").fetchall()
            }
            if described != expected:
                differing = sorted(
                    name
                    for name in set(described) | set(expected)
                    if described.get(name) != expected.get(name)
                )
                raise ReviewStoreError(
                    f"the review store at {resolved} has an unexpected schema for table "
                    f"{table!r}; differing columns: {differing}. Expected {expected}, found "
                    f"{described}. This store was written by a different version; refusing to read "
                    f"it as though it matched."
                )

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> ReviewStore:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    @property
    def path(self) -> Path:
        return self._path

    # -- writes ------------------------------------------------------------------------------

    def append_review(self, review: HumanReview) -> ReviewHistory:
        """Append ``review`` to its subject's history and return the new history.

        The order of operations is the point:

        1. read the subject's current history (which validates it),
        2. build the extended history through
           :func:`~aegistrace.review.history.append_review`, which refuses a bad append,
        3. insert the single new row.

        All three happen inside one transaction, so a concurrent reader never observes a history
        that has been validated but not yet written, or vice versa. If the insert fails - most
        likely because ``review_id`` already exists - the transaction rolls back and the store is
        unchanged.

        A duplicate is refused rather than tolerated. By the identity rule, two reviews with the
        same ``review_id`` are not two events; they are the same judgment recorded twice, so
        storing both would fabricate a second decision that no human made.
        """

        try:
            self._connection.execute("BEGIN TRANSACTION")
            history = self._load_history_in_transaction(review.subject_triage_id)
            extended = append_review(history, review)
            self._connection.execute(
                f"INSERT INTO {REVIEW_TABLE} "
                f"(sequence, {', '.join(_COLUMNS)}) "
                f"VALUES (nextval('{REVIEW_SEQUENCE}'), {', '.join('?' for _ in _COLUMNS)})",
                [self._value(review, column) for column in _COLUMNS],
            )
            # Journal the new head in the same transaction. Both rows land or neither does, so the
            # journal can never describe a history that was not written.
            self._connection.execute(
                f"INSERT INTO {HEAD_JOURNAL_TABLE} "
                f"(sequence, subject_triage_id, head_review_id, review_count) "
                f"VALUES (nextval('{HEAD_JOURNAL_SEQUENCE}'), ?, ?, ?)",
                [
                    str(review.subject_triage_id),
                    str(extended.reviews[-1].review_id),
                    len(extended.reviews),
                ],
            )
            self._connection.execute("COMMIT")
        except ReviewStoreError:
            self._rollback()
            raise
        except Exception as error:
            self._rollback()
            raise ReviewStoreError(
                f"could not append review {review.review_id} for subject "
                f"{review.subject_triage_id}: {error}"
            ) from error
        return extended

    def _rollback(self) -> None:
        # A rollback failure must not mask the error that caused it, so it is suppressed rather
        # than allowed to replace the real diagnostic.
        with contextlib.suppress(Exception):  # pragma: no cover - defensive
            self._connection.execute("ROLLBACK")

    # -- reads -------------------------------------------------------------------------------

    def load_history(self, subject_triage_id: UUID) -> ReviewHistory:
        """Return the full review history for one subject, or an empty history if none exists.

        An empty history here means *this subject has not been reviewed yet*, which is a legitimate
        state - it is the state every spine record starts in. It never means "the store is broken":
        a broken store raises :class:`ReviewStoreError`.
        """

        try:
            return self._load_history_in_transaction(subject_triage_id)
        except ReviewStoreError:
            raise
        except Exception as error:
            raise ReviewStoreError(
                f"could not read the review history for subject {subject_triage_id}: {error}"
            ) from error

    def _load_history_in_transaction(self, subject_triage_id: UUID) -> ReviewHistory:
        rows = self._connection.execute(
            f"SELECT {', '.join(_COLUMNS)} FROM {REVIEW_TABLE} "
            f"WHERE subject_triage_id = ? ORDER BY sequence",
            [str(subject_triage_id)],
        ).fetchall()

        reviews: list[HumanReview] = []
        for index, row in enumerate(rows):
            payload = dict(zip(_COLUMNS, row, strict=True))
            try:
                reviews.append(HumanReview.model_validate(payload))
            except Exception as error:
                # Refuse to skip the bad row. Dropping it would present the remainder as a complete
                # history, which is a stronger and falser claim than admitting the record is broken.
                raise ReviewStoreError(
                    f"stored review {index} for subject {subject_triage_id} is not a valid "
                    f"HumanReview: {error}"
                ) from error

        try:
            # Constructed from fields, never `model_copy`, so `validate_chain_is_linear`,
            # `validate_subjects_match` and the per-review identity check all run on the READ path.
            history = ReviewHistory(
                subject_triage_id=subject_triage_id,
                reviews=tuple(reviews),
            )
        except Exception as error:
            raise ReviewStoreError(
                f"the stored reviews for subject {subject_triage_id} do not form a valid "
                f"append-only history: {error}"
            ) from error

        self._require_journal_agrees(subject_triage_id, history)
        return history

    def _require_journal_agrees(self, subject_triage_id: UUID, history: ReviewHistory) -> None:
        """Refuse a history the append-only journal does not corroborate.

        The chain validators check the shape of a history, not its completeness: a chain with its
        newest row deleted is shorter but still internally valid. The journal records the head and
        count written at each append, so a truncated, padded or re-tailed history is caught here.

        An empty history needs no journal entry - a subject that has never been reviewed is the
        state every spine record starts in - but reviews without a journal entry are refused, since
        rows that no append produced are exactly what tampering looks like.
        """

        row = self._connection.execute(
            f"SELECT head_review_id, review_count FROM {HEAD_JOURNAL_TABLE} "
            f"WHERE subject_triage_id = ? ORDER BY sequence DESC LIMIT 1",
            [str(subject_triage_id)],
        ).fetchone()

        if row is None:
            if history.reviews:
                raise ReviewStoreError(
                    f"subject {subject_triage_id} has {len(history.reviews)} stored review(s) but "
                    f"no journal entry; the reviews were not produced by an append"
                )
            return

        recorded_head, recorded_count = str(row[0]), int(row[1])
        actual_count = len(history.reviews)
        if recorded_count != actual_count:
            raise ReviewStoreError(
                f"the review journal for subject {subject_triage_id} records {recorded_count} "
                f"review(s) but {actual_count} are stored; the history has been truncated or padded"
            )
        if history.reviews:
            actual_head = str(history.reviews[-1].review_id)
            if recorded_head != actual_head:
                raise ReviewStoreError(
                    f"the review journal for subject {subject_triage_id} records head "
                    f"{recorded_head} but the stored history ends at {actual_head}; the tail "
                    f"of the history has been replaced"
                )

    def subjects(self) -> tuple[UUID, ...]:
        """Every subject with at least one recorded review, in first-appearance order."""

        rows = self._connection.execute(
            f"SELECT subject_triage_id, MIN(sequence) AS first_seen FROM {REVIEW_TABLE} "
            f"GROUP BY subject_triage_id ORDER BY first_seen"
        ).fetchall()
        return tuple(UUID(row[0]) for row in rows)

    def review_count(self) -> int:
        """Total reviews stored, across all subjects."""

        row = self._connection.execute(f"SELECT COUNT(*) FROM {REVIEW_TABLE}").fetchone()
        return int(row[0]) if row is not None else 0

    # -- serialization -----------------------------------------------------------------------

    @staticmethod
    def _value(review: HumanReview, column: str) -> Any:
        """Render one field as the scalar DuckDB stores.

        Enums are written as their string values, identifiers as their canonical string form, and
        timestamps as ISO-8601 strings, so a row read back reconstructs the same object through the
        same validators that accepted it on the way in.
        """

        value = getattr(review, column)
        if value is None:
            return None
        if isinstance(value, UUID):
            return str(value)
        if isinstance(value, datetime):
            return value.isoformat()
        if hasattr(value, "value"):  # StrEnum members
            return str(value.value)
        return value


__all__ = ["REVIEW_SEQUENCE", "REVIEW_TABLE", "ReviewStore", "ReviewStoreError"]
