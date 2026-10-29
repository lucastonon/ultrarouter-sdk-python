"""Delayed outcomes from a signed webhook: verify, deduplicate, report with ``source="webhook"``.

A business system (a payment processor, a ticketing tool, your own back office) learns whether a
task succeeded long after the model answered, and tells your application through a webhook. This
module verifies that webhook and reports it exactly once. The checks run in a fixed order, the same
as the TypeScript SDK's ``createWebhookReceiver``:

1. **Headers.** ``x-webhook-signature`` (``sha256=<64 hex>``) and ``x-webhook-timestamp`` (Unix
   seconds) must be present and well formed.
2. **Freshness.** A timestamp more than ``tolerance_s`` (default 300 s) from now, either way, is
   refused, so a captured request cannot be replayed later.
3. **Signature.** HMAC-SHA256 of ``"<timestamp>.<raw body>"`` under the shared secret (the SDK's
   signing recipe), compared in constant time (``hmac.compare_digest``). Several secrets may be
   accepted at once, to rotate one without downtime.
4. **Payload**, parsed only after the signature verified: ``{"event_id", "request_id",
   "verdict"}`` plus optional ``observed_at`` and ``evidence_hash`` (pass ``parse=`` for another
   shape).
5. **Deduplication.** A :class:`DedupeStore` claims the ``event_id`` atomically; a redelivery is a
   no-op. The report is also idempotent on its own (its ``idempotency_key`` is the event id), so
   two processes racing on one delivery still record one outcome.
6. **Report** with ``source="webhook"``. If the gateway did not acknowledge it (the report stayed
   queued) the claim is released and the delivery is *deferred* (answer 503) so the sender
   redelivers; the redelivery replays the identical event.

The secret comes from the environment (``ULTRAROUTER_WEBHOOK_SECRET`` by default) or an explicit
argument; it is never logged, printed or included in an error or a result.
"""

from __future__ import annotations

import hmac
import json
import os
import re
import threading
import time
from collections import OrderedDict
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, Protocol, runtime_checkable

from .._errors import ConfigurationError, InvalidRequestError, UltraRouterError
from .._outcome_report import OutcomeReport
from .._signing import sign_payload, signature_headers
from .._verdicts import Verdict

if TYPE_CHECKING:
    from .._client import AsyncUltraRouter, UltraRouter

__all__ = [
    "DEFAULT_WEBHOOK_SECRET_ENV",
    "DEFAULT_WEBHOOK_TOLERANCE_S",
    "WEBHOOK_SIGNATURE_HEADER",
    "WEBHOOK_TIMESTAMP_HEADER",
    "DedupeStore",
    "MemoryDedupeStore",
    "WebhookHandled",
    "WebhookOutcome",
    "WebhookOutcomeHandler",
    "WebhookPayloadError",
    "WebhookSignatureError",
    "WebhookTimestampError",
    "WebhookVerificationError",
    "WebhookVerifier",
    "parse_webhook_outcome",
    "sign_webhook",
]

#: The default header carrying the webhook signature (``sha256=<hex>``).
WEBHOOK_SIGNATURE_HEADER = "x-webhook-signature"
#: The default header carrying the webhook timestamp (Unix seconds).
WEBHOOK_TIMESTAMP_HEADER = "x-webhook-timestamp"
#: The environment variable the shared secret is read from by default.
DEFAULT_WEBHOOK_SECRET_ENV = "ULTRAROUTER_WEBHOOK_SECRET"  # noqa: S105 - a variable name
#: How far (seconds, either way) a webhook timestamp may be from now.
DEFAULT_WEBHOOK_TOLERANCE_S = 300.0
#: How long a handled event id is remembered by default (seconds): 7 days.
DEFAULT_DEDUPE_TTL_S = 7 * 24 * 3600.0

_SIGNATURE_FORMAT = re.compile(r"sha256=[0-9a-f]{64}")
_TIMESTAMP_FORMAT = re.compile(r"[0-9]{1,12}")

