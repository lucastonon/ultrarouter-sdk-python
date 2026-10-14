# Errors

Every exception the SDK raises derives from `UltraRouterError`, which carries:

| Attribute | Meaning |
| --- | --- |
| `code` | stable error code from the gateway (for example `rate_limited`), or `connection` / `timeout` for transport failures |
| `status` | HTTP status, or `0` when no response was received (or for client-side checks) |
| `message` | human-readable explanation (never contains secrets) |
| `request_id` | the gateway's `req_...` correlation id, when there was a response |
| `retryable` | whether repeating the identical request may succeed |
| `provider_code` | the upstream provider's error code, when a provider failed |
| `body` | the decoded error body |

```python
from ultrarouter import UltraRouter, UltraRouterError

client = UltraRouter()
try:
    client.chat.completions.create(
        model="acme/missing-model", messages=[{"role": "user", "content": "Hi"}]
    )
except UltraRouterError as exc:
    print(type(exc).__name__, exc.code, exc.status, exc.retryable, exc.request_id)
```

Include `request_id` when you contact support.

## Error classes

Each gateway code maps to its own class; `error_class_for(code, status)` returns it. An unknown
code falls back to the class for its HTTP status (400, 401, 403, 404, 409, 429, 5xx), then to
`APIStatusError`.

| Class | Code | HTTP | Retried by the SDK | What to do |
| --- | --- | --- | --- | --- |
| `InvalidRequestError` | `invalid_request` | 400 | no | fix the request (the message names the field) |
| `ManifestInvalidError` | `manifest_invalid` | 400 | no | fix the declared `ur.manifest` |
| `ManifestMismatchError` | `manifest_mismatch` | 400 | no | recompute the manifest over the exact bytes you send |
| `CapabilityUnsupportedError` | `capability_unsupported` | 400 | no | use a model that supports the capability (tools, JSON schema, vision, embeddings) |
| `PromptVariablesMissingError` | `prompt_variables_missing` | 400 | no | supply the named variables in `ur.prompt_vars` |
| `ContentFilteredError` | `content_filtered` | 400 | no | the provider refused the content |
| `ContextLengthError` | `context_length` | 400 | no | shorten the prompt or `max_tokens` |
| `AuthenticationError` | `authentication` | 401 | no | check the API key |
| `PermissionDeniedError` | `permission` | 403 | no | the key lacks the scope this endpoint needs |
| `ModelDeniedByPolicyError` | `model_denied_by_policy` | 403 | no | the workspace model policy forbids this model |
| `ModelUnpricedError` | `model_unpriced` | 403 | **never** | the model has no price; use a priced model (nothing was called or billed) |
| `NotFoundError` | `not_found` | 404 | no | unknown model, request, call type or resource |
| `ConflictError` | `conflict` | 409 | no | an idempotent write collided with different content |
| `SpendCapExceededError` | `spend_cap_exceeded` | 402 | no | the period's hard spend cap is reached |
| `MaxCostExceededError` | `max_cost_exceeded` | 402 | no | the estimated cost exceeds `ur.max_cost_usd` |
| `RateLimitError` | `rate_limited` | 429 | yes | slow down; the SDK already backed off |
| `RequestCancelledError` | `cancelled` | 499 | no | the request was aborted |
| `InternalServerError` | `internal` | 500 | per the gateway's `retryable` flag | retry later; report the `request_id` |
| `ProviderUnavailableError` | `provider_unavailable` | 502 | yes | transient upstream failure; consider `models=[...]` fallbacks |
| `SpendGuardUnavailableError` | `atomic_spend_guard_unavailable` | 503 | **never** | paid execution is unavailable on this deployment; a retry cannot help |
| `ProviderTimeoutError` | `provider_timeout` | 504 | yes | the provider exceeded its deadline |
| `APIConnectionError` | `connection` | 0 | yes | network problem reaching the gateway |
| `APITimeoutError` | `timeout` | 0 | no | the call exceeded its total `timeout` |
| `APIResponseValidationError` | `invalid_response` | any | no | the response did not match the expected shape (report it) |
| `OutcomeStoreError` | `outcome_store` | 0 | no | a durable queue store could not be read or written; a damaged queue file is left untouched for recovery |

