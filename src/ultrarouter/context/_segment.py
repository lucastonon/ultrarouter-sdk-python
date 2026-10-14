"""Segmentation: split a chat request into typed parts before any transform.

Pure. Uses role boundaries, retrieval-style delimiters and few-shot markers (English,
Portuguese, Spanish). Only ``reference_context`` and ``history`` parts are eligible for lossy
compression. ``from_messages`` drives it with messages only; ``ur.segments`` hints refine it (a
hint for a message index overrides the heuristic).
"""

from __future__ import annotations

from typing import Any

from ._never_touch import PinnedSpan, pin_never_touch_spans

__all__ = ["HINTABLE_SEGMENT_KINDS", "SEGMENT_KINDS", "segment"]

SEGMENT_KINDS: tuple[str, ...] = (
    "system_instructions",
    "user_question",
    "reference_context",
    "few_shot_examples",
    "tool_schemas",
    "tool_results",
    "history",
    "output_contract",
)

HINTABLE_SEGMENT_KINDS: tuple[str, ...] = (
    "system_instructions",
    "user_question",
    "reference_context",
    "few_shot_examples",
    "tool_results",
    "history",
)

_RAG_DELIMITERS = (
    "<document",
    "</document",
    "<doc>",
    "</doc>",
    "<context",
    "</context",
    "<source",
    '"""',
    "```json",
    "\n---\n",
    "[doc",
    "context:",
    "contexto:",
    "reference:",
    "referência:",
    "referencia:",
    "source:",
    "fonte:",
    "fuente:",
    "begin context",
    "<<<",
    ">>>",
)

_FEW_SHOT_MARKERS = (
    "example",
    "exemplo",
    "ejemplo",
    "q:",
    "a:",
    "input:",
    "output:",
    "few-shot",
)


def _has_rag_delimiter(text: str | None) -> bool:
    if text is None:
        return False
    lowered = text.lower()
    return any(d != "" and d.lower() in lowered for d in _RAG_DELIMITERS)


_JS_WHITESPACE = (
    "\t\n\x0b\x0c\r \u00a0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007"
    "\u2008\u2009\u200a\u2028\u2029\u202f\u205f\u3000\ufeff"
)


def _looks_like_few_shot(text: str | None) -> bool:
    if text is None:
        return False
    lowered = text.lstrip(_JS_WHITESPACE).lower()
    return any(lowered.startswith(marker) for marker in _FEW_SHOT_MARKERS)


def _text_of(message: dict[str, Any]) -> str | None:
    content = message.get("content")
    return content if isinstance(content, str) else None


def _eligible_for_kind(kind: str) -> bool:
    return kind in ("reference_context", "history")


def _is_js_integer(value: Any) -> bool:
    """``Number.isInteger`` semantics: an int, or a float with no fractional part."""
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return True
    return isinstance(value, float) and value.is_integer()


def to_utf16_view(text: str) -> str:
    """``text`` with every astral character split into its UTF-16 surrogate pair.

    Indexing the result behaves like indexing a JavaScript string (UTF-16 code units).
    """
    if all(ord(ch) < 0x10000 for ch in text):
        return text
    out: list[str] = []
    for ch in text:
        code = ord(ch)
        if code >= 0x10000:
            code -= 0x10000
            out.append(chr(0xD800 + (code >> 10)))
            out.append(chr(0xDC00 + (code & 0x3FF)))
        else:
            out.append(ch)
    return "".join(out)


def from_utf16_view(text: str) -> str:
    """Inverse of :func:`to_utf16_view`: re-join surrogate pairs (lone surrogates are kept)."""
    if all(not 0xD800 <= ord(ch) <= 0xDFFF for ch in text):
        return text
    return text.encode("utf-16-le", "surrogatepass").decode("utf-16-le", "surrogatepass")


def utf16_length(text: str) -> int:
    """The JavaScript ``length`` of ``text`` (UTF-16 code units)."""
    return len(text) + sum(1 for ch in text if ord(ch) >= 0x10000)


