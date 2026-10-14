# Configuration and authentication

## API keys

Every request is authenticated with an ultrarouter API key sent as `Authorization: Bearer
<key>`. Keys look like `ur_sk_live_...` (production traffic) or `ur_sk_test_...` (testing).
Pass the key explicitly or let the client read it from the environment:

```python
from ultrarouter import UltraRouter

client = UltraRouter()  # ULTRAROUTER_API_KEY, then UR_API_KEY
explicit = UltraRouter(api_key="ur_sk_test_example")
```

If no key is found, construction fails immediately with a `ConfigurationError` whose `code` is
`missing_api_key`. Keep keys out of source control: read them from the environment or a secret
manager. A key's scopes decide which endpoints it may call; `client.key.get()` shows them.

```python
info = client.key.get()
print(info.mode)  # "live" or "test"
print(info.scopes)  # e.g. ["gateway:invoke", "config:read"]
print(info.limits.rps_limit, info.usage.key_spent_micro_usd)
```

## Base URL and self-hosted gateways

The SDK has no default gateway, so you must point it at one: pass `base_url=` or set
`ULTRAROUTER_BASE_URL` (then `UR_BASE_URL`). It can be a self-hosted gateway, a staging
environment or a local stack. Constructing a client with no base URL from any source fails
immediately with a `ConfigurationError` whose `code` is `missing_base_url`.

```python
local = UltraRouter(base_url="http://localhost:8080")
internal = UltraRouter(base_url="https://gateway.example.com/v1")  # "/v1" is accepted
print(internal.base_url)  # https://gateway.example.com
```

A trailing slash or `/v1` is removed, because every SDK path already starts with `/v1`.

### Precedence

Explicit constructor arguments win over environment variables. The API key and base URL have no
default: without one from some source, construction fails with a `ConfigurationError`.

| Setting | Argument | Environment | Default |
| --- | --- | --- | --- |
| API key | `api_key` | `ULTRAROUTER_API_KEY`, `UR_API_KEY` | none (required) |
| Base URL | `base_url` | `ULTRAROUTER_BASE_URL`, `UR_BASE_URL` | none (required) |
| Bench tag | `bench` | `UR_BENCH`, `UR_BENCH_RUN`, `UR_BENCH_TRACE` | none |

## Client defaults and per-call overrides

`default_model` and `defaults=` fill in request fields you leave out. A value passed to a call
always wins.

```python
client = UltraRouter(
    default_model="openai/gpt-5.2-mini",
    defaults={
        "call_type": "support-reply",  # group traffic for evals and routing
        "router": "off",  # serve the requested model
        "compression": "off",  # never rewrite prompts
        "provider": {"sort": "latency"},  # provider preferences
        "max_cost_usd": 0.05,  # refuse calls estimated above this, per call
    },
)

reply = client.chat.completions.create(messages=[{"role": "user", "content": "Hi"}])
override = client.chat.completions.create(
    model="openai/gpt-5.2",  # per-call model wins
    call_type="escalation",  # per-call call type wins
    ur={"max_cost_usd": 0.20},  # per-call ur.max_cost_usd wins
    messages=[{"role": "user", "content": "Hi"}],
)
print(reply.ur.model_served, override.ur.model_served)
```

| Default | Applies to | Notes |
| --- | --- | --- |
| `default_model` | chat, embeddings | used when `model` is omitted |
| `call_type` | chat, embeddings | a call-type slug |
| `router` | chat | `off`, `candidates` or `auto` (ignored when `autopilot` is set) |
| `compression` | chat | `off`, `semantic_safe`, `adaptive`, or a structured object |
| `provider` | chat | OpenRouter-style provider preferences |
| `max_cost_usd` | chat, embeddings | merged into `ur.max_cost_usd` |

## Autopilot

`autopilot=` states how much routing autonomy you allow, in one argument:

| Intent | Router mode sent | Meaning |
| --- | --- | --- |
| `"audit"` | `off` | observe only; always serve the requested model |
| `"recommend"` | `candidates` | rank an approved candidate list |
| `"auto"` | `auto` | let the router choose, where the gateway allows it |

The intent is also a ceiling: a per-call `router` can lower autonomy but never raise it above the
intent (the SDK clamps the value, and the gateway applies the same rule). `"auto"` expresses
intent; it does not bypass any gateway check.

```python
audit = UltraRouter(autopilot="audit")
print(audit.autopilot.mode)  # "audit"
audit.chat.completions.create(
    model="openai/gpt-5.2-mini",
    router="auto",  # clamped to "off" by the audit ceiling
    messages=[{"role": "user", "content": "Hi"}],
)
readiness = audit.autopilot.status()
print(readiness.state, readiness.observing_call_types)
```

See [Autopilot](autopilot.md).

## Bench tagging

`bench=` tags every request for a Bench suite with `X-UR-Bench-*` headers, so a test run can be
captured and compared later. It accepts a suite slug or a mapping with `suite`, optional `run`
(for example a commit SHA) and optional `trace` (a string, or a callable that returns a fresh id
per request). Without the argument, `UR_BENCH` (+ `UR_BENCH_RUN`, `UR_BENCH_TRACE`) is used.

```python
import uuid

tagged = UltraRouter(
    bench={"suite": "checkout-flow", "run": "abc123", "trace": lambda: uuid.uuid4().hex}
)
tagged.chat.completions.create(
    model="openai/gpt-5.2-mini", messages=[{"role": "user", "content": "Hi"}]
)

# A per-call tag is sent in the body as ur.bench and wins over the client headers.
tagged.chat.completions.create(
    model="openai/gpt-5.2-mini",
    bench={"suite": "checkout-flow", "trace": "order-17"},
    messages=[{"role": "user", "content": "Hi"}],
)
```

Bench capture is meant for test keys. With a live key the client warns once at construction,
because the gateway refuses Bench capture on live keys unless a workspace owner allows it.

## Headers, timeouts and retries

```python
client = UltraRouter(
    default_headers={"X-Team": "search"},  # added to every request
    timeout=30,  # total seconds per call, across retries
    max_retries=4,  # automatic retries for transient failures
)
```

Per call, the OpenAI-compatible methods accept `timeout=`, `max_retries=`, `extra_headers=`,
`extra_query=`, `extra_body=` and `idempotency_key=`; every other method accepts
`options={"timeout": ..., "max_retries": ..., "extra_headers": {...}, ...}`. See
[Retries, timeouts and idempotency](retries-timeouts.md).

## Custom HTTP clients (proxies, mTLS, transports)

Pass your own `httpx.Client` (or `httpx.AsyncClient` for the async client) to control proxies,
certificates, connection limits or transports. The SDK never closes a client you pass in.

```python
import httpx

http = httpx.Client(limits=httpx.Limits(max_connections=20), verify=True)
client = UltraRouter(http_client=http)
client.models.list()
http.close()
```

## Next steps

- [Sync and async clients](clients.md)
- [Errors](errors.md)
