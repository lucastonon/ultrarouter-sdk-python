# Streaming

Pass `stream=True` to `client.chat.completions.create` to receive the answer as server-sent
events. The sync client returns a [`Stream`](api-reference.md#stream), the async client an
[`AsyncStream`](api-reference.md#asyncstream). Each item is a
[`ChatCompletionChunk`](types-reference.md#chatcompletionchunk).

```python
from ultrarouter import UltraRouter

client = UltraRouter()
stream = client.chat.completions.create(
    model="openai/gpt-5.2-mini",
    messages=[{"role": "user", "content": "Write a haiku about routers."}],
    stream=True,
)
with stream:
    for chunk in stream:
        for choice in chunk.choices:
            if choice.delta.content:
                print(choice.delta.content, end="", flush=True)
print()
```

## The final chunk: usage and `ur`

The last chunk before the end of the stream has empty `choices` and carries `usage` and the `ur`
block. The stream object also keeps them, so you can read them after iterating:

```python
stream = client.chat.completions.create(
    model="openai/gpt-5.2-mini",
    messages=[{"role": "user", "content": "Say hi."}],
    stream=True,
)
text = stream.text()  # consume the stream and join the content deltas
print(text)
print(stream.usage.total_tokens if stream.usage else None)
print(stream.ur.request_id if stream.ur else None)
```

## Closing early

Leaving a `with` block (or calling `close()`) closes the HTTP response even if you stop reading
early. Iterating to the end closes it too.

```python
stream = client.chat.completions.create(
    model="openai/gpt-5.2-mini",
    messages=[{"role": "user", "content": "Tell me a long story."}],
    stream=True,
)
first = next(stream)
stream.close()
print(first.choices[0].delta.role)
```

## Async streaming

```python
import asyncio

from ultrarouter import AsyncUltraRouter


async def main() -> None:
    async with AsyncUltraRouter() as client:
        stream = await client.chat.completions.create(
            model="openai/gpt-5.2-mini",
            messages=[{"role": "user", "content": "Count to five."}],
            stream=True,
        )
        async with stream:
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    print(chunk.choices[0].delta.content, end="")
        print()
        print(stream.ur.cost_usd if stream.ur else None)


asyncio.run(main())
```

## Errors during a stream

- An error before the first byte (for example `401`, `403 model_unpriced`, `429`) raises from
  `create(...)` itself, as a typed error.
- An error after the stream started arrives as an `event: error` frame and is raised from the
  iterator as the same typed error. Content received before it remains valid.
- Streams are **not** retried automatically and carry no idempotency key; retry yourself if a
  restart is acceptable for your use case.
- `timeout` is the deadline for the stream to *start* (connection and response headers), then the
  longest silence allowed between chunks; a longer silence raises `APITimeoutError` from the
  iterator. The total length of a stream is not limited. See
  [Timeouts in streams](retries-timeouts.md#timeouts-in-streams).
- A connection that breaks mid-stream raises `APIConnectionError` from the iterator.

```python
from ultrarouter import UltraRouterError

try:
    for chunk in client.chat.completions.create(
        model="openai/gpt-5.2-mini", messages=[{"role": "user", "content": "Hi"}], stream=True
    ):
        pass
except UltraRouterError as exc:
    print("stream failed:", exc.code, exc.request_id)
```

## Tool calls in a stream

Tool calls arrive as fragments in `choice.delta.tool_calls`; join the `function.arguments`
fragments per `index`. See [Tools](tools.md#streaming-tool-calls).
