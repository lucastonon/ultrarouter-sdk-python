"""``diff_stats(draft, final)``: edit statistics between a draft and its approved final (pure).

Use it to report a human edit without sending either text: lengths, an edit ratio, a count of
changed regions and a SHA-256 of the final are all the gateway needs when the workspace has
not consented to storing corrections (see :meth:`ultrarouter.UltraRouter.artifacts` ``final``).

Lengths and positions are counted in UTF-16 code units, the same unit the gateway and the
TypeScript SDK use, so the numbers agree across languages (a character outside the Basic
Multilingual Plane, such as most emoji, counts as two).

The diff trims the common prefix and suffix, then runs a character LCS over the differing
middle. Inputs whose middle exceeds 4,000,000 LCS cells degrade to "the whole middle changed",
which can only over-report change, never under-report it.
"""

from __future__ import annotations

import hashlib
from typing import TypedDict

from ._jscompat import utf8_bytes, utf16_units

__all__ = ["DiffLengths", "DiffStats", "diff_stats", "sha256_hex"]

_MAX_LCS_CELLS = 4_000_000


class DiffLengths(TypedDict):
    """Lengths of the draft and the final, in UTF-16 code units."""

    draft: int
    final: int


class DiffStats(TypedDict):
    """The result of :func:`diff_stats`."""

    edit_ratio: float
    """Normalized edit ratio in ``[0, 1]``: 0 means identical, 1 means nothing shared."""

    changed_spans: int
    """Number of maximal contiguous changed regions (0 when identical)."""

    lengths: DiffLengths
    """Draft and final lengths."""

    final_hash: str
    """SHA-256 hex digest of the final's UTF-8 bytes."""


def sha256_hex(text: str) -> str:
    """SHA-256 hex digest of ``text`` encoded as UTF-8 (unpaired surrogates become U+FFFD)."""
    return hashlib.sha256(utf8_bytes(text)).hexdigest()


def _common_prefix(a: list[int], b: list[int]) -> int:
    limit = min(len(a), len(b))
    i = 0
    while i < limit and a[i] == b[i]:
        i += 1
    return i


def _common_suffix(a: list[int], b: list[int], prefix: int) -> int:
    limit = min(len(a), len(b)) - prefix
    i = 0
    while i < limit and a[len(a) - 1 - i] == b[len(b) - 1 - i]:
        i += 1
    return i


def _lcs_changed_spans(a: list[int], b: list[int]) -> tuple[int, int]:
    """Bounded LCS: return (matched units, contiguous changed regions)."""
    n = len(a)
    m = len(b)
    width = m + 1
    dp = [0] * ((n + 1) * width)
    for i in range(n - 1, -1, -1):
        ai = a[i]
        row = i * width
        below = (i + 1) * width
        for j in range(m - 1, -1, -1):
            if ai == b[j]:
                dp[row + j] = dp[below + j + 1] + 1
            else:
                down = dp[below + j]
                right = dp[row + j + 1]
                dp[row + j] = down if down >= right else right
    matched = dp[0]
    i = j = spans = 0
    in_change = False
    while i < n and j < m:
        if a[i] == b[j]:
            in_change = False
            i += 1
            j += 1
        else:
            if not in_change:
                spans += 1
                in_change = True
            if dp[(i + 1) * width + j] >= dp[i * width + j + 1]:
                i += 1
            else:
                j += 1
    if (i < n or j < m) and not in_change:
        spans += 1
    return matched, spans


def diff_stats(draft: str, final: str) -> DiffStats:
    """Compute :class:`DiffStats` for ``draft`` → ``final`` (deterministic, no side effects)."""
    a = utf16_units(draft)
    b = utf16_units(final)
    lengths: DiffLengths = {"draft": len(a), "final": len(b)}
    final_hash = sha256_hex(final)
    if a == b:
        return {"edit_ratio": 0, "changed_spans": 0, "lengths": lengths, "final_hash": final_hash}
    prefix = _common_prefix(a, b)
    suffix = _common_suffix(a, b, prefix)
    mid_a = a[prefix : len(a) - suffix]
    mid_b = b[prefix : len(b) - suffix]
    if not mid_a or not mid_b:
        matched_middle = 0
        spans = 0 if (not mid_a and not mid_b) else 1
    elif len(mid_a) * len(mid_b) <= _MAX_LCS_CELLS:
        matched_middle, spans = _lcs_changed_spans(mid_a, mid_b)
    else:
        matched_middle = 0
        spans = 1
    matched = prefix + suffix + matched_middle
    total = lengths["draft"] + lengths["final"]
    ratio = 0.0 if total == 0 else (total - 2 * matched) / total
    ratio = 0.0 if ratio < 0 else 1.0 if ratio > 1 else ratio
    return {
        "edit_ratio": ratio,
        "changed_spans": spans,
        "lengths": lengths,
        "final_hash": final_hash,
    }