def _hints_by_index(request: dict[str, Any]) -> dict[int, dict[str, Any]]:
    result: dict[int, dict[str, Any]] = {}
    segments = request.get("segments")
    if not isinstance(segments, list):
        return result
    for hint in segments:
        if isinstance(hint, dict) and _is_js_integer(hint.get("index")):
            result[int(hint["index"])] = hint
    return result


def _is_high_surrogate(code: int) -> bool:
    return 0xD800 <= code <= 0xDBFF


def _is_low_surrogate(code: int) -> bool:
    return 0xDC00 <= code <= 0xDFFF


def _is_code_point_boundary(text: str, pos: int) -> bool:
    if pos <= 0 or pos >= len(text):
        return True
    return not (_is_high_surrogate(ord(text[pos - 1])) and _is_low_surrogate(ord(text[pos])))


def _snap_outward(text: str, pos: int, direction: int, pins: list[PinnedSpan]) -> int:
    p = max(0, min(len(text), pos))
    for _ in range(len(text) + 2):
        moved = False
        if not _is_code_point_boundary(text, p):
            p = p + 1 if direction == 1 else p - 1
            moved = True
        for pin in pins:
            if p > pin.start and p < pin.end:
                p = pin.end if direction == 1 else pin.start
                moved = True
        if not moved:
            break
    return max(0, min(len(text), p))


def _parse_hint_span(
    hint: dict[str, Any], text: str | None, pins: list[PinnedSpan]
) -> dict[str, Any]:
    has_start = "start" in hint
    has_end = "end" in hint
    if not has_start and not has_end:
        return {"kind": "whole"}
    if text is None:
        return {"kind": "invalid", "reason": "non_string_content"}
    if has_start != has_end:
        return {"kind": "invalid", "reason": "partial_span"}
    raw_start = hint["start"]
    raw_end = hint["end"]
    if not _is_js_integer(raw_start) or not _is_js_integer(raw_end):
        return {"kind": "invalid", "reason": "non_integer"}
    raw_start = int(raw_start)
    raw_end = int(raw_end)
    length = len(text)
    if raw_start < 0 or raw_end < 0 or raw_start > length or raw_end > length:
        return {"kind": "invalid", "reason": "out_of_range"}
    if raw_start >= raw_end:
        return {"kind": "invalid", "reason": "inverted_or_empty"}
    start = _snap_outward(text, raw_start, 1, pins)
    end = _snap_outward(text, raw_end, -1, pins)
    if start >= end:
        return {"kind": "invalid", "reason": "collapsed_on_boundary_snap"}
    if start == 0 and end == length:
        return {"kind": "whole"}
    return {"kind": "span", "start": start, "end": end}


def _has_output_contract(response_format: Any) -> bool:
    if not isinstance(response_format, dict):
        return False
    return response_format.get("type") in ("json_object", "json_schema")


def _make_segment(
    *,
    kind: str,
    eligible: bool,
    origin: str,
    messageIndex: int,
    role: str | None,
    text: str | None,
    message: dict[str, Any] | None,
    protected: bool = False,
    spanStart: int | None = None,
    spanEnd: int | None = None,
) -> dict[str, Any]:
    seg: dict[str, Any] = {
        "kind": kind,
        "eligible": eligible,
        "origin": origin,
        "messageIndex": messageIndex,
        "role": role,
        "text": text,
        "message": message,
        "protected": protected,
        "note": False,
        "dropped": False,
    }
    if spanStart is not None:
        seg["spanStart"] = spanStart
    if spanEnd is not None:
        seg["spanEnd"] = spanEnd
    return seg


def _split_at_span(
    *,
    heuristicKind: str,
    hintKind: str,
    span: dict[str, int],
    messageIndex: int,
    role: str | None,
    text: str,
    message: dict[str, Any],
) -> list[dict[str, Any]]:
    start = span["start"]
    end = span["end"]
    out: list[dict[str, Any]] = []
    if start > 0:
        out.append(
            _make_segment(
                kind=heuristicKind,
                eligible=False,
                protected=True,
                origin="message",
                messageIndex=messageIndex,
                role=role,
                text=from_utf16_view(text[:start]),
                message=message,
                spanStart=0,
                spanEnd=start,
            )
        )
    out.append(
        _make_segment(
            kind=hintKind,
            eligible=_eligible_for_kind(hintKind),
            origin="message",
            messageIndex=messageIndex,
            role=role,
            text=from_utf16_view(text[start:end]),
            message=message,
            spanStart=start,
            spanEnd=end,
        )
    )
    if end < len(text):
        out.append(
            _make_segment(
                kind=heuristicKind,
                eligible=False,
                protected=True,
                origin="message",
                messageIndex=messageIndex,
                role=role,
                text=from_utf16_view(text[end:]),
                message=message,
                spanStart=end,
                spanEnd=len(text),
            )
        )
    return out


