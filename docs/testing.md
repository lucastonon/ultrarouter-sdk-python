# Testing and mocking

Code that uses the SDK can be tested without a gateway. The SDK uses `httpx`, so any `httpx`
mocking approach works. Three options, from lightest to heaviest:

## 1. `httpx.MockTransport` (no extra dependency)

Pass an `httpx.Client` with a mock transport. The handler sees the real request the SDK built.

```python
import json

import httpx

from ultrarouter import UltraRouter

CHAT = {
    "id": "chatcmpl-1",
    "object": "chat.completion",
    "created": 0,
    "model": "openai/gpt-5.2-mini",
    "choices": [
        {"index": 0, "message": {"role": "assistant", "content": "mocked"}, "finish_reason": "stop"}
    ],
    "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
    "ur": {
        "request_id": "req_test",
        "call_type": None,
        "model_served": "openai/gpt-5.2-mini",
        "provider": "openai",
        "routing": {"mode": "off", "fallback_used": False},
        "compression": {"applied": "off"},
        "cost_usd": 0.0,
        "byok": False,
    },
}

seen: list[httpx.Request] = []


def handler(request: httpx.Request) -> httpx.Response:
    seen.append(request)
    return httpx.Response(200, json=CHAT)


client = UltraRouter(
    api_key="ur_sk_test_unit",
    base_url="https://gateway.test",
    http_client=httpx.Client(transport=httpx.MockTransport(handler)),
)
reply = client.chat.completions.create(
    model="openai/gpt-5.2-mini", messages=[{"role": "user", "content": "hi"}]
)
assert reply.choices[0].message.content == "mocked"
assert json.loads(seen[0].content)["model"] == "openai/gpt-5.2-mini"
```

Use `httpx.AsyncClient(transport=httpx.MockTransport(handler))` for `AsyncUltraRouter`.

## 2. `respx`

[`respx`](https://lundberg.github.io/respx/) patches `httpx` globally and gives route matchers and
call assertions:

```python
import respx

from ultrarouter import RateLimitError, UltraRouter

with respx.mock(base_url="https://gateway.test", assert_all_called=True) as router:
    route = router.post("/v1/chat/completions").respond(
        429,
        json={
            "error": {
                "code": "rate_limited",
                "message": "slow down",
                "request_id": "req_1",
                "retryable": True,
            }
        },
        headers={"retry-after": "0"},
    )
    limited = UltraRouter(api_key="ur_sk_test_unit", base_url="https://gateway.test", max_retries=1)
    try:
        limited.chat.completions.create(
            model="openai/gpt-5.2-mini", messages=[{"role": "user", "content": "hi"}]
        )
    except RateLimitError as exc:
        print(exc.request_id, route.call_count)  # req_1 2 (one retry)
```

## 3. Test retries quickly

Retry backoff uses real sleeps. In tests, inject a no-op sleep and a fixed jitter through the
private `_sleep` / `_rand` constructor arguments, or set `max_retries=0`:

```python
fast = UltraRouter(
    api_key="ur_sk_test_unit",
    base_url="https://gateway.test",
    http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    _sleep=lambda seconds: None,
    _rand=lambda: 0.5,
)
```

## Testing outcome and reviewer code

Use a `MemoryOutcomeStore` (the default) or a `FileOutcomeStore` in a temporary directory, then
inspect the store:

```python
from ultrarouter import MemoryOutcomeStore

store = MemoryOutcomeStore()
offline = UltraRouter(
    api_key="ur_sk_test_unit",
    base_url="https://gateway.test",
    max_retries=0,
    outcome_store=store,
    http_client=httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(503, json={}))),
)
receipt = offline.outcomes.record("art_1", {"channel": "behavioral", "kind": "accepted"})
assert receipt.status == "queued"
assert store.list()[0]["event"]["kind"] == "accepted"
```

## A local mock gateway

This repository's own tests run against a local mock of the whole API
(`tests/support/mock_gateway.py`). It serves every endpoint in `openapi/openapi.yaml` over real
HTTP with spec-shaped responses and is handy for running the examples locally:

```bash
python tests/support/mock_gateway.py --port 8787 &
ULTRAROUTER_BASE_URL=http://127.0.0.1:8787 ULTRAROUTER_API_KEY=ur_sk_test_mock python examples/quickstart.py
```

Control endpoints script its behaviour: `POST /__mock__/fail` queues error responses and
`POST /__mock__/slow` delays the headers or drips the body
(`{"path": "/v1/models", "chunk_delay": 0.15, "chunks": 8}`), which is how the suite proves that
the total `timeout` holds even when every chunk arrives quickly. It is a development tool and is
not installed with the package.

## Live integration tests

`tests/integration/` runs against a real gateway and is skipped unless both
`ULTRAROUTER_API_KEY` and `ULTRAROUTER_BASE_URL` are set. See [CONTRIBUTING.md](../CONTRIBUTING.md).
