"""Request and episode correlation (pure helpers).

Every gateway response carries the request id (``req_...``) in the ``x-ur-request-id`` header and
in the ``ur`` block of the body. Two optional request headers tie your own records to it:

* ``x-ur-request-id``: a request id **you** mint before the call (``[A-Za-z0-9_-]{1,64}``), so you
  know it even when the response is lost or still streaming. :func:`new_request_id` mints one.
* ``x-ur-artifact``: the **episode key**. Every step (model call) that carries the same key belongs
  to one episode, so a terminal outcome reported on the last step is attributed to the whole task.
  The body field ``ur.artifact`` is equivalent; the body wins when both are sent.

Why concurrent episodes need distinct keys: without an explicit key the gateway groups steps into
episodes by their opening text. Two tasks that start with the same text at the same time (two
users asking the same question, a batch of identical jobs) are then indistinguishable and their
steps and outcomes would be merged. Give each concurrent task its own key
(:func:`new_episode_key`, or your own stable id such as ``"order:A-100"``).
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from ._errors import InvalidRequestError
from ._queue import new_ulid

__all__ = [
    "EPISODE_HEADER",
    "MAX_EPISODE_KEY_LENGTH",
    "REQUEST_ID_HEADER",
    "REQUEST_ID_PATTERN",
    "correlation_headers",
    "is_valid_request_id",
    "new_episode_key",
    "new_request_id",
    "request_id_of",
    "validate_episode_key",
    "validate_request_id",
]

#: The header carrying the request id, on every response and optionally on a request.
REQUEST_ID_HEADER = "x-ur-request-id"

#: The header carrying the episode key (``X-UR-Artifact``) on a request.
EPISODE_HEADER = "x-ur-artifact"

#: What a client-minted request id must match.
REQUEST_ID_PATTERN = re.compile(r"[A-Za-z0-9_-]{1,64}")

#: The longest episode key the SDK sends.
MAX_EPISODE_KEY_LENGTH = 256

#: Printable ASCII with no leading or trailing space: what a header value carries unchanged.
_EPISODE_KEY_PATTERN = re.compile(r"[!-~](?:[ -~]*[!-~])?")


def new_request_id() -> str:
    """Mint a client-side request id to send as ``x-ur-request-id``: ``"req_c_"`` plus a ULID.

    The ``req_c_`` prefix keeps a client-minted id apart from the ids the gateway mints itself
    (``req_<ULID>``). The same scheme as the TypeScript SDK's ``mintRequestId``.
    """
    return "req_c_" + new_ulid()


def new_episode_key(prefix: str = "ep") -> str:
    """Mint a unique episode key: ``"<prefix>_"`` plus a ULID (``ep_01J...`` by default)."""
    return validate_episode_key(f"{prefix}_{new_ulid()}")


def is_valid_request_id(value: object) -> bool:
    """Whether ``value`` is a string matching ``[A-Za-z0-9_-]{1,64}``."""
    return isinstance(value, str) and REQUEST_ID_PATTERN.fullmatch(value) is not None


def validate_request_id(value: str) -> str:
    """Return ``value`` unchanged, or raise :class:`~ultrarouter.InvalidRequestError` (status 0)."""
    if not is_valid_request_id(value):
        raise InvalidRequestError(
            "request_id must match [A-Za-z0-9_-]{1,64} (use ultrarouter.new_request_id())",
            status=0,
        )
    return value


def validate_episode_key(value: str) -> str:
    """Return ``value`` unchanged, or raise :class:`~ultrarouter.InvalidRequestError` (status 0).

    An episode key is 1 to 256 printable ASCII characters with no leading or trailing space (it
    travels in a header). Send any other key in the body as ``ur.artifact`` instead.
    """
    if (
        not isinstance(value, str)
        or len(value) > MAX_EPISODE_KEY_LENGTH
        or _EPISODE_KEY_PATTERN.fullmatch(value) is None
    ):
        raise InvalidRequestError(
            f"episode_key must be 1 to {MAX_EPISODE_KEY_LENGTH} printable ASCII characters with "
            "no leading or trailing space; send any other key in the body as ur.artifact",
            status=0,
        )
    return value


def correlation_headers(
    *, request_id: str | None = None, episode_key: str | None = None
) -> dict[str, str]:
    """The correlation headers for one call, validated.

    Pass the result as ``extra_headers`` to any OpenAI-compatible client pointed at the gateway
    (for example the ``openai`` package) to know the request id before the call and to group the
    call into an episode::

        from ultrarouter import correlation_headers, new_request_id

        request_id = new_request_id()
        headers = correlation_headers(request_id=request_id, episode_key="order:A-100")
        assert headers == {"x-ur-request-id": request_id, "x-ur-artifact": "order:A-100"}
    """
    headers: dict[str, str] = {}
    if request_id is not None:
        headers[REQUEST_ID_HEADER] = validate_request_id(request_id)
    if episode_key is not None:
        headers[EPISODE_HEADER] = validate_episode_key(episode_key)
    return headers


def _from_headers(headers: Any) -> str | None:
    if headers is None:
        return None
    try:
        value = headers.get(REQUEST_ID_HEADER)
    except Exception:  # an exotic headers object; treat as absent
        return None
    return value if isinstance(value, str) and value else None


def _from_ur(ur: Any) -> str | None:
    value = ur.get("request_id") if isinstance(ur, Mapping) else getattr(ur, "request_id", None)
    return value if isinstance(value, str) and value else None


def request_id_of(result: Any) -> str:
    """The gateway request id of a result, whichever client produced it.

    Accepts a request id string, an SDK response (``reply.ur.request_id``), a
    :class:`~ultrarouter.Stream` or :class:`~ultrarouter.AsyncStream` (known from the response
    header before the first chunk), an ``openai`` package response or stream pointed at the
    gateway (the ``ur`` block it keeps as an extra field, or the response headers), an
    ``httpx.Response``, or a mapping with a ``ur`` block. Raises
    :class:`~ultrarouter.InvalidRequestError` (status 0) when no id can be found.
    """
    if isinstance(result, str):
        return validate_request_id(result) if result else _missing()
    direct = getattr(result, "request_id", None)
    if isinstance(direct, str) and direct:
        return direct
    found = _from_ur(getattr(result, "ur", None))
    if found is None and isinstance(result, Mapping):
        found = _from_ur(result.get("ur"))
    if found is None:
        extra = getattr(result, "model_extra", None)
        if isinstance(extra, Mapping):
            found = _from_ur(extra.get("ur"))
    if found is None:
        found = _from_headers(getattr(result, "headers", None))
    if found is None:
        found = _from_headers(getattr(getattr(result, "response", None), "headers", None))
    return found if found is not None else _missing()


def _missing() -> str:
    raise InvalidRequestError(
        "no ultrarouter request id found on this result (expected a ur block or an "
        "x-ur-request-id header); mint one up front with new_request_id()",
        status=0,
    )