def segment(request: dict[str, Any]) -> dict[str, Any]:
    """Segment a request into typed parts. Returns ``{"parts", "unparseable", "warnings"?}``."""
    messages = request.get("messages")
    if not isinstance(messages, list):
        return {"parts": [], "unparseable": True}
    hints = _hints_by_index(request)

    last_user_index = -1
    for i in range(len(messages) - 1, -1, -1):
        message = messages[i]
        if isinstance(message, dict) and message.get("role") == "user":
            last_user_index = i
            break

    parts: list[dict[str, Any]] = []
    warnings: list[str] = []
    prev_kind: str | None = None
    for i, message in enumerate(messages):
        if message is None:
            continue
        role = message.get("role") if isinstance(message.get("role"), str) else None
        text = _text_of(message)

        eligible = False
        if role in ("system", "developer"):
            kind = "system_instructions"
        elif role == "tool":
            kind = "tool_results"
        elif role == "assistant":
            if prev_kind == "few_shot_examples":
                kind = "few_shot_examples"
            else:
                kind = "history"
                eligible = True
        elif role == "user":
            if i == last_user_index:
                kind = "user_question"
            elif _looks_like_few_shot(text):
                kind = "few_shot_examples"
            elif _has_rag_delimiter(text):
                kind = "reference_context"
                eligible = True
            else:
                kind = "history"
                eligible = True
        else:
            kind = "history"
            eligible = False

        hint = hints.get(i)
        heuristic_kind = kind
        view = to_utf16_view(text) if text is not None else None
        parsed = (
            _parse_hint_span(hint, view, pin_never_touch_spans(view or ""))
            if hint is not None
            else None
        )

        if hint is not None and parsed is not None and parsed["kind"] == "invalid":
            warnings.append(f"segment_hint_ignored:index={i}:reason={parsed['reason']}")
            parts.append(
                _make_segment(
                    kind=kind,
                    eligible=eligible,
                    origin="message",
                    messageIndex=i,
                    role=role,
                    text=text,
                    message=message,
                )
            )
        elif (
            hint is not None
            and parsed is not None
            and parsed["kind"] == "span"
            and view is not None
        ):
            kind = hint["kind"]
            eligible = _eligible_for_kind(hint["kind"])
            for sub in _split_at_span(
                heuristicKind=heuristic_kind,
                hintKind=hint["kind"],
                span={"start": parsed["start"], "end": parsed["end"]},
                messageIndex=i,
                role=role,
                text=view,
                message=message,
            ):
                parts.append(sub)
        else:
            if hint is not None:
                kind = hint["kind"]
                eligible = _eligible_for_kind(hint["kind"])
            parts.append(
                _make_segment(
                    kind=kind,
                    eligible=eligible,
                    origin="message",
                    messageIndex=i,
                    role=role,
                    text=text,
                    message=message,
                )
            )
        prev_kind = kind

    tools = request.get("tools")
    if isinstance(tools, list) and len(tools) > 0:
        parts.append(
            _make_segment(
                kind="tool_schemas",
                eligible=False,
                origin="tools",
                messageIndex=-1,
                role=None,
                text=None,
                message=None,
            )
        )
    if _has_output_contract(request.get("responseFormat")):
        parts.append(
            _make_segment(
                kind="output_contract",
                eligible=False,
                origin="response_format",
                messageIndex=-1,
                role=None,
                text=None,
                message=None,
            )
        )

    if warnings:
        return {"parts": parts, "unparseable": False, "warnings": warnings}
    return {"parts": parts, "unparseable": False}
