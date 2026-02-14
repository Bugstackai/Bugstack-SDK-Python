"""Tests for bugstack.client module."""

import pytest

from bugstack.client import BugStackClient
from bugstack.types import BugStackConfig, ErrorEvent, RequestContext
from helpers import make_exception


class TestBugStackClient:
    def test_capture_returns_true(self, client):
        exc = make_exception("test error")
        assert client.capture_exception(exc) is True

    def test_capture_disabled(self):
        config = BugStackConfig(api_key="bs_test_123", enabled=False)
        c = BugStackClient(config)
        exc = make_exception("disabled test")
        assert c.capture_exception(exc) is False

    def test_capture_with_request_context(self, client):
        exc = make_exception("req test")
        ctx = RequestContext(route="/api/users", method="GET")
        assert client.capture_exception(exc, request=ctx) is True

    def test_capture_with_metadata(self, client):
        exc = make_exception("meta test")
        assert client.capture_exception(exc, metadata={"user_id": "42"}) is True

    def test_deduplication(self, client):
        exc = make_exception("dedup test")
        assert client.capture_exception(exc) is True
        # Same exception again should be deduplicated
        assert client.capture_exception(exc) is False

    def test_different_errors_not_deduplicated(self, client):
        exc1 = make_exception("error one", ValueError)
        exc2 = make_exception("error two", TypeError)
        assert client.capture_exception(exc1) is True
        assert client.capture_exception(exc2) is True


class TestIgnoredErrors:
    def test_ignore_by_type(self):
        config = BugStackConfig(
            api_key="bs_test_123",
            dry_run=True,
            ignored_errors=[ValueError],
        )
        c = BugStackClient(config)
        exc = make_exception("ignored", ValueError)
        assert c.capture_exception(exc) is False

    def test_ignore_by_message(self):
        config = BugStackConfig(
            api_key="bs_test_123",
            dry_run=True,
            ignored_errors=["expected error"],
        )
        c = BugStackClient(config)
        exc = make_exception("expected error")
        assert c.capture_exception(exc) is False

    def test_non_ignored_passes_through(self):
        config = BugStackConfig(
            api_key="bs_test_123",
            dry_run=True,
            ignored_errors=[TypeError],
        )
        c = BugStackClient(config)
        exc = make_exception("not ignored", ValueError)
        assert c.capture_exception(exc) is True

    def test_ignore_subclass(self):
        config = BugStackConfig(
            api_key="bs_test_123",
            dry_run=True,
            ignored_errors=[Exception],
        )
        c = BugStackClient(config)
        exc = make_exception("subclass", ValueError)  # ValueError is a subclass of Exception
        assert c.capture_exception(exc) is False


class TestBeforeSend:
    def test_drop_event(self):
        def drop_all(event: ErrorEvent):
            return None

        config = BugStackConfig(
            api_key="bs_test_123",
            dry_run=True,
            before_send=drop_all,
        )
        c = BugStackClient(config)
        exc = make_exception("dropped")
        assert c.capture_exception(exc) is False

    def test_modify_event(self):
        def add_tag(event: ErrorEvent):
            event.metadata["tag"] = "modified"
            return event

        config = BugStackConfig(
            api_key="bs_test_123",
            dry_run=True,
            before_send=add_tag,
        )
        c = BugStackClient(config)
        exc = make_exception("modified")
        assert c.capture_exception(exc) is True

    def test_passthrough(self):
        calls = []

        def spy(event: ErrorEvent):
            calls.append(event)
            return event

        config = BugStackConfig(
            api_key="bs_test_123",
            dry_run=True,
            before_send=spy,
        )
        c = BugStackClient(config)
        exc = make_exception("spy test")
        c.capture_exception(exc)
        assert len(calls) == 1
        assert calls[0].message == "spy test"


class TestNeverCrash:
    def test_capture_never_raises(self, client):
        """capture_exception should never raise, even with broken input."""
        # Pass something that's not a proper exception
        result = client.capture_exception(ValueError())  # No traceback
        # Should not crash — either True or False is fine
        assert isinstance(result, bool)

    def test_before_send_exception_handled(self):
        def broken_hook(event):
            raise RuntimeError("hook exploded")

        config = BugStackConfig(
            api_key="bs_test_123",
            dry_run=True,
            before_send=broken_hook,
        )
        c = BugStackClient(config)
        exc = make_exception("crash test")
        # Should not raise
        result = c.capture_exception(exc)
        assert result is False


class TestDryRun:
    def test_dry_run_returns_true(self, capsys):
        config = BugStackConfig(
            api_key="bs_test_123",
            dry_run=True,
        )
        c = BugStackClient(config)
        exc = make_exception("dry run test")
        result = c.capture_exception(exc)
        assert result is True

        output = capsys.readouterr().out
        assert "[BugStack DryRun]" in output
        assert "dry run test" in output

    def test_dry_run_no_transport(self):
        config = BugStackConfig(
            api_key="bs_test_123",
            dry_run=True,
        )
        c = BugStackClient(config)
        assert c._transport is None


class TestShutdown:
    def test_shutdown_is_safe(self, client):
        client.shutdown()
        # Should be safe to call twice
        client.shutdown()

    def test_config_property(self, client, config):
        assert client.config is config
