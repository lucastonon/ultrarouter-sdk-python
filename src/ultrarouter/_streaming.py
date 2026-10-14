"""Server-sent events parsing and the :class:`Stream` / :class:`AsyncStream` wrappers.

The gateway streams OpenAI-style ``data:`` frames carrying ``chat.completion.chunk`` JSON.
A ``:`` comment line is a heartbeat and is ignored. ``data: [DONE]`` ends the stream. An
``event: error`` frame carries the standard error envelope and raises the matching typed
error mid-stream. The last chunk before ``[DONE]`` has empty ``choices`` and carries ``usage``
plus the ``ur`` block (request id, served model, cost, routing).
"""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator, AsyncIterator, Generator, Iterator
from types import TracebackType
from typing import TYPE_CHECKING, Any

import httpx

from ._errors import (
    APIConnectionError,
    APIResponseValidationError,
    APITimeoutError,
    error_from_response,
)

if TYPE_CHECKING:
    from .types import ChatCompletionChunk, ChatCompletionUsage, UrBlock

__all__ = ["AsyncStream", "SSEDecoder", "Stream"]


class SSEDecoder:
    """Accumulates SSE lines into ``(event, data)`` frames (per the SSE specification)."""

    def __init__(self) -> None:
        self._event = "message"
        self._data: list[str] = []

    def push(self, raw_line: str) -> tuple[str, str] | None:
        """Feed one line; return a completed ``(event, data)`` frame at a blank separator."""
        line = raw_line.rstrip("\r\n")
        if line == "":
            if not self._data:
                self._event = "message"
                return None
            frame = (self._event, "\n".join(self._data))
            self._event = "message"
            self._data = []
            return frame
        if line.startswith(":"):
            return None  # heartbeat comment
        name, _, value = line.partition(":")
        if value.startswith(" "):
            value = value[1:]
        if name == "event":
            self._event = value
        elif name == "data":
            self._data.append(value)
        return None

    def flush(self) -> tuple[str, str] | None:
        """Return a trailing frame that was not terminated by a blank line, if any."""
        if not self._data:
            return None
        frame = (self._event, "\n".join(self._data))
        self._data = []
        return frame


_DONE = object()


def decode_frame(event: str, data: str) -> Any:
    """Decode one frame into a parsed JSON object, or the ``_DONE`` sentinel.

    Raises the typed gateway error for an ``event: error`` frame and
    :class:`~ultrarouter.APIResponseValidationError` for malformed JSON.
    """
    if data == "[DONE]":
        return _DONE
    try:
        parsed = json.loads(data)
    except json.JSONDecodeError as exc:
        raise APIResponseValidationError(
            "malformed server-sent event received from the gateway",
            body=data,
        ) from exc
    if event == "error" or (
        isinstance(parsed, dict) and "error" in parsed and "choices" not in parsed
    ):
        raise error_from_response(0, parsed)
    return parsed


def _parse_chunk(parsed: Any) -> ChatCompletionChunk:
    from pydantic import ValidationError

    from .types import ChatCompletionChunk

    try:
        return ChatCompletionChunk.model_validate(parsed)
    except ValidationError as exc:
        raise APIResponseValidationError(
            f"stream chunk did not match the expected shape: {exc.error_count()} error(s)",
            body=parsed,
        ) from exc


def iter_chunks(lines: Iterator[str]) -> Iterator[ChatCompletionChunk]:
    """Yield typed chunks from an iterator of SSE lines (stops at ``[DONE]``)."""
    decoder = SSEDecoder()
    for raw in lines:
        frame = decoder.push(raw)
        if frame is None:
            continue
        parsed = decode_frame(*frame)
        if parsed is _DONE:
            return
        yield _parse_chunk(parsed)
    tail = decoder.flush()
    if tail is not None:
        parsed = decode_frame(*tail)
        if parsed is not _DONE:
            yield _parse_chunk(parsed)


async def aiter_chunks(lines: AsyncIterator[str]) -> AsyncIterator[ChatCompletionChunk]:
    """Yield typed chunks from an async iterator of SSE lines (stops at ``[DONE]``)."""
    decoder = SSEDecoder()
    async for raw in lines:
        frame = decoder.push(raw)
        if frame is None:
            continue
        parsed = decode_frame(*frame)
        if parsed is _DONE:
            return
        yield _parse_chunk(parsed)
    tail = decoder.flush()
    if tail is not None:
        parsed = decode_frame(*tail)
        if parsed is not _DONE:
            yield _parse_chunk(parsed)


