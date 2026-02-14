"""Tests for bugstack.fingerprint module."""

import time
import threading

from bugstack.fingerprint import (
    Deduplicator,
    extract_error_location,
    format_traceback,
    generate_fingerprint,
)
from helpers import make_exception


class TestGenerateFingerprint:
    def test_produces_hex_string(self):
        fp = generate_fingerprint("ValueError", "app.py", "handler")
        assert isinstance(fp, str)
        assert len(fp) == 16
        # Should be valid hex
        int(fp, 16)

    def test_stable_same_inputs(self):
        a = generate_fingerprint("ValueError", "app.py", "handler", 42)
        b = generate_fingerprint("ValueError", "app.py", "handler", 42)
        assert a == b

    def test_different_inputs_different_hash(self):
        a = generate_fingerprint("ValueError", "app.py", "handler", 42)
        b = generate_fingerprint("TypeError", "app.py", "handler", 42)
        assert a != b

    def test_line_number_optional(self):
        a = generate_fingerprint("ValueError", "app.py", "handler")
        b = generate_fingerprint("ValueError", "app.py", "handler", 10)
        assert a != b

    def test_empty_strings(self):
        fp = generate_fingerprint("", "", "")
        assert isinstance(fp, str)
        assert len(fp) == 16


class TestExtractErrorLocation:
    def test_extracts_from_traceback(self):
        exc = make_exception("test error", ValueError)
        exc_type, file, function, line = extract_error_location(exc)
        assert exc_type == "ValueError"
        assert file.endswith("helpers.py")
        assert function == "make_exception"
        assert isinstance(line, int)
        assert line > 0

    def test_no_traceback(self):
        exc = ValueError("no tb")
        exc_type, file, function, line = extract_error_location(exc)
        assert exc_type == "ValueError"
        assert file == ""
        assert function == ""
        assert line is None

    def test_nested_exception(self):
        """Extracts from the innermost frame."""
        def inner():
            raise RuntimeError("inner error")

        def outer():
            inner()

        try:
            outer()
        except RuntimeError as exc:
            exc_type, file, function, line = extract_error_location(exc)
            assert exc_type == "RuntimeError"
            assert function == "inner"


class TestFormatTraceback:
    def test_includes_exception_message(self):
        exc = make_exception("format test")
        result = format_traceback(exc)
        assert "format test" in result
        assert "ValueError" in result

    def test_includes_file_info(self):
        exc = make_exception("file info")
        result = format_traceback(exc)
        assert "helpers.py" in result

    def test_no_traceback(self):
        exc = ValueError("no tb")
        result = format_traceback(exc)
        assert "ValueError" in result


class TestDeduplicator:
    def test_first_occurrence_allowed(self):
        dedup = Deduplicator(window=60.0)
        assert dedup.should_send("fp_abc") is True

    def test_duplicate_blocked(self):
        dedup = Deduplicator(window=60.0)
        dedup.should_send("fp_abc")
        assert dedup.should_send("fp_abc") is False

    def test_different_fingerprints_allowed(self):
        dedup = Deduplicator(window=60.0)
        assert dedup.should_send("fp_1") is True
        assert dedup.should_send("fp_2") is True

    def test_expired_entry_allowed(self):
        dedup = Deduplicator(window=0.01)  # 10ms window
        dedup.should_send("fp_abc")
        time.sleep(0.02)  # Wait for window to expire
        assert dedup.should_send("fp_abc") is True

    def test_clear(self):
        dedup = Deduplicator(window=60.0)
        dedup.should_send("fp_abc")
        dedup.clear()
        assert dedup.should_send("fp_abc") is True

    def test_thread_safety(self):
        dedup = Deduplicator(window=60.0)
        results = []

        def send(fp):
            results.append(dedup.should_send(fp))

        threads = [threading.Thread(target=send, args=(f"fp_{i}",)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All unique fingerprints should be allowed
        assert all(results)
