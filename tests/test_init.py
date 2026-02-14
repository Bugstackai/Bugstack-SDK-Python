"""Tests for bugstack top-level API."""

import warnings

import bugstack
from bugstack.types import SDK_VERSION, RequestContext
from helpers import make_exception


class TestInit:
    def test_returns_client(self):
        client = bugstack.init(api_key="bs_test_key", dry_run=True)
        assert client is not None
        assert client.config.api_key == "bs_test_key"

    def test_sets_global_client(self):
        bugstack.init(api_key="bs_test_key", dry_run=True)
        assert bugstack.get_client() is not None

    def test_reinit_shuts_down_previous(self):
        c1 = bugstack.init(api_key="bs_test_key_1", dry_run=True)
        c2 = bugstack.init(api_key="bs_test_key_2", dry_run=True)
        assert bugstack.get_client() is c2
        assert c1 is not c2

    def test_all_config_params(self):
        client = bugstack.init(
            api_key="bs_test_key",
            endpoint="https://custom.api.dev",
            project_id="proj_123",
            environment="staging",
            auto_fix=True,
            enabled=True,
            debug=False,
            dry_run=True,
            deduplication_window=120.0,
            timeout=10.0,
            max_retries=5,
            ignored_errors=[ValueError],
            redact_fields=["password"],
        )
        cfg = client.config
        assert cfg.endpoint == "https://custom.api.dev"
        assert cfg.project_id == "proj_123"
        assert cfg.environment == "staging"
        assert cfg.auto_fix is True
        assert cfg.deduplication_window == 120.0
        assert cfg.timeout == 10.0
        assert cfg.max_retries == 5
        assert cfg.ignored_errors == [ValueError]
        assert cfg.redact_fields == ["password"]


class TestCaptureException:
    def test_capture_initialized(self):
        bugstack.init(api_key="bs_test_key", dry_run=True)
        exc = make_exception("capture test")
        assert bugstack.capture_exception(exc) is True

    def test_capture_not_initialized(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = bugstack.capture_exception(ValueError("no init"))
            assert result is False
            assert len(w) == 1
            assert "not initialized" in str(w[0].message).lower()

    def test_capture_from_sys_exc_info(self):
        bugstack.init(api_key="bs_test_key", dry_run=True)
        try:
            raise RuntimeError("caught in except")
        except RuntimeError:
            result = bugstack.capture_exception()
            assert result is True

    def test_capture_no_active_exception(self):
        bugstack.init(api_key="bs_test_key", dry_run=True)
        result = bugstack.capture_exception()
        assert result is False

    def test_capture_with_request(self):
        bugstack.init(api_key="bs_test_key", dry_run=True)
        exc = make_exception("request test")
        ctx = RequestContext(route="/api/health", method="GET")
        result = bugstack.capture_exception(exc, request=ctx)
        assert result is True

    def test_capture_with_metadata(self):
        bugstack.init(api_key="bs_test_key", dry_run=True)
        exc = make_exception("meta test")
        result = bugstack.capture_exception(exc, metadata={"user": "42"})
        assert result is True


class TestGetClient:
    def test_none_before_init(self):
        assert bugstack.get_client() is None

    def test_returns_client_after_init(self):
        bugstack.init(api_key="bs_test_key", dry_run=True)
        assert bugstack.get_client() is not None


class TestVersion:
    def test_version_exported(self):
        assert bugstack.__version__ == SDK_VERSION
