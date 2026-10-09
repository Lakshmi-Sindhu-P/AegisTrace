"""The append-only review store, and every way it refuses to sell a good record.

``ReviewStore`` is a DuckDB-backed store whose one job is append-only custody of human-review
history. Most of its value is in the *refusals*: a duplicate append, a corrupted read, a database
edited by hand, an unreadable path. These tests pin the store's public contract (open/append/load)
and prove that each refusal is loud and typed as :class:`ReviewStoreError` — never an empty history,
never a raw DuckDB error that escapes the module's single error type, and never a silently corrected
record.

A shared concern throughout is that the store's detection logic must not be *vacuous*: every
"refuses" test exists because tampering or corruption is genuinely detected, which is what a
custody record is for. The read path revalidates the full chain and the head journal on every load,
so a hand-edited file is noticed rather than served as authority.
"""

from __future__ import annotations

import ast
import builtins
import pathlib
import re
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest import mock
from uuid import UUID, uuid4

import pytest

import aegistrace.storage.reviews as reviews_mod
from aegistrace.schemas.review import (
    EscalationState,
    HumanReview,
    ReviewDecision,
    ReviewTier,
    review_id_for,
)
from aegistrace.schemas.triage import AssessorRole
from aegistrace.storage.reviews import (
    HEAD_JOURNAL_TABLE,
    REVIEW_TABLE,
    ReviewStore,
    ReviewStoreError,
)

SUBJECT = uuid4()
REVIEWED_AT = datetime(2026, 10, 9, 12, 0, tzinfo=UTC)


def _review(
    *,
    reviewer: str = "r1",
    decision: ReviewDecision = ReviewDecision.CONFIRM,
    supersedes: UUID | None = None,
    subject: UUID = SUBJECT,
) -> HumanReview:
    """Build a valid review; identity derived so the coherence check is satisfied."""

    return HumanReview(
        review_id=review_id_for(
            subject_triage_id=subject,
            subject_role=AssessorRole.TRIAGE_ANALYST,
            reviewer_ref=reviewer,
            decision=decision,
            final_disposition="disposition",
            supersedes_review_id=supersedes,
        ),
        subject_triage_id=subject,
        subject_role=AssessorRole.TRIAGE_ANALYST,
        reviewer_ref=reviewer,
        tier=ReviewTier.A_MACHINE_CHECK,
        decision=decision,
        notes="note",
        reviewed_at=REVIEWED_AT,
        escalation_state=EscalationState.NONE,
        final_disposition="disposition",
        supersedes_review_id=supersedes,
    )


@pytest.fixture
def store(tmp_path: Path) -> Iterator[ReviewStore]:
    with ReviewStore.open(tmp_path / "reviews.duckdb") as s:
        yield s


def _raw(path: Path) -> Any:
    """Open a raw DuckDB connection to the store file, for the tamper tests."""

    import duckdb

    return duckdb.connect(str(path))


def _seed_two_review_store(path: Path) -> tuple[HumanReview, HumanReview]:
    """Write a known-good two-review history to ``path``, close the store, and return its models."""

    r1 = _review()
    r2 = _review(reviewer="r2", decision=ReviewDecision.REVISE, supersedes=r1.review_id)
    with ReviewStore.open(path) as s:
        s.append_review(r1)
        s.append_review(r2)
    return r1, r2


def _string_fragments(value: ast.AST) -> list[str]:
    """The string pieces of an f-string / plain string AST node."""

    if isinstance(value, ast.Constant) and isinstance(value.value, str):
        return [value.value]
    if isinstance(value, ast.JoinedStr):
        return [
            part.value
            for part in value.values
            if isinstance(part, ast.Constant) and isinstance(part.value, str)
        ]
    return []


def _module_sql_literals() -> str:
    """Every SQL string the module issues, extracted from source with ``ast``.

    This captures the ``_CREATE*`` constants *and* the literal arguments to every
    ``connection.execute(...)`` call (including f-string fragments such as the inline
    ``CREATE SEQUENCE ...`` statement), so a scan of this text reflects the SQL the module can
    actually run. It deliberately does not read docstring prose.
    """

    source = pathlib.Path(reviews_mod.__file__).read_text()
    tree = ast.parse(source)
    fragments: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.startswith("_CREATE"):
                    fragments.extend(_string_fragments(node.value))
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr == "execute" and node.args:
                fragments.extend(_string_fragments(node.args[0]))
    return "\n".join(fragments)


