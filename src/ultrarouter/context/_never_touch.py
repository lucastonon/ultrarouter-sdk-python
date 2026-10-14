"""Never-touch spans: the character ranges a lossy transform must never remove or alter.

Pure. Given a segment's text it returns protected ``[start, end)`` ranges (code, tables,
structured lines, URLs, e-mails, ids, numbers, money, dates, legal citations, named entities). In
the context runtime it is used only when ``from_messages`` receives span hints.

The patterns reproduce JavaScript regular-expression semantics exactly (the gateway is the
reference): ``\\w``, ``\\d`` and ``\\b`` are ASCII-only, ``\\s`` is the JavaScript whitespace
set, ``^``/``$`` in multi-line patterns honour every JavaScript line terminator, and offsets are
UTF-16 code units (callers pass text in which astral characters are surrogate pairs).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

__all__ = ["PinnedSpan", "overlaps_pinned_span", "pin_never_touch_spans"]


@dataclass(frozen=True)
class PinnedSpan:
    """A protected ``[start, end)`` range and the category that protected it."""

    start: int
    end: int
    category: str


_GAZETTEER = ("LumaShop", "ultrarouter", "OpenRouter")

# JavaScript (non-unicode) character classes, spelled out.
_W = "[A-Za-z0-9_]"
_B = f"(?:(?<={_W})(?!{_W})|(?<!{_W})(?={_W}))"
_WS = "\\t\\n\\x0b\\x0c\\r \\u00a0\\u1680\\u2000-\\u200a\\u2028\\u2029\\u202f\\u205f\\u3000\\ufeff"
_S = f"[{_WS}]"
_NS = f"[^{_WS}]"
_BOL = "(?:\\A|(?<=[\\n\\r\\u2028\\u2029]))"
_EOL = "(?=[\\n\\r\\u2028\\u2029]|\\Z)"
_A = re.ASCII
_AI = re.ASCII | re.IGNORECASE

_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("code_fence", re.compile(r"```[\s\S]*?```", _A)),
    ("code_inline", re.compile(r"`[^`\n]+`", _A)),
    ("table", re.compile(f"{_BOL}[^\\n]*\\|[^\\n]*\\|[^\\n]*{_EOL}", _A)),
    (
        "structure",
        re.compile(f"{_BOL}[ \\t]*[A-Za-z_][A-Za-z0-9_.\\-]*:[ \\t]+{_NS}[^\\n]*{_EOL}", _A),
    ),
    ("structure", re.compile(r"\{[^{}\n]*:[^{}\n]*\}", _A)),
    ("url", re.compile(f"{_B}(?:https?://|www\\.)[^{_WS}<>\"'`]+", _AI)),
    ("email", re.compile(f"{_B}[A-Za-z0-9_.+\\-]+@[A-Za-z0-9_\\-]+\\.[A-Za-z0-9_.\\-]+{_B}", _AI)),
    (
        "uuid",
        re.compile(
            f"{_B}[0-9a-f]{{8}}-[0-9a-f]{{4}}-[0-9a-f]{{4}}-[0-9a-f]{{4}}-[0-9a-f]{{12}}{_B}", _AI
        ),
    ),
    ("currency", re.compile(f"(?:R\\$|US\\$|[$\u20ac\u00a3\u00a5]){_S}?[0-9][0-9.,]*", _A)),
    (
        "currency",
        re.compile(
            f"{_B}[0-9][0-9.,]*{_S}?(?:USD|EUR|BRL|GBP|JPY|reais|d[\u00f3o\u00d3]lares|euros){_B}",
            _AI,
        ),
    ),
    ("date", re.compile(f"{_B}[0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}}{_B}", _A)),
    ("date", re.compile(f"{_B}[0-9]{{1,2}}/[0-9]{{1,2}}/[0-9]{{2,4}}{_B}", _A)),
    (
        "legal_citation",
        re.compile(
            f"{_B}(?:section|sec\\.|clause|article|art\\.|cl[\u00e1a\u00c1]usula|artigo|"
            f"art[\u00edi\u00cd]culo){_S}*\\.?{_S}*[0-9IVXLCDM]+(?:\\.[0-9]+)*",
            _AI,
        ),
    ),
    ("legal_citation", re.compile(f"\u00a7{_S}*[0-9IVXLCDM]+(?:\\.[0-9]+)*", _A)),
    (
        "id",
        re.compile(
            f"{_B}(?=[A-Za-z0-9_\\-]*[0-9])(?=[A-Za-z0-9_\\-]*[A-Za-z])"
            f"[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*{_B}",
            _A,
        ),
    ),
    ("number", re.compile(r"[0-9]+(?:[.,][0-9]+)*", _A)),
    (
        "named_entity",
        re.compile(
            f"{_B}[A-Z\u00c0-\u00dd][A-Za-z\u00c0-\u00ff'\u2019]+"
            f"(?:{_S}+[A-Z\u00c0-\u00dd][A-Za-z\u00c0-\u00ff'\u2019]+)+{_B}",
            _A,
        ),
    ),
)

_GAZETTEER_RE = re.compile(_B + "(?:" + "|".join(re.escape(g) for g in _GAZETTEER) + ")" + _B, _AI)


def _collect(text: str, category: str, pattern: re.Pattern[str], out: list[PinnedSpan]) -> None:
    for match in pattern.finditer(text):
        if match.group(0) == "":
            continue
        out.append(PinnedSpan(match.start(), match.end(), category))


def _merge_spans(spans: list[PinnedSpan]) -> list[PinnedSpan]:
    if len(spans) <= 1:
        return spans
    spans.sort(key=lambda span: (span.start, span.end))
    merged: list[PinnedSpan] = []
    for span in spans:
        last = merged[-1] if merged else None
        if last is not None and span.start <= last.end:
            if span.end > last.end:
                merged[-1] = PinnedSpan(last.start, span.end, last.category)
        else:
            merged.append(span)
    return merged


def pin_never_touch_spans(text: str) -> list[PinnedSpan]:
    """Compute the never-touch spans for a piece of text — a sorted, merged,
    non-overlapping list of protected ``[start, end)`` ranges."""
    if text == "":
        return []
    spans: list[PinnedSpan] = []
    for category, pattern in _PATTERNS:
        _collect(text, category, pattern, spans)
    _collect(text, "named_entity", _GAZETTEER_RE, spans)
    return _merge_spans(spans)


def overlaps_pinned_span(spans: list[PinnedSpan], start: int, end: int) -> bool:
    """Whether a ``[start, end)`` range overlaps ANY pinned span."""
    return any(span.start < end and start < span.end for span in spans)
