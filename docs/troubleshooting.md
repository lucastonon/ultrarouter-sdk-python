# Troubleshooting and FAQ

## `UltraRouterError: missing API key`

Set `ULTRAROUTER_API_KEY` or pass `api_key=`. Check with:

```python
from ultrarouter import UltraRouter

print(UltraRouter().key.get().mode)
```

## `AuthenticationError` (401)

The key is wrong, revoked, or for another deployment. Make sure `ULTRAROUTER_BASE_URL` points at
the gateway that issued the key. The client prints neither the key nor the URL in errors;
`client.base_url` shows the URL it uses.

## `PermissionDeniedError` (403)

The key is valid but lacks a scope: chat, embeddings, models and preflight need `gateway:invoke`;
reading call types and flywheel state needs `config:read`; changing call types needs
`config:write`; outcomes, artifacts, imports and the reviewer need `outcomes:write`; Bench needs
`bench:run`. `client.key.get().scopes` lists your key's scopes.

## `ModelUnpricedError` (403, `model_unpriced`)

The model has no price, so the gateway did not call it. Nothing was billed. Choose a model from
`client.models.list()` (each has a price), or add pricing to the custom provider that serves it.
The SDK never retries this error.

## `NotFoundError` right after a call

The request record (used by `requests.feedback` and `generation.get`) is written asynchronously.
Retry after a short delay.

## My base URL ends in `/v1`

That is fine: the SDK removes a trailing `/v1` (and `/`) because its paths include `/v1`.

## How do I use a proxy, custom CA or connection limits?

Pass your own `httpx.Client(...)` as `http_client=`. See
[Configuration](configuration.md#custom-http-clients-proxies-mtls-transports).

## Requests are slow to fail

The default `timeout` is a total budget of 600 seconds across retries. Lower it on the client or
per call, and lower `max_retries` for interactive paths.

## How do I see the raw request?

Use an `httpx` event hook (see [Retries](retries-timeouts.md#seeing-what-happened)) or a mock
transport in tests (see [Testing](testing.md)). Errors carry the decoded body in `exc.body`.

## Does the SDK log anything?

No. It does not print or log requests, responses, keys or outcome events.

## A field I need is missing from a response model

A newer gateway may send fields this SDK version does not know yet. They are kept:
`response.model_extra["field"]` or `response.to_dict()["field"]`.

## `as_openai()` raises `dependency_missing`

Install the extra: `pip install "ultrarouter[openai]"`.

## Is it safe to share a client between threads or tasks?

Yes: share one `UltraRouter` between threads, or one `AsyncUltraRouter` between tasks on the same
event loop. Do not share an async client across event loops.

## Python version errors on install

The SDK needs Python 3.10 or newer.

## Where do I report a bug or a security issue?

Bugs: the issue tracker linked from the README. Security issues: privately, as described in
[SECURITY.md](../SECURITY.md).
