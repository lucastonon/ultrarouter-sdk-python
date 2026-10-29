# OpenAI compatibility

The gateway speaks the OpenAI Chat Completions, Embeddings and Models APIs under `/v1`. You can
use this SDK's OpenAI-shaped methods, or keep the official `openai` package and point it at the
gateway.

## Option 1: this SDK's OpenAI-shaped surface

`client.chat.completions.create`, `client.embeddings.create`, `client.models.list` and
`client.models.retrieve` take the same arguments as the `openai` package (plus the ultrarouter
extensions) and accept the same per-call options (`timeout`, `max_retries`, `extra_headers`,
`extra_query`, `extra_body`). Responses are typed pydantic models with the `ur` block as a
typed attribute.

```python
from ultrarouter import UltraRouter

client = UltraRouter()
reply = client.chat.completions.create(
    model="openai/gpt-5.2-mini", messages=[{"role": "user", "content": "Hello"}]
)
print(reply.choices[0].message.content, reply.ur.cost_usd)
```

## Option 2: the `openai` package, configured by `as_openai()`

Install the `openai` extra (see [Installation](installation.md#the-openai-extra)), then:

```python
from ultrarouter import UltraRouter

openai_client = UltraRouter().as_openai()
reply = openai_client.chat.completions.create(
    model="openai/gpt-5.2-mini", messages=[{"role": "user", "content": "Hello"}]
)
print(reply.choices[0].message.content)
print(reply.model_extra["ur"]["request_id"])  # the ur block arrives as an extra field
```

`as_openai()` returns `openai.OpenAI(base_url=f"{base_url}/v1", api_key=..., default_headers=...)`
with the client's default headers (including any Bench tag headers). The async client returns an
`openai.AsyncOpenAI`. Pass any callable that accepts those keyword arguments to build something
else instead, such as a test double: `client.as_openai(FakeOpenAI)`.

## Option 3: configure `openai` yourself

Nothing is special about `as_openai()`; this is equivalent:

```python
import os

import openai

manual = openai.OpenAI(
    base_url=os.environ["ULTRAROUTER_BASE_URL"].rstrip("/") + "/v1",
    api_key=os.environ["ULTRAROUTER_API_KEY"],
)
print(manual.models.list().data[0].id)
```

To correlate calls made through the `openai` package (for outcome reporting), mint the request id
up front and send it as a header; `ultrarouter.request_id_of(reply)` reads it back from the `ur`
block the gateway adds:

```python
from ultrarouter import correlation_headers, new_request_id, request_id_of

request_id = new_request_id()
reply = manual.chat.completions.create(
    model="openai/gpt-5.2-mini",
    messages=[{"role": "user", "content": "Hi"}],
    extra_headers=correlation_headers(request_id=request_id),
)
assert request_id_of(reply) == request_id
```

See [Plug-and-play learning](learning.md).

## Migrating from `openai`

| `openai` | `ultrarouter` |
| --- | --- |
| `OpenAI(api_key=...)` | `UltraRouter(api_key=...)` (`ULTRAROUTER_API_KEY`) |
| `OpenAI(base_url=...)` | `UltraRouter(base_url=...)` (`ULTRAROUTER_BASE_URL`; `/v1` optional) |
| `AsyncOpenAI` | `AsyncUltraRouter` |
| `client.chat.completions.create(...)` | same |
| `client.embeddings.create(...)` | same |
| `client.models.list()` / `retrieve(id)` | same |
| `openai.APIError` and subclasses | `ultrarouter.UltraRouterError` and subclasses (`RateLimitError`, `AuthenticationError`, `NotFoundError`, ...) |
| `model="gpt-4o"` | provider-prefixed ids, for example `model="openai/gpt-5.2-mini"` |

Differences to keep in mind:

- Model ids are provider-prefixed. `client.models.list()` shows what is available.
- Errors carry the gateway's stable `code` (for example `model_unpriced`) and `request_id`.
- Responses include `ur` (served model, provider, routing, cost); with the `openai` package it is
  in `model_extra["ur"]`.
- The OpenAI Assistants, Files, Images and Audio APIs are not part of the gateway.
