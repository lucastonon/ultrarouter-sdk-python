"""``ultrarouter.context``: a pure context runtime you can adopt in one file and leave in one file.

It turns the context a model call sees into explicit, hashable data:

* :func:`from_messages` lifts a plain OpenAI ``messages`` list into a labelled manifest, and
  :func:`to_messages` turns it back into the byte-identical list (the exit guarantee);
* :func:`compile` admits typed :class:`Module` candidates into a :class:`Manifest` under a
  :class:`Contract` (required / optional / forbidden kinds, token or count budgets, pins,
  availability cutoffs) and a :class:`CompatibilityProfile`, recording a typed refusal for every
  module it does not admit;
* :func:`render` turns a compiled manifest plus module bodies into provider messages, and
  :func:`to_wire` renders the ``ur.manifest`` request field the gateway verifies.

Everything here is pure: no I/O, clock, environment or randomness, and no third-party
dependency (only :mod:`hashlib`). Manifest bytes and hashes are byte-identical to the TypeScript
SDK's runtime (verified by shared golden fixtures).

    from ultrarouter.context import from_messages, to_messages

    lifted = from_messages([{"role": "user", "content": "hi"}])
    assert to_messages(lifted["manifest"]) == [{"role": "user", "content": "hi"}]

Not yet in the Python runtime (available in the TypeScript SDK): the standard-operating-
procedure compiler, the prompt-surface linter, native delivery planning and knowledge packs.
"""

from __future__ import annotations

from .._errors import PromptVariablesMissingError
from .._learned_placement import (
    LEARNED_MESSAGE_ROLE,
    LearnedMessage,
    apply_learned_context,
    learned_placement_index,
)
from .._prompt_render import (
    PROMPT_VARIABLES_MISSING_CODE,
    render_hosted_prompt_result,
    render_prompt,
)
from ._compile import AdapterRefusal, CompileResult, ContextCandidate, compile
from ._contract import PIN_POLICIES, Contract, Limit
from ._envelope import (
    Envelope,
    EnvelopeBudgets,
    Pin,
    SealedEnvelope,
    hash_envelope,
    seal_envelope,
)
from ._hash import canonical_json, hash_context_value, sha256_hex
from ._kinds import KindSet, define_kinds
from ._lift import from_messages
from ._manifest import (
    NATIVE_DELIVERY_STATES,
    ContextRange,
    Manifest,
    ManifestBudgets,
    ManifestEntry,
    ScaffoldSubjectEntry,
    scaffold_subject,
    to_wire,
)
from ._memory import CORE_MEMORY_CLASSES, MemoryClassSet, define_memory_classes
from ._messages import (
    INSTRUCTION_SLOT,
    REFERENCE_SLOTS,
    ChatMessage,
    RenderSerializer,
    default_render_serializer,
)
from ._module import TRUST_CLASSES, Availability, Module
from ._never_touch import PinnedSpan, overlaps_pinned_span, pin_never_touch_spans
from ._profile import (
    ULTRAROUTER_PROFILE,
    BudgetStrategy,
    CompatibilityProfile,
    EncodedManifest,
    ManifestEncoder,
    default_volatility_rank,
    encode_ultrarouter_manifest,
    ultrarouter_manifest_encoder,
)
from ._refusals import (
    CONTEXT_DELIVERY_REFUSAL_REASONS,
    CONTEXT_REFUSAL_REASONS,
    Refusal,
    RefusalRegistry,
    define_refusals,
    is_context_delivery_refusal_reason,
    is_context_refusal_reason,
)
from ._render import ContextExitError, render, to_messages
from ._segment import HINTABLE_SEGMENT_KINDS, SEGMENT_KINDS, segment

__all__ = [
    "CONTEXT_DELIVERY_REFUSAL_REASONS",
    "CONTEXT_REFUSAL_REASONS",
    "CORE_MEMORY_CLASSES",
    "HINTABLE_SEGMENT_KINDS",
    "INSTRUCTION_SLOT",
    # learned-module placement and hosted-prompt rendering (also on the top-level package)
    "LEARNED_MESSAGE_ROLE",
    "NATIVE_DELIVERY_STATES",
    "PIN_POLICIES",
    "PROMPT_VARIABLES_MISSING_CODE",
    "REFERENCE_SLOTS",
    "SEGMENT_KINDS",
    "TRUST_CLASSES",
    "ULTRAROUTER_PROFILE",
    "AdapterRefusal",
    # types + helpers
    "Availability",
    # profile machinery
    "BudgetStrategy",
    "ChatMessage",
    "CompatibilityProfile",
    "CompileResult",
    "ContextCandidate",
    "ContextExitError",
    "ContextRange",
    "Contract",
    "EncodedManifest",
    # core
    "Envelope",
    "EnvelopeBudgets",
    "KindSet",
    "LearnedMessage",
    "Limit",
    "Manifest",
    "ManifestBudgets",
    "ManifestEncoder",
    "ManifestEntry",
    "MemoryClassSet",
    "Module",
    "Pin",
    "PinnedSpan",
    "PromptVariablesMissingError",
    "Refusal",
    "RefusalRegistry",
    "RenderSerializer",
    "ScaffoldSubjectEntry",
    "SealedEnvelope",
    "apply_learned_context",
    "canonical_json",
    "compile",
    "default_render_serializer",
    "default_volatility_rank",
    "define_kinds",
    "define_memory_classes",
    # vocab helpers
    "define_refusals",
    "encode_ultrarouter_manifest",
    "from_messages",
    "hash_context_value",
    "hash_envelope",
    "is_context_delivery_refusal_reason",
    "is_context_refusal_reason",
    "learned_placement_index",
    "overlaps_pinned_span",
    "pin_never_touch_spans",
    "render",
    "render_hosted_prompt_result",
    "render_prompt",
    "scaffold_subject",
    # functions
    "seal_envelope",
    "segment",
    "sha256_hex",
    "to_messages",
    "to_wire",
    "ultrarouter_manifest_encoder",
]
