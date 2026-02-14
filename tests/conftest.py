"""Shared test fixtures for BugStack SDK tests."""

import pytest
import bugstack
from bugstack.client import BugStackClient
from bugstack.types import BugStackConfig


@pytest.fixture(autouse=True)
def _reset_global_client():
    """Reset the global client between tests."""
    bugstack._client = None
    yield
    if bugstack._client is not None:
        bugstack._client.shutdown()
        bugstack._client = None


@pytest.fixture
def config():
    """A basic test config with transport disabled."""
    return BugStackConfig(
        api_key="bs_test_abc123",
        enabled=True,
        dry_run=True,  # prevent real HTTP
        debug=False,
    )


@pytest.fixture
def client(config):
    """A BugStack client in dry-run mode."""
    c = BugStackClient(config)
    yield c
    c.shutdown()


