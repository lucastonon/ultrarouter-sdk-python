"""Keyword-argument shapes for the OpenAI-compatible create methods (hand-written).

``chat.completions.create(**kwargs)`` and ``embeddings.create(**kwargs)`` accept these keys.
They mirror the request bodies in ``openapi/openapi.yaml`` (a test keeps them in sync) and add
one SDK convenience: ``bench``, which the SDK moves into ``ur.bench``.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Literal

from typing_extensions import Required, TypedDict

from ._generated import (
    BenchTagParam,
    ChatMessageParam,
    CompressionParam,
    ProviderPreferencesParam,
    ReasoningParam,
    ResponseFormatJsonObjectParam,
    ResponseFormatJsonSchemaParam,
    ResponseFormatTextParam,
    UrParams,
)

__all__ = [
    "ChatCompletionCreateKwargs",
    "CompressionMode",
    "EmbeddingCreateKwargs",
    "ReasoningEffort",
    "RouterMode",
]

RouterMode = Literal["off", "auto", "candidates"]
"""Routing mode: ``off`` serves the requested model, ``candidates`` ranks an approved list,
``auto`` lets the router choose."""

CompressionMode = Literal["off", "semantic_safe", "adaptive", "lossless", "auto"]
"""Prompt compression mode. ``off`` (default) never rewrites the prompt; ``semantic_safe`` and
``adaptive`` are the current tiers; ``lossless`` and ``auto`` are accepted legacy aliases."""

ReasoningEffort = Literal["none", "minimal", "low", "medium", "high"]
"""Reasoning effort for models that support it."""


class ChatCompletionCreateKwargs(TypedDict, total=False):
    """Keyword arguments of ``client.chat.completions.create`` (besides ``stream`` and options)."""

    messages: Required[Sequence[ChatMessageParam | Mapping[str, Any]]]
    """The conversation, OpenAI format (``role`` + ``content``; tool calls supported)."""

    model: str
    """Provider-prefixed model id, e.g. ``"openai/gpt-5.2-mini"`` (default: ``default_model``)."""

    models: Sequence[str]
    """Ordered fallback model ids tried when the primary model fails."""

    temperature: float
    """Sampling temperature."""

    top_p: float
    """Nucleus sampling probability mass."""

    max_tokens: int
    """Maximum output tokens (legacy name)."""

    max_completion_tokens: int
    """Maximum output tokens including reasoning tokens."""

    n: int
    """Number of choices to generate."""

    stop: str | Sequence[str]
    """Stop sequence(s)."""

    seed: int
    """Sampling seed, where supported."""

    presence_penalty: float
    """Presence penalty."""

    frequency_penalty: float
    """Frequency penalty."""

    logprobs: bool
    """Return log probabilities, where supported."""

    top_logprobs: int
    """Number of most likely tokens to return per position (with ``logprobs``)."""

    tools: Sequence[Mapping[str, Any]]
    """Tool (function) definitions, OpenAI format."""

    tool_choice: str | Mapping[str, Any]
    """Tool selection: ``"auto"``, ``"none"``, ``"required"`` or a specific function."""

    response_format: (
        ResponseFormatTextParam
        | ResponseFormatJsonObjectParam
        | ResponseFormatJsonSchemaParam
        | Mapping[str, Any]
    )
    """Structured output: ``{"type": "json_object"}`` or
    ``{"type": "json_schema", "json_schema": {...}}``."""

    reasoning_effort: ReasoningEffort
    """Reasoning effort, OpenAI style."""

    reasoning: ReasoningParam
    """Reasoning control, OpenRouter style (``effort``, ``max_tokens``, ``exclude``)."""

    stream_options: Mapping[str, Any]
    """Streaming options, e.g. ``{"include_usage": True}``."""

    user: str
    """An end-user identifier."""

    metadata: Mapping[str, Any]
    """Opaque JSON stored with the request."""

    provider: ProviderPreferencesParam
    """Provider preferences (order, sort, allow/ignore lists, data collection)."""

    router: RouterMode
    """Routing mode for this call (clamped to the client's ``autopilot`` ceiling)."""

    compression: CompressionMode | CompressionParam
    """Prompt compression mode or structured compression options."""

    call_type: str
    """The call-type slug this request belongs to."""

    ur: UrParams | Mapping[str, Any]
    """ultrarouter per-request controls (``max_cost_usd``, ``trace_id``, ``artifact``, ``segments``,
    ``manifest``, ``prompt_vars``, ``tags``, ...)."""

    bench: str | BenchTagParam
    """Tag this request for a Bench suite; sent as ``ur.bench``."""


class EmbeddingCreateKwargs(TypedDict, total=False):
    """Keyword arguments of ``client.embeddings.create`` (besides request options)."""

    input: Required[str | Sequence[str]]
    """Text, or a list of texts, to embed."""

    model: str
    """Embedding model id. Falls back to ``default_model``."""

    dimensions: int
    """Output dimensions, for models that support shortening."""

    encoding_format: Literal["float", "base64"]
    """``float`` (default) returns lists of floats; ``base64`` returns base64 strings."""

    user: str
    """An end-user identifier."""

    metadata: Mapping[str, Any]
    """Opaque JSON stored with the request."""

    call_type: str
    """The call-type slug this request belongs to."""

    ur: UrParams | Mapping[str, Any]
    """ultrarouter per-request controls."""

    bench: str | BenchTagParam
    """Tag this request for a Bench suite; sent as ``ur.bench``."""
