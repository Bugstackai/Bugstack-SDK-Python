"""Tests for caught-and-logged error capture (integrations/logging_capture.py)."""

from __future__ import annotations

import io
import logging

import pytest

import bugstack
from bugstack.integrations import logging_capture
from bugstack.integrations.logging_capture import MAX_PER_MINUTE, REPEAT_WINDOW_SECONDS, redact_text


class Clock:
    def __init__(self) -> None:
        self.t = 1000.0

    def __call__(self) -> float:
        return self.t


@pytest.fixture
def clock():
    c = Clock()
    logging_capture._reset_for_tests(now=c)
    yield c
    logging_capture._reset_for_tests()


@pytest.fixture
def sent(monkeypatch):
    """Every event that reaches the client's send path (before_send, dedup, transport)."""
    events = []
    from bugstack.client import BugStackClient

    original = BugStackClient._send

    def spy(self, event):
        events.append(event)
        return original(self, event)

    monkeypatch.setattr(BugStackClient, "_send", spy)
    return events


@pytest.fixture
def app_logger():
    """A logger with its own handler, like an app's, writing to a buffer."""
    buf = io.StringIO()
    log = logging.getLogger("tests.app")
    handler = logging.StreamHandler(buf)
    handler.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
    log.addHandler(handler)
    log.setLevel(logging.DEBUG)
    yield log, buf
    log.removeHandler(handler)


def grant_credits(log):
    try:
        raise KeyError("org-1")
    except KeyError:
        log.exception("[billing] grant failed")


def test_logger_exception_is_forwarded_anchored_at_the_logging_call(clock, sent, app_logger):
    log, buf = app_logger
    bugstack.init(api_key="bs_test", dry_run=True)
    grant_credits(log)
    assert "ERROR [billing] grant failed" in buf.getvalue()
    assert "KeyError" in buf.getvalue()  # the handler still wrote the traceback
    assert len(sent) == 1
    e = sent[0]
    assert e.message == "[billing] grant failed: KeyError: 'org-1'"
    assert e.function == "grant_credits"
    assert e.file.endswith("test_logging_capture.py")
    assert "KeyError" in e.stack_trace
    assert e.metadata["source"] == "logging"
    assert e.metadata["handled"] is True
    assert e.metadata["causeName"] == "KeyError"
    assert e.metadata["logger"] == "tests.app"


def test_exception_as_a_format_argument_is_forwarded(clock, sent, app_logger):
    log, buf = app_logger
    bugstack.init(api_key="bs_test", dry_run=True)
    try:
        int("x")
    except ValueError as exc:
        log.error("[import] row failed: %s", exc)
    assert len(sent) == 1
    assert "ValueError" in sent[0].message
    assert "row failed" in sent[0].message


def test_plain_error_message_stays_a_log_line_by_default(clock, sent, app_logger):
    log, buf = app_logger
    bugstack.init(api_key="bs_test", dry_run=True)
    log.error("[sweep] could not update org-1")
    log.warning("careful", exc_info=ValueError("not an error level"))
    assert "could not update org-1" in buf.getvalue()
    assert sent == []


def test_capture_log_messages_forwards_message_only_records_once_per_site(clock, sent, app_logger):
    log, _ = app_logger
    bugstack.init(api_key="bs_test", dry_run=True, capture_log_messages=True)

    def site(org):
        log.error("[sweep] could not update %s", org)

    site("org-1")
    site("org-2")
    assert len(sent) == 1
    assert sent[0].message == "[sweep] could not update org-1"
    assert sent[0].metadata["messageOnly"] is True
    clock.t += REPEAT_WINDOW_SECONDS
    site("org-3")
    assert len(sent) == 2


def test_sdk_own_logger_and_already_reported_exceptions_are_skipped(clock, sent, app_logger):
    log, _ = app_logger
    bugstack.init(api_key="bs_test", dry_run=True)
    logging.getLogger("bugstack").error("[BugStack] send failed", exc_info=RuntimeError("network"))
    try:
        raise RuntimeError("boom")
    except RuntimeError as exc:
        bugstack.capture_exception(exc)
        log.exception("[x] failed")
    assert len(sent) == 1  # capture_exception's, not the log record's
    assert logging_capture.dropped["sdk_logger"] == 1
    assert logging_capture.dropped["already_reported"] == 1


def test_rate_limited_per_minute(clock, sent, app_logger):
    log, _ = app_logger
    bugstack.init(api_key="bs_test", dry_run=True, deduplication_window=0)
    for i in range(MAX_PER_MINUTE + 5):
        log.error("[x] failed %s", i, exc_info=ValueError(f"e{i}"))
    assert len(sent) == MAX_PER_MINUTE
    assert logging_capture.logging_stats()["dropped"]["rate_limited"] == 5


def test_never_raises_and_never_loops(clock, app_logger):
    log, buf = app_logger

    def before_send(event):
        logging.getLogger("tests.app").error("from before_send", exc_info=ValueError("inner"))
        raise RuntimeError("before_send broke")

    bugstack.init(api_key="bs_test", dry_run=True, before_send=before_send)
    log.error("[x] failed", exc_info=ValueError("outer"))
    assert "[x] failed" in buf.getvalue()
    assert "from before_send" in buf.getvalue()


def test_redacts_the_logged_text(clock, sent, app_logger):
    log, _ = app_logger
    bugstack.init(api_key="bs_test", dry_run=True, redact_fields=["session_id"])
    log.error(
        "login failed password=hunter2 session_id: abc123 Authorization: Bearer abcdefghijkl",
        exc_info=ValueError("token=s3cr3t"),
    )
    m = sent[0].message
    for secret in ("hunter2", "abc123", "abcdefghijkl", "s3cr3t"):
        assert secret not in m
    assert "s3cr3t" not in sent[0].stack_trace


def test_capture_logging_false_leaves_logging_untouched(clock, sent, app_logger):
    log, _ = app_logger
    original = logging.Logger.callHandlers
    bugstack.init(api_key="bs_test", dry_run=True, capture_logging=False)
    assert logging.Logger.callHandlers is original
    grant_credits(log)
    assert sent == []


def test_shutdown_restores_call_handlers_and_root_logger_is_unchanged(clock):
    original = logging.Logger.callHandlers
    root_handlers = list(logging.getLogger().handlers)
    client = bugstack.init(api_key="bs_test", dry_run=True)
    assert logging.Logger.callHandlers is not original
    assert logging.getLogger().handlers == root_handlers  # basicConfig still works after init
    client.shutdown()
    assert logging.Logger.callHandlers is original


def test_last_resort_output_is_preserved(clock, capsys):
    """With no handlers anywhere, Python prints ERROR records to stderr; that still happens."""
    log = logging.getLogger("tests.no_handlers")
    log.propagate = False
    bugstack.init(api_key="bs_test", dry_run=True)
    log.error("unhandled path", exc_info=ValueError("x"))
    assert "unhandled path" in capsys.readouterr().err


def test_redact_text_helper():
    assert redact_text("password=hunter2 next", ["password"]) == "password=[REDACTED] next"
    assert redact_text("client_secret: xyz", ["secret"]) == "client_secret: [REDACTED]"
    assert redact_text("Bearer abcdefghijklmnop", []) == "Bearer [REDACTED]"
