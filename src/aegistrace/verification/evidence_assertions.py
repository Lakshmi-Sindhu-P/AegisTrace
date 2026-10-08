"""Machine-checkable evidence assertions against referenced artifacts.

A results-ledger evidence string can be one of two things. Most entries are human prose that no
program can audit; those stay allowed but unenforced. A minority take the machine-checkable form
``path = value``, e.g.::

    headline.model_score_best_at_every_strictness_and_budget_all_captures = true and
    headline.uncertainty_ever_beats_model_score_any_capture = false

A machine-checkable string declares that some value inside the cited artifact equals some literal,
and that IS audited. Without this, a claim can drift from its own artifact while the ledger still
reports green, so enforcement is the point of the defect this module fixes.

Grammar for one enforced assertion:

* ``key`` followed by zero or more ``[field=value]`` selectors (each selects exactly ONE item from a
  list by exact string match on that field), then a final ``.field`` segment;
* the equality separator `` = ``;
* a value literal: ``true``, ``false``, an integer, or a float.

A multi-assertion string joins fragments with `` and `` (split FIRST, before any parsing, so a
trailing ``false`` of one fragment is never absorbed into the next).
"""

from __future__ import annotations

import re
from typing import Any

_SEGMENT_RE = re.compile(
    r"^([A-Za-z_][A-Za-z0-9_]*)((?:\[[A-Za-z_][A-Za-z0-9_]*=[^\[\]]+\])*)$"
)
_SELECTOR_RE = re.compile(r"\[([A-Za-z_][A-Za-z0-9_]*)=([^\[\]]+?)\]")

Assertion = tuple[list[tuple[str, list[tuple[str, str]]]], Any]
"""A parsed assertion: resolved path segments and the expected literal value."""


def _coerce(raw: str) -> Any:
    """Coerce ``raw`` to a bool/int/float literal, or ``None`` if it is not one."""
    low = raw.lower()
    if low == "true":
        return True
    if low == "false":
        return False
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        return None


def _parse_value(raw: str) -> Any:
    """Parse a value literal, tolerating a single trailing sentence-period."""
    value = _coerce(raw.strip())
    if value is not None:
        return value
    stripped = raw.strip()
    if stripped.endswith("."):
        return _coerce(stripped[:-1].rstrip())
    return None


def _is_valid_path(path: str) -> bool:
    return bool(path) and all(_SEGMENT_RE.fullmatch(seg) for seg in path.split("."))


def parse_assertions(text: str) -> list[Assertion] | None:
    """Parse ``text`` into enforced assertions, or return ``None`` if it is prose.

    Every `` and `` fragment must itself be a well-formed ``path = value`` assertion. If any
    fragment fails to parse, the whole string is treated as unenforced prose rather than a partial
    assertion -- so an assertion that has drifted toward prose never silently escapes as a fragment.
    """
    assertions: list[Assertion] = []
    for fragment in text.split(" and "):
        parsed = _parse_fragment(fragment)
        if parsed is None:
            return None
        assertions.append(parsed)
    return assertions


def _parse_fragment(fragment: str) -> Assertion | None:
    if " = " not in fragment:
        return None
    left, right = fragment.split(" = ", 1)
    path = left.strip()
    value = _parse_value(right)
    if value is None or not _is_valid_path(path):
        return None
    segments: list[tuple[str, list[tuple[str, str]]]] = []
    for seg in path.split("."):
        match = _SEGMENT_RE.fullmatch(seg)
        assert match is not None
        name = match.group(1)
        selectors = [(m.group(1), m.group(2)) for m in _SELECTOR_RE.finditer(match.group(2) or "")]
        segments.append((name, selectors))
    return (segments, value)


def resolve_path(
    document: Any, segments: list[tuple[str, list[tuple[str, str]]]]
) -> tuple[str, Any]:
    """Resolve ``segments`` against ``document``.

    Returns ``(kind, value)`` where ``kind`` is ``"matched"``, ``"unresolved"`` (a path segment
    missing or not a list when a selector needs one), or ``"ambiguous"`` (a selector matched more
    than one list item, so the path does not pick out exactly one value).
    """
    current: Any = document
    for name, selectors in segments:
        if not isinstance(current, dict) or name not in current:
            return ("unresolved", None)
        current = current[name]
        for field, wanted in selectors:
            if not isinstance(current, list):
                return ("unresolved", None)
            matches = [
                item
                for item in current
                if isinstance(item, dict) and str(item.get(field)) == wanted
            ]
            if not matches:
                return ("unresolved", None)
            if len(matches) > 1:
                return ("ambiguous", None)
            current = matches[0]
    return ("matched", current)


def _resolve_across_documents(
    documents: list[Any], segments: list[tuple[str, list[tuple[str, str]]]]
) -> tuple[str, Any]:
    """Resolve ``segments`` against the first document that yields a match.

    Depth-first over the claim's artifacts: a clean resolution anywhere counts. If none resolves,
    an ``ambiguous`` resolution anywhere outranks a merely ``unresolved`` one so the stronger signal
    is reported.
    """
    result: tuple[str, Any] = ("unresolved", None)
    for document in documents:
        kind, value = resolve_path(document, segments)
        if kind == "matched":
            return (kind, value)
        if kind == "ambiguous":
            result = (kind, value)
    return result


def values_equal(actual: Any, expected: Any) -> bool:
    """Compare a resolved artifact value with an expected literal, bool-safe.

    ``True == 1`` in Python, so a boolean literal is only equal to an actual boolean -- never to an
    integer that merely compares equal.
    """
    if isinstance(expected, bool) or isinstance(actual, bool):
        return isinstance(actual, bool) and isinstance(expected, bool) and actual is expected
    return bool(actual == expected)


def validate_evidence(
    evidence: list[Any], documents: list[Any]
) -> tuple[list[str], int, int]:
    """Enforce every machine-checkable evidence string against ``documents``.

    Returns ``(violations, enforced_strings, assertions_checked)``. Prose evidence contributes to
    neither of the two coverage counts' enforced/checked tallies and never yields a violation.
    """
    violations: list[str] = []
    enforced_strings = 0
    assertions_checked = 0
    for entry in evidence:
        if not isinstance(entry, str):
            continue
        assertions = parse_assertions(entry)
        if assertions is None:
            continue
        enforced_strings += 1
        for segments, expected in assertions:
            assertions_checked += 1
            kind, actual = _resolve_across_documents(documents, segments)
            if kind == "unresolved":
                violations.append(f"evidence path does not resolve: {entry!r} -> {expected!r}")
            elif kind == "ambiguous":
                violations.append(f"evidence selector is ambiguous (matches >1 item): {entry!r}")
            elif not values_equal(actual, expected):
                violations.append(
                    f"evidence value mismatch: {entry!r} expected {expected!r} "
                    f"but artifact has {actual!r}"
                )
    return violations, enforced_strings, assertions_checked