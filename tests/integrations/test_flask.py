"""Tests for bugstack.integrations.flask module."""

import pytest

flask = pytest.importorskip("flask")

import bugstack
from bugstack.integrations.flask import init_app


class TestFlaskIntegration:
    def test_registers_error_handler(self, capsys):
        app = flask.Flask(__name__)
        bugstack.init(api_key="bs_test_key", dry_run=True)
        init_app(app)

        @app.route("/fail")
        def fail():
            raise ValueError("flask test error")

        client = app.test_client()
        # Our handler re-raises so Flask propagates the exception
        try:
            client.get("/fail")
        except Exception:
            pass

        output = capsys.readouterr().out
        assert "[BugStack DryRun]" in output
        assert "flask test error" in output

    def test_captures_exception(self, capsys):
        app = flask.Flask(__name__)
        app.config["TESTING"] = True
        bugstack.init(api_key="bs_test_key", dry_run=True)
        init_app(app)

        @app.route("/fail")
        def fail():
            raise ValueError("flask capture test")

        client = app.test_client()
        try:
            client.get("/fail")
        except ValueError:
            pass

        output = capsys.readouterr().out
        assert "[BugStack DryRun]" in output

    def test_normal_routes_unaffected(self):
        app = flask.Flask(__name__)
        bugstack.init(api_key="bs_test_key", dry_run=True)
        init_app(app)

        @app.route("/ok")
        def ok():
            return "OK"

        client = app.test_client()
        response = client.get("/ok")
        assert response.status_code == 200
        assert response.data == b"OK"
