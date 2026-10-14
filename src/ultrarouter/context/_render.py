"""``render`` and the exit function ``to_messages``.

``render`` turns a compiled manifest plus bodies into provider messages through a serializer.
``to_messages`` is the exit: for a *lifted* manifest it rebuilds the exact original ``messages``
(byte-identical); for a compiled manifest it renders the supplied bodies with the default
serializer. Nothing in the gateway requires a manifest, so leaving is always possible.
"""

from __future__ import annotations

from typing import Any

from ._manifest import Manifest, ManifestEntry
from ._messages import ChatMessage, RenderSerializer, default_render_serializer

__all__ = ["ContextExitError", "render", "to_messages"]


class ContextExitError(Exception):
    """Raised when ``to_messages`` is asked to exit a manifest that carries neither lift
    reconstruction data nor supplied bodies."""


def render(
    manifest: Manifest,
    bodies: dict[str, str],
    serializer: RenderSerializer = default_render_serializer,
) -> list[ChatMessage]:
    """Render a compiled manifest into provider messages using a serializer (default: the
    ultrarouter serializer). ``bodies`` maps ``moduleId`` → body text. Pure."""
    return serializer(manifest, bodies)


def _lift_ext_of(manifest: Manifest) -> dict[str, Any] | None:
    ext = manifest.get("ext")
    if ext is None:
        return None
    lift = ext.get("lift")
    if lift is None or not isinstance(lift, dict):
        return None
    messages = lift.get("messages")
    if not isinstance(messages, list):
        return None
    return lift


def _entry_text(entry: ManifestEntry) -> str:
    ext = entry.get("ext")
    if ext is None:
        return ""
    text = ext.get("text")
    return text if isinstance(text, str) else ""


def _entry_message_index(entry: ManifestEntry) -> int | None:
    ext = entry.get("ext")
    if ext is None:
        return None
    index = ext.get("messageIndex")
    # Booleans are ints in Python; exclude them to mirror the JS ``typeof index === 'number'``.
    return index if isinstance(index, int) and not isinstance(index, bool) else None


def to_messages(manifest: Manifest, bodies: dict[str, str] | None = None) -> list[ChatMessage]:
    """Exit a manifest back to messages. A LIFTED manifest reconstructs the exact original
    input; a COMPILED manifest is rendered from ``bodies`` via the default serializer. Pure."""
    lift = _lift_ext_of(manifest)
    if lift is not None:
        return _reconstruct_from_lift(manifest, lift)
    if bodies is not None:
        return render(manifest, bodies)
    raise ContextExitError("to_messages needs a lifted manifest or a bodies map to exit")


def _reconstruct_from_lift(manifest: Manifest, lift: dict[str, Any]) -> list[ChatMessage]:
    by_message: dict[int, list[ManifestEntry]] = {}
    for entry in manifest["entries"]:
        index = _entry_message_index(entry)
        if index is None:
            continue
        by_message.setdefault(index, []).append(entry)

    records = sorted(lift["messages"], key=lambda record: record["index"])
    messages: list[ChatMessage] = []
    for record in records:
        segments = sorted(
            by_message.get(record["index"], []),
            key=lambda entry: (entry.get("range") or {}).get("start", 0),
        )
        if record["contentIsString"]:
            content: Any = "".join(_entry_text(entry) for entry in segments)
        else:
            content = record["rawContent"]
        message: dict[str, Any] = {}
        for key in record["keyOrder"]:
            message[key] = content if key == "content" else record["scaffold"][key]
        messages.append(message)
    return messages