# ---------------------------------------------------------------------------
# Required coverage
# ---------------------------------------------------------------------------


def test_empty_history_is_distinct_from_a_broken_open(tmp_path: Path) -> None:
    """An unreviewed subject yields a legitimately empty history, never an error; a store that
    cannot open raises :class:`ReviewStoreError`. The two states must be distinguishable, or a
    caller could mistake 'you pointed me at the wrong place' for 'no reviews yet'."""

    fresh = uuid4()
    store = ReviewStore.open(tmp_path / "empty.duckdb")
    try:
        history = store.load_history(fresh)
    finally:
        store.close()
    assert history.reviews == ()
    assert history.subject_triage_id == fresh

    # Broken open: the parent directory is missing, so this must be an error, not an empty history.
    with pytest.raises(ReviewStoreError):
        ReviewStore.open(tmp_path / "no_such_dir" / "reviews.duckdb")


def test_first_append_returns_the_new_history(store: ReviewStore) -> None:
    """The append's return value is the subject's new history holding exactly one review, so the
    caller does not need a separate read to see what it just wrote."""

    history = store.append_review(_review())
    assert len(history.reviews) == 1
    assert history.subject_triage_id == SUBJECT


def test_exact_round_trip(store: ReviewStore) -> None:
    """A stored review reads back equal to the one appended, even though ``reviewed_at`` round-trips
    through the ISO-8601 VARCHAR column (the schema normalizes it back on read). Exact equality is
    the guarantee a custody record needs: nothing is silently altered in transit."""

    r1 = _review()
    store.append_review(r1)
    loaded = store.load_history(SUBJECT).reviews[0]
    assert loaded == r1
    assert loaded.reviewed_at == r1.reviewed_at


def test_duplicate_review_is_refused_and_count_is_unchanged(store: ReviewStore) -> None:
    """Appending the identical review twice must refuse the second and leave exactly one stored.
    Two rows with the same id would fabricate a second decision no human made."""

    store.append_review(_review())
    with pytest.raises(ReviewStoreError):
        store.append_review(_review())  # same substance -> same review_id
    assert store.review_count() == 1


def test_correction_supersedes_and_preserves_the_original(store: ReviewStore) -> None:
    """A REVISE correction extends the history in order and never rewrites the original. The first
    entry is byte-for-byte ``r1`` after the correction lands, the whole point of append-only."""

    r1 = _review()
    store.append_review(r1)
    r2 = _review(reviewer="r2", decision=ReviewDecision.REVISE, supersedes=r1.review_id)
    store.append_review(r2)
    history = store.load_history(SUBJECT)
    assert [r.review_id for r in history.reviews] == [r1.review_id, r2.review_id]
    assert history.reviews[-1].supersedes_review_id == r1.review_id
    assert history.reviews[0] == r1


def test_second_review_must_supersede_the_first(store: ReviewStore) -> None:
    """A second, non-superseding review (an unexplained second opinion) is refused, keeping the
    chain linear so the last entry is unambiguously current."""

    store.append_review(_review())
    with pytest.raises(ReviewStoreError):
        store.append_review(_review(reviewer="r2", decision=ReviewDecision.CONFIRM))
    assert store.review_count() == 1


def test_history_is_durable_across_reopen(tmp_path: Path) -> None:
    """Two written reviews survive closing and reopening the same file, reconstructing to the same
    two models. Durability is what makes the store a record rather than a session."""

    path = tmp_path / "reviews.duckdb"
    with ReviewStore.open(path) as s:
        r1 = _review()
        s.append_review(r1)
        r2 = _review(reviewer="r2", decision=ReviewDecision.REVISE, supersedes=r1.review_id)
        s.append_review(r2)
    with ReviewStore.open(path) as s:
        assert s.review_count() == 2
        history = s.load_history(SUBJECT)
        assert [r.review_id for r in history.reviews] == [r1.review_id, r2.review_id]
        assert list(history.reviews) == [r1, r2]


