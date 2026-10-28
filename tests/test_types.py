"""Tests for bugstack.types module."""

from bugstack.types import (
    BugStackConfig,
    EnvironmentInfo,
    ErrorEvent,
    RequestContext,
    SDK_VERSION,
)


class TestBugStackConfig:
    def test_defaults(self):
        config = BugStackConfig(api_key="bs_test_123")
        assert config.api_key == "bs_test_123"
        assert config.endpoint == "https://dashboard.bugstack.ai/api/ingest/sdk"
        assert config.environment == "production"
        assert config.auto_fix is False
        assert config.enabled is True
        assert config.debug is False
        assert config.dry_run is False
        assert config.deduplication_window == 300.0
        assert config.timeout == 5.0
        assert config.max_retries == 3
        assert config.ignored_errors == []
        assert config.before_send is None
        assert config.redact_fields == []

    def test_custom_values(self):
        config = BugStackConfig(
            api_key="bs_test_xyz",
            endpoint="https://custom.api.dev",
            environment="staging",
            auto_fix=True,
            enabled=False,
        )
        assert config.endpoint == "https://custom.api.dev"
        assert config.environment == "staging"
        assert config.auto_fix is True
        assert config.enabled is False


class TestRequestContext:
    def test_defaults(self):
        ctx = RequestContext()
        assert ctx.route == ""
        assert ctx.method == ""
        assert ctx.query_params is None
        assert ctx.headers is None
        assert ctx.body is None

    def test_custom_values(self):
        ctx = RequestContext(
            route="/api/users",
            method="POST",
            query_params={"page": "1"},
        )
        assert ctx.route == "/api/users"
        assert ctx.method == "POST"
        assert ctx.query_params == {"page": "1"}


class TestEnvironmentInfo:
    def test_defaults(self):
        env = EnvironmentInfo()
        assert env.language == "python"
        assert env.language_version  # non-empty
        assert env.sdk_version == SDK_VERSION
        assert env.os  # non-empty

    def test_custom_framework(self):
        env = EnvironmentInfo(framework="fastapi", framework_version="0.109.0")
        assert env.framework == "fastapi"
        assert env.framework_version == "0.109.0"


class TestErrorEvent:
    def test_to_payload_minimal(self):
        config = BugStackConfig(api_key="bs_test_key")
        event = ErrorEvent(
            message="something broke",
            stack_trace="Traceback ...",
            file="app.py",
            function="handler",
            fingerprint="abc123",
            exception_type="ValueError",
            timestamp="2026-01-01T00:00:00+00:00",
        )

        payload = event.to_payload(config)

        assert payload["apiKey"] == "bs_test_key"
        assert payload["error"]["message"] == "something broke"
        assert payload["error"]["stackTrace"] == "Traceback ..."
        assert payload["error"]["file"] == "app.py"
        assert payload["error"]["function"] == "handler"
        assert payload["error"]["fingerprint"] == "abc123"
        assert payload["environment"]["language"] == "python"
        assert payload["environment"]["sdkVersion"] == SDK_VERSION
        assert payload["timestamp"] == "2026-01-01T00:00:00+00:00"
        assert "request" not in payload
        assert "metadata" not in payload

    def test_to_payload_with_request(self):
        config = BugStackConfig(api_key="bs_test_key")
        event = ErrorEvent(
            message="err",
            request=RequestContext(route="/api/users", method="GET"),
            timestamp="2026-01-01T00:00:00+00:00",
        )

        payload = event.to_payload(config)
        assert payload["request"]["route"] == "/api/users"
        assert payload["request"]["method"] == "GET"

    def test_to_payload_with_project_id(self):
        config = BugStackConfig(api_key="bs_test_key", project_id="proj_123")
        event = ErrorEvent(message="err", timestamp="2026-01-01T00:00:00+00:00")

        payload = event.to_payload(config)
        assert payload["projectId"] == "proj_123"

    def test_to_payload_with_metadata(self):
        config = BugStackConfig(api_key="bs_test_key")
        event = ErrorEvent(
            message="err",
            metadata={"user_id": "42"},
            timestamp="2026-01-01T00:00:00+00:00",
        )

        payload = event.to_payload(config)
        assert payload["metadata"]["user_id"] == "42"

    def test_to_payload_auto_fix_flag(self):
        config = BugStackConfig(api_key="bs_test_key", auto_fix=True)
        event = ErrorEvent(message="err", timestamp="2026-01-01T00:00:00+00:00")

        payload = event.to_payload(config)
        assert payload["metadata"]["autoFix"] is True
