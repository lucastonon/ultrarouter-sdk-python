"""``client.embeddings`` and ``client.models`` (OpenAI-compatible) plus ``client.key``."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from typing_extensions import Unpack

from .._base_client import RequestOptions
from ..types import CreateEmbeddingResponse, EmbeddingCreateKwargs, KeyInfo, ModelDetail, ModelList
from ._base import AsyncAPIResource, SyncAPIResource, build, openai_options, seg

__all__ = [
    "AsyncEmbeddings",
    "AsyncKey",
    "AsyncModels",
    "Embeddings",
    "Key",
    "Models",
]


class Embeddings(SyncAPIResource):
    """``client.embeddings``: create embeddings."""

    def create(
        self,
        *,
        extra_headers: Mapping[str, str] | None = None,
        extra_query: Mapping[str, Any] | None = None,
        extra_body: Mapping[str, Any] | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        idempotency_key: str | None = None,
        request_id: str | None = None,
        episode_key: str | None = None,
        **params: Unpack[EmbeddingCreateKwargs],
    ) -> CreateEmbeddingResponse:
        """Create embeddings (``POST /v1/embeddings``).

        Args:
            extra_headers: Additional HTTP headers for this call.
            extra_query: Additional query-string parameters for this call.
            extra_body: Additional JSON body fields (merged last).
            timeout: Total seconds for this call across retries.
            max_retries: Automatic retries for this call.
            idempotency_key: Explicit ``Idempotency-Key`` (a key is generated otherwise).
            request_id: Your own request id, sent as ``x-ur-request-id``.
            episode_key: The episode this call belongs to, sent as ``X-UR-Artifact``.
            **params: ``input`` (required), ``model``, ``dimensions``, ``encoding_format``, ...;
                see :class:`~ultrarouter.types.EmbeddingCreateKwargs`.
        """
        body = self._client._embedding_body(dict(params), extra_body)
        options = self._client._correlate(
            openai_options(extra_headers, extra_query, timeout, max_retries, idempotency_key),
            request_id,
            episode_key,
        )
        return self._client.request_model(
            build("POST", "/v1/embeddings", body=body, options=options), CreateEmbeddingResponse
        )


class AsyncEmbeddings(AsyncAPIResource):
    """``client.embeddings`` on :class:`~ultrarouter.AsyncUltraRouter`."""

    async def create(
        self,
        *,
        extra_headers: Mapping[str, str] | None = None,
        extra_query: Mapping[str, Any] | None = None,
        extra_body: Mapping[str, Any] | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        idempotency_key: str | None = None,
        request_id: str | None = None,
        episode_key: str | None = None,
        **params: Unpack[EmbeddingCreateKwargs],
    ) -> CreateEmbeddingResponse:
        """Create embeddings; async twin of :meth:`Embeddings.create`."""
        body = self._client._embedding_body(dict(params), extra_body)
        options = self._client._correlate(
            openai_options(extra_headers, extra_query, timeout, max_retries, idempotency_key),
            request_id,
            episode_key,
        )
        return await self._client.request_model(
            build("POST", "/v1/embeddings", body=body, options=options), CreateEmbeddingResponse
        )


class Models(SyncAPIResource):
    """``client.models``: the model catalog."""

    def list(
        self,
        *,
        provider: str | None = None,
        capability: str | None = None,
        extra_headers: Mapping[str, str] | None = None,
        extra_query: Mapping[str, Any] | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
    ) -> ModelList:
        """List the model catalog (``GET /v1/models``).

        Args:
            provider: Only models served by this provider (e.g. ``"openai"``).
            capability: Only models with this capability (e.g. ``"vision"``, ``"tools"``).
            extra_headers: Additional HTTP headers for this call.
            extra_query: Additional query-string parameters for this call.
            timeout: Total seconds for this call across retries.
            max_retries: Automatic retries for this call.
        """
        options = openai_options(extra_headers, extra_query, timeout, max_retries)
        return self._client.request_model(
            build(
                "GET",
                "/v1/models",
                query={"provider": provider, "capability": capability},
                options=options,
            ),
            ModelList,
        )

    def retrieve(
        self,
        model: str,
        *,
        extra_headers: Mapping[str, str] | None = None,
        extra_query: Mapping[str, Any] | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
    ) -> ModelDetail:
        """Get one model with every provider offer and its pricing (``GET /v1/models/{id}``).

        Args:
            model: The provider-prefixed model id, e.g. ``"openai/gpt-5.2"``.
            extra_headers: Additional HTTP headers for this call.
            extra_query: Additional query-string parameters for this call.
            timeout: Total seconds for this call across retries.
            max_retries: Automatic retries for this call.
        """
        options = openai_options(extra_headers, extra_query, timeout, max_retries)
        return self._client.request_model(
            build("GET", f"/v1/models/{seg(model)}", options=options), ModelDetail
        )


class AsyncModels(AsyncAPIResource):
    """``client.models`` on :class:`~ultrarouter.AsyncUltraRouter`."""

    async def list(
        self,
        *,
        provider: str | None = None,
        capability: str | None = None,
        extra_headers: Mapping[str, str] | None = None,
        extra_query: Mapping[str, Any] | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
    ) -> ModelList:
        """List the model catalog; async twin of :meth:`Models.list`."""
        options = openai_options(extra_headers, extra_query, timeout, max_retries)
        return await self._client.request_model(
            build(
                "GET",
                "/v1/models",
                query={"provider": provider, "capability": capability},
                options=options,
            ),
            ModelList,
        )

    async def retrieve(
        self,
        model: str,
        *,
        extra_headers: Mapping[str, str] | None = None,
        extra_query: Mapping[str, Any] | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
    ) -> ModelDetail:
        """Get one model; async twin of :meth:`Models.retrieve`."""
        options = openai_options(extra_headers, extra_query, timeout, max_retries)
        return await self._client.request_model(
            build("GET", f"/v1/models/{seg(model)}", options=options), ModelDetail
        )


class Key(SyncAPIResource):
    """``client.key``: introspect the API key the client is using."""

    def get(self, *, options: RequestOptions | None = None) -> KeyInfo:
        """Describe the presented key: scopes, mode, limits and usage this period (``GET /v1/key``).

        A cheap way to verify configuration: it fails with
        :class:`~ultrarouter.AuthenticationError` when the key is wrong.
        """
        return self._client.request_model(build("GET", "/v1/key", options=options), KeyInfo)


class AsyncKey(AsyncAPIResource):
    """``client.key`` on :class:`~ultrarouter.AsyncUltraRouter`."""

    async def get(self, *, options: RequestOptions | None = None) -> KeyInfo:
        """Describe the presented key; async twin of :meth:`Key.get`."""
        return await self._client.request_model(build("GET", "/v1/key", options=options), KeyInfo)
