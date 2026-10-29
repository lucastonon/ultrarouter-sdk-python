"""Typed request and response shapes.

Response models (pydantic, subclasses of :class:`ultrarouter.BaseModel`) and request
``TypedDict`` shapes are generated from the API specification into ``_generated``. Written by
hand: the streaming chunk models, the keyword-argument shapes of the OpenAI-compatible create
methods, and the provisional learning-loop models (``_learning``: outcome receipts, learning
status, versions and evaluations, for endpoints newer than the synced specification). Import from
here: ``from ultrarouter.types import ChatCompletion``.
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
from ._learning import (
    LearningArmEvidence,
    LearningBudget,
    LearningEvaluation,
    LearningEvaluationInterval,
    LearningEvaluationList,
    LearningEvidenceCounts,
    LearningLesson,
    LearningPromotionPolicy,
    LearningProvenance,
    LearningProvider,
    LearningStatus,
    LearningVersion,
    LearningVersionList,
    LearningVersionRef,
    OutcomeReceiptRecord,
    OutcomeReceiptRecordList,
)
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
    "LearningArmEvidence",
    "LearningBudget",
    "LearningEvaluation",
    "LearningEvaluationInterval",
    "LearningEvaluationList",
    "LearningEvidenceCounts",
    "LearningLesson",
    "LearningPromotionPolicy",
    "LearningProvenance",
    "LearningProvider",
    "LearningStatus",
    "LearningVersion",
    "LearningVersionList",
    "LearningVersionRef",
    "OutcomeReceiptRecord",
    "OutcomeReceiptRecordList",
    "ReasoningEffort",
    "RouterMode",
    *_generated_all,
]
