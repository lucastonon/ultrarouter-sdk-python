"""Starter outcome adapters: turn the checks you already have into trustworthy verdicts.

* :func:`run_verifier`, :func:`verdict_from_command` and :func:`run_test_suite`: a computable
  check, a command's exit code or a test suite becomes a ``verifier`` verdict;
* :func:`validate_output`: structured output validated by a pydantic model plus named business
  rules becomes a ``business_rule`` verdict with reasons (always ``pass`` or ``fail``);
* :class:`WebhookVerifier` and :class:`WebhookOutcomeHandler`: a signed, delayed webhook from a
  business system is verified (HMAC-SHA256, timestamp tolerance, constant-time comparison),
  deduplicated by event id and reported once with ``source="webhook"``.

A verdict is ``pass``, ``fail`` or ``unknown``; ``unknown`` (the check could not decide) reports
nothing. :func:`evidence_hash` is ``"sha256:"`` plus the hex SHA-256 of the canonical JSON of the
evidence. Semantics, reasons, hashes and the webhook scheme match the TypeScript SDK's
``@ultrarouter/sdk/learning`` entry.

Report a result with ``client.outcomes.report(request_id, result.verdict, source=result.source,
evidence_hash=result.evidence_hash)``. Reasons and outputs stay local: only the verdict, its
source and an optional evidence hash are sent.

Pure apart from :func:`run_test_suite` (a subprocess) and the handler's report call.
"""

from ._rules import Rule, ValidationResult, validate_output
from ._verifier import (
    VerifierResult,
    evidence_hash,
    run_test_suite,
    run_verifier,
    verdict_from_command,
)
from ._webhook import (
    DEFAULT_DEDUPE_TTL_S,
    DEFAULT_WEBHOOK_SECRET_ENV,
    DEFAULT_WEBHOOK_TOLERANCE_S,
    WEBHOOK_SIGNATURE_HEADER,
    WEBHOOK_TIMESTAMP_HEADER,
    DedupeStore,
    MemoryDedupeStore,
    WebhookHandled,
    WebhookOutcome,
    WebhookOutcomeHandler,
    WebhookPayloadError,
    WebhookRejectReason,
    WebhookSignatureError,
    WebhookTimestampError,
    WebhookVerificationError,
    WebhookVerifier,
    parse_webhook_outcome,
    sign_webhook,
)

__all__ = [
    "DEFAULT_DEDUPE_TTL_S",
    "DEFAULT_WEBHOOK_SECRET_ENV",
    "DEFAULT_WEBHOOK_TOLERANCE_S",
    "WEBHOOK_SIGNATURE_HEADER",
    "WEBHOOK_TIMESTAMP_HEADER",
    "DedupeStore",
    "MemoryDedupeStore",
    "Rule",
    "ValidationResult",
    "VerifierResult",
    "WebhookHandled",
    "WebhookOutcome",
    "WebhookOutcomeHandler",
    "WebhookPayloadError",
    "WebhookRejectReason",
    "WebhookSignatureError",
    "WebhookTimestampError",
    "WebhookVerificationError",
    "WebhookVerifier",
    "evidence_hash",
    "parse_webhook_outcome",
    "run_test_suite",
    "run_verifier",
    "sign_webhook",
    "validate_output",
    "verdict_from_command",
]
