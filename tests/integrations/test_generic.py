"""Tests for bugstack.integrations.generic module."""

import sys
import threading

import bugstack
from bugstack.integrations.generic import (
    install_hooks,
    uninstall_hooks,
    _original_excepthook,
    _original_threading_excepthook,
)


class TestInstallHooks:
    def test_installs_sys_excepthook(self):
        original = sys.excepthook
        try:
            install_hooks()
            assert sys.excepthook is not original
            assert sys.excepthook.__name__ == "_bugstack_excepthook"
        finally:
            uninstall_hooks()

    def test_installs_threading_excepthook(self):
        if not hasattr(threading, "excepthook"):
            return  # Skip if Python < 3.8

        original = threading.excepthook
        try:
            install_hooks()
            assert threading.excepthook is not original
        finally:
            uninstall_hooks()

    def test_uninstall_restores_original(self):
        original_sys = sys.excepthook
        install_hooks()
        uninstall_hooks()
        assert sys.excepthook is _original_excepthook


class TestExcepthook:
    def test_captures_exception(self, capsys):
        bugstack.init(api_key="bs_test_key", dry_run=True)
        install_hooks()

        try:
            # Simulate an unhandled exception through the hook
            try:
                raise ValueError("unhandled test error")
            except ValueError as exc:
                # Call the hook directly (simulating what Python does)
                sys.excepthook(type(exc), exc, exc.__traceback__)

            output = capsys.readouterr().out
            assert "[BugStack DryRun]" in output
            assert "unhandled test error" in output
        finally:
            uninstall_hooks()

    def test_hook_never_crashes(self):
        """Even without init, the hook should not crash."""
        install_hooks()
        try:
            exc = ValueError("safe crash test")
            try:
                raise exc
            except ValueError:
                # Should not raise
                sys.excepthook(type(exc), exc, exc.__traceback__)
        finally:
            uninstall_hooks()
