"""Typed errors raised by the ultrarouter SDK.

Every failure the gateway returns is a JSON envelope of the form
``{"error": {"code", "message", "request_id", "retryable", "provider_code"}}``. The SDK turns
that envelope into an :class:`UltraRouterError` subclass chosen by the stable ``code`` string
(see :data:`GATEWAY_ERROR_TAXONOMY`). Transport failures that never produced a response become
:class:`APIConnectionError` / :class:`APITimeoutError`.

Catch the base class to handle everything, or a specific subclass to branch::

    from ultrarouter import ModelUnpricedError, RateLimitError, UltraRouter, UltraRouterError

    client = UltraRouter()
    try:
        client.chat.completions.create(
            model="acme/unpriced-model", messages=[{"role": "user", "content": "Hi"}]
        )
    except ModelUnpricedError as exc:
        print("pick a priced model; retrying cannot help:", exc.message)
    except RateLimitError:
        print("already retried with backoff; back off further")
    except UltraRouterError as exc:
        print(exc.code, exc.status, exc.request_id)
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any, NamedTuple

__all__ = [
    "GATEWAY_ERROR_CODES",
    "GATEWAY_ERROR_TAXONOMY",
    "LEARNING_ERROR_ACTIONS",
    "LEARNING_ERROR_CODES",
    "LEARNING_ERROR_REASONS",
    "APIConnectionError",
    "APIResponseValidationError",
    "APIStatusError",
    "APITimeoutError",
    "AuthenticationError",
    "CapabilityUnsupportedError",
    "ConfigurationError",
    "ConflictError",
    "ContentFilteredError",
    "ContextLengthError",
    "ErrorTaxonomyEntry",
    "InternalServerError",
    "InvalidRequestError",
    "LearningBudgetExhaustedError",
    "LearningConsentRequiredError",
    "LearningError",
    "LearningForbiddenError",
    "LearningNotEnabledError",
    "LearningNotFoundError",
    "LearningPolicyInvalidError",
    "LearningProviderUnavailableError",
    "LearningQuotaExhaustedError",
    "LearningVersionConflictError",
    "ManifestInvalidError",
    "ManifestMismatchError",
    "MaxCostExceededError",
    "ModelDeniedByPolicyError",
    "ModelUnpricedError",
    "NotFoundError",
    "OutcomeBacklogFullError",
    "OutcomeStoreError",
    "PermissionDeniedError",
    "PromptVariablesMissingError",
    "ProviderTimeoutError",
    "ProviderUnavailableError",
    "RateLimitError",
    "ReceiptWaitTimeoutError",
    "RequestCancelledError",
    "SpendCapExceededError",
    "SpendGuardUnavailableError",
    "UltraRouterError",
    "error_class_for",
    "error_from_response",
    "is_gateway_error_code",
    "is_retryable_status",
    "learning_error",
    "parse_gateway_error_envelope",
    "parse_learning_refusal",
]


class ErrorTaxonomyEntry(NamedTuple):
    """The canonical HTTP status of a gateway error code and whether it is safe to retry."""

    status: int
    retryable: bool


#: The stable gateway error codes, their canonical HTTP status, and whether a client may
#: safely retry the identical request. The gateway's own ``retryable`` flag on a response can
#: mark a retryable code non-retryable, but a code listed here as non-retryable stays
#: non-retryable even if a response says ``retryable: true``.
GATEWAY_ERROR_TAXONOMY: Mapping[str, ErrorTaxonomyEntry] = {
    "invalid_request": ErrorTaxonomyEntry(400, False),
    "manifest_invalid": ErrorTaxonomyEntry(400, False),
    "manifest_mismatch": ErrorTaxonomyEntry(400, False),
    "authentication": ErrorTaxonomyEntry(401, False),
    "permission": ErrorTaxonomyEntry(403, False),
    "not_found": ErrorTaxonomyEntry(404, False),
    "model_denied_by_policy": ErrorTaxonomyEntry(403, False),
    "model_unpriced": ErrorTaxonomyEntry(403, False),
    "capability_unsupported": ErrorTaxonomyEntry(400, False),
    "prompt_variables_missing": ErrorTaxonomyEntry(400, False),
    "conflict": ErrorTaxonomyEntry(409, False),
    "rate_limited": ErrorTaxonomyEntry(429, True),
    "outcome_backlog_full": ErrorTaxonomyEntry(429, True),
    "spend_cap_exceeded": ErrorTaxonomyEntry(402, False),
    "max_cost_exceeded": ErrorTaxonomyEntry(402, False),
    "atomic_spend_guard_unavailable": ErrorTaxonomyEntry(503, False),
    "provider_unavailable": ErrorTaxonomyEntry(502, True),
    "provider_timeout": ErrorTaxonomyEntry(504, True),
    "content_filtered": ErrorTaxonomyEntry(400, False),
    "context_length": ErrorTaxonomyEntry(400, False),
    "cancelled": ErrorTaxonomyEntry(499, False),
    "internal": ErrorTaxonomyEntry(500, False),
}

#: The closed set of error ``code`` strings the gateway returns (the keys of
#: :data:`GATEWAY_ERROR_TAXONOMY`, in a stable order).
GATEWAY_ERROR_CODES: tuple[str, ...] = tuple(GATEWAY_ERROR_TAXONOMY)


def is_gateway_error_code(value: str) -> bool:
    """Return ``True`` when ``value`` is one of :data:`GATEWAY_ERROR_CODES`.

    Transport codes produced by the SDK itself (``connection``, ``timeout``) and unknown
    codes are not members.
    """
    return value in GATEWAY_ERROR_TAXONOMY


def is_retryable_status(status: int) -> bool:
    """Return ``True`` for HTTP statuses the SDK may retry: 408, 429 and 5xx."""
    return status in (408, 429) or 500 <= status <= 599


def parse_gateway_error_envelope(body: Any) -> dict[str, Any] | None:
    """Validate a decoded response body as the gateway's error envelope; ``None`` otherwise.

    Returns the inner object only when ``body`` is ``{"error": {...}}`` with a non-empty string
    ``code``, a string ``message`` and ``request_id``, a boolean ``retryable`` and, when present, a
    string ``provider_code``. Anything else (an HTML page from a proxy, an empty body, another
    JSON shape, a field of the wrong type) is not an envelope.
    """
    if not isinstance(body, Mapping):
        return None
    error = body.get("error")
    if not isinstance(error, Mapping):
        return None
    code, message = error.get("code"), error.get("message")
    request_id, retryable = error.get("request_id"), error.get("retryable")
    if not isinstance(code, str) or not code or not isinstance(message, str):
        return None
    if not isinstance(request_id, str) or not isinstance(retryable, bool):
        return None
    if "provider_code" in error and not isinstance(error["provider_code"], str):
        return None
    envelope: dict[str, Any] = {
        "code": code,
        "message": message,
        "request_id": request_id,
        "retryable": retryable,
    }
    if "provider_code" in error:
        envelope["provider_code"] = error["provider_code"]
    return envelope


class UltraRouterError(Exception):
    """Base class of every error the SDK raises.

    Attributes:
        code: The stable error code (a gateway code such as ``"rate_limited"``, or
            ``"connection"`` / ``"timeout"`` for transport failures).
        message: Human-readable, secret-free explanation.
        status: HTTP status, or ``0`` when no response was received.
        request_id: The gateway correlation id (``req_...``) when one was returned.
        retryable: Whether the identical request may safely be retried.
        provider_code: The raw upstream provider error code, when a provider failed.
        body: The decoded error response body, when there was one.
        envelope: The validated gateway error envelope (see
            :func:`parse_gateway_error_envelope`) when, and only when, the response body was a
            complete ``{"error": {"code", "message", "request_id", "retryable"}}`` object.
    """

    #: The code this class represents (``None`` for the generic classes).
    default_code: str | None = None

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        status: int = 0,
        request_id: str | None = None,
        retryable: bool = False,
        provider_code: str | None = None,
        body: Any = None,
        envelope: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        resolved = code if code is not None else self.default_code
        self.code: str = resolved if resolved is not None else "error"
        self.message: str = message
        self.status: int = status
        self.request_id: str | None = request_id
        self.retryable: bool = retryable
        self.provider_code: str | None = provider_code
        self.body: Any = body
        self.envelope: Mapping[str, Any] | None = envelope

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(code={self.code!r}, status={self.status}, "
            f"request_id={self.request_id!r}, retryable={self.retryable}, "
            f"message={self.message!r})"
        )


class APIConnectionError(UltraRouterError):
    """The request never produced a response (DNS, refused connection, reset, ...).

    Retried automatically (``retryable`` is ``True``) up to ``max_retries`` times.
    """

    default_code = "connection"


class APITimeoutError(APIConnectionError):
    """The request exceeded its total ``timeout`` budget. Never retried automatically."""

    default_code = "timeout"


class APIResponseValidationError(UltraRouterError):
    """The gateway answered 2xx but the body did not match the documented shape."""

    default_code = "invalid_response"


class OutcomeStoreError(UltraRouterError):
    """A durable queue store could not be read or written (for example a damaged queue file).

    Raised instead of treating the store as empty: the original file is left untouched so the
    queued events can be recovered. Never retried automatically.
    """

    default_code = "outcome_store"


class ConfigurationError(UltraRouterError):
    """The client cannot be constructed because required configuration is missing.

    Raised before any network call (``status == 0``) when neither the constructor argument nor
    any environment variable supplies a value: ``code="missing_api_key"`` when the API key is
    absent, ``code="missing_base_url"`` when the gateway base URL is absent. There is no default
    gateway, so a base URL must come from ``base_url=``, ``ULTRAROUTER_BASE_URL`` or
    ``UR_BASE_URL``. It derives from :class:`UltraRouterError`, so ``except UltraRouterError``
    catches it too.
    """

    default_code = "configuration"


class APIStatusError(UltraRouterError):
    """The gateway answered with a non-2xx status. Base class of all code-specific errors."""


class InvalidRequestError(APIStatusError):
    """``invalid_request`` (400): malformed body, parameters, or an unsupported option."""

    default_code = "invalid_request"


class ManifestInvalidError(APIStatusError):
    """``manifest_invalid`` (400): a declared ``ur.manifest`` is structurally invalid."""

    default_code = "manifest_invalid"


class ManifestMismatchError(APIStatusError):
    """``manifest_mismatch`` (400): a declared manifest hash does not match the bytes sent."""

    default_code = "manifest_mismatch"


class AuthenticationError(APIStatusError):
    """``authentication`` (401): the API key is missing, malformed, revoked or unknown."""

    default_code = "authentication"


class PermissionDeniedError(APIStatusError):
    """``permission`` (403): the key is valid but lacks the scope this endpoint needs."""

    default_code = "permission"


class NotFoundError(APIStatusError):
    """``not_found`` (404): unknown model, request, call type or other resource."""

    default_code = "not_found"


class ModelDeniedByPolicyError(APIStatusError):
    """``model_denied_by_policy`` (403): the workspace model policy forbids this model.

    Not retryable as-is: choose another model or change the workspace model policy.
    """

    default_code = "model_denied_by_policy"


class ModelUnpricedError(APIStatusError):
    """``model_unpriced`` (403): the requested model has no usable price.

    The gateway refuses a call it cannot cost before anything reaches a provider, so
    nothing is billed. Never retried by the SDK: use a priced model, or declare pricing
    for the custom provider that serves it.
    """

    default_code = "model_unpriced"


class CapabilityUnsupportedError(APIStatusError):
    """``capability_unsupported`` (400): the model cannot honour a requested capability.

    For example a ``json_schema`` response format, tools, vision or embeddings on a model
    that does not support them. The message names the capability.
    """

    default_code = "capability_unsupported"


class PromptVariablesMissingError(APIStatusError):
    """``prompt_variables_missing`` (400): a required hosted-prompt variable was not supplied.

    Raised by the gateway when it applies a hosted prompt, and raised client-side (with
    ``status == 0``) by :func:`ultrarouter.render_prompt`. ``missing`` lists the variable
    names when they are known.
    """

    default_code = "prompt_variables_missing"

    def __init__(
        self,
        message: str | None = None,
        *,
        missing: Sequence[str] = (),
        code: str | None = None,
        status: int = 0,
        request_id: str | None = None,
        retryable: bool = False,
        provider_code: str | None = None,
        body: Any = None,
        envelope: Mapping[str, Any] | None = None,
    ) -> None:
        names = list(missing)
        if message is None:
            message = "prompt_variables_missing: required variable(s) not supplied: " + ", ".join(
                names
            )
        super().__init__(
            message,
            code=code,
            status=status,
            request_id=request_id,
            retryable=retryable,
            provider_code=provider_code,
            body=body,
            envelope=envelope,
        )
        self.missing: list[str] = names


class ConflictError(APIStatusError):
    """``conflict`` (409): an idempotent write collided with a different payload."""

    default_code = "conflict"


class RateLimitError(APIStatusError):
    """``rate_limited`` (429): a per-key or per-workspace rate limit was hit (retried)."""

    default_code = "rate_limited"


class SpendCapExceededError(APIStatusError):
    """``spend_cap_exceeded`` (402): the hard spend cap for the period was reached."""

    default_code = "spend_cap_exceeded"


class MaxCostExceededError(APIStatusError):
    """``max_cost_exceeded`` (402): the estimated call cost exceeds ``ur.max_cost_usd``."""

    default_code = "max_cost_exceeded"


class SpendGuardUnavailableError(APIStatusError):
    """``atomic_spend_guard_unavailable`` (503): live paid execution is not available.

    A deployment capability gap, not a transient fault: never retried by the SDK.
    """

    default_code = "atomic_spend_guard_unavailable"


class ProviderUnavailableError(APIStatusError):
    """``provider_unavailable`` (502): the upstream provider failed or was unreachable."""

    default_code = "provider_unavailable"


class ProviderTimeoutError(APIStatusError):
    """``provider_timeout`` (504): the upstream provider exceeded its deadline."""

    default_code = "provider_timeout"


class ContentFilteredError(APIStatusError):
    """``content_filtered`` (400): the provider refused the content (moderation/safety)."""

    default_code = "content_filtered"


class ContextLengthError(APIStatusError):
    """``context_length`` (400): prompt plus requested completion exceed the context window."""

    default_code = "context_length"


class RequestCancelledError(APIStatusError):
    """``cancelled`` (499): the request was aborted before completion."""

    default_code = "cancelled"


class InternalServerError(APIStatusError):
    """``internal`` (500): an unexpected gateway failure."""

    default_code = "internal"


class OutcomeBacklogFullError(RateLimitError):
    """``outcome_backlog_full`` (429): the workspace already holds the maximum number of pending
    outcome receipts (5,000), outcomes reported for requests not recorded yet.

    Nothing was stored. The SDK retries after the ``Retry-After`` hint within the call's time
    budget, and an outcome reported through ``client.outcomes`` stays durably queued for
    ``flush()``.
    """

    default_code = "outcome_backlog_full"


class ReceiptWaitTimeoutError(APITimeoutError):
    """``outcomes.wait_for_receipt`` ran out of time before the receipt reached a final status.

    ``receipt_id`` is the receipt waited on; ``last_receipt`` the last one read (still
    ``pending``), or ``None`` when no read succeeded. The outcome is not lost: the receipt is
    durable and keeps reconciling on the gateway; read it again later with
    ``outcomes.receipt(receipt_id)``.
    """

    def __init__(
        self,
        message: str,
        *,
        receipt_id: str,
        last_receipt: Any = None,
        request_id: str | None = None,
    ) -> None:
        super().__init__(message, request_id=request_id)
        self.receipt_id: str = receipt_id
        self.last_receipt: Any = last_receipt


#: Why a learning control was refused, in terms you can act on (the TypeScript SDK's vocabulary).
LEARNING_ERROR_REASONS: tuple[str, ...] = (
    "missing_consent",
    "provider_unavailable",
    "not_enabled",
    "invalid_promotion",
    "version_conflict",
    "quota_exhausted",
    "budget_exhausted",
    "not_found",
    "forbidden",
)

#: The refusals each reason is recognised from: a named refusal (the first token of the gateway's
#: message, as in ``"corrections_consent_required: ..."`` or
#: ``"reflection_model_not_workspace_owned (no_workspace_key): ..."``), else the error code.
LEARNING_ERROR_CODES: Mapping[str, tuple[str, ...]] = {
    "missing_consent": ("corrections_consent_required",),
    "provider_unavailable": ("reflection_model_not_workspace_owned",),
    "not_enabled": ("learning_not_enabled",),
    "invalid_promotion": ("promotion_invalid",),
    "version_conflict": (
        "version_already_active",
        "version_active",
        "no_rollback_target",
        "rollback_target_not_earlier",
    ),
    "quota_exhausted": ("quota_exhausted",),
    "budget_exhausted": ("budget_exhausted", "spend_cap_exceeded"),
    "not_found": ("not_found",),
    "forbidden": ("permission",),
}

#: What to do about each reason.
LEARNING_ERROR_ACTIONS: Mapping[str, str] = {
    "missing_consent": (
        "A workspace owner or admin must turn on the workspace's corrections consent before "
        "learning can be enabled."
    ),
    "provider_unavailable": (
        "Give the reflection model a workspace-owned offer (one of your custom providers, or a "
        "provider your workspace stored its own key for); learning never falls back to a platform "
        "provider. `detail` names what is missing."
    ),
    "not_enabled": "Enable learning for this call type first (client.learning.enable).",
    "invalid_promotion": (
        "Fix the promotion policy: `detail` names the field or combination that is out of range."
    ),
    "version_conflict": (
        "Read the version history (client.learning.versions): a rollback needs an earlier, "
        "non-active version (or a previous active one), and promote / reject act on a candidate "
        "that is not already active."
    ),
    "quota_exhausted": (
        "The learning provider refused for quota. Learning retries with backoff on its own; "
        "resume it once the quota is raised."
    ),
    "budget_exhausted": (
        "The learning budget is spent. Raise the budget or wait for the next period, then "
        "resume learning."
    ),
    "not_found": "Check the call type id (or slug) and the version id.",
    "forbidden": (
        "Use a key with the config:write scope (config:read for reads) or an owner/admin session."
    ),
}


class LearningError(APIStatusError):
    """A learning control refused for a reason you can act on.

    ``reason`` names it (see :data:`LEARNING_ERROR_REASONS`), ``refusal`` is the gateway's named
    refusal (the first token of its message, for example ``corrections_consent_required``) or, when
    there is none, the error code; ``detail`` is the sub-reason in parentheses when there is one
    (for example ``no_offer`` in ``reflection_model_not_workspace_owned (no_offer)``), and
    ``action`` says what to do; the message ends with the action too. ``code``, ``status``,
    ``request_id`` and ``retryable`` are the gateway's. Catch a subclass to branch on one reason.
    """

    #: The reason this class represents.
    learning_reason: str = ""

    def __init__(
        self,
        message: str,
        *,
        refusal: str = "",
        detail: str | None = None,
        **fields: Any,
    ) -> None:
        super().__init__(message, **fields)
        self.reason: str = self.learning_reason
        self.refusal: str = refusal or self.code
        self.detail: str | None = detail
        self.action: str = LEARNING_ERROR_ACTIONS.get(self.learning_reason, "")


class LearningConsentRequiredError(LearningError):
    """``missing_consent``: learning needs the workspace's corrections consent, which is off."""

    learning_reason = "missing_consent"


