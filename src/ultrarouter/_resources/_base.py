"""Shared plumbing for resource namespaces (internal)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from .._base_client import APIRequest, RequestOptions, encode_path_segment

if TYPE_CHECKING:
    from .._client import AsyncUltraRouter, UltraRouter

__all__ = ["AsyncAPIResource", "SyncAPIResource", "build", "openai_options", "seg"]

_NO_BODY = object()


class SyncAPIResource:
    """Base class of every synchronous namespace (``client.chat``, ``client.bench``, ...)."""

    def __init__(self, client: UltraRouter) -> None:
        self._client = client


class AsyncAPIResource:
    """Base class of every asynchronous namespace."""

    def __init__(self, client: AsyncUltraRouter) -> None:
        self._client = client


def seg(value: str | int) -> str:
    """Percent-encode one path segment."""
    return encode_path_segment(str(value))


def build(
    method: str,
    path: str,
    *,
    query: Mapping[str, Any] | None = None,
    body: Any = _NO_BODY,
    options: RequestOptions | Mapping[str, Any] | None = None,
    headers: Mapping[str, str] | None = None,
    content: bytes | None = None,
    stream: bool = False,
    accept_not_modified: bool = False,
) -> APIRequest:
    """Build an :class:`~ultrarouter._base_client.APIRequest`."""
    has_body = body is not _NO_BODY
    return APIRequest(
        method=method,
        path=path,
        query=query,
        body=body if has_body else None,
        has_body=has_body,
        content=content,
        headers=dict(headers or {}),
        options=dict(options or {}),
        stream=stream,
        accept_not_modified=accept_not_modified,
    )


def openai_options(
    extra_headers: Mapping[str, str] | None,
    extra_query: Mapping[str, Any] | None,
    timeout: float | None,
    max_retries: int | None,
    idempotency_key: str | None = None,
) -> RequestOptions:
    """Fold OpenAI-style per-call keyword arguments into :class:`RequestOptions`."""
    options: RequestOptions = {}
    if extra_headers is not None:
        options["extra_headers"] = extra_headers
    if extra_query is not None:
        options["extra_query"] = extra_query
    if timeout is not None:
        options["timeout"] = timeout
    if max_retries is not None:
        options["max_retries"] = max_retries
    if idempotency_key is not None:
        options["idempotency_key"] = idempotency_key
    return options
