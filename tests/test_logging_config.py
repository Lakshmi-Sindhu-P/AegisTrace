"""Tests for structured logs and nested sensitive-value redaction."""

import json
import logging
import sys
from io import StringIO

from aegistrace.logging_config import JsonFormatter, configure_logging


def test_configured_logger_emits_json_and_redacts_sensitive_fields() -> None:
    stream = StringIO()
    logger = configure_logging("INFO", stream=stream)

    logger.info(
        "fixture ingested",
        extra={
            "event_id": "event-001",
            "api_key": "not-a-real-key",
            "context": {"password": "not-a-real-password", "source": "synthetic"},
        },
    )

    payload = json.loads(stream.getvalue())
    assert payload["message"] == "fixture ingested"
    assert payload["level"] == "INFO"
    assert payload["event_id"] == "event-001"
    assert payload["api_key"] == "[REDACTED]"
    assert payload["context"] == {"password": "[REDACTED]", "source": "synthetic"}


def test_configure_logging_is_idempotent() -> None:
    first_stream = StringIO()
    second_stream = StringIO()

    configure_logging(stream=first_stream)
    logger = configure_logging(stream=second_stream)
    logger.info("once")

    assert first_stream.getvalue() == ""
    assert len(second_stream.getvalue().splitlines()) == 1


def test_json_formatter_includes_exception() -> None:
    formatter = JsonFormatter()
    try:
        raise ValueError("fixture failure")
    except ValueError:
        record = logging.LogRecord(
            name="aegistrace.test",
            level=logging.ERROR,
            pathname=__file__,
            lineno=1,
            msg="failed",
            args=(),
            exc_info=sys.exc_info(),
        )

    payload = json.loads(formatter.format(record))
    assert "ValueError: fixture failure" in payload["exception"]
