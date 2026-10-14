"""Where a learned context module goes in a message list (pure helpers).

The gateway inserts a learned module immediately after the leading run of ``system`` messages,
as a ``user`` message carrying the module text. That keeps the provider's stable prompt prefix
byte-identical (good for prompt caching) and places the learned block ahead of every volatile
turn. When there is no leading system message the block goes first.

:meth:`ultrarouter.LearnedSession.apply` uses these helpers so a call you make directly to a
provider receives the module in exactly the place a proxied call would. They are also exported
from :mod:`ultrarouter.context` for use without a client.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, TypedDict

__all__ = [
    "LEARNED_MESSAGE_ROLE",
    "LearnedMessage",
    "apply_learned_context",
    "learned_placement_index",
]

#: The role the learned block is inserted under (a data ``user`` message).
LEARNED_MESSAGE_ROLE = "user"


class LearnedMessage(TypedDict):
    """The message :func:`apply_learned_context` inserts."""

    role: str
    content: str


def _role_of(message: Any) -> Any:
    if isinstance(message, Mapping):
        return message.get("role")
    return getattr(message, "role", None)


def learned_placement_index(messages: Sequence[Any]) -> int:
    """Return the index right after the leading run of ``system`` messages.

    ``messages`` items may be mappings with a ``"role"`` key or objects with a ``role`` attribute.
    """
    index = 0
    while index < len(messages) and _role_of(messages[index]) == "system":
        index += 1
    return index


def apply_learned_context(messages: Sequence[Any], content: str | None) -> list[Any]:
    """Return a new list with ``{"role": "user", "content": content}`` inserted at the index.

    ``messages`` is never mutated. When ``content`` is ``None`` or empty (a holdout arm, or no
    learned module) the messages are returned unchanged (as a new list).
    """
    if not content:
        return list(messages)
    at = learned_placement_index(messages)
    block: LearnedMessage = {"role": LEARNED_MESSAGE_ROLE, "content": content}
    return [*messages[:at], block, *messages[at:]]