class LearningProviderUnavailableError(LearningError):
    """``provider_unavailable``: the reflection model has no usable workspace-owned provider.

    Learning runs only on a provider offer the workspace configured; there is no platform or paid
    fallback. ``detail`` names why: ``no_offer``, ``platform_offer_only``, ``no_workspace_key``,
    ``model_denied_by_policy``, ``workspace_funding_not_byok`` or ``workspace_funding_frozen``.
    """

    learning_reason = "provider_unavailable"


class LearningQuotaExhaustedError(LearningError):
    """``quota_exhausted``: the learning provider refused for quota."""

    learning_reason = "quota_exhausted"


class LearningBudgetExhaustedError(LearningError):
    """``budget_exhausted``: the call type's learning budget is spent."""

    learning_reason = "budget_exhausted"


class LearningNotFoundError(LearningError, NotFoundError):
    """``not_found``: the call type, version or evaluation does not exist in this workspace."""

    learning_reason = "not_found"


class LearningForbiddenError(LearningError, PermissionDeniedError):
    """``forbidden``: the key or user may not do this (reads need ``config:read``, controls
    ``config:write``, manual promote/reject an owner or admin)."""

    learning_reason = "forbidden"


class LearningNotEnabledError(LearningError, ConflictError):
    """``not_enabled`` (409 ``learning_not_enabled``): the control needs learning enabled through
    the learning API first."""

    learning_reason = "not_enabled"


