"""The client-side cache behind :meth:`~ultrarouter.UltraRouter.preflight` (pure helpers).

``POST /v1/preflight`` answers, before a call you make yourself: which model and fallbacks to
use, which learned context module to inject (and where), and, when you pass a cluster key
(``artifact_key`` or ``trace_id``), the exposure grant that assigns this call to the treated or
holdout arm.

The response has two cache lifetimes and one part that is never cached:

* the **config part** (routing model, learned module, hosted prompt) carries a strong ``ETag``
  and ``Cache-Control: private, max-age=5``; it is revalidated with ``If-None-Match``, and a
  ``304 Not Modified`` reuses the cached body;
* the **live part** (health-ordered fallbacks) is fresh for 30 seconds
  (``X-UR-Live-Max-Age`` / ``routing.max_age_s``); after that a full refetch is required;
* the **grant** is never cached: it is read from the ``X-UR-Grant`` header of every response,
  including a 304, and stripped from the stored body.

When ``messages`` are sent (needed for case-based learned modules), their digest is part of the
cache key, so a module rendered for one input is never served for another. The messages
themselves are never stored.

The cache is bounded: at most :data:`DEFAULT_PREFLIGHT_CACHE_SIZE` identities per client by
default (``preflight_cache_size=`` on the client), least recently used first out, and entries
whose live part has expired are evicted, so unique per-call identities cannot grow it forever.

Every function here is pure, so the cache decision is testable in isolation.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import threading
from collections import OrderedDict
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal

__all__ = [
    "DEFAULT_PREFLIGHT_CACHE_SIZE",
    "PREFLIGHT_DEFAULT_CONFIG_MAX_AGE_S",
    "PREFLIGHT_DEFAULT_LIVE_MAX_AGE_S",
    "PREFLIGHT_GRANT_HEADER",
    "PREFLIGHT_LIVE_MAX_AGE_HEADER",
    "PreflightCache",
    "PreflightCacheDecision",
    "PreflightCacheEntry",
    "build_cache_entry",
    "decide_preflight_cache",
    "parse_grant_header",
    "parse_max_age_seconds",
    "preflight_cache_key",
    "preflight_has_cluster_key",
    "with_header_grant",
]

#: Response header carrying the exposure grant (uncached; present on 200 and 304).
PREFLIGHT_GRANT_HEADER = "x-ur-grant"
#: Response header carrying the live-part (fallbacks) max age in seconds.
PREFLIGHT_LIVE_MAX_AGE_HEADER = "x-ur-live-max-age"
#: Default config-part max age in seconds (``Cache-Control: private, max-age=5``).
PREFLIGHT_DEFAULT_CONFIG_MAX_AGE_S = 5
#: Default live-part max age in seconds.
PREFLIGHT_DEFAULT_LIVE_MAX_AGE_S = 30
#: Default bound on cached preflight identities per client (least recently used evicted first).
DEFAULT_PREFLIGHT_CACHE_SIZE = 1024

_MAX_AGE_RE = re.compile(r"(?:^|,)\s*max-age\s*=\s*(\d+)", re.IGNORECASE)


@dataclass
class PreflightCacheEntry:
    """A cached preflight response. ``body`` always has ``grant`` set to ``None``."""

    etag: str
    """The strong ETag the response carried (sent back as ``If-None-Match``)."""

    body: dict[str, Any]
    """The response body with the grant stripped."""

    stored_at_ms: float
    """When the entry was stored by a full (non-304) fetch, in epoch milliseconds."""

    config_max_age_s: float
    """Freshness of the config part, in seconds."""

    live_max_age_s: float
    """Freshness of the live part (fallbacks), in seconds."""


@dataclass
class PreflightCacheDecision:
    """How to serve one preflight call (computed by :func:`decide_preflight_cache`).

    ``kind`` is ``"fresh"`` (serve from cache, no network), ``"revalidate"`` (send
    ``If-None-Match: <if_none_match>``; a 304 reuses the body) or ``"fetch"`` (unconditional).
    """

    kind: Literal["fresh", "revalidate", "fetch"]
    if_none_match: str | None = None


def decide_preflight_cache(
    entry: PreflightCacheEntry | None,
    now_ms: float,
    has_cluster_key: bool,
    live_max_age_override_s: float | None = None,
) -> PreflightCacheDecision:
    """Decide how to serve a preflight call from the two-lifetime cache.

    * no entry: ``fetch``;
    * the live part expired: ``fetch`` (a 304 must never resurrect stale fallbacks);
    * live part fresh, no cluster key and config part fresh: ``fresh`` (no network);
    * otherwise: ``revalidate`` (a cluster key always needs a fresh grant).
    """
    if entry is None:
        return PreflightCacheDecision(kind="fetch")
    age_ms = now_ms - entry.stored_at_ms
    live_s = (
        live_max_age_override_s if live_max_age_override_s is not None else entry.live_max_age_s
    )
    if age_ms >= live_s * 1000:
        return PreflightCacheDecision(kind="fetch")
    if not has_cluster_key and age_ms < entry.config_max_age_s * 1000:
        return PreflightCacheDecision(kind="fresh")
    return PreflightCacheDecision(kind="revalidate", if_none_match=entry.etag)


def preflight_has_cluster_key(params: Mapping[str, Any]) -> bool:
    """Whether a preflight request carries a cluster key (so a grant will be minted)."""
    return params.get("artifact_key") is not None or params.get("trace_id") is not None


def _messages_digest(messages: Any) -> str | None:
    if messages is None:
        return None
    encoded = json.dumps(messages, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def preflight_cache_key(params: Mapping[str, Any]) -> str:
    """A stable cache key: call type, cluster key, budget and a digest of ``messages``."""
    return json.dumps(
        {
            "call_type": params.get("call_type"),
            "artifact_key": params.get("artifact_key"),
            "trace_id": params.get("trace_id"),
            "budget": params.get("budget"),
            "messages_sha256": _messages_digest(params.get("messages")),
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def parse_grant_header(value: str | None) -> dict[str, Any] | None:
    """Parse the ``X-UR-Grant`` header into a dict; ``None`` when absent, blank or invalid."""
    if not value:
        return None
    try:
        parsed = json.loads(value)
    except ValueError:
        return None
    return parsed if isinstance(parsed, dict) else None


def parse_max_age_seconds(cache_control: str | None) -> int | None:
    """Extract ``max-age`` seconds from a ``Cache-Control`` header value, or ``None``."""
    if cache_control is None:
        return None
    match = _MAX_AGE_RE.search(cache_control)
    return int(match.group(1)) if match else None


def with_header_grant(
    body: Mapping[str, Any], header_grant: dict[str, Any] | None
) -> dict[str, Any]:
    """Return a copy of ``body`` whose grant comes from the header, never from the cache.

    Without a header grant, ``grant`` is ``None`` and the body's ``grant_reason`` is kept;
    with one, ``grant_reason`` is ``None``.
    """
    return {
        **body,
        "grant": header_grant,
        "grant_reason": body.get("grant_reason") if header_grant is None else None,
    }


def build_cache_entry(
    body: Mapping[str, Any], etag: str, headers: Mapping[str, str], stored_at_ms: float
) -> PreflightCacheEntry:
    """Build a cache entry from a 200 response (the grant is stripped, never stored)."""
    config_max_age = parse_max_age_seconds(headers.get("cache-control"))
    live_candidate: float | None = None
    raw_live = headers.get(PREFLIGHT_LIVE_MAX_AGE_HEADER)
    if raw_live:
        try:
            live_candidate = float(raw_live)
        except ValueError:
            live_candidate = None
        if live_candidate is not None and (math.isnan(live_candidate) or live_candidate <= 0):
            live_candidate = None
    routing = body.get("routing")
    routing_max_age = routing.get("max_age_s") if isinstance(routing, Mapping) else None
    live_max_age = live_candidate or routing_max_age or PREFLIGHT_DEFAULT_LIVE_MAX_AGE_S
    return PreflightCacheEntry(
        etag=etag,
        body={**body, "grant": None},
        stored_at_ms=stored_at_ms,
        config_max_age_s=float(
            config_max_age if config_max_age is not None else PREFLIGHT_DEFAULT_CONFIG_MAX_AGE_S
        ),
        live_max_age_s=float(live_max_age),
    )


def _expired(entry: PreflightCacheEntry, now_ms: float) -> bool:
    return now_ms - entry.stored_at_ms >= entry.live_max_age_s * 1000


class PreflightCache:
    """A bounded in-memory preflight cache, one entry per request identity (one per client).

    At most ``max_entries`` entries are kept (default :data:`DEFAULT_PREFLIGHT_CACHE_SIZE`);
    storing one more evicts the least recently used. Entries whose live part has expired can
    never be served again, so they are dropped when read and swept whenever an entry is stored.
    ``max_entries=0`` disables caching. Safe to share between threads.
    """

    def __init__(self, max_entries: int = DEFAULT_PREFLIGHT_CACHE_SIZE) -> None:
        if max_entries < 0:
            raise ValueError(f"max_entries must be >= 0 (got {max_entries})")
        self.max_entries: int = max_entries
        self._entries: OrderedDict[str, PreflightCacheEntry] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: str, now_ms: float | None = None) -> PreflightCacheEntry | None:
        """Return the entry for ``key`` (marking it recently used), if any.

        With ``now_ms``, an entry whose live part has expired is dropped and ``None`` returned.
        """
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            if now_ms is not None and _expired(entry, now_ms):
                del self._entries[key]
                return None
            self._entries.move_to_end(key)
            return entry

    def set(self, key: str, entry: PreflightCacheEntry) -> None:
        """Store ``entry`` under ``key``, sweeping expired entries and evicting beyond the bound."""
        if self.max_entries == 0:
            return
        with self._lock:
            now_ms = entry.stored_at_ms
            for stale in [k for k, e in self._entries.items() if _expired(e, now_ms)]:
                del self._entries[stale]
            self._entries[key] = entry
            self._entries.move_to_end(key)
            while len(self._entries) > self.max_entries:
                self._entries.popitem(last=False)

    def clear(self) -> None:
        """Drop every entry."""
        with self._lock:
            self._entries.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._entries)
