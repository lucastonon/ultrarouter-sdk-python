"""HTTP transport shared by :class:`~ultrarouter.UltraRouter` and its async twin.

One request policy for both clients:

* a **total** time budget per call (``timeout``) that spans every retry and is enforced as a
  real deadline through connecting, waiting and reading the whole body, not only per network
  read (a server that drips a body slowly cannot stretch a call past it). A stream is
  different: ``timeout`` is the deadline for the response to start, then the longest wait for
  each next chunk;
* automatic retries (``max_retries``) for connection failures and 408/429/5xx responses that the
  gateway did not mark ``retryable: false``, with jittered exponential backoff that honours
  ``Retry-After``;
* an ``Idempotency-Key`` on every non-streaming ``POST``, stable across retries;
* non-2xx responses raised as typed :class:`~ultrarouter.UltraRouterError` subclasses.
"""

from __future__ import annotations

import asyncio
import contextlib
import contextvars
import json
import os
import random
import socket
import threading
import time
import warnings
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, TypedDict, TypeVar
from urllib.parse import quote

import httpx
import pydantic

from ._config import AUTOPILOT_ROUTER, ResolvedBench, resolve_bench
from ._constants import (
    API_KEY_ENV_VARS,
    BASE_URL_ENV_VARS,
    DEFAULT_MAX_RETRIES,
    DEFAULT_TIMEOUT_S,
    USER_AGENT,
)
from ._errors import (
    APIConnectionError,
    APIResponseValidationError,
    APITimeoutError,
    ConfigurationError,
    UltraRouterError,
    error_from_response,
)
from ._retry import capped_backoff, parse_retry_after, resolve_idempotency_key, should_retry

__all__ = [
    "AsyncAPIClient",
    "RequestOptions",
    "SyncAPIClient",
]

ModelT = TypeVar("ModelT", bound=pydantic.BaseModel)


class RequestOptions(TypedDict, total=False):
    """Per-call overrides accepted by every method as ``options=``.

    Keys:
        timeout: Total seconds for this call, across retries.
        max_retries: Automatic retries for this call.
        idempotency_key: Explicit ``Idempotency-Key`` for a ``POST`` (one is generated otherwise).
        extra_headers: Additional HTTP headers for this call.
        extra_query: Additional query-string parameters for this call.
    """

    timeout: float
    max_retries: int
    idempotency_key: str
    extra_headers: Mapping[str, str]
    extra_query: Mapping[str, Any]


@dataclass
class APIRequest:
    """A single prepared call for a client's low-level request surface.

    :class:`~ultrarouter.UltraRouter` and :class:`~ultrarouter.AsyncUltraRouter` expose
    ``request`` (the raw ``httpx`` response), ``request_json`` (the decoded body), ``request_model``
    (validated into a typed model) and ``request_text`` for endpoints the typed methods do not wrap
    — for example the native passthrough routes ``POST /v1/responses`` (OpenAI Responses API) and
    ``POST /v1/messages`` (Anthropic Messages API). Build one of these and pass it to the method
    that returns the shape you want. Authentication, the ``User-Agent``, JSON encoding, the per-call
    deadline, retries and the ``Idempotency-Key`` on a ``POST`` are added for you.

    Attributes:
        method: HTTP method (``"GET"``, ``"POST"``, ...).
        path: Request path starting at ``/v1`` (the client's base URL is prepended).
        query: Query-string parameters; keys whose value is ``None`` are dropped.
        body: JSON request body. A non-``None`` body is encoded and sent.
        has_body: Send ``body`` even when it is ``None`` (an explicit empty body); set
            automatically when ``body`` is not ``None``.
        content: Raw bytes to send instead of JSON-encoding ``body``.
        headers: Extra request headers (for example ``X-UR-Call-Type`` on a passthrough call).
        options: Per-call :class:`RequestOptions` (``timeout``, ``max_retries``,
            ``idempotency_key``, ``extra_headers``, ``extra_query``).
        stream: Keep the response body open for incremental reads.
        accept_not_modified: Treat a ``304`` as a success (conditional requests).
    """

    method: str
    path: str
    query: Mapping[str, Any] | None = None
    body: Any = None
    has_body: bool = False
    content: bytes | None = None
    headers: Mapping[str, str] = field(default_factory=dict)
    options: Mapping[str, Any] = field(default_factory=dict)
    stream: bool = False
    accept_not_modified: bool = False

    def __post_init__(self) -> None:
        # Direct construction convenience: a non-None body is sent as JSON. ``build()`` already
        # sets ``has_body`` explicitly (including for a deliberate ``None`` body), so it is a no-op
        # there; it only helps callers who construct an APIRequest by hand.
        if self.body is not None and not self.has_body:
            self.has_body = True


