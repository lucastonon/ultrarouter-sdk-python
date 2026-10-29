"""Typed request and response shapes.

Response models (pydantic, subclasses of :class:`ultrarouter.BaseModel`) and request
``TypedDict`` shapes are generated from the API specification into ``_generated``; the streaming
chunk models and the keyword-argument shapes of the OpenAI-compatible create methods are written
by hand. Import from here: ``from ultrarouter.types import ChatCompletion``.
"""

from ._chunk import (
    ChatCompletionChunk,
    ChunkChoice,
    ChunkDelta,
    ChunkDeltaToolCall,
    ChunkDeltaToolCallFunction,
)
from ._generated import *
from ._generated import __all__ as _generated_all
from ._requests import (
    ChatCompletionCreateKwargs,
    CompressionMode,
    EmbeddingCreateKwargs,
    ReasoningEffort,
    RouterMode,
)

__all__ = [
    "ChatCompletionChunk",
    "ChatCompletionCreateKwargs",
    "ChunkChoice",
    "ChunkDelta",
    "ChunkDeltaToolCall",
    "ChunkDeltaToolCallFunction",
    "CompressionMode",
    "EmbeddingCreateKwargs",
    "ReasoningEffort",
    "RouterMode",
    *_generated_all,
]
