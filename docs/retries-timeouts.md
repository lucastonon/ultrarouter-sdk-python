# Retries, timeouts and idempotency

## The request policy

| Behaviour | Default | Override |
| --- | --- | --- |
| Total time budget per call (all attempts and waits) | 600 s | `timeout=` on the client, per call (`timeout=` or `options={"timeout": ...}`) |
| Automatic retries | 2 (up to 3 attempts) | `max_retries=` on the client or per call |
| Backoff | jittered exponential: 0.5 s × 2^attempt, capped at 8 s, × a random factor in [0.5, 1] | |
| `Retry-After` | honoured (seconds or HTTP date), capped at 32 s | |
| Idempotency key | a fresh UUID on every non-streaming `POST`, the same across its retries | `idempotency_key=` / `options={"idempotency_key": ...}` |

What is retried:

- connection failures (`APIConnectionError`);
- responses with status 408, 429 or 5xx, **unless** the gateway marked the error
  `retryable: false` (for example `atomic_spend_guard_unavailable`).

What is not retried: every other 4xx response (for example `model_unpriced`, `authentication`,
`invalid_request`), `APITimeoutError` (the budget is spent), and streams (`stream=True`). A wait
never extends past the remaining time budget. A code that is non-retryable by definition (see
[Errors](errors.md)) is never retried, even if a response claims `retryable: true`.

## The time budget is a real deadline

`timeout` is the total time a call may take: connecting, sending, waiting for the response, reading
the **whole** body, every retry and every backoff wait. It is enforced as a deadline, not as a
per-read limit: a server that sends a body in small pieces, each arriving quickly, cannot stretch a
call past `timeout`. When the deadline passes, the call raises `APITimeoutError` (`code="timeout"`)
at once, and the abandoned response is closed in the background.

Synchronous calls achieve this by doing the blocking network work in a short-lived request
thread and waiting for it at most until the deadline (context variables are carried over). When
the deadline passes, the SDK shuts the transfer's connection down, so the thread stops reading at
once, closes the response and ends; nothing keeps consuming a body after the call has returned.
One client (with its `with_options` copies) runs at most 100 request threads at a time
(`ultrarouter._base_client.MAX_REQUEST_THREADS`); a call that cannot get one before its
deadline raises `APITimeoutError` ("too many requests in flight"). Asynchronous calls cancel
the operation at the deadline and close the response.

```python
from ultrarouter import UltraRouter

client = UltraRouter(timeout=30, max_retries=4)

# Per call, on the OpenAI-compatible methods:
client.chat.completions.create(
    model="openai/gpt-5.2-mini",
    messages=[{"role": "user", "content": "Hi"}],
    timeout=10,
    max_retries=0,
)

# Per call, on every other method:
client.call_types.list(options={"timeout": 5, "max_retries": 1})
```

## Idempotency

The gateway uses the `Idempotency-Key` header to replay a request it already processed instead of
running it twice. The SDK sends one on every non-streaming `POST` automatically, and keeps it the
same across retries, so a retry after a lost response is safe. To make a request idempotent
across separate calls too (for example across process restarts), pass your own key:

```python
order_id = "order-1001"
client.chat.completions.create(
    model="openai/gpt-5.2-mini",
    messages=[{"role": "user", "content": "Write the confirmation email."}],
    idempotency_key=f"confirmation-email:{order_id}",
)
client.artifacts.create(
    key="order-1001:email", options={"idempotency_key": "artifact:order-1001:email"}
)
```

`GET`, `PATCH` and streaming requests carry no automatic key. Outcome and reviewer events have
their own idempotency (`source_event_id`, `event_id`), which the durable queues fix before the
first attempt.

## Timeouts in streams

A stream (`stream=True`) can legitimately run for minutes, so `timeout` means two things there:

1. **A deadline for the stream to start.** Connecting, sending the request and receiving the
   response headers must finish within `timeout`, enforced as a real deadline like any other
   call. Otherwise `create(...)` raises `APITimeoutError`. When the gateway answers with an
   error instead of a stream, reading that error body belongs to the same deadline.
2. **An idle limit between chunks.** After the stream has started, each wait for the next piece
   of data may take at most `timeout` seconds. A longer silence raises `APITimeoutError` from the
   iterator (`for chunk in stream`, `stream.text()`), and the response is closed.

The total length of a stream is not limited. To bound it, stop iterating and call
`stream.close()` (or leave the `with` block) when your own deadline passes. A connection that
breaks mid-stream raises `APIConnectionError` from the iterator. Streams are never retried
automatically.

## Seeing what happened

`UltraRouterError.retryable` tells whether a retry could help. To observe retries, pass an
`httpx` client with event hooks:

```python
import httpx

attempts: list[str] = []
http = httpx.Client(event_hooks={"request": [lambda request: attempts.append(str(request.url))]})
observed = UltraRouter(http_client=http)
observed.models.list()
print(attempts)
http.close()
```
