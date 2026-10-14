# ultrarouter Python SDK

[![PyPI](https://img.shields.io/pypi/v/ultrarouter.svg)](https://pypi.org/project/ultrarouter/)
[![Python versions](https://img.shields.io/pypi/pyversions/ultrarouter.svg)](https://pypi.org/project/ultrarouter/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/lucastonon/ultrarouter-sdk-python/blob/main/LICENSE)

The official Python client for ultrarouter, an OpenAI-compatible LLM gateway with model routing,
fallbacks, evals, and an outcome ledger that records what happened after a model answered.

- **OpenAI-compatible**: `client.chat.completions.create(...)`, `client.embeddings.create(...)`,
  `client.models.list()`, streaming, tools and structured outputs, or hand an existing
  `openai` client the gateway with `client.as_openai()`.
- **Sync and async**: `UltraRouter` and `AsyncUltraRouter` have the same surface.
- **Typed**: every response is a pydantic v2 model; the package ships `py.typed` and passes
  `mypy --strict`.
- **Production defaults**: a total time budget per call, automatic retries with backoff for
  transient failures, idempotency keys on every write, and typed errors.
- **Beyond chat**: call types, hosted prompts, Bench comparisons, outcomes, preflight with
  learned context, a reviewer adapter, and a pure context runtime (`ultrarouter.context`).

> Status: `0.0.1` is an early (alpha) release. The API surface may change before `1.0`.
> You need an ultrarouter API key and the URL of a gateway you have access to.

## Install

```bash
pip install ultrarouter            # or: uv add ultrarouter / poetry add ultrarouter
pip install "ultrarouter[openai]"  # adds the openai package for client.as_openai()
```

Python 3.10 or newer. Runtime dependencies: `httpx`, `pydantic` (v2) and `typing-extensions`.

## 60-second quickstart

Set your key and the URL of the gateway you have access to (there is no default gateway):

```bash
export ULTRAROUTER_API_KEY="ur_sk_test_..."
export ULTRAROUTER_BASE_URL="https://gateway.example.com"   # or http://localhost:8080 for a local gateway
```

```python
from ultrarouter import UltraRouter

client = UltraRouter()  # reads ULTRAROUTER_API_KEY and ULTRAROUTER_BASE_URL

reply = client.chat.completions.create(
    model="openai/gpt-5.2-mini",
    messages=[{"role": "user", "content": "Write a one-line greeting."}],
)
print(reply.choices[0].message.content)
print(reply.ur.request_id, reply.ur.model_served, reply.ur.cost_usd)
```

Every response carries an `ur` block: the request id (use it for feedback and stats), the model
that actually served the call, the provider, the routing decision and the cost in USD.

The async client is the same API with `await`:

```python
import asyncio

from ultrarouter import AsyncUltraRouter


async def main() -> None:
    async with AsyncUltraRouter() as client:
        reply = await client.chat.completions.create(
            model="openai/gpt-5.2-mini",
            messages=[{"role": "user", "content": "Write a one-line greeting."}],
        )
        print(reply.choices[0].message.content)


asyncio.run(main())
```

## Configuration

| Setting | Constructor argument | Environment variable | Default |
| --- | --- | --- | --- |
| API key | `api_key=` | `ULTRAROUTER_API_KEY` (or `UR_API_KEY`) | required |
| Gateway URL | `base_url=` | `ULTRAROUTER_BASE_URL` (or `UR_BASE_URL`) | required |
| Default model | `default_model=` | | none |
| Time budget per call | `timeout=` (seconds) | | `600` |
| Automatic retries | `max_retries=` | | `2` |
| Extra headers | `default_headers=` | | none |

Point `base_url` at any deployment (self-hosted, staging, a local stack); a trailing `/v1` is
accepted. See [Configuration](https://github.com/lucastonon/ultrarouter-sdk-python/blob/main/docs/configuration.md) for per-call defaults (`defaults=`), the
`autopilot` routing intent and Bench tagging.

```python
from ultrarouter import UltraRouter

client = UltraRouter(
    base_url="https://gateway.example.com",
    default_model="openai/gpt-5.2-mini",
    defaults={"call_type": "support-reply", "max_cost_usd": 0.05},
    timeout=60,
    max_retries=3,
)
reply = client.chat.completions.create(messages=[{"role": "user", "content": "Hello"}])
print(reply.ur.model_served)
```

## Feature tour

**Streaming.** `stream=True` returns an iterator of chunks; the last chunk carries usage and
the `ur` block, also available on the stream afterwards.

```python
from ultrarouter import UltraRouter

client = UltraRouter()
with client.chat.completions.create(
    model="openai/gpt-5.2-mini",
    messages=[{"role": "user", "content": "Count to three."}],
    stream=True,
) as stream:
    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            print(chunk.choices[0].delta.content, end="", flush=True)
print()
print(stream.ur.request_id if stream.ur else None)
```

**Embeddings and models.**

```python
from ultrarouter import UltraRouter

client = UltraRouter()
vectors = client.embeddings.create(model="openai/text-embedding-3-small", input=["alpha", "beta"])
print(len(vectors.data), len(vectors.data[0].embedding))

for model in client.models.list(provider="openai").data:
    print(model.id, model.pricing.input_usd_per_1m)
```

**Feedback and post-hoc stats** for a served request:

```python
from ultrarouter import UltraRouter

client = UltraRouter()
reply = client.chat.completions.create(
    model="openai/gpt-5.2-mini", messages=[{"role": "user", "content": "Hi"}]
)
client.requests.feedback(reply.ur.request_id, rating=1, tags=["helpful"])
stats = client.generation.get(reply.ur.request_id)
print(stats.tokens.total, stats.cost.total_usd)
```

**Outcomes**: record what happened after the answer (accepted, edited, resolved) on an
*artifact*, durably queued and retried without double counting:

```python
from ultrarouter import UltraRouter

client = UltraRouter()
with client.with_artifact("ticket:4812:reply") as scope:
    draft = scope.chat.completions.create(
        model="openai/gpt-5.2-mini",
        messages=[{"role": "user", "content": "Draft a reply about a late order."}],
    )
    scope.record({"channel": "behavioral", "kind": "accepted"})
```

More: [call types and hosted prompts](https://github.com/lucastonon/ultrarouter-sdk-python/blob/main/docs/call-types.md), [Bench](https://github.com/lucastonon/ultrarouter-sdk-python/blob/main/docs/bench.md),
[preflight and learned context](https://github.com/lucastonon/ultrarouter-sdk-python/blob/main/docs/preflight.md), [the reviewer adapter](https://github.com/lucastonon/ultrarouter-sdk-python/blob/main/docs/reviewer.md),
[the context runtime](https://github.com/lucastonon/ultrarouter-sdk-python/blob/main/docs/context-runtime.md) and the [full guide index](https://github.com/lucastonon/ultrarouter-sdk-python/blob/main/docs/index.md).

## Use it as the OpenAI client

Already using the `openai` package? Keep your code and point it at the gateway:

```python
from ultrarouter import UltraRouter

openai_client = UltraRouter().as_openai()  # an openai.OpenAI configured for the gateway
reply = openai_client.chat.completions.create(
    model="openai/gpt-5.2-mini", messages=[{"role": "user", "content": "Hi"}]
)
print(reply.choices[0].message.content)
```

`AsyncUltraRouter().as_openai()` returns an `openai.AsyncOpenAI`. See
[OpenAI compatibility](https://github.com/lucastonon/ultrarouter-sdk-python/blob/main/docs/openai-compatibility.md).

## Errors and retries

Failures raise typed exceptions that all derive from `UltraRouterError` and carry `code`,
`status`, `message`, `request_id` and `retryable`:

```python
from ultrarouter import ModelUnpricedError, RateLimitError, UltraRouter, UltraRouterError

client = UltraRouter()
try:
    client.chat.completions.create(
        model="acme/unpriced-model", messages=[{"role": "user", "content": "Hi"}]
    )
except ModelUnpricedError as exc:  # 403: the gateway will not call a model it cannot price
    print("pick a priced model:", exc.message)
except RateLimitError:
    print("still rate limited after automatic retries")
except UltraRouterError as exc:
    print(exc.code, exc.status, exc.request_id)
```

The SDK retries connection errors and 408/429/5xx responses that the gateway did not mark
`retryable: false` (two retries by default, jittered exponential backoff, `Retry-After`
honoured), all within the call's total `timeout`. Every non-streaming `POST` carries an
`Idempotency-Key` that stays the same across retries. Streams are not retried. Details:
[Errors](https://github.com/lucastonon/ultrarouter-sdk-python/blob/main/docs/errors.md) and [Retries, timeouts and idempotency](https://github.com/lucastonon/ultrarouter-sdk-python/blob/main/docs/retries-timeouts.md).

## Documentation

- [Guide index](https://github.com/lucastonon/ultrarouter-sdk-python/blob/main/docs/index.md): installation, configuration, every surface, typing, testing,
  troubleshooting.
- [API reference](https://github.com/lucastonon/ultrarouter-sdk-python/blob/main/docs/api-reference.md) and [API coverage](https://github.com/lucastonon/ultrarouter-sdk-python/blob/main/docs/api-coverage.md) (every
  endpoint the SDK calls, sync and async).
- [Examples](https://github.com/lucastonon/ultrarouter-sdk-python/tree/main/examples): runnable scripts.
- For AI agents: [AGENTS.md](https://github.com/lucastonon/ultrarouter-sdk-python/blob/main/AGENTS.md), [llms.txt](https://github.com/lucastonon/ultrarouter-sdk-python/blob/main/llms.txt) and [llms-full.txt](https://github.com/lucastonon/ultrarouter-sdk-python/blob/main/llms-full.txt).

## Contributing and security

See [CONTRIBUTING.md](https://github.com/lucastonon/ultrarouter-sdk-python/blob/main/CONTRIBUTING.md) (`make check` runs the full gate) and
[SECURITY.md](https://github.com/lucastonon/ultrarouter-sdk-python/blob/main/SECURITY.md) for reporting vulnerabilities. Changes are listed in
[CHANGELOG.md](https://github.com/lucastonon/ultrarouter-sdk-python/blob/main/CHANGELOG.md).

## License

[MIT](https://github.com/lucastonon/ultrarouter-sdk-python/blob/main/LICENSE)
