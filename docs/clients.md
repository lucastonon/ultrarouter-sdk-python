# Sync and async clients

The SDK has two clients with the same surface:

| | `UltraRouter` | `AsyncUltraRouter` |
| --- | --- | --- |
| Calls | `client.models.list()` | `await client.models.list()` |
| Streams | `Stream` (`for chunk in stream`) | `AsyncStream` (`async for chunk in stream`) |
| Context manager | `with UltraRouter() as client:` | `async with AsyncUltraRouter() as client:` |
| HTTP client | `httpx.Client` | `httpx.AsyncClient` |
| `as_openai()` | `openai.OpenAI` | `openai.AsyncOpenAI` |

Constructor arguments, namespaces, method names and return types are identical. A few local-only
helpers stay synchronous on the async client because they never touch the network:
`client.reviewer.record(...)` and `client.reviewer.dead_letters()`.

## Lifecycle

A client owns a connection pool. Create one per process (or per worker) and reuse it; close it
when you are done, or use it as a context manager.

```python
from ultrarouter import UltraRouter

with UltraRouter() as client:
    models = client.models.list()
    print(len(models.data))
# the pool is closed here
```

```python
import asyncio

from ultrarouter import AsyncUltraRouter


async def main() -> None:
    async with AsyncUltraRouter() as client:
        models = await client.models.list()
        print(len(models.data))


asyncio.run(main())
```

Creating a client is cheap, but creating one per request wastes connections. Clients are safe
to share between threads (the sync client) or tasks on one event loop (the async client).

## Concurrency with the async client

```python
import asyncio

from ultrarouter import AsyncUltraRouter


async def summarize_all(texts: list[str]) -> list[str]:
    async with AsyncUltraRouter(default_model="openai/gpt-5.2-mini") as client:
        replies = await asyncio.gather(
            *(
                client.chat.completions.create(
                    messages=[{"role": "user", "content": f"Summarize: {text}"}]
                )
                for text in texts
            )
        )
    return [reply.choices[0].message.content or "" for reply in replies]


print(asyncio.run(summarize_all(["first document", "second document"])))
```

To bound concurrency, wrap calls in an `asyncio.Semaphore`; the gateway answers excess traffic
with `rate_limited` (429), which the SDK retries with backoff.

## Per-call settings and `with_options`

Any call can override the timeout, retries and headers. To reuse a set of overrides, derive a
client with `with_options`: it shares the parent's connection pool, and closing it does not close
the pool.

```python
from ultrarouter import UltraRouter

client = UltraRouter()
fast = client.with_options(timeout=5, max_retries=0, default_headers={"X-Priority": "interactive"})
print(fast.timeout, client.timeout)  # 5.0 600.0
fast.models.list()
```

Everything a derived client sends uses its own options, including the outcome events and
reviewer decisions it delivers. What it shares with its parent:

| Shared | Consequence |
| --- | --- |
| the connection pool | closing the derived client does not close the pool |
| the outcome store and the reviewer store | an event queued through either client is pending for both; whichever client records or flushes it delivers it with **its own** headers, timeout and retries |
| the preflight cache | a cached preflight answer is reused by both (the grant is never cached) |
| the request-thread limit (synchronous clients) | at most 100 calls in flight across the client and its copies (see [the deadline](retries-timeouts.md#the-time-budget-is-a-real-deadline)) |

Delivering a shared event twice (for example both clients flush at once) is harmless: the event
keeps its identity (`source_event_id`, `event_id`) and outcome deliveries reuse the same
`Idempotency-Key`, so the second delivery is recorded as a duplicate. Construct a separate client
with its own `outcome_store=` and `reviewer_store=` if two configurations must never share pending
events.

```python
fast.outcomes.record("ticket:4812:reply", {"channel": "behavioral", "kind": "accepted"})
print(fast.outcomes.size() == client.outcomes.size())  # True: one shared store
client.outcomes.flush()  # delivered with the parent's options
```

## Bringing your own HTTP client

```python
import httpx

from ultrarouter import AsyncUltraRouter, UltraRouter

sync_http = httpx.Client(timeout=httpx.Timeout(30.0))
client = UltraRouter(http_client=sync_http)
client.models.list()
client.close()  # does not close sync_http: you own it
sync_http.close()

async_client = AsyncUltraRouter(http_client=httpx.AsyncClient())
```

The SDK applies its own total time budget per call (`timeout=`) on top of whatever the HTTP
client is configured with: it is a deadline for the whole call, including reading the body (see
[Retries, timeouts and idempotency](retries-timeouts.md#the-time-budget-is-a-real-deadline)).

## Next steps

- [Chat completions](chat-completions.md)
- [Retries, timeouts and idempotency](retries-timeouts.md)