WebhookRejectReason = Literal[
    "missing_signature",
    "missing_timestamp",
    "malformed_signature",
    "malformed_timestamp",
    "stale_timestamp",
    "bad_signature",
    "malformed_payload",
]
"""Why a delivery was refused before anything was reported (the TypeScript SDK's vocabulary)."""


class WebhookVerificationError(UltraRouterError):
    """A webhook was refused before anything was reported.

    ``reason`` is one of the :data:`WebhookRejectReason` values; ``http_status`` is what to answer
    the sender (401, or 400 for a malformed payload). The message never contains the secret, the
    signature or the body.
    """

    default_code = "webhook_invalid"
    http_status: int = 401

    def __init__(self, reason: str, message: str) -> None:
        super().__init__(message)
        self.reason: str = reason


class WebhookSignatureError(WebhookVerificationError):
    """The signature header is missing, malformed, or does not verify under any secret."""

    default_code = "webhook_signature_invalid"


class WebhookTimestampError(WebhookVerificationError):
    """The timestamp header is missing, malformed or outside the tolerance window (a replay)."""

    default_code = "webhook_timestamp_invalid"


class WebhookPayloadError(WebhookVerificationError):
    """The signed body is not the expected JSON payload."""

    default_code = "webhook_payload_invalid"
    http_status = 400

    def __init__(self, message: str) -> None:
        super().__init__("malformed_payload", message)


def _secrets_from(secret: str | Sequence[str] | None, secret_env: str) -> tuple[str, ...]:
    if secret is None:
        value = os.environ.get(secret_env, "")
        if not value:
            raise ConfigurationError(
                f"no webhook secret: pass secret= or set the {secret_env} environment variable",
                code="missing_webhook_secret",
            )
        values: Sequence[str] = (value,)
    elif isinstance(secret, str):
        values = (secret,)
    else:
        values = tuple(secret)
    if not values or any(not isinstance(v, str) or not v for v in values):
        raise ConfigurationError(
            "a webhook secret must be a non-empty string", code="missing_webhook_secret"
        )
    return tuple(values)


def sign_webhook(
    raw_body: str | bytes,
    *,
    secret: str | None = None,
    secret_env: str = DEFAULT_WEBHOOK_SECRET_ENV,
    now_s: float | None = None,
    signature_header: str = WEBHOOK_SIGNATURE_HEADER,
    timestamp_header: str = WEBHOOK_TIMESTAMP_HEADER,
) -> dict[str, str]:
    """The headers a sender attaches: ``x-webhook-timestamp`` and ``x-webhook-signature``.

    For the system that sends the webhook (and for tests). ``raw_body`` must be the exact bytes
    sent. The secret defaults to the ``secret_env`` environment variable.
    """
    key = _secrets_from(secret, secret_env)[0]
    return signature_headers(signature_header, timestamp_header, key, raw_body, now_s)


def _header(headers: Mapping[str, Any], name: str) -> str | None:
    lower = name.lower()
    for key, value in headers.items():
        if str(key).lower() != lower:
            continue
        first = value[0] if isinstance(value, (list, tuple)) and value else value
        return first if isinstance(first, str) else None
    return None