class LearningVersionConflictError(LearningError, ConflictError):
    """``version_conflict`` (409 ``version_already_active`` / ``version_active`` /
    ``no_rollback_target`` / ``rollback_target_not_earlier``): promoting the active version,
    rejecting it (roll back instead), or rolling back with no earlier version to go to."""

    learning_reason = "version_conflict"


class LearningPolicyInvalidError(LearningError, InvalidRequestError):
    """``invalid_promotion`` (400 ``promotion_invalid (<reason>)``): the promotion policy is not
    valid; ``detail`` names the field."""

    learning_reason = "invalid_promotion"


_LEARNING_CLASSES: dict[str, type[LearningError]] = {
    cls.learning_reason: cls
    for cls in (
        LearningConsentRequiredError,
        LearningProviderUnavailableError,
        LearningQuotaExhaustedError,
        LearningBudgetExhaustedError,
        LearningNotFoundError,
        LearningForbiddenError,
        LearningNotEnabledError,
        LearningVersionConflictError,
        LearningPolicyInvalidError,
    )
}


_CODE_CLASSES: dict[str, type[APIStatusError]] = {
    cls.default_code: cls
    for cls in (
        InvalidRequestError,
        ManifestInvalidError,
        ManifestMismatchError,
        AuthenticationError,
        PermissionDeniedError,
        NotFoundError,
        ModelDeniedByPolicyError,
        ModelUnpricedError,
        CapabilityUnsupportedError,
        PromptVariablesMissingError,
        ConflictError,
        RateLimitError,
        SpendCapExceededError,
        MaxCostExceededError,
        SpendGuardUnavailableError,
        ProviderUnavailableError,
        ProviderTimeoutError,
        ContentFilteredError,
        ContextLengthError,
        RequestCancelledError,
        InternalServerError,
        OutcomeBacklogFullError,
    )
    if cls.default_code is not None
}