def test_subjects_are_independent(tmp_path: Path) -> None:
    """Two subjects each keep only their own history, and ``subjects()`` lists both. A record that
    mixed reviews across subjects would corrupt every attribution."""

    path = tmp_path / "reviews.duckdb"
    other = uuid4()
    with ReviewStore.open(path) as s:
        s.append_review(_review())
        s.append_review(_review(subject=other))
    with ReviewStore.open(path) as s:
        assert SUBJECT in s.subjects()
        assert other in s.subjects()
        assert len(s.load_history(SUBJECT).reviews) == 1
        assert len(s.load_history(other).reviews) == 1
        assert s.load_history(SUBJECT).reviews[0].subject_triage_id == SUBJECT
        assert s.load_history(other).reviews[0].subject_triage_id == other


def test_stale_schema_is_refused(tmp_path: Path) -> None:
    """Opening a store whose ``human_review`` table was altered by a different version refuses with
    an error naming the differing column, rather than silently mis-assigning fields."""

    path = tmp_path / "reviews.duckdb"
    with ReviewStore.open(path) as s:
        s.append_review(_review())
    con = _raw(path)
    try:
        con.execute(f"ALTER TABLE {REVIEW_TABLE} ADD COLUMN extra VARCHAR")
    finally:
        con.close()
    with pytest.raises(ReviewStoreError, match="extra"):
        ReviewStore.open(path)


def test_missing_parent_directory_is_refused(tmp_path: Path) -> None:
    """A mistyped path whose parent directory is absent raises and names the missing directory, so
    the mistake cannot be mistaken for an empty store."""

    target = tmp_path / "no_such_dir" / "reviews.duckdb"
    with pytest.raises(ReviewStoreError, match="review store directory does not exist"):
        ReviewStore.open(target)


def test_read_path_revalidates_a_corrupt_supersede_link(tmp_path: Path) -> None:
    """Clearing a tail review's supersede link is caught on read as an invalid stored review, with
    the corrupt index named. The read path re-runs schema validation, so a hand-edited row cannot
    pass silently."""

    path = tmp_path / "reviews.duckdb"
    _seed_two_review_store(path)
    con = _raw(path)
    try:
        con.execute(f"UPDATE {REVIEW_TABLE} SET supersedes_review_id = NULL WHERE sequence = 2")
    finally:
        con.close()
    with ReviewStore.open(path) as s, pytest.raises(ReviewStoreError, match="stored review 1"):
        s.load_history(SUBJECT)


def test_module_issues_no_mutation_sql() -> None:
    """The module's only SQL is CREATE/INSERT/SELECT/DESCRIBE and transaction control — no UPDATE,
    DELETE, DROP, ALTER, TRUNCATE or MERGE. This scans the ``_CREATE*`` constants and every literal
    passed to ``connection.execute(...)`` (via ``ast``, so f-string fragments are captured) rather
    than trusting the module docstring, which mentions UPDATE/DELETE in prose. It also asserts the
    scan captured statements, so the test cannot pass vacuously on an empty set."""

    sql = _module_sql_literals()
    assert sql.strip(), "the scan captured no SQL; the test would be vacuous"
    upper = sql.upper()
    for verb in ("UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE", "MERGE"):
        assert not re.search(rf"\b{verb}\b", upper), f"module issues a {verb} statement"


# ---------------------------------------------------------------------------
# Guard-ratchet: every raise path must be exercised, and every failure must stay typed.
# ---------------------------------------------------------------------------


def test_open_reports_the_missing_storage_extra(tmp_path: Path) -> None:
    """When DuckDB cannot be imported, ``open`` is a loud :class:`ReviewStoreError` naming the
    extra, not a raw ``ModuleNotFoundError`` that escapes the module's single error type."""

    real_import: Any = builtins.__import__

    def _block_duckdb_import(name: str, *args: object, **kwargs: object) -> object:
        if name == "duckdb":
            raise ModuleNotFoundError("No module named 'duckdb'")
        return real_import(name, *args, **kwargs)

    with (
        mock.patch.object(builtins, "__import__", _block_duckdb_import),
        pytest.raises(ReviewStoreError, match="storage extra is not installed"),
    ):
        ReviewStore.open(tmp_path / "reviews.duckdb")


