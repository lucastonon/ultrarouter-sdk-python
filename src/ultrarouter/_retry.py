"""Pure retry-policy helpers shared by the sync and async transports.

Retries cover HTTP 408, 429 and 5xx responses whose body does not say ``retryable: false``,
plus connection failures. Backoff is jittered exponential (0.5 s base, 8 s cap) and honours a
``Retry-After`` header; the sleep never extends past the call's total timeout. Every
non-streaming ``POST`` carries an idempotency key that stays the same across retries, so the
gateway replays a retried mutation instead of executing it twice.
"""

from __future__ import annotations

import uuid
from email.utils import parsedate_to_datetime

from ._errors import UltraRouterError, is_retryable_status

__all__ = [
    "BASE_DELAY_S",
    "MAX_DELAY_S",
    "backoff_seconds",
    "capped_backoff",
    "parse_retry_after",
    "resolve_idempotency_key",
    "should_retry",
]

BASE_DELAY_S = 0.5
MAX_DELAY_S = 8.0


def parse_retry_after(header: str | None, now: float) -> float | None:
    """Parse a ``Retry-After`` header (delta-seconds or HTTP date) into seconds, or ``None``.

    ``now`` is the current epoch time in seconds (injected so the function stays pure).
    """
    if header is None:
        return None
    value = header.strip()
    try:
        return max(0.0, float(value))
    except ValueError:
        pass
    try:
        when = parsedate_to_datetime(value)
    except (TypeError, ValueError, IndexError):
        return None
    return max(0.0, when.timestamp() - now)


def backoff_seconds(attempt: int, retry_after: float | None, rand: float) -> float:
    """Jittered exponential backoff for 0-based ``attempt``; ``Retry-After`` wins when present.

    ``rand`` is a number in ``[0, 1)``; the delay is ``window * (0.5 + rand / 2)``.
    """
    if retry_after is not None:
        return min(retry_after, MAX_DELAY_S * 4)
    window = min(MAX_DELAY_S, BASE_DELAY_S * (2.0**attempt))
    return window * (0.5 + rand * 0.5)


def capped_backoff(attempt: int, retry_after: float | None, rand: float, remaining: float) -> float:
    """:func:`backoff_seconds` clamped so a sleep never outlives the remaining time budget."""
    return max(0.0, min(backoff_seconds(attempt, retry_after, rand), remaining))


def should_retry(error: UltraRouterError, attempt: int, max_retries: int) -> bool:
    """Whether ``error`` (raised on 0-based ``attempt``) may be retried.

    A response error retries only when its status is retryable (408/429/5xx) AND the gateway
    did not mark it ``retryable: false``. A connection error retries; a timeout never does.
    """
    if attempt >= max_retries or not error.retryable:
        return False
    if error.status == 0:
        return error.code == "connection"
    return is_retryable_status(error.status)


def resolve_idempotency_key(method: str, stream: bool, explicit: str | None) -> str | None:
    """The caller's key, else a fresh UUID for a non-streaming ``POST`` (``None`` otherwise)."""
    if explicit is not None:
        return explicit
    if method.upper() == "POST" and not stream:
        return str(uuid.uuid4())
    return None
