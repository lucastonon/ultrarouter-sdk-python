"""Shared pytest fixtures.

* Unit tests never see the developer's real ``ULTRAROUTER_*`` / ``UR_*`` environment.
* ``mock_gateway`` is a real HTTP server (``tests/support/mock_gateway.py``) on a free local port.
* ``sandbox_network`` reroutes every httpx request, whatever its host, to the mock gateway, so
  documentation snippets that show the hosted URL still run offline.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import httpx
import pytest

SUPPORT = Path(__file__).resolve().parent / "support"
sys.path.insert(0, str(SUPPORT))

from mock_gateway import STATE, start_in_thread  # noqa: E402

ENV_VARS = (
    "ULTRAROUTER_API_KEY",
    "UR_API_KEY",
    "ULTRAROUTER_BASE_URL",
    "UR_BASE_URL",
    "UR_BENCH",
    "UR_BENCH_RUN",
    "UR_BENCH_TRACE",
)

TEST_KEY = "ur_sk_test_mock"


@pytest.fixture(autouse=True)
def _isolated_env(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    if request.node.get_closest_marker("integration") is not None:
        return
    for name in ENV_VARS:
        monkeypatch.delenv(name, raising=False)


class MockGateway:
    """Handle on the running mock gateway."""

    def __init__(self, url: str) -> None:
        self.url = url

    def reset(self) -> None:
        """Clear recorded requests and state."""
        STATE.reset()

    @property
    def requests(self) -> list[dict[str, Any]]:
        """Requests recorded since the last reset."""
        with STATE.lock:
            return list(STATE.requests)

    def slow(
        self,
        path: str,
        *,
        header_delay: float = 0.0,
        chunk_delay: float = 0.0,
        chunks: int = 8,
        times: int = 1,
    ) -> None:
        """Make the next ``times`` responses for ``path`` slow (see the mock's docstring)."""
        with STATE.lock:
            STATE.slow.append(
                {
                    "path": path,
                    "header_delay": header_delay,
                    "chunk_delay": chunk_delay,
                    "chunks": chunks,
                    "times": times,
                }
            )

    def fail(
        self,
        path: str,
        *,
        status: int = 503,
        code: str = "provider_unavailable",
        times: int = 1,
        **extra: Any,
    ) -> None:
        """Make the next ``times`` requests to ``path`` fail."""
        with STATE.lock:
            STATE.failures.append(
                {"path": path, "status": status, "code": code, "times": times, **extra}
            )


@pytest.fixture(scope="session")
def _mock_server() -> Iterator[str]:
    server, url = start_in_thread()
    try:
        yield url
    finally:
        server.shutdown()
        server.server_close()


@pytest.fixture
def mock_gateway(_mock_server: str) -> MockGateway:
    """A fresh (reset) mock gateway for one test."""
    STATE.reset()
    return MockGateway(_mock_server)


@pytest.fixture
def gateway_env(mock_gateway: MockGateway, monkeypatch: pytest.MonkeyPatch) -> MockGateway:
    """Point ``ULTRAROUTER_BASE_URL`` / ``ULTRAROUTER_API_KEY`` at the mock gateway."""
    monkeypatch.setenv("ULTRAROUTER_BASE_URL", mock_gateway.url)
    monkeypatch.setenv("ULTRAROUTER_API_KEY", TEST_KEY)
    return mock_gateway


@pytest.fixture
def sandbox_network(gateway_env: MockGateway, monkeypatch: pytest.MonkeyPatch) -> MockGateway:
    """Reroute every outgoing httpx request to the mock gateway (no real network).

    Requests to ``*.test`` hosts are left alone so mocking libraries can intercept them.
    """
    target = httpx.URL(gateway_env.url)
    original_sync = httpx.HTTPTransport.handle_request
    original_async = httpx.AsyncHTTPTransport.handle_async_request

    def reroute(request: httpx.Request) -> None:
        # Hosts under the reserved ".test" TLD belong to mocking examples (respx); leave them alone.
        if request.url.host.endswith(".test"):
            return
        request.url = request.url.copy_with(
            scheme=target.scheme, host=target.host, port=target.port
        )
        request.headers["host"] = f"{target.host}:{target.port}"

    def handle(self: httpx.HTTPTransport, request: httpx.Request) -> httpx.Response:
        reroute(request)
        return original_sync(self, request)

    async def handle_async(
        self: httpx.AsyncHTTPTransport, request: httpx.Request
    ) -> httpx.Response:
        reroute(request)
        return await original_async(self, request)

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", handle)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", handle_async)
    return gateway_env


def pytest_report_header(config: pytest.Config) -> str:
    """Show whether the live-gateway integration suite will run."""
    live = bool(os.environ.get("ULTRAROUTER_API_KEY") and os.environ.get("ULTRAROUTER_BASE_URL"))
    return f"integration suite: {'enabled' if live else 'skipped (set ULTRAROUTER_API_KEY and ULTRAROUTER_BASE_URL)'}"
