"""Tests for bugstack.integrations.django module."""

import pytest

django = pytest.importorskip("django")

import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.integrations.django_settings")

import django as dj
dj.setup()

import bugstack
from bugstack.integrations.django import BugStackMiddleware


class TestDjangoMiddleware:
    def test_init_ensures_initialized(self):
        """Middleware should auto-initialize from Django settings."""
        bugstack._client = None  # Reset
        middleware = BugStackMiddleware(get_response=lambda r: r)
        # Should have auto-initialized from django_settings
        client = bugstack.get_client()
        assert client is not None
        assert client.config.api_key == "bs_test_django_key"

    def test_process_exception_captures(self, capsys):
        bugstack.init(api_key="bs_test_key", dry_run=True)
        middleware = BugStackMiddleware(get_response=lambda r: r)

        class FakeRequest:
            path = "/api/users"
            method = "GET"
            resolver_match = None

        exc = ValueError("django test error")
        try:
            raise exc
        except ValueError as e:
            middleware.process_exception(FakeRequest(), e)

        output = capsys.readouterr().out
        assert "[BugStack DryRun]" in output

    def test_process_exception_extracts_route(self, capsys):
        bugstack.init(api_key="bs_test_key", dry_run=True)
        middleware = BugStackMiddleware(get_response=lambda r: r)

        class FakeResolverMatch:
            route = "api/users/<int:pk>"

        class FakeRequest:
            path = "/api/users/42"
            method = "POST"
            resolver_match = FakeResolverMatch()

        exc = RuntimeError("route test")
        try:
            raise exc
        except RuntimeError as e:
            middleware.process_exception(FakeRequest(), e)

        output = capsys.readouterr().out
        assert "[BugStack DryRun]" in output

    def test_call_passes_through(self):
        """__call__ should just call get_response."""
        responses = []

        def get_response(request):
            responses.append(request)
            return "response"

        middleware = BugStackMiddleware(get_response=get_response)
        result = middleware({"type": "test"})
        assert result == "response"
        assert len(responses) == 1
