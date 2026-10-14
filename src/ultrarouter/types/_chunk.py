"""Streaming chunk shapes (``chat.completion.chunk``).

Server-sent events are not described by the OpenAPI document, so these models are written by
hand. They follow the OpenAI chunk format plus the ``ur`` block on the final chunk.
"""

from __future__ import annotations

from typing import Any

from pydantic import Field

from .._models import BaseModel
from ._generated import ChatCompletionUsage, UrBlock

__all__ = [
    "ChatCompletionChunk",
    "ChunkChoice",
    "ChunkDelta",
    "ChunkDeltaToolCall",
    "ChunkDeltaToolCallFunction",
]


class ChunkDeltaToolCallFunction(BaseModel):
    """An incremental fragment of a tool call's function name and JSON arguments."""

    name: str | None = None
    """The function name (present on the first fragment of a call)."""

    arguments: str | None = None
    """A fragment of the JSON-encoded arguments; concatenate fragments in order."""


class ChunkDeltaToolCall(BaseModel):
    """An incremental fragment of one tool call, keyed by ``index``."""

    index: int = 0
    """Which tool call (within the choice) this fragment belongs to."""

    id: str | None = None
    """The tool-call id (present on the first fragment of a call)."""

    type: str | None = None
    """The tool type, usually ``"function"``."""

    function: ChunkDeltaToolCallFunction | None = None
    """The function-name / arguments fragment."""


class ChunkDelta(BaseModel):
    """The incremental message content carried by one streamed choice."""

    role: str | None = None
    """The message role (present on the first chunk)."""

    content: str | None = None
    """The next fragment of assistant text."""

    tool_calls: list[ChunkDeltaToolCall] | None = None
    """Tool-call fragments, when the model is calling tools."""


class ChunkChoice(BaseModel):
    """One streamed choice."""

    index: int = 0
    """The choice index."""

    delta: ChunkDelta = ChunkDelta()
    """The incremental content."""

    finish_reason: str | None = None
    """Why generation stopped (``stop``, ``length``, ``tool_calls``, ...); set on the last chunk."""

    logprobs: Any = None
    """Log-probability information, when requested and supported."""


class ChatCompletionChunk(BaseModel):
    """One server-sent ``chat.completion.chunk`` event.

    Content chunks carry ``choices``. The final chunk before ``[DONE]`` has empty ``choices``
    and carries ``usage`` plus the ``ur`` block.
    """

    id: str
    """The completion id (the same on every chunk of a stream)."""

    object: str = "chat.completion.chunk"
    """Always ``"chat.completion.chunk"``."""

    created: int = 0
    """Unix timestamp (seconds) of the completion."""

    model: str = ""
    """The model that produced the chunk."""

    choices: list[ChunkChoice] = Field(default_factory=list)
    """The streamed choices (empty on the final usage chunk)."""

    usage: ChatCompletionUsage | None = None
    """Token usage, on the final chunk."""

    ur: UrBlock | None = None
    """The ultrarouter block (request id, served model, cost, routing), on the final chunk."""

    system_fingerprint: str | None = None
    """Provider system fingerprint, when reported."""