_STATUS_CLASSES: dict[int, type[APIStatusError]] = {
    400: InvalidRequestError,
    401: AuthenticationError,
    403: PermissionDeniedError,
    404: NotFoundError,
    409: ConflictError,
    429: RateLimitError,
}


def error_class_for(code: str, status: int) -> type[APIStatusError]:
    """Pick the exception class for a gateway error.

    The stable ``code`` decides first; an unknown code falls back to the HTTP status
    class (400, 401, 403, 404, 409, 429, 5xx), then to :class:`APIStatusError`.
    """
    by_code = _CODE_CLASSES.get(code)
    if by_code is not None:
        return by_code
    by_status = _STATUS_CLASSES.get(status)
    if by_status is not None:
        return by_status
    if 500 <= status <= 599:
        return InternalServerError
    return APIStatusError


def error_from_response(status: int, body: Any) -> APIStatusError:
    """Build the typed error for a non-2xx response (or an SSE ``error`` frame).

    ``status`` is the HTTP status (``0`` for an error frame inside a stream, in which case
    the code's canonical status is used). ``retryable`` follows the gateway's own flag when
    present, otherwise the taxonomy default, otherwise the status class; a code the taxonomy
    marks non-retryable is never made retryable by the flag.
    """
    err: Mapping[str, Any] = {}
    if isinstance(body, Mapping):
        candidate = body.get("error")
        if isinstance(candidate, Mapping):
            err = candidate
    raw_code = err.get("code")
    code = raw_code if isinstance(raw_code, str) and raw_code else f"http_{status}"
    entry = GATEWAY_ERROR_TAXONOMY.get(code)
    if status == 0 and entry is not None:
        status = entry.status
    raw_retryable = err.get("retryable")
    if entry is not None and not entry.retryable:
        # A categorically non-retryable code stays non-retryable whatever the envelope says.
        retryable = False
    elif isinstance(raw_retryable, bool):
        retryable = raw_retryable
    elif entry is not None:
        retryable = entry.retryable
    else:
        retryable = is_retryable_status(status)
    raw_message = err.get("message")
    message = (
        raw_message
        if isinstance(raw_message, str) and raw_message
        else f"request failed with status {status}"
    )
    request_id = err.get("request_id")
    provider_code = err.get("provider_code")
    cls = error_class_for(code, status)
    return cls(
        message,
        code=code,
        status=status,
        request_id=request_id if isinstance(request_id, str) else None,
        retryable=retryable,
        provider_code=provider_code if isinstance(provider_code, str) else None,
        body=body,
        envelope=parse_gateway_error_envelope(body),
    )