def test_open_on_a_directory_raises_the_documented_error(tmp_path: Path) -> None:
    """Opening a path that is a directory fails as :class:`ReviewStoreError`. Regression pin: the
    pre-fix code raised ``UnboundLocalError`` here, escaping the module's single error type."""

    target = tmp_path / "a_directory"
    target.mkdir()
    with pytest.raises(ReviewStoreError):
        ReviewStore.open(target)


def test_open_on_a_corrupt_file_raises_the_documented_error(tmp_path: Path) -> None:
    """A corrupt file fails loudly as :class:`ReviewStoreError`, never a raw DuckDB error."""

    bad = tmp_path / "corrupt.duckdb"
    bad.write_bytes(b"not a duckdb database" * 50)
    with pytest.raises(ReviewStoreError):
        ReviewStore.open(bad)


def test_append_after_close_is_a_reviewstoreerror(tmp_path: Path) -> None:
    """Calling append on a closed store fails as :class:`ReviewStoreError` naming the append, not a
    raw connection error. The single error type holds on every failure path."""

    path = tmp_path / "a.duckdb"
    store = ReviewStore.open(path)
    try:
        r1 = _review()
        store.append_review(r1)
    finally:
        store.close()
    r2 = _review(reviewer="r2", decision=ReviewDecision.REVISE, supersedes=r1.review_id)
    with pytest.raises(ReviewStoreError, match="could not append review"):
        store.append_review(r2)


def test_load_after_close_is_a_reviewstoreerror(tmp_path: Path) -> None:
    """load_history on a closed store fails as :class:`ReviewStoreError`, not a raw connection
    error, so a caller catching the module's one error type sees all failures."""

    path = tmp_path / "b.duckdb"
    store = ReviewStore.open(path)
    try:
        store.append_review(_review())
    finally:
        store.close()
    with pytest.raises(ReviewStoreError, match="could not read the review history"):
        store.load_history(SUBJECT)


def test_append_with_corrupted_journal_re_raises_reviewstoreerror(tmp_path: Path) -> None:
    """When the append path's own read finds the journal corrupted, the :class:`ReviewStoreError`
    is re-raised unchanged rather than swallowed, so the append stops over a broken record."""

    path = tmp_path / "c.duckdb"
    _, r2 = _seed_two_review_store(path)
    con = _raw(path)
    try:
        con.execute(
            f"DELETE FROM {HEAD_JOURNAL_TABLE} WHERE subject_triage_id = ?",
            [str(SUBJECT)],
        )
    finally:
        con.close()
    r3 = _review(reviewer="r3", decision=ReviewDecision.DISMISS, supersedes=r2.review_id)
    with ReviewStore.open(path) as s, pytest.raises(ReviewStoreError, match="no journal entry"):
        s.append_review(r3)


# ---------------------------------------------------------------------------
# Tamper detection: a hand-edited database must be noticed, not served.
# ---------------------------------------------------------------------------


def test_tamper_delete_newest_review_is_detected(tmp_path: Path) -> None:
    """Deleting the newest review row is caught by the head journal's count check: the table now
    holds one review where the journal recorded two. This is exactly the case the shape validators
    miss — a shorter but internally valid chain — so the journal must catch it."""

    path = tmp_path / "t1.duckdb"
    _seed_two_review_store(path)
    con = _raw(path)
    try:
        con.execute(f"DELETE FROM {REVIEW_TABLE} WHERE sequence = 2")
    finally:
        con.close()
    with ReviewStore.open(path) as s, pytest.raises(ReviewStoreError, match="records 2 review"):
        s.load_history(SUBJECT)


def test_tamper_delete_first_review_is_detected(tmp_path: Path) -> None:
    """Deleting the first review leaves a tail whose supersede link dangles; the schema refuses the
    chain on read, since the lone remaining review cannot be first and yet supersede something."""

    path = tmp_path / "t2.duckdb"
    _seed_two_review_store(path)
    con = _raw(path)
    try:
        con.execute(f"DELETE FROM {REVIEW_TABLE} WHERE sequence = 1")
    finally:
        con.close()
    with (
        ReviewStore.open(path) as s,
        pytest.raises(ReviewStoreError, match="do not form a valid append-only history"),
    ):
        s.load_history(SUBJECT)


