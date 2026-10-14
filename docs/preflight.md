# Preflight and learned context

Preflight is for calls you make **yourself**, directly to a model provider, while still using
what the gateway knows. Before the call, `client.preflight(...)` (`POST /v1/preflight`) answers:

- which model to use and the health-ordered fallbacks;
- which learned context module to inject, and where;
- the active hosted prompt, if the call type has one;
- with a cluster key (`artifact_key` or `trace_id`), the **exposure grant** that puts this call
  in the treated or holdout arm of a live experiment.

Preflight never calls a model and is never charged as one. It needs a key with
`gateway:invoke`.

```python
from ultrarouter import UltraRouter

client = UltraRouter()
advice = client.preflight(call_type="support-reply", artifact_key="ticket:4812:reply")

print(advice.routing.mode, advice.routing.model.id if advice.routing.model else None)
print([fallback.id for fallback in advice.routing.fallbacks])
if advice.knowledge is not None:
    print(advice.knowledge.placement, advice.knowledge.module.tokens)
else:
    print("no learned module:", advice.knowledge_reason)
print(advice.grant.arm if advice.grant else advice.grant_reason)
print(advice.provisional, advice.reason)
```

## `messages` for case-based modules

Some call types (classification tasks in particular) learn *verified cases* instead of a fixed
module: the module is rendered for the input of each request, from the cases nearest to it. For
those, pass the messages you are about to send. Without them, preflight returns
`knowledge=None` with `knowledge_reason="case_query_missing"`.

```python
messages = [
    {"role": "system", "content": "Classify the ticket."},
    {"role": "user", "content": "I was charged twice for my subscription."},
]

without = client.preflight(call_type="ticket-classifier")
print(without.knowledge, without.knowledge_reason)  # None case_query_missing

advice = client.preflight(call_type="ticket-classifier", messages=messages)
print(advice.knowledge.module.content if advice.knowledge else advice.knowledge_reason)
```

The messages are used only to render the module; the gateway does not store or log them, and the
SDK's cache keys on a digest of them (never the text), so a module rendered for one input is
never reused for another. A static (non-case) module ignores `messages`.

## `use_learned`: preflight plus placement plus outcomes

`client.use_learned(...)` preflights once and returns a
[`LearnedSession`](api-reference.md#learnedsession):

- `session.apply(messages)` returns your messages with the learned module inserted exactly where
  the gateway would put it (after the leading system messages). For a holdout arm, or when no
  module is configured, it returns the messages unchanged.
- `session.record(outcome)` upserts the artifact (`artifact_key`) with the grant attached, then
  records the outcome through the durable queue.

```python
session = client.use_learned(
    call_type="support-reply",
    artifact_key="ticket:4812:reply",
    messages=[{"role": "user", "content": "Where is my refund?"}],
)

prompt_messages = session.apply(
    [
        {"role": "system", "content": "You are a support agent."},
        {"role": "user", "content": "Where is my refund?"},
    ]
)
model = session.model or "openai/gpt-5.2-mini"
# ... call your provider directly with `model` and `prompt_messages` ...

receipt = session.record({"channel": "behavioral", "kind": "accepted"})
print(receipt.status, session.grant.arm if session.grant else None)
```

`apply` always injects the returned module, whatever `knowledge.delivery` says: `delivery`
describes whether the gateway injects on *proxied* requests, and a direct call never passes
through the gateway. `record` requires `artifact_key`; without it, it raises
`InvalidRequestError` instead of silently recording an outcome with no grant.

## Hosted prompts

`advice.prompt` is the active hosted prompt (or `None` for a code-owned call type);
`client.get_prompt(call_type)` returns just that part. Render it with
[`render_prompt`](prompt-render.md).

## Caching

Preflight answers have two lifetimes, and the client honours both:

| Part | Lifetime | How the SDK handles it |
| --- | --- | --- |
| Config part (model, learned module, hosted prompt) | `Cache-Control: max-age=5` + strong `ETag` | served from cache while fresh; then revalidated with `If-None-Match` (a `304` reuses the cached body) |
| Live part (health-ordered fallbacks) | 30 s (`X-UR-Live-Max-Age`) | after it expires, a full refetch |
| Grant | never cached | read from the `X-UR-Grant` header of every response, including a `304` |

A request with a cluster key always reaches the gateway (to get a fresh grant). Options:

```python
fresh = client.preflight(call_type="support-reply", no_cache=True)  # bypass the cache
short = client.preflight(call_type="support-reply", max_age_s=10)  # shrink the live window
print(fresh.config_version, short.config_version)
```

The cache is bounded. It keeps at most 1024 request identities per client by default
(`DEFAULT_PREFLIGHT_CACHE_SIZE`); storing one more evicts the least recently used, and entries
whose live part has expired are dropped (they could never be served again). A long-lived client
that sends unique `trace_id`, `artifact_key` or `messages` on every call therefore stays within the
bound. Choose the size with `preflight_cache_size=` (`0` turns the cache off):

```python
from ultrarouter import UltraRouter

small = UltraRouter(preflight_cache_size=128)
uncached = UltraRouter(preflight_cache_size=0)
```

A client derived with `with_options(...)` shares its parent's cache. The cache decision is a pure
function, `ultrarouter.decide_preflight_cache`, if you want to reason about it or reuse it.

## Async

```python
import asyncio

from ultrarouter import AsyncUltraRouter


async def main() -> None:
    async with AsyncUltraRouter() as client:
        advice = await client.preflight(
            call_type="ticket-classifier",
            messages=[{"role": "user", "content": "Refund not received"}],
        )
        session = await client.use_learned(call_type="support-reply", artifact_key="ticket:9")
        print(advice.knowledge_reason, session.apply([{"role": "user", "content": "hi"}]))
        await session.record({"channel": "behavioral", "kind": "accepted"})


asyncio.run(main())
```