def _learning_reason_for(token: str) -> str | None:
    for reason, codes in LEARNING_ERROR_CODES.items():
        if token in codes:
            return reason
    return None


_REFUSAL = re.compile(r"([a-z][a-z0-9]*(?:_[a-z0-9]+)+)(?:\s*\(([a-z0-9_]+)\))?(?=\s*(?::|$))")


def parse_learning_refusal(message: str) -> tuple[str, str | None] | None:
    """The named refusal a gateway message starts with, and its parenthesized sub-reason.

    A ``snake_case`` token (at least one underscore), optionally followed by ``(detail)``, then
    ``:`` or the end of the message; ``None`` for anything else. The TypeScript SDK's
    ``parseLearningRefusal``.
    """
    match = _REFUSAL.match(message)
    if match is None:
        return None
    return match.group(1), match.group(2)


def learning_error(error: UltraRouterError) -> UltraRouterError:
    """Turn a gateway refusal of a learning control into the matching :class:`LearningError`.

    The named refusal at the start of the message decides first, then the error code
    (:data:`LEARNING_ERROR_CODES`). Anything else (a transport failure, an unrecognised refusal) is
    returned unchanged. The same rule as the TypeScript SDK's ``toLearningError``.
    """
    if not isinstance(error, APIStatusError) or isinstance(error, LearningError):
        return error
    if not error.status:  # no answer: a transport failure is not a refusal
        return error
    named = parse_learning_refusal(error.message)
    reason = _learning_reason_for(named[0]) if named is not None else None
    if reason is not None and named is not None:
        refusal, detail = named
    else:
        reason, refusal, detail = _learning_reason_for(error.code), error.code, None
    if reason is None:
        return error
    cls = _LEARNING_CLASSES[reason]
    return cls(
        f"{error.message} ({LEARNING_ERROR_ACTIONS[reason]})",
        refusal=refusal,
        detail=detail,
        code=error.code,
        status=error.status,
        request_id=error.request_id,
        retryable=error.retryable,
        provider_code=error.provider_code,
        body=error.body,
        envelope=error.envelope,
    )
