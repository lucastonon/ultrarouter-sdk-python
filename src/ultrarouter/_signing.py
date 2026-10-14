"""HMAC request signing (pure helpers).

Some endpoints require the request body to be signed so a captured request cannot be replayed
elsewhere. The recipe is the same everywhere; only the header names differ: the signature is
``"sha256="`` followed by the hex HMAC-SHA256, keyed by the secret, of ``"<timestamp>.<raw_body>"``,
where ``timestamp`` is the current Unix time in seconds (sent in its own header and bound into the
MAC) and ``raw_body`` is the exact request body bytes. The SDK serializes the body once, signs
those bytes and sends the same bytes, so the signature always describes what was sent.

For the reviewer endpoint the secret is your API key.
"""

from __future__ import annotations

import hashlib
import hmac
import time

__all__ = [
    "REVIEWER_SIGNATURE_HEADER",
    "REVIEWER_TIMESTAMP_HEADER",
    "reviewer_signature_headers",
    "reviewer_signed_payload",
    "sign_payload",
    "signature_headers",
]

#: Header carrying the reviewer signature (``sha256=<hex>``).
REVIEWER_SIGNATURE_HEADER = "x-ur-reviewer-signature"
#: Header carrying the reviewer signature timestamp (Unix seconds).
REVIEWER_TIMESTAMP_HEADER = "x-ur-reviewer-timestamp"


def _as_bytes(raw_body: str | bytes) -> bytes:
    return raw_body.encode("utf-8") if isinstance(raw_body, str) else raw_body


def reviewer_signed_payload(timestamp: str, raw_body: str | bytes) -> bytes:
    """The exact bytes that are signed: ``b"<timestamp>.<raw body>"``."""
    return timestamp.encode("ascii") + b"." + _as_bytes(raw_body)


def sign_payload(secret: str, timestamp: str, raw_body: str | bytes) -> str:
    """Return ``"sha256=<hex>"``: HMAC-SHA256 of ``"<timestamp>.<raw_body>"``.

    The HMAC key is ``secret`` (your API key for reviewer events and candidate decisions, the
    oracle secret for pull oracles).
    """
    mac = hmac.new(
        secret.encode("utf-8"), reviewer_signed_payload(timestamp, raw_body), hashlib.sha256
    )
    return "sha256=" + mac.hexdigest()


def signature_headers(
    signature_header: str,
    timestamp_header: str,
    secret: str,
    raw_body: str | bytes,
    now_s: float | None = None,
) -> dict[str, str]:
    """Build the signature + timestamp headers for an already-serialized body."""
    timestamp = str(int(now_s if now_s is not None else time.time()))
    return {
        timestamp_header: timestamp,
        signature_header: sign_payload(secret, timestamp, raw_body),
    }


def reviewer_signature_headers(
    secret: str, raw_body: str | bytes, now_s: float | None = None
) -> dict[str, str]:
    """The ``X-UR-Reviewer-Signature`` / ``X-UR-Reviewer-Timestamp`` headers for ``raw_body``."""
    return signature_headers(
        REVIEWER_SIGNATURE_HEADER, REVIEWER_TIMESTAMP_HEADER, secret, raw_body, now_s
    )
