"""Caught-and-logged errors reach BugStack.

An ``except`` block that calls ``logger.exception(...)`` or
``logger.error("... %s", exc)`` and carries on never reaches
``sys.excepthook``: nothing re-raises it. This integration forwards those
errors through the same client every other capture path uses, so they get the
same ``ignored_errors``, ``before_send``, deduplication and transport.

How it hooks in: ``logging.Logger.callHandlers`` is wrapped once per process.
The original runs first, unchanged, so every handler (and Python's
``lastResort`` handler when none is configured) writes exactly what it wrote
before; nothing is added to the root logger, so ``logging.basicConfig()``
still works after ``bugstack.init()``.

What is forwarded: a record at ERROR or above that carries an exception,
either as ``exc_info`` (``logger.exception``, ``exc_info=True``) or as one of
its ``%`` arguments (``logger.error("failed: %s", exc)``). A record with no
exception is noise by default; ``capture_log_messages=True`` forwards it too,
as its message.

Not forwarded: BugStack's own ``bugstack`` logger, an exception the SDK
already reported, the same logging site and message again within five
minutes, and anything past 20 a minute per process. The report is anchored
at the logging call (its file, function and line), so each site is its own
issue. Redact fields are masked in the logged text. Never raises.
"""

from __future__ import annotations

import logging
import re
import threading
import time
from collections import OrderedDict
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Callable, Optional

from ..fingerprint import format_traceback, generate_fingerprint
from ..types import EnvironmentInfo, ErrorEvent

if TYPE_CHECKING:
    from ..client import BugStackClient

MAX_PER_MINUTE = 20
REPEAT_WINDOW_SECONDS = 300.0
_MAX_REMEMBERED = 500
_MESSAGE_MAX = 500
REPORTED_ATTR = "__bugstack_reported__"

_DEFAULT_REDACT = (
    "password", "secret", "token", "apikey", "api_key", "authorization",
    "auth", "credential", "private", "credit_card", "card_number", "cvv", "ssn",
)

_lock = threading.Lock()
_busy = threading.local()
_original_call_handlers: Optional[Callable[..., Any]] = None
_client: Optional["BugStackClient"] = None
_capture_messages = False
_window_start = 0.0
_in_window = 0
_last_sent: "OrderedDict[str, float]" = OrderedDict()
_now: Callable[[], float] = time.monotonic
_stdlib_call_handlers = logging.Logger.callHandlers

stats: "dict[str, int]" = {"forwarded": 0, "message_only": 0}
dropped: "dict[str, int]" = {}


def logging_stats() -> "dict[str, Any]":
    """Forwarded and dropped counts since the process started, dropped counted per rule."""
    return {**stats, "dropped": dict(dropped)}


def mark_reported(exc: BaseException) -> None:
    """Say this exception was already sent, so a log record for it is not sent again."""
    try:
        setattr(exc, REPORTED_ATTR, True)
    except Exception:
        pass


def _drop(rule: str) -> None:
    dropped[rule] = dropped.get(rule, 0) + 1


def redact_text(text: str, fields: "list[str] | tuple[str, ...]") -> str:
    """Mask ``field=value`` / ``field: value`` for each redact field, and bearer tokens."""
    out = re.sub(
        r"\b(Bearer|Basic)\s+[A-Za-z0-9._~+/=-]{8,}", r"\1 [REDACTED]", text, flags=re.IGNORECASE
    )
    names = "|".join(re.escape(f) for f in fields if f)
    if names:
        out = re.sub(
            r"([\"']?\b\w*(?:" + names + r")\w*[\"']?\s*[=:]\s*)(\"[^\"]*\"|'[^']*'|[^\s,;&)}\]]+)",
            r"\1[REDACTED]",
            out,
            flags=re.IGNORECASE,
        )
    return out


def _exception_of(record: logging.LogRecord) -> Optional[BaseException]:
    exc_info = record.exc_info
    if isinstance(exc_info, tuple) and len(exc_info) > 1:
        if isinstance(exc_info[1], BaseException):
            return exc_info[1]
    args = record.args
    if isinstance(args, tuple):
        for a in args:
            if isinstance(a, BaseException):
                return a
    elif isinstance(args, dict):
        for a in args.values():
            if isinstance(a, BaseException):
                return a
    return None


