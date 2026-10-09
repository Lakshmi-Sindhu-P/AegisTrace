"""Structural invariants of the human-review store that are not about behaviour.

These are the properties that would rot silently rather than fail loudly:

* the store's column list must stay in exact step with ``HumanReview``'s fields - if a field were
  added to the model and not to ``_COLUMNS``, the store would persist a review and read it back
  with a field missing, which is a *wrong answer* rather than an error;
* the declared column types must cover exactly the column list plus the ordering column;
* ``duckdb`` must remain an optional extra, because the research library must never depend on a
  database engine.

Each is asserted against the code itself, so it cannot drift from the thing it describes.
"""

from __future__ import annotations

import ast
import tomllib
from pathlib import Path

from aegistrace.schemas.review import HumanReview
from aegistrace.storage import reviews as reviews_module

PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"

MUTATING_VERBS = ("UPDATE ", "DELETE ", "DROP ", "ALTER ", "TRUNCATE ", "MERGE ")


def test_the_store_columns_match_the_review_model_exactly() -> None:
    """``_COLUMNS`` must be exactly ``HumanReview``'s fields: none missing, none extra.

    This is the invariant that makes a silent mis-assignment impossible. The store writes and reads
    with the same list, so if the list and the model disagree the round-trip either loses a field
    or shifts one into another's slot - and a shifted field is a wrong value that still validates,
    which is the failure mode this project treats as the worst kind.
    """

    columns = set(reviews_module._COLUMNS)
    model_fields = set(HumanReview.model_fields)

    assert columns - model_fields == set(), (
        "the store has columns that are not HumanReview fields: "
        f"{sorted(columns - model_fields)}"
    )
    assert model_fields - columns == set(), (
        "HumanReview has fields the store does not persist: "
        f"{sorted(model_fields - columns)}"
    )
    assert len(reviews_module._COLUMNS) == len(set(reviews_module._COLUMNS)), (
        "_COLUMNS must not repeat a name; a repeat would shift every later column"
    )


def test_the_declared_column_types_cover_the_columns_plus_the_ordering_column() -> None:
    """``_EXPECTED_TYPES`` must describe exactly ``_COLUMNS`` plus ``sequence``.

    ``sequence`` is deliberately excluded from ``_COLUMNS`` because it is arrival bookkeeping and
    not part of a review's identity. It is still a real column, so the schema check must know about
    it. Anything else in ``_EXPECTED_TYPES`` would mean the store expects a column it never writes.
    """

    expected = set(reviews_module._EXPECTED_TYPES)
    assert expected == set(reviews_module._COLUMNS) | {"sequence"}, (
        "_EXPECTED_TYPES must be exactly _COLUMNS plus 'sequence'; got "
        f"{sorted(expected)}"
    )


def test_the_ordering_column_is_not_part_of_a_reviews_identity() -> None:
    """``sequence`` must stay out of ``_COLUMNS``, because it is arrival bookkeeping.

    By the identity rule (`docs/identity_rule.md`) an identifier covers the fields that make the
    entity what it is and nothing else; the row's arrival order is not part of what a review *is*.
    Including it would make the persisted payload carry a field the model does not have.
    """

    assert "sequence" not in reviews_module._COLUMNS
    assert "sequence" in reviews_module._EXPECTED_TYPES


def test_duckdb_is_an_optional_extra_and_never_a_core_dependency() -> None:
    """The research library must never depend on a database engine.

    Checked against the declared dependency groups rather than by uninstalling anything: ``duckdb``
    must appear under the optional ``storage`` extra and must not appear under core
    ``dependencies``. The same structural guarantee already covers ``fastapi``/``uvicorn`` in
    ``tests/test_ui_app.py``.
    """

    declared = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    project = declared["project"]

    core = [requirement.lower() for requirement in project["dependencies"]]
    assert not any("duckdb" in requirement for requirement in core), (
        "duckdb must not be a core dependency"
    )
    assert not any("fastapi" in requirement for requirement in core)
    assert not any("uvicorn" in requirement for requirement in core)

    extras = project.get("optional-dependencies", {})
    assert "storage" in extras, "the storage extra must be declared"
    assert any("duckdb" in requirement.lower() for requirement in extras["storage"]), (
        "the storage extra must declare duckdb"
    )


def test_the_store_issues_no_mutating_sql() -> None:
    """No ``UPDATE``/``DELETE``/``DROP`` may appear in the SQL the module actually issues.

    Scoped to the SQL rather than to the file text, because the module docstring and its error
    messages legitimately *discuss* UPDATE and DELETE when explaining what DuckDB does not prevent.
    A whole-file text scan passes or fails for the wrong reason: an error message reading "refusing
    to delete" would trip it.

    So the SQL is extracted precisely - the ``_CREATE*`` constants by value, and every literal or
    f-string handed to an ``.execute(...)`` call via the AST. The extraction is asserted to have
    found the inline statements as well as the constants, so the test cannot pass vacuously against
    a set containing only the constants.
    """

    source = Path(reviews_module.__file__).read_text(encoding="utf-8")

    constants: list[str] = []
    for name in ("_CREATE_TABLE", "_CREATE_SEQUENCE", "_CREATE_HEAD_JOURNAL"):
        value = getattr(reviews_module, name)
        assert isinstance(value, str) and value.strip(), f"{name} must be non-empty SQL"
        constants.append(value)

    inline: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not (isinstance(func, ast.Attribute) and func.attr == "execute"):
            continue
        for argument in node.args:
            if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
                inline.append(argument.value)
            elif isinstance(argument, ast.JoinedStr):
                inline.append(ast.unparse(argument))

    # Non-vacuity: the inline extraction must have found real statements, not just the constants.
    assert len(inline) >= 4, (
        f"the AST extraction found only {len(inline)} inline statement(s); expected the "
        f"transaction and query statements too. The test would be vacuous."
    )
    assert any("INSERT" in statement.upper() for statement in inline), (
        "the extraction must include the INSERT statements"
    )
    assert any("SELECT" in statement.upper() for statement in inline), (
        "the extraction must include the SELECT statements"
    )

    joined = "\n".join(constants + inline).upper()
    for verb in MUTATING_VERBS:
        assert verb not in joined, f"the store must not issue {verb.strip()} statements"