def _stall_error(exc: Exception) -> APITimeoutError:
    return APITimeoutError(f"stream stalled: no data within the timeout ({exc or 'read timeout'})")


class Stream:
    """A synchronous stream of :class:`~ultrarouter.types.ChatCompletionChunk` objects.

    Iterate it to receive chunks; it closes the HTTP response when exhausted, on error, or when
    used as a context manager. After iteration, :attr:`ur` and :attr:`usage` hold the values
    from the final chunk::

        from ultrarouter import UltraRouter

        client = UltraRouter()
        with client.chat.completions.create(
            model="openai/gpt-5.2-mini", messages=[{"role": "user", "content": "Hi"}], stream=True
        ) as stream:
            for chunk in stream:
                if chunk.choices:
                    print(chunk.choices[0].delta.content or "", end="")
        print(stream.ur.request_id if stream.ur else None)
    """

    def __init__(self, response: httpx.Response) -> None:
        self.response = response
        self.ur: UrBlock | None = None
        self.usage: ChatCompletionUsage | None = None
        self._iterator = self._iterate()

    def _iterate(self) -> Generator[ChatCompletionChunk, None, None]:
        try:
            for chunk in iter_chunks(self.response.iter_lines()):
                if chunk.ur is not None:
                    self.ur = chunk.ur
                if chunk.usage is not None:
                    self.usage = chunk.usage
                yield chunk
        except httpx.TimeoutException as exc:
            raise _stall_error(exc) from exc
        except httpx.HTTPError as exc:
            raise APIConnectionError(f"stream interrupted: {exc}", retryable=True) from exc
        finally:
            self.response.close()

    def __iter__(self) -> Iterator[ChatCompletionChunk]:
        return self._iterator

    def __next__(self) -> ChatCompletionChunk:
        return next(self._iterator)

    def text(self) -> str:
        """Consume the rest of the stream and return the concatenated ``delta.content``."""
        parts: list[str] = []
        for chunk in self:
            for choice in chunk.choices:
                if choice.delta.content:
                    parts.append(choice.delta.content)
        return "".join(parts)

    def close(self) -> None:
        """Close the underlying HTTP response (safe to call more than once)."""
        self._iterator.close()
        self.response.close()

    def __enter__(self) -> Stream:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()


class AsyncStream:
    """An asynchronous stream of :class:`~ultrarouter.types.ChatCompletionChunk` objects.

    The async twin of :class:`Stream`: ``async for chunk in stream`` and ``async with``.
    """

    def __init__(self, response: httpx.Response) -> None:
        self.response = response
        self.ur: UrBlock | None = None
        self.usage: ChatCompletionUsage | None = None
        self._iterator = self._iterate()

    async def _iterate(self) -> AsyncGenerator[ChatCompletionChunk, None]:
        try:
            async for chunk in aiter_chunks(self.response.aiter_lines()):
                if chunk.ur is not None:
                    self.ur = chunk.ur
                if chunk.usage is not None:
                    self.usage = chunk.usage
                yield chunk
        except httpx.TimeoutException as exc:
            raise _stall_error(exc) from exc
        except httpx.HTTPError as exc:
            raise APIConnectionError(f"stream interrupted: {exc}", retryable=True) from exc
        finally:
            await self.response.aclose()

    def __aiter__(self) -> AsyncIterator[ChatCompletionChunk]:
        return self._iterator

    async def __anext__(self) -> ChatCompletionChunk:
        return await self._iterator.__anext__()

    async def text(self) -> str:
        """Consume the rest of the stream and return the concatenated ``delta.content``."""
        parts: list[str] = []
        async for chunk in self:
            for choice in chunk.choices:
                if choice.delta.content:
                    parts.append(choice.delta.content)
        return "".join(parts)

    async def close(self) -> None:
        """Close the underlying HTTP response (safe to call more than once)."""
        await self._iterator.aclose()
        await self.response.aclose()

    async def __aenter__(self) -> AsyncStream:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.close()
