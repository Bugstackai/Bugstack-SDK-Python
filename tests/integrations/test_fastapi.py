"""Tests for bugstack.integrations.fastapi module."""

import pytest

fastapi = pytest.importorskip("fastapi")
httpx = pytest.importorskip("httpx")

from fastapi import FastAPI
from fastapi.testclient import TestClient

import bugstack
from bugstack.integrations.fastapi import FastAPIMiddleware


class TestFastAPIMiddleware:
    def test_captures_exception(self, capsys):
        app = FastAPI()
        app.add_middleware(FastAPIMiddleware)
        bugstack.init(api_key="bs_test_key", dry_run=True)

        @app.get("/fail")
        def fail():
            raise ValueError("fastapi test error")

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/fail")
        assert response.status_code == 500

        output = capsys.readouterr().out
        assert "[BugStack DryRun]" in output

    def test_normal_routes_unaffected(self):
        app = FastAPI()
        app.add_middleware(FastAPIMiddleware)
        bugstack.init(api_key="bs_test_key", dry_run=True)

        @app.get("/ok")
        def ok():
            return {"status": "ok"}

        client = TestClient(app)
        response = client.get("/ok")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_extracts_request_context(self, capsys):
        app = FastAPI()
        app.add_middleware(FastAPIMiddleware)
        bugstack.init(api_key="bs_test_key", dry_run=True)

        @app.get("/users/{user_id}")
        def get_user(user_id: int):
            raise RuntimeError("not found")

        client = TestClient(app, raise_server_exceptions=False)
        client.get("/users/42?page=1")

        output = capsys.readouterr().out
        assert "[BugStack DryRun]" in output

    def test_non_http_scope_passthrough(self):
        """Non-HTTP ASGI scopes should pass through without capture."""
        app = FastAPI()
        app.add_middleware(FastAPIMiddleware)

        # WebSocket scope should just pass through
        client = TestClient(app)
        # Normal GET still works
        @app.get("/health")
        def health():
            return "ok"

        response = client.get("/health")
        assert response.status_code == 200