def test_tamper_clear_tail_supersede_link_is_detected(tmp_path: Path) -> None:
    """Clearing the tail's supersede link turns a revising review into an unlinked one; the store
    catches it on read as an invalid stored review at index 1, so the corruption is named."""

    path = tmp_path / "t3.duckdb"
    _seed_two_review_store(path)
    con = _raw(path)
    try:
        con.execute(f"UPDATE {REVIEW_TABLE} SET supersedes_review_id = NULL WHERE sequence = 2")
    finally:
        con.close()
    with ReviewStore.open(path) as s, pytest.raises(ReviewStoreError, match="stored review 1"):
        s.load_history(SUBJECT)


def test_tamper_rewrite_tail_disposition_is_detected(tmp_path: Path) -> None:
    """Rewriting the tail's final_disposition breaks its derived identity; the coherence validator
    re-runs on read and refuses the row at index 1. A forged disposition cannot be served."""

    path = tmp_path / "t4.duckdb"
    _seed_two_review_store(path)
    con = _raw(path)
    try:
        con.execute(f"UPDATE {REVIEW_TABLE} SET final_disposition = 'forged' WHERE sequence = 2")
    finally:
        con.close()
    with ReviewStore.open(path) as s, pytest.raises(ReviewStoreError, match="stored review 1"):
        s.load_history(SUBJECT)


def test_tamper_pad_duplicate_review_id_is_refused(tmp_path: Path) -> None:
    """A hand-inserted row duplicating an existing review_id is refused by the table's UNIQUE
    constraint: the low-level insert itself fails, so a forged duplicate can never enter the table.
    """

    path = tmp_path / "t5.duckdb"
    _, r2 = _seed_two_review_store(path)
    con = _raw(path)
    try:
        with pytest.raises(Exception, match=r"(?i)unique|duplicate"):
            con.execute(
                f"INSERT INTO {REVIEW_TABLE} "
                f"(sequence, schema_version, review_id, subject_triage_id, subject_role, "
                f"reviewer_ref, tier, decision, notes, reviewed_at, escalation_state, "
                f"final_disposition, supersedes_review_id) "
                f"VALUES (3, '1.0.0', ?, ?, 'triage_analyst', 'r2', 'tier_a_machine_check', "
                f"'revise', 'note', ?, 'none', 'forged', NULL)",
                [str(r2.review_id), str(SUBJECT), REVIEWED_AT.isoformat()],
            )
    finally:
        con.close()


def test_tamper_delete_journal_entry_is_detected(tmp_path: Path) -> None:
    """Deleting the subject's journal entry leaves stored reviews with no journal corroboration;
    the read refuses them as 'not produced by an append'. Rows that no append produced are exactly
    what tampering looks like."""

    path = tmp_path / "t6.duckdb"
    _seed_two_review_store(path)
    con = _raw(path)
    try:
        con.execute(
            f"DELETE FROM {HEAD_JOURNAL_TABLE} WHERE subject_triage_id = ?",
            [str(SUBJECT)],
        )
    finally:
        con.close()
    with ReviewStore.open(path) as s, pytest.raises(ReviewStoreError, match="no journal entry"):
        s.load_history(SUBJECT)


def test_tamper_forge_journal_head_is_detected(tmp_path: Path) -> None:
    """Rewriting the journal's recorded head to a different (but valid-looking) id is caught on read
    as a head mismatch: the journal says the tail ends elsewhere, so the tail has been replaced."""

    path = tmp_path / "t7.duckdb"
    _seed_two_review_store(path)
    con = _raw(path)
    try:
        con.execute(
            f"UPDATE {HEAD_JOURNAL_TABLE} SET head_review_id = ? "
            f"WHERE sequence = (SELECT MAX(sequence) FROM {HEAD_JOURNAL_TABLE})",
            [str(uuid4())],
        )
    finally:
        con.close()
    with ReviewStore.open(path) as s, pytest.raises(ReviewStoreError, match="journal"):
        s.load_history(SUBJECT)