def encode_path_segment(segment: str) -> str:
    """Percent-encode one path segment (ids, slugs) so it can never alter the route."""
    return quote(str(segment), safe="")


def _clean_query(
    query: Mapping[str, Any] | None,
) -> list[tuple[str, str | int | float | bool | None]]:
    pairs: list[tuple[str, str | int | float | bool | None]] = []
    if not query:
        return pairs
    for key, value in query.items():
        if value is None:
            continue
        if isinstance(value, bool):
            pairs.append((key, "true" if value else "false"))
        elif isinstance(value, (list, tuple)):
            pairs.extend((key, str(item)) for item in value)
        else:
            pairs.append((key, str(value)))
    return pairs


def _resolve_api_key(explicit: str | None) -> str:
    if explicit:
        return explicit
    for name in API_KEY_ENV_VARS:
        value = os.environ.get(name)
        if value:
            return value
    raise ConfigurationError(
        "missing API key: pass api_key=... or set the ULTRAROUTER_API_KEY environment variable",
        code="missing_api_key",
    )


def _resolve_base_url(explicit: str | None) -> str:
    url = explicit
    if not url:
        for name in BASE_URL_ENV_VARS:
            value = os.environ.get(name)
            if value:
                url = value
                break
    if not url:
        raise ConfigurationError(
            "no gateway base URL configured: pass base_url= or set ULTRAROUTER_BASE_URL "
            "(or UR_BASE_URL). There is no default gateway to fall back to; for a local "
            "gateway use http://localhost:8080",
            code="missing_base_url",
        )
    url = url.rstrip("/")
    # Accept an OpenAI-style base URL ending in /v1: every SDK path already starts with /v1.
    if url.endswith("/v1"):
        url = url[: -len("/v1")]
    return url