class WebhookVerifier:
    """Verifies a webhook's headers, freshness and signature, then decodes its JSON body.

    Example::

        import json

        from ultrarouter.adapters import WebhookVerifier, sign_webhook

        body = json.dumps({"event_id": "evt_1", "request_id": "req_1", "verdict": "pass"})
        headers = sign_webhook(body, secret="demo-secret")
        payload = WebhookVerifier(secret="demo-secret").verify(body, headers)
        assert payload["verdict"] == "pass"

    Args:
        secret: The shared secret, or several (any one may sign: rotation). Default: the
            ``secret_env`` environment variable.
        secret_env: The environment variable to read the secret from.
        tolerance_s: How far the timestamp may be from now, either way, in seconds.
        signature_header: The signature header name.
        timestamp_header: The timestamp header name.
        clock: Current Unix time in seconds (injectable for tests).
    """

    def __init__(
        self,
        secret: str | Sequence[str] | None = None,
        *,
        secret_env: str = DEFAULT_WEBHOOK_SECRET_ENV,
        tolerance_s: float = DEFAULT_WEBHOOK_TOLERANCE_S,
        signature_header: str = WEBHOOK_SIGNATURE_HEADER,
        timestamp_header: str = WEBHOOK_TIMESTAMP_HEADER,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._secrets = _secrets_from(secret, secret_env)
        self.tolerance_s = float(tolerance_s)
        """The freshness window, in seconds, either way."""
        self.signature_header = signature_header
        """The signature header name."""
        self.timestamp_header = timestamp_header
        """The timestamp header name."""
        self._clock = clock

    def __repr__(self) -> str:
        hidden = f"<{len(self._secrets)} hidden>"
        return f"WebhookVerifier(secrets={hidden}, tolerance_s={self.tolerance_s})"

    def verify(self, raw_body: str | bytes, headers: Mapping[str, Any]) -> dict[str, Any]:
        """Check the headers, the timestamp and the signature; return the decoded JSON object.

        Raises :class:`WebhookSignatureError`, :class:`WebhookTimestampError` or
        :class:`WebhookPayloadError` (each with ``reason``); nothing is reported for a refused
        webhook.
        """
        return self.verify_signed(raw_body, headers)[0]

    def verify_signed(
        self, raw_body: str | bytes, headers: Mapping[str, Any]
    ) -> tuple[dict[str, Any], int]:
        """Like :meth:`verify`, also returning the verified timestamp (Unix seconds)."""
        body = raw_body.encode("utf-8") if isinstance(raw_body, str) else raw_body
        signature = _header(headers, self.signature_header)
        timestamp = _header(headers, self.timestamp_header)
        if not signature:
            raise WebhookSignatureError("missing_signature", "missing webhook signature")
        if not timestamp:
            raise WebhookTimestampError("missing_timestamp", "missing webhook timestamp")
        if _SIGNATURE_FORMAT.fullmatch(signature) is None:
            raise WebhookSignatureError("malformed_signature", "malformed webhook signature")
        if _TIMESTAMP_FORMAT.fullmatch(timestamp) is None:
            raise WebhookTimestampError("malformed_timestamp", "malformed webhook timestamp")
        if abs(int(self._clock()) - int(timestamp)) > self.tolerance_s:
            raise WebhookTimestampError(
                "stale_timestamp",
                f"the webhook timestamp is outside the {self.tolerance_s:g}s tolerance window",
            )
        if not any(
            hmac.compare_digest(sign_payload(key, timestamp, body), signature)
            for key in self._secrets
        ):
            raise WebhookSignatureError("bad_signature", "the webhook signature does not verify")
        try:
            payload = json.loads(body)
        except ValueError:
            raise WebhookPayloadError("the webhook body is not valid JSON") from None
        if not isinstance(payload, dict):
            raise WebhookPayloadError("the webhook body is not a JSON object")
        return payload, int(timestamp)


@dataclass(frozen=True)
class WebhookOutcome:
    """The outcome a webhook carries."""

    event_id: str
    """The sender's id for this event (the deduplication key)."""

    request_id: str
    """The gateway request the outcome is about (the last step of the episode)."""

    verdict: Verdict
    """``pass``, ``fail`` or ``unknown`` (``unknown`` reports nothing)."""

    observed_at: str | None = None
    """When the business outcome happened (ISO-8601), if the sender says."""

    evidence_hash: str | None = None
    """A hash of the sender's evidence, if any."""


def parse_webhook_outcome(payload: Mapping[str, Any]) -> WebhookOutcome:
    """Read the default payload: ``event_id``, ``request_id``, ``verdict`` (``pass``/``fail``/
    ``unknown``), optional ``observed_at`` and ``evidence_hash``; raises
    :class:`WebhookPayloadError` otherwise."""
    event_id, request_id, verdict = (
        payload.get("event_id"),
        payload.get("request_id"),
        payload.get("verdict"),
    )
    if not isinstance(event_id, str) or not event_id:
        raise WebhookPayloadError("event_id is missing")
    if not isinstance(request_id, str) or not request_id:
        raise WebhookPayloadError("request_id is missing")
    if verdict not in ("pass", "fail", "unknown"):
        raise WebhookPayloadError("verdict is invalid")
    observed_at, digest = payload.get("observed_at"), payload.get("evidence_hash")
    return WebhookOutcome(
        event_id=event_id,
        request_id=request_id,
        verdict=verdict,
        observed_at=observed_at if isinstance(observed_at, str) else None,
        evidence_hash=digest if isinstance(digest, str) else None,
    )


@runtime_checkable
class DedupeStore(Protocol):
    """Remembers which webhook event ids were handled. ``claim`` must be atomic: it returns
    ``True`` only to the first caller for an id (until the claim expires or is released). Back it
    with a unique database row or a Redis ``SET NX PX`` to deduplicate across processes."""

    def claim(self, event_id: str, ttl_s: float) -> bool:
        """Claim ``event_id`` for ``ttl_s`` seconds; ``False`` if an unexpired claim exists."""

    def release(self, event_id: str) -> None:
        """Release a claim whose processing did not complete, so a redelivery is processed."""


class MemoryDedupeStore:
    """The default in-process :class:`DedupeStore`: thread-safe, claims expire after their TTL,
    and the oldest claims are forgotten beyond ``max_entries``. One process only.

    Args:
        max_entries: Most claims remembered (default 10,000; oldest forgotten first).
        clock: Current time in seconds (injectable for tests).
    """

    def __init__(
        self, *, max_entries: int = 10_000, clock: Callable[[], float] = time.monotonic
    ) -> None:
        self.max_entries = max(1, int(max_entries))
        """Most claims remembered."""
        self._clock = clock
        self._claims: OrderedDict[str, float] = OrderedDict()
        self._lock = threading.Lock()

    def claim(self, event_id: str, ttl_s: float) -> bool:
        """Claim ``event_id`` unless an unexpired claim exists."""
        now = self._clock()
        with self._lock:
            expires = self._claims.get(event_id)
            if expires is not None and expires > now:
                return False
            self._claims.pop(event_id, None)
            self._claims[event_id] = now + ttl_s
            while len(self._claims) > self.max_entries:
                self._claims.popitem(last=False)
            return True

    def release(self, event_id: str) -> None:
        """Forget a claim."""
        with self._lock:
            self._claims.pop(event_id, None)

    def __len__(self) -> int:
        with self._lock:
            return len(self._claims)


@dataclass(frozen=True)
class WebhookHandled:
    """What :meth:`WebhookOutcomeHandler.handle` did with one delivery, and what to answer."""

    status: Literal["reported", "duplicate", "rejected", "deferred"]
    """``reported`` (reported with ``source="webhook"``; an ``unknown`` verdict reports nothing),
    ``duplicate`` (already handled), ``rejected`` (refused before anything was reported) or
    ``deferred`` (the gateway did not acknowledge the report yet; the claim was released so a
    redelivery reports again, under the same identity)."""

    http_status: int
    """What to answer the sender: 200 (reported, duplicate), 400 or 401 (rejected), 503
    (deferred)."""

    outcome: WebhookOutcome | None = None
    """The outcome the webhook carried (``None`` when it was rejected before parsing)."""

    report: OutcomeReport | None = None
    """The report, when one was made."""

    reason: str | None = None
    """Why it was rejected or deferred."""


class WebhookOutcomeHandler:
    """Verify, deduplicate and report delayed outcomes from a signed webhook.

    Call :meth:`handle` (sync client) or :meth:`ahandle` (async client) from your webhook route
    with the raw body bytes and the headers, and answer the sender with ``result.http_status``.

    Args:
        verifier: The header, freshness and signature check.
        dedupe: Where handled event ids are claimed (default :class:`MemoryDedupeStore`).
        dedupe_ttl_s: How long a claim lasts (default 7 days).
        parse: Turns the verified payload into a :class:`WebhookOutcome`.
    """

    def __init__(
        self,
        verifier: WebhookVerifier,
        *,
        dedupe: DedupeStore | None = None,
        dedupe_ttl_s: float = DEFAULT_DEDUPE_TTL_S,
        parse: Callable[[Mapping[str, Any]], WebhookOutcome] = parse_webhook_outcome,
    ) -> None:
        self.verifier = verifier
        """The header, freshness and signature check."""
        self.dedupe: DedupeStore = dedupe if dedupe is not None else MemoryDedupeStore()
        """Where handled event ids are claimed."""
        self.dedupe_ttl_s = float(dedupe_ttl_s)
        """How long a claim lasts, in seconds."""
        self._parse = parse

    def _accept(
        self, raw_body: str | bytes, headers: Mapping[str, Any]
    ) -> tuple[WebhookOutcome, str | None] | WebhookHandled:
        """Verify, parse and claim; a :class:`WebhookHandled` when the delivery stops here."""
        try:
            payload, signed_at = self.verifier.verify_signed(raw_body, headers)
            outcome = self._parse(payload)
        except WebhookVerificationError as error:
            return WebhookHandled("rejected", error.http_status, reason=error.reason)
        except Exception:  # a custom parser that failed: the payload is not what it expects
            return WebhookHandled("rejected", 400, reason="malformed_payload")
        if not self.dedupe.claim(outcome.event_id, self.dedupe_ttl_s):
            return WebhookHandled("duplicate", 200, outcome)
        # Without a sender-given time, the signed timestamp: identical in every process that
        # handles this delivery, so racing handlers send byte-identical events.
        return outcome, outcome.observed_at or _iso_seconds(signed_at)

    def _settle(self, outcome: WebhookOutcome, report: OutcomeReport) -> WebhookHandled:
        if report.status == "queued":
            self.dedupe.release(outcome.event_id)
            error = getattr(report, "error", None)
            reason = getattr(error, "code", None) or "queued"
            return WebhookHandled("deferred", 503, outcome, report, reason)
        return WebhookHandled("reported", 200, outcome, report)

    def _failed(self, outcome: WebhookOutcome, error: Exception) -> WebhookHandled:
        self.dedupe.release(outcome.event_id)
        if isinstance(error, InvalidRequestError) and error.status == 0:
            return WebhookHandled("rejected", 400, outcome, reason="malformed_payload")
        return WebhookHandled("deferred", 503, outcome, reason=type(error).__name__)

    def handle(
        self, client: UltraRouter, raw_body: str | bytes, headers: Mapping[str, Any]
    ) -> WebhookHandled:
        """Verify one delivery and report it once through ``client.outcomes.report``."""
        accepted = self._accept(raw_body, headers)
        if isinstance(accepted, WebhookHandled):
            return accepted
        outcome, observed_at = accepted
        try:
            report: OutcomeReport = client.outcomes.report(
                outcome.request_id,
                outcome.verdict,
                source="webhook",
                idempotency_key=outcome.event_id,
                observed_at=observed_at,
                evidence_hash=outcome.evidence_hash,
            )
        except Exception as error:
            return self._failed(outcome, error)
        except BaseException:  # interrupted or cancelled: let a redelivery try again
            self.dedupe.release(outcome.event_id)
            raise
        return self._settle(outcome, report)

    async def ahandle(
        self, client: AsyncUltraRouter, raw_body: str | bytes, headers: Mapping[str, Any]
    ) -> WebhookHandled:
        """Async twin of :meth:`handle` for :class:`~ultrarouter.AsyncUltraRouter`."""
        accepted = self._accept(raw_body, headers)
        if isinstance(accepted, WebhookHandled):
            return accepted
        outcome, observed_at = accepted
        try:
            report: OutcomeReport = await client.outcomes.report(
                outcome.request_id,
                outcome.verdict,
                source="webhook",
                idempotency_key=outcome.event_id,
                observed_at=observed_at,
                evidence_hash=outcome.evidence_hash,
            )
        except Exception as error:
            return self._failed(outcome, error)
        except BaseException:  # interrupted or cancelled: let a redelivery try again
            self.dedupe.release(outcome.event_id)
            raise
        return self._settle(outcome, report)


def _iso_seconds(unix_s: int) -> str:
    """The signed timestamp as ``YYYY-MM-DDTHH:MM:SS.000Z``."""
    return time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime(unix_s))
