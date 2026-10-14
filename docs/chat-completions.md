# Chat completions

`client.chat.completions.create(...)` sends `POST /v1/chat/completions`. It accepts the OpenAI
chat parameters plus the ultrarouter extensions, and returns a
[`ChatCompletion`](types-reference.md#chatcompletion).

```python
from ultrarouter import UltraRouter

client = UltraRouter()
reply = client.chat.completions.create(
    model="openai/gpt-5.2-mini",
    messages=[
        {"role": "system", "content": "You answer in one sentence."},
        {"role": "user", "content": "What is a call type?"},
    ],
    temperature=0.2,
    max_tokens=200,
)
choice = reply.choices[0]
print(choice.message.content, choice.finish_reason)
print(reply.usage.prompt_tokens, reply.usage.completion_tokens)
```

Model ids are provider-prefixed (`openai/gpt-5.2-mini`); `client.models.list()` lists the ids
your workspace can use.

## Parameters

OpenAI parameters are passed through unchanged: `messages` (required), `model`, `temperature`,
`top_p`, `max_tokens`, `max_completion_tokens`, `n`, `stop`, `seed`, `presence_penalty`,
`frequency_penalty`, `logprobs`, `top_logprobs`, `tools`, `tool_choice`, `response_format`,
`reasoning_effort`, `stream_options`, `user` and `metadata`.

ultrarouter extensions:

| Parameter | Type | Meaning |
| --- | --- | --- |
| `models` | `list[str]` | ordered fallback models tried if the primary model fails |
| `provider` | mapping | provider preferences: `order`, `sort` (`price`, `throughput`, `latency`), `ignore`, `allow_fallbacks`, `data_collection` |
| `router` | `"off"`, `"candidates"`, `"auto"` | routing mode for this call |
| `compression` | mode or mapping | `off` (default, the prompt is never rewritten), `semantic_safe`, `adaptive`, or `{"mode": ..., "no_compress_fields": [...]}` |
| `call_type` | `str` | the call-type slug this request belongs to |
| `reasoning` | mapping | OpenRouter-style reasoning control (`effort`, `max_tokens`, `exclude`) |
| `ur` | mapping | per-request controls (below) |
| `bench` | `str` or mapping | tag this request for a Bench suite (sent as `ur.bench`) |

The `ur` mapping:

| Key | Meaning |
| --- | --- |
| `max_cost_usd` | refuse the call if its estimated cost exceeds this (raises `MaxCostExceededError`) |
| `trace_id` | group the calls of one multi-step task |
| `artifact` | the artifact key this request contributes to (see [Outcomes](outcomes.md)) |
| `tags` | free-form key/value tags stored with the request |
| `timeout_ms` | gateway-side deadline for this call |
| `prompt_vars` | values for the active hosted prompt's variables (see [Hosted prompts](hosted-prompts.md)) |
| `segments` | label message parts (for example reference material) |
| `manifest` | a context manifest from [`ultrarouter.context`](context-runtime.md) |
| `context_modules` | context modules this call opts into |

```python
reply = client.chat.completions.create(
    model="openai/gpt-5.2-mini",
    models=["openai/gpt-5.2"],  # fallback if the primary fails
    provider={"sort": "latency"},
    call_type="support-reply",
    ur={"max_cost_usd": 0.02, "trace_id": "order-1001", "tags": {"team": "support"}},
    messages=[{"role": "user", "content": "Where is order 1001?"}],
)
print(reply.ur.routing.fallback_used)
```

Anything the SDK does not model yet can be sent with `extra_body=`; it is merged into the JSON
body last.

```python
reply = client.chat.completions.create(
    model="openai/gpt-5.2-mini",
    messages=[{"role": "user", "content": "Hi"}],
    extra_body={"some_new_option": True},
)
```

## The `ur` response block

| Field | Meaning |
| --- | --- |
| `request_id` | `req_...` id; use it for [feedback](feedback.md), [generation lookup](generation.md) and support |
| `model_served` | the model that actually answered (it can differ from the requested model when routing or fallbacks apply) |
| `provider` | the provider that served it |
| `routing` | `mode`, `fallback_used` and the routing `engine` when one ran |
| `compression` | the compression tier `applied` (`off`, `semantic_safe`, `adaptive`) and its details |
| `cost_usd` | the cost of this call in USD |
| `byok` | whether your own provider key (BYOK) was used |
| `call_type` | the resolved call type, if any |
| `artifact_id` | the artifact the request was bound to, when `ur.artifact` was sent |
| `bench` | the Bench capture status, when the request was tagged |

```python
print(reply.ur.request_id, reply.ur.model_served, reply.ur.provider, reply.ur.cost_usd)
print(reply.ur.routing.mode, reply.ur.compression.applied)
```

## Defaults

Use `default_model` and `defaults=` on the client to avoid repeating values; per-call values win.
See [Configuration](configuration.md#client-defaults-and-per-call-overrides).

```python
client = UltraRouter(default_model="openai/gpt-5.2-mini", defaults={"call_type": "support-reply"})
reply = client.chat.completions.create(messages=[{"role": "user", "content": "Hi"}])
```

## Async

```python
import asyncio

from ultrarouter import AsyncUltraRouter


async def main() -> str | None:
    async with AsyncUltraRouter() as client:
        reply = await client.chat.completions.create(
            model="openai/gpt-5.2-mini", messages=[{"role": "user", "content": "Hi"}]
        )
        return reply.choices[0].message.content


print(asyncio.run(main()))
```

## Related

- [Streaming](streaming.md), [Tools](tools.md), [Structured outputs](structured-outputs.md)
- [Errors](errors.md): which exceptions `create` can raise