def _safe_json(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        text = response.text
        return {"error": {"message": text}} if text else {}


def parse_model(model: type[ModelT], data: Any, *, status: int = 0) -> ModelT:
    """Validate ``data`` into ``model``; raise :class:`~ultrarouter.APIResponseValidationError`."""
    try:
        return model.model_validate(data)
    except pydantic.ValidationError as exc:
        raise APIResponseValidationError(
            f"response did not match {model.__name__}: {exc.error_count()} validation error(s); "
            f"first: {exc.errors()[0].get('loc')} {exc.errors()[0].get('msg')}",
            status=status,
            body=data,
        ) from exc


class _DeadlineExceeded(Exception):
    """Internal: the call's deadline passed before the transport finished."""


#: Most request threads one synchronous client (with its ``with_options`` copies) runs at once.
#: Each in-flight call holds one; a timed-out call's thread is stopped and frees its slot.
MAX_REQUEST_THREADS = 100


class _WorkerSlots:
    """A bounded count of request threads, shared by a client and its ``with_options`` copies."""

    def __init__(self, limit: int = MAX_REQUEST_THREADS) -> None:
        self.limit = limit
        self._free = limit
        self._condition = threading.Condition()

    def acquire(self, timeout: float) -> bool:
        """Take a slot, waiting at most ``timeout`` seconds; False if none became free."""
        with self._condition:
            return self._condition.wait_for(lambda: self._free > 0, max(0.0, timeout)) and (
                self._take()
            )

    def _take(self) -> bool:
        self._free -= 1
        return True

    def release(self) -> None:
        """Give a slot back."""
        with self._condition:
            self._free = min(self.limit, self._free + 1)
            self._condition.notify()

    def free(self) -> int:
        """Slots currently free."""
        with self._condition:
            return self._free


@dataclass
class _Transfer:
    """Shared state between a waiting caller and its request thread."""

    lock: threading.Lock = field(default_factory=threading.Lock)
    done: threading.Event = field(default_factory=threading.Event)
    response: httpx.Response | None = None
    value: httpx.Response | None = None
    error: BaseException | None = None
    abandoned: bool = False


def _close_quietly(response: httpx.Response) -> None:
    with contextlib.suppress(Exception):  # best-effort cleanup of an abandoned response
        response.close()


def _interrupt(response: httpx.Response) -> None:
    """Stop a transfer another thread is reading: shut its socket down so the read returns.

    Only for HTTP/1 (an HTTP/2 connection carries other requests); otherwise, or when the
    transport exposes no socket, the response is closed instead.
    """
    sock = None
    stream = response.extensions.get("network_stream")
    if stream is not None and response.http_version.startswith("HTTP/1"):
        with contextlib.suppress(Exception):
            sock = stream.get_extra_info("socket")
    if sock is None:
        _close_quietly(response)
        return
    with contextlib.suppress(OSError):
        sock.shutdown(socket.SHUT_RDWR)


def _needs_body(req: APIRequest, response: httpx.Response) -> bool:
    """Whether the body belongs to the deadline: always, except a successful stream's."""
    if not req.stream:
        return True
    return not (response.is_success or (req.accept_not_modified and response.status_code == 304))


class _BaseAPIClient:
    """Configuration shared by the sync and async clients (no I/O here)."""

    def __init__(
        self,
        *,
        api_key: str | None,
        base_url: str | None,
        timeout: float,
        max_retries: int,
        default_headers: Mapping[str, str] | None,
        autopilot: str | None,
        bench: Any,
        rand: Callable[[], float],
        clock: Callable[[], float],
    ) -> None:
        self.api_key: str = _resolve_api_key(api_key)
        self.base_url: str = _resolve_base_url(base_url)
        self.timeout: float = float(timeout)
        self.max_retries: int = int(max_retries)
        self._default_headers: dict[str, str] = dict(default_headers or {})
        self._rand = rand
        self._clock = clock
        if autopilot is not None and autopilot not in AUTOPILOT_ROUTER:
            raise ValueError(
                f"autopilot must be one of {sorted(AUTOPILOT_ROUTER)} (got {autopilot!r})"
            )
        self.autopilot_mode: str | None = autopilot
        self._autopilot_router: str | None = (
            AUTOPILOT_ROUTER[autopilot] if autopilot is not None else None
        )
        self._bench: ResolvedBench | None = resolve_bench(
            bench,
            {name: os.environ.get(name) for name in ("UR_BENCH", "UR_BENCH_RUN", "UR_BENCH_TRACE")},
        )
        if self._bench is not None:
            self._default_headers.update(self._bench.headers)
            if self.api_key.startswith("ur_sk_live_"):
                warnings.warn(
                    f"ultrarouter: Bench capture for suite {self._bench.suite!r} is refused on a "
                    "live key unless a workspace owner enables live capture; use a test key "
                    "(ur_sk_test_...) for Bench.",
                    UserWarning,
                    stacklevel=4,
                )

    @property
    def default_headers(self) -> dict[str, str]:
        """The headers added to every request (including any Bench tag headers)."""
        return dict(self._default_headers)

    def _build_headers(self, req: APIRequest) -> dict[str, str]:
        headers: dict[str, str] = {
            "accept": "text/event-stream" if req.stream else "application/json",
            "user-agent": USER_AGENT,
            "authorization": f"Bearer {self.api_key}",
        }
        headers.update(self._default_headers)
        if self._bench is not None and self._bench.trace_factory is not None:
            headers["x-ur-bench-trace"] = self._bench.trace_factory()
        if req.has_body or req.content is not None:
            headers["content-type"] = "application/json"
        extra = req.options.get("extra_headers")
        if extra:
            headers.update({k.lower(): v for k, v in extra.items()})
        headers.update({k.lower(): v for k, v in req.headers.items()})
        idem = resolve_idempotency_key(req.method, req.stream, req.options.get("idempotency_key"))
        if idem is not None:
            headers["idempotency-key"] = idem
        return headers

    def _build_request(
        self, client: httpx.Client | httpx.AsyncClient, req: APIRequest
    ) -> httpx.Request:
        url = f"{self.base_url}{req.path}"
        params = _clean_query(req.query) + _clean_query(req.options.get("extra_query"))
        content: bytes | None = req.content
        if content is None and req.has_body:
            content = json.dumps(req.body, separators=(",", ":"), ensure_ascii=False).encode(
                "utf-8"
            )
        return client.build_request(
            req.method,
            url,
            params=params or None,
            headers=self._build_headers(req),
            content=content,
        )

    @staticmethod
    def _transport_timeout(req: APIRequest, timeout: float, remaining: float) -> dict[str, Any]:
        # A stream waits at most ``timeout`` for each next chunk once it has started.
        if req.stream:
            return httpx.Timeout(remaining, read=timeout).as_dict()
        return httpx.Timeout(remaining).as_dict()

    def _budget(self, req: APIRequest) -> tuple[float, int]:
        timeout = float(req.options.get("timeout", self.timeout))
        max_retries = int(req.options.get("max_retries", self.max_retries))
        if req.stream:
            max_retries = 0  # a stream is never retried automatically
        return timeout, max_retries

    def _openai_preset(self) -> dict[str, Any]:
        preset: dict[str, Any] = {"base_url": f"{self.base_url}/v1", "api_key": self.api_key}
        if self._default_headers:
            preset["default_headers"] = dict(self._default_headers)
        return preset


class SyncAPIClient(_BaseAPIClient):
    """The synchronous transport (internal base of :class:`~ultrarouter.UltraRouter`)."""

    def __init__(
        self,
        *,
        api_key: str | None,
        base_url: str | None,
        timeout: float,
        max_retries: int,
        default_headers: Mapping[str, str] | None,
        autopilot: str | None,
        bench: Any,
        http_client: httpx.Client | None,
        sleep: Callable[[float], None],
        rand: Callable[[], float],
        clock: Callable[[], float],
    ) -> None:
        super().__init__(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            default_headers=default_headers,
            autopilot=autopilot,
            bench=bench,
            rand=rand,
            clock=clock,
        )
        self._owns_http = http_client is None
        self._http: httpx.Client = http_client if http_client is not None else httpx.Client()
        self._sleep = sleep
        self._worker_slots = _WorkerSlots()

    def _send_within_deadline(
        self, http_request: httpx.Request, req: APIRequest, remaining: float
    ) -> httpx.Response:
        """Send and read (headers, and the body unless it is a successful stream) by the deadline.

        A blocking socket read cannot time out as a whole, so a request thread does the network
        work while the caller waits at most ``remaining`` seconds. On the deadline the caller
        shuts the transfer's socket down, so the thread stops reading at once, closes the
        response and frees its slot; the number of request threads is bounded by
        :data:`MAX_REQUEST_THREADS`. Context variables are carried over.
        """
        waited_from = time.monotonic()
        if not self._worker_slots.acquire(remaining):
            raise _DeadlineExceeded("too many requests in flight")
        remaining -= time.monotonic() - waited_from
        transfer = _Transfer()
        context = contextvars.copy_context()

        def work() -> None:
            try:
                response = self._http.send(http_request, stream=True)
                with transfer.lock:
                    transfer.response = response
                    abandoned = transfer.abandoned
                if not abandoned and _needs_body(req, response):
                    response.read()
                transfer.value = response
            except BaseException as exc:  # handed to the waiting caller
                transfer.error = exc
            finally:
                with transfer.lock:
                    transfer.done.set()
                    late = transfer.abandoned
                if late and transfer.response is not None:
                    _close_quietly(transfer.response)
                self._worker_slots.release()

        thread = threading.Thread(
            target=lambda: context.run(work), name="ultrarouter-request", daemon=True
        )
        try:
            thread.start()
        except BaseException:
            self._worker_slots.release()
            raise
        try:
            finished = transfer.done.wait(max(0.0, remaining))
        except BaseException:  # for example KeyboardInterrupt while waiting
            self._abandon(transfer)
            raise
        if not finished and self._abandon(transfer):
            raise _DeadlineExceeded
        if transfer.error is not None:
            raise transfer.error
        assert transfer.value is not None
        return transfer.value

    @staticmethod
    def _abandon(transfer: _Transfer) -> bool:
        """Give up on ``transfer`` unless it already finished; stop its read if one is running."""
        with transfer.lock:
            if transfer.done.is_set():
                return False
            transfer.abandoned = True
            response = transfer.response
        if response is not None:
            _interrupt(response)
        return True

    def request(self, req: APIRequest) -> httpx.Response:
        """Execute ``req`` with the retry policy and return the raw 2xx (or accepted 304) response.

        For a streaming request the response body is left open for the caller to read.
        """
        timeout, max_retries = self._budget(req)
        deadline = time.monotonic() + timeout
        http_request = self._build_request(self._http, req)
        last: UltraRouterError | None = None
        for attempt in range(max_retries + 1):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            http_request.extensions["timeout"] = self._transport_timeout(req, timeout, remaining)
            try:
                response = self._send_within_deadline(http_request, req, remaining)
            except _DeadlineExceeded as exc:
                reason = f" ({exc})" if str(exc) else ""
                raise APITimeoutError(f"request timed out after {timeout}s{reason}") from None
            except httpx.TimeoutException as exc:
                raise APITimeoutError(f"request timed out after {timeout}s: {exc}") from exc
            except httpx.HTTPError as exc:
                last = APIConnectionError(f"connection error: {exc}", retryable=True)
                if should_retry(last, attempt, max_retries):
                    self._sleep(
                        capped_backoff(attempt, None, self._rand(), deadline - time.monotonic())
                    )
                    continue
                raise last from exc
            if response.is_success or (req.accept_not_modified and response.status_code == 304):
                return response
            if req.stream:
                response.close()  # its body was already read within the deadline
            error = error_from_response(response.status_code, _safe_json(response))
            last = error
            if should_retry(error, attempt, max_retries):
                retry_after = parse_retry_after(response.headers.get("retry-after"), self._clock())
                self._sleep(
                    capped_backoff(attempt, retry_after, self._rand(), deadline - time.monotonic())
                )
                continue
            raise error
        raise last if last is not None else APITimeoutError(f"request timed out after {timeout}s")

    def request_json(self, req: APIRequest) -> Any:
        """Execute ``req`` and return the decoded JSON body (``{}`` for an empty body)."""
        response = self.request(req)
        if not response.content:
            return {}
        try:
            return response.json()
        except ValueError as exc:
            raise APIResponseValidationError(
                "response body is not valid JSON", status=response.status_code, body=response.text
            ) from exc

    def request_model(
        self, req: APIRequest, model: type[ModelT], *, unwrap: str | None = None
    ) -> ModelT:
        """Execute ``req`` and validate the JSON body into ``model``.

        ``unwrap`` names an envelope key (``{"artifact": {...}}``) to unwrap first when present.
        """
        data = self.request_json(req)
        if unwrap is not None and isinstance(data, dict) and isinstance(data.get(unwrap), dict):
            data = data[unwrap]
        return parse_model(model, data)

    def request_text(self, req: APIRequest) -> str:
        """Execute ``req`` and return the body as text."""
        return self.request(req).text

    def close(self) -> None:
        """Close the HTTP connection pool (only when the SDK created it)."""
        if self._owns_http:
            self._http.close()


class AsyncAPIClient(_BaseAPIClient):
    """The asynchronous transport (internal base of :class:`~ultrarouter.AsyncUltraRouter`)."""

    def __init__(
        self,
        *,
        api_key: str | None,
        base_url: str | None,
        timeout: float,
        max_retries: int,
        default_headers: Mapping[str, str] | None,
        autopilot: str | None,
        bench: Any,
        http_client: httpx.AsyncClient | None,
        sleep: Callable[[float], Awaitable[None]],
        rand: Callable[[], float],
        clock: Callable[[], float],
    ) -> None:
        super().__init__(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            default_headers=default_headers,
            autopilot=autopilot,
            bench=bench,
            rand=rand,
            clock=clock,
        )
        self._owns_http = http_client is None
        self._http: httpx.AsyncClient = (
            http_client if http_client is not None else httpx.AsyncClient()
        )
        self._sleep = sleep

    async def _send_and_read(self, http_request: httpx.Request, req: APIRequest) -> httpx.Response:
        """Send and read (headers, and the body unless it is a successful stream); the caller
        cancels this at the deadline, and a cancelled or failed read closes the response."""
        response = await self._http.send(http_request, stream=True)
        try:
            if _needs_body(req, response):
                await response.aread()
        except BaseException:
            await response.aclose()
            raise
        return response

    async def request(self, req: APIRequest) -> httpx.Response:
        """Async twin of :meth:`SyncAPIClient.request`."""
        timeout, max_retries = self._budget(req)
        deadline = time.monotonic() + timeout
        http_request = self._build_request(self._http, req)
        last: UltraRouterError | None = None
        for attempt in range(max_retries + 1):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            http_request.extensions["timeout"] = self._transport_timeout(req, timeout, remaining)
            try:
                response = await asyncio.wait_for(self._send_and_read(http_request, req), remaining)
            except asyncio.TimeoutError:
                raise APITimeoutError(f"request timed out after {timeout}s") from None
            except httpx.TimeoutException as exc:
                raise APITimeoutError(f"request timed out after {timeout}s: {exc}") from exc
            except httpx.HTTPError as exc:
                last = APIConnectionError(f"connection error: {exc}", retryable=True)
                if should_retry(last, attempt, max_retries):
                    await self._sleep(
                        capped_backoff(attempt, None, self._rand(), deadline - time.monotonic())
                    )
                    continue
                raise last from exc
            if response.is_success or (req.accept_not_modified and response.status_code == 304):
                return response
            if req.stream:
                await response.aclose()  # its body was already read within the deadline
            error = error_from_response(response.status_code, _safe_json(response))
            last = error
            if should_retry(error, attempt, max_retries):
                retry_after = parse_retry_after(response.headers.get("retry-after"), self._clock())
                await self._sleep(
                    capped_backoff(attempt, retry_after, self._rand(), deadline - time.monotonic())
                )
                continue
            raise error
        raise last if last is not None else APITimeoutError(f"request timed out after {timeout}s")

    async def request_json(self, req: APIRequest) -> Any:
        """Async twin of :meth:`SyncAPIClient.request_json`."""
        response = await self.request(req)
        if not response.content:
            return {}
        try:
            return response.json()
        except ValueError as exc:
            raise APIResponseValidationError(
                "response body is not valid JSON", status=response.status_code, body=response.text
            ) from exc

    async def request_model(
        self, req: APIRequest, model: type[ModelT], *, unwrap: str | None = None
    ) -> ModelT:
        """Async twin of :meth:`SyncAPIClient.request_model`."""
        data = await self.request_json(req)
        if unwrap is not None and isinstance(data, dict) and isinstance(data.get(unwrap), dict):
            data = data[unwrap]
        return parse_model(model, data)

    async def request_text(self, req: APIRequest) -> str:
        """Async twin of :meth:`SyncAPIClient.request_text`."""
        return (await self.request(req)).text

    async def close(self) -> None:
        """Close the HTTP connection pool (only when the SDK created it)."""
        if self._owns_http:
            await self._http.aclose()


def default_sleep(seconds: float) -> None:
    """The real sleep used between retries (injectable in tests)."""
    time.sleep(seconds)


async def default_async_sleep(seconds: float) -> None:
    """The real async sleep used between retries (injectable in tests)."""
    await asyncio.sleep(seconds)


def default_rand() -> float:
    """Backoff jitter source (not used for anything security-sensitive)."""
    return random.random()  # noqa: S311 - jitter only


DEFAULTS = {
    "timeout": DEFAULT_TIMEOUT_S,
    "max_retries": DEFAULT_MAX_RETRIES,
}