All HTTP errors derive from `APIStatusError`; `APITimeoutError` derives from
`APIConnectionError`. `GATEWAY_ERROR_TAXONOMY` maps each code to its canonical status and default
retryability; `is_gateway_error_code(code)` tells gateway codes from transport ones.

`retryable` starts from the taxonomy. A response's own `retryable: false` can lower it, but a
code the taxonomy marks non-retryable (for example `model_unpriced`) stays non-retryable even if
a response says `retryable: true`, so neither the SDK's retries nor your own logic retry it.

## `model_unpriced`

The gateway refuses to call a model it cannot price (for example a newly discovered model, or a
custom provider registered without pricing), because the call could not be costed. The refusal
happens before any provider is contacted, so nothing is billed. The SDK raises
`ModelUnpricedError` and never retries it, whatever `max_retries` is.

```python
from ultrarouter import ModelUnpricedError

try:
    client.chat.completions.create(
        model="acme/unpriced-model", messages=[{"role": "user", "content": "Hi"}]
    )
except ModelUnpricedError as exc:
    print(exc.status, exc.retryable, exc.message)  # 403 False ...
```

Fix it by choosing a priced model (`client.models.list()` shows prices), or by declaring pricing on
the custom provider that serves the model.

## Errors inside a stream

An error after a stream started arrives as an `event: error` frame and is raised from the
iterator as the same typed class. See [Streaming](streaming.md#errors-during-a-stream).

## Client-side errors

Some checks happen before anything is sent; they raise with `status == 0`:

| Situation | Exception |
| --- | --- |
| no API key configured | `ConfigurationError` with `code="missing_api_key"` |
| no base URL configured (there is no default gateway) | `ConfigurationError` with `code="missing_base_url"` |
| `as_openai()` without the `openai` package | `UltraRouterError` with `code="dependency_missing"` |
| `render_prompt` missing a required variable | `PromptVariablesMissingError` |
| invalid arguments (for example `bench.record` without `suite`/`run`, `flywheel.grant` without a cluster key, `LearnedSession.record` without `artifact_key`) | `InvalidRequestError` |
| an unknown `autopilot` value | `ValueError` |

`ConfigurationError` is a subclass of `UltraRouterError` raised before any network call when the
client cannot be constructed: the API key or the gateway base URL is missing from the argument and
from both environment variables. There is no default gateway, so a base URL must come from
`base_url=`, `ULTRAROUTER_BASE_URL` or `UR_BASE_URL` (for a local gateway, `http://localhost:8080`).

```python
from ultrarouter import InvalidRequestError

try:
    client.bench.record([{"trace": "t1", "passed": True}])
except InvalidRequestError as exc:
    print(exc.status, exc.message)  # 0 bench.record requires suite= or run=
```

## Outcome and reviewer queues

`outcomes.record(...)` never raises for a delivery failure: it returns an `OutcomeReceipt` whose
`status` is `delivered` (a valid outcome result), `queued` (anything else that does not prove the
event invalid: timeouts, cancellation, connection failures, any 401/403/408/429, 5xx, a body
without a complete gateway error envelope, a malformed success; kept for `flush()`) or `rejected`
(a validated refusal of the event: a complete envelope with `invalid_request`, `not_found` or
`conflict` at that code's status and `retryable: false`; dropped, with `error`).
`reviewer.flush()` removes an event only on a valid per-event verdict and keeps every failed batch
queued: it ends quietly on an ambiguous failure and raises any other non-retryable 4xx (for
example an invalid signature). See [Outcomes](outcomes.md#recording-outcomes).

`UltraRouterError.envelope` holds the gateway's error object when, and only when, the response
body was a complete envelope (`code` a non-empty string, `message` and `request_id` strings,
`retryable` a boolean, `provider_code` a string when present);
`ultrarouter.parse_gateway_error_envelope(body)` applies the same check to any decoded body.

A durable store that cannot be read or written raises `OutcomeStoreError` (`code="outcome_store"`)
from `record`, `flush` and the store itself; a damaged `FileOutcomeStore` file is never overwritten.
