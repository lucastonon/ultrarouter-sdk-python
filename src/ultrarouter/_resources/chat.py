"""``client.chat.completions`` (OpenAI-compatible chat completions)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal, overload

from typing_extensions import Unpack

from .._streaming import AsyncStream, Stream
from ..types import ChatCompletion, ChatCompletionCreateKwargs
from ._base import AsyncAPIResource, SyncAPIResource, build, openai_options

__all__ = ["AsyncChat", "AsyncCompletions", "Chat", "Completions"]


class Completions(SyncAPIResource):
    """``client.chat.completions``: create chat completions, streamed or not."""

    @overload
    def create(
        self,
        *,
        stream: Literal[False] = False,
        extra_headers: Mapping[str, str] | None = None,
        extra_query: Mapping[str, Any] | None = None,
        extra_body: Mapping[str, Any] | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        idempotency_key: str | None = None,
        request_id: str | None = None,
        episode_key: str | None = None,
        **params: Unpack[ChatCompletionCreateKwargs],
    ) -> ChatCompletion: ...

    @overload
    def create(
        self,
        *,
        stream: Literal[True],
        extra_headers: Mapping[str, str] | None = None,
        extra_query: Mapping[str, Any] | None = None,
        extra_body: Mapping[str, Any] | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        idempotency_key: str | None = None,
        request_id: str | None = None,
        episode_key: str | None = None,
        **params: Unpack[ChatCompletionCreateKwargs],
    ) -> Stream: ...

    @overload
    def create(
        self,
        *,
        stream: bool,
        extra_headers: Mapping[str, str] | None = None,
        extra_query: Mapping[str, Any] | None = None,
        extra_body: Mapping[str, Any] | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        idempotency_key: str | None = None,
        request_id: str | None = None,
        episode_key: str | None = None,
        **params: Unpack[ChatCompletionCreateKwargs],
    ) -> ChatCompletion | Stream: ...

    def create(
        self,
        *,
        stream: bool = False,
        extra_headers: Mapping[str, str] | None = None,
        extra_query: Mapping[str, Any] | None = None,
        extra_body: Mapping[str, Any] | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        idempotency_key: str | None = None,
        request_id: str | None = None,
        episode_key: str | None = None,
        **params: Unpack[ChatCompletionCreateKwargs],
    ) -> ChatCompletion | Stream:
        """Create a chat completion (``POST /v1/chat/completions``).

        Accepts every OpenAI chat parameter (``messages``, ``model``, ``temperature``, ``tools``,
        ``response_format``, ...) plus the ultrarouter extensions (``models`` fallbacks,
        ``provider``, ``router``, ``compression``, ``call_type``, ``ur``, ``bench``). Client
        defaults (``default_model``, ``defaults=``) apply to anything you leave out.

        Args:
            stream: ``True`` returns a :class:`~ultrarouter.Stream` of chunks instead of a
                :class:`~ultrarouter.types.ChatCompletion`. Streams are never retried.
            extra_headers: Additional HTTP headers for this call.
            extra_query: Additional query-string parameters for this call.
            extra_body: Additional JSON body fields (merged last; for options the SDK does not
                model yet).
            timeout: Total seconds for this call across retries.
            max_retries: Automatic retries for this call.
            idempotency_key: Explicit ``Idempotency-Key`` (a key is generated otherwise).
            request_id: Your own request id, sent as ``x-ur-request-id``
                (``[A-Za-z0-9_-]{1,64}``; mint one with :func:`~ultrarouter.new_request_id`), so
                you know the id before the call returns (and on an error or a stream).
            episode_key: The episode this step belongs to, sent as ``X-UR-Artifact``: every step
                with the same key is one episode. Concurrent tasks that open with identical text
                need distinct keys, or they are grouped together.
            **params: The request body; see :class:`~ultrarouter.types.ChatCompletionCreateKwargs`.

        Returns:
            The completion, whose ``ur`` block carries the request id, served model and cost
            (``stream.request_id`` on a stream).
        """
        body = self._client._chat_body(dict(params), extra_body)
        options = self._client._correlate(
            openai_options(extra_headers, extra_query, timeout, max_retries, idempotency_key),
            request_id,
            episode_key,
        )
        if stream:
            body["stream"] = True
            response = self._client.request(
                build("POST", "/v1/chat/completions", body=body, options=options, stream=True)
            )
            return Stream(response)
        body.pop("stream", None)
        return self._client.request_model(
            build("POST", "/v1/chat/completions", body=body, options=options), ChatCompletion
        )


class Chat(SyncAPIResource):
    """``client.chat``: the chat namespace (holds :attr:`completions`)."""

    def __init__(self, client: Any) -> None:
        super().__init__(client)
        self.completions = Completions(client)
        """Chat completions."""


class AsyncCompletions(AsyncAPIResource):
    """``client.chat.completions`` on :class:`~ultrarouter.AsyncUltraRouter`."""

    @overload
    async def create(
        self,
        *,
        stream: Literal[False] = False,
        extra_headers: Mapping[str, str] | None = None,
        extra_query: Mapping[str, Any] | None = None,
        extra_body: Mapping[str, Any] | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        idempotency_key: str | None = None,
        request_id: str | None = None,
        episode_key: str | None = None,
        **params: Unpack[ChatCompletionCreateKwargs],
    ) -> ChatCompletion: ...

    @overload
    async def create(
        self,
        *,
        stream: Literal[True],
        extra_headers: Mapping[str, str] | None = None,
        extra_query: Mapping[str, Any] | None = None,
        extra_body: Mapping[str, Any] | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        idempotency_key: str | None = None,
        request_id: str | None = None,
        episode_key: str | None = None,
        **params: Unpack[ChatCompletionCreateKwargs],
    ) -> AsyncStream: ...

    @overload
    async def create(
        self,
        *,
        stream: bool,
        extra_headers: Mapping[str, str] | None = None,
        extra_query: Mapping[str, Any] | None = None,
        extra_body: Mapping[str, Any] | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        idempotency_key: str | None = None,
        request_id: str | None = None,
        episode_key: str | None = None,
        **params: Unpack[ChatCompletionCreateKwargs],
    ) -> ChatCompletion | AsyncStream: ...

    async def create(
        self,
        *,
        stream: bool = False,
        extra_headers: Mapping[str, str] | None = None,
        extra_query: Mapping[str, Any] | None = None,
        extra_body: Mapping[str, Any] | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        idempotency_key: str | None = None,
        request_id: str | None = None,
        episode_key: str | None = None,
        **params: Unpack[ChatCompletionCreateKwargs],
    ) -> ChatCompletion | AsyncStream:
        """Create a chat completion; async twin of :meth:`Completions.create`.

        With ``stream=True`` it returns an :class:`~ultrarouter.AsyncStream`; use
        ``async for chunk in stream``.
        """
        body = self._client._chat_body(dict(params), extra_body)
        options = self._client._correlate(
            openai_options(extra_headers, extra_query, timeout, max_retries, idempotency_key),
            request_id,
            episode_key,
        )
        if stream:
            body["stream"] = True
            response = await self._client.request(
                build("POST", "/v1/chat/completions", body=body, options=options, stream=True)
            )
            return AsyncStream(response)
        body.pop("stream", None)
        return await self._client.request_model(
            build("POST", "/v1/chat/completions", body=body, options=options), ChatCompletion
        )


class AsyncChat(AsyncAPIResource):
    """``client.chat`` on :class:`~ultrarouter.AsyncUltraRouter`."""

    def __init__(self, client: Any) -> None:
        super().__init__(client)
        self.completions = AsyncCompletions(client)
        """Chat completions."""
