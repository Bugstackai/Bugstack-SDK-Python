"""Tests for bugstack.transport module."""

import json
import time

import httpx
import pytest
import respx

from bugstack.transport import Transport
from bugstack.types import SDK_VERSION


class TestTransport:
    def test_enqueue_sends_payload(self):
        with respx.mock:
            route = respx.post("https://api.test.dev/capture").mock(
                return_value=httpx.Response(200, json={"ok": True})
            )

            transport = Transport(
                endpoint="https://api.test.dev/capture",
                api_key="bs_test_key",
                timeout=2.0,
                max_retries=1,
                debug=False,
            )

            transport.enqueue({"apiKey": "bs_test_key", "error": {"message": "test"}})

            # Wait for background worker to process
            time.sleep(1.5)
            transport.shutdown()

            assert route.called

    def test_sends_correct_headers(self):
        captured_headers = {}

        def capture_request(request):
            captured_headers.update(dict(request.headers))
            return httpx.Response(200)

        with respx.mock:
            respx.post("https://api.test.dev/capture").mock(side_effect=capture_request)

            transport = Transport(
                endpoint="https://api.test.dev/capture",
                api_key="bs_test_key",
            )

            transport.enqueue({"test": True})
            time.sleep(1.5)
            transport.shutdown()

            assert captured_headers.get("x-bugstack-api-key") == "bs_test_key"
            assert captured_headers.get("x-bugstack-sdk-version") == SDK_VERSION
            assert captured_headers.get("content-type") == "application/json"

    def test_retry_on_failure(self):
        call_count = 0

        def fail_then_succeed(request):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return httpx.Response(500, text="Internal Server Error")
            return httpx.Response(200)

        with respx.mock:
            respx.post("https://api.test.dev/capture").mock(side_effect=fail_then_succeed)

            transport = Transport(
                endpoint="https://api.test.dev/capture",
                api_key="bs_test_key",
                max_retries=3,
            )

            transport.enqueue({"test": True})
            time.sleep(5)  # Allow time for retry with backoff
            transport.shutdown()

            assert call_count >= 2

    def test_queue_bounded(self):
        transport = Transport(
            endpoint="https://api.test.dev/capture",
            api_key="bs_test_key",
        )

        # Enqueue more than 100 items
        for i in range(150):
            transport.enqueue({"index": i})

        with transport._queue_lock:
            assert len(transport._queue) <= 100

        transport.shutdown()

    def test_shutdown_stops_worker(self):
        transport = Transport(
            endpoint="https://api.test.dev/capture",
            api_key="bs_test_key",
        )
        transport.shutdown()
        assert not transport._worker_thread.is_alive()


class TestTransportAsync:
    @pytest.mark.asyncio
    async def test_send_async(self):
        with respx.mock:
            route = respx.post("https://api.test.dev/capture").mock(
                return_value=httpx.Response(200, json={"ok": True})
            )

            transport = Transport(
                endpoint="https://api.test.dev/capture",
                api_key="bs_test_key",
                max_retries=1,
            )

            result = await transport.send_async({"apiKey": "key", "error": {"message": "async test"}})
            transport.shutdown()

            assert result is True
            assert route.called

    @pytest.mark.asyncio
    async def test_send_async_retry(self):
        call_count = 0

        def fail_then_succeed(request):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return httpx.Response(500)
            return httpx.Response(200)

        with respx.mock:
            respx.post("https://api.test.dev/capture").mock(side_effect=fail_then_succeed)

            transport = Transport(
                endpoint="https://api.test.dev/capture",
                api_key="bs_test_key",
                max_retries=3,
            )

            result = await transport.send_async({"test": True})
            transport.shutdown()

            assert result is True
            assert call_count >= 2