def _forward(record: logging.LogRecord) -> None:
    global _window_start, _in_window
    client = _client
    if client is None:
        return
    if record.levelno < logging.ERROR:
        return
    if record.name == "bugstack" or record.name.startswith("bugstack."):
        _drop("sdk_logger")
        return
    exc = _exception_of(record)
    if exc is None and not _capture_messages:
        _drop("no_exception")
        return
    if exc is not None and getattr(exc, REPORTED_ATTR, False):
        _drop("already_reported")
        return
    try:
        text = record.getMessage()
    except Exception:
        text = str(record.msg)
    site = f"{record.pathname}:{record.lineno}"
    key = f"{site}|message-only" if exc is None else f"{site}|{type(exc).__name__}: {exc}"
    with _lock:
        now = _now()
        last = _last_sent.get(key)
        if last is not None and now - last < REPEAT_WINDOW_SECONDS:
            _drop("repeat")
            return
        if now - _window_start >= 60.0:
            _window_start = now
            _in_window = 0
        if _in_window >= MAX_PER_MINUTE:
            _drop("rate_limited")
            return
        _in_window += 1
        _last_sent[key] = now
        _last_sent.move_to_end(key)
        while len(_last_sent) > _MAX_REMEMBERED:
            _last_sent.popitem(last=False)
    if exc is not None:
        mark_reported(exc)

    cfg = client.config
    fields = list(_DEFAULT_REDACT) + list(cfg.redact_fields)
    if exc is None:
        message = text
    else:
        exc_text = f"{type(exc).__name__}: {exc}"
        message = exc_text if not text or text == str(exc) else f"{text}: {exc_text}"
    metadata: "dict[str, Any]" = {
        "source": "logging",
        "handled": True,
        "logger": record.name,
        "level": record.levelname,
        "logSite": {"file": record.pathname, "function": record.funcName, "line": record.lineno},
    }
    if exc is None:
        metadata["messageOnly"] = True
    else:
        metadata["causeName"] = type(exc).__name__
    event = ErrorEvent(
        message=redact_text(message, fields)[:_MESSAGE_MAX],
        stack_trace=redact_text(format_traceback(exc), fields) if exc is not None else "",
        file=record.pathname,
        function=record.funcName,
        exception_type="LoggedError",
        fingerprint=generate_fingerprint(
            type(exc).__name__ if exc is not None else "LoggedError",
            record.pathname,
            record.funcName,
            record.lineno,
        ),
        environment=EnvironmentInfo(),
        timestamp=datetime.now(timezone.utc).isoformat(),
        metadata=metadata,
    )
    if client.send_event(event, exc):
        stats["forwarded"] += 1
        if exc is None:
            stats["message_only"] += 1


def _call_handlers_with_bugstack(self: logging.Logger, record: logging.LogRecord) -> None:
    original = _original_call_handlers or _stdlib_call_handlers
    original(self, record)
    if getattr(_busy, "active", False):
        return
    _busy.active = True
    try:
        _forward(record)
    except Exception:
        pass  # a log line was written; forwarding is best-effort
    finally:
        _busy.active = False


def install(client: "BugStackClient", capture_messages: bool = False) -> None:
    """Forward logged errors to ``client``. Idempotent: a second call swaps the client."""
    global _original_call_handlers, _client, _capture_messages
    with _lock:
        _client = client
        _capture_messages = capture_messages
        if _original_call_handlers is None:
            _original_call_handlers = logging.Logger.callHandlers
            logging.Logger.callHandlers = _call_handlers_with_bugstack  # type: ignore[method-assign]


def uninstall(client: Optional["BugStackClient"] = None) -> None:
    """Stop forwarding (for ``client`` only, when given) and restore ``Logger.callHandlers``."""
    global _original_call_handlers, _client
    with _lock:
        if client is not None and _client is not client:
            return
        _client = None
        ours = logging.Logger.callHandlers is _call_handlers_with_bugstack
        if _original_call_handlers is not None and ours:
            logging.Logger.callHandlers = _original_call_handlers  # type: ignore[method-assign]
            _original_call_handlers = None


def _reset_for_tests(now: Callable[[], float] = time.monotonic) -> None:
    global _window_start, _in_window, _last_sent, _now
    uninstall()
    _window_start = 0.0
    _in_window = 0
    _last_sent = OrderedDict()
    _now = now
    stats["forwarded"] = 0
    stats["message_only"] = 0
    dropped.clear()
