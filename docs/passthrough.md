# Native passthrough: the official OpenAI and Anthropic SDKs through your gateway

The gateway exposes two routes that forward a provider request **verbatim** and return the
provider response **unchanged**:

- `POST /v1/responses` — the OpenAI **Responses API**;
- `POST /v1/messages` — the Anthropic **Messages API**.

The JSON body is passed through untouched (no routing, no compression, no model remapping, no
field injection); the gateway meters the call, applies your spend caps and captures it, then hands
back the provider's own object. The model id in the body is the model that is called, so it is the
provider's native id (`gpt-6-sol`, `claude-opus-5-5`), not a provider-prefixed ultrarouter id.

The intended client for these routes is the **official** `openai` and `anthropic` SDK: point it at
the gateway by changing only the base URL and the key. You can also reach them from this SDK's raw
request surface (below).

## Point the official SDK at the gateway

Each official SDK reads a base-URL environment variable. Set it to your gateway (no trailing path
for Anthropic; the OpenAI SDK expects the `/v1` suffix), and put your ultrarouter key where that
SDK puts the provider key:

```bash
# OpenAI SDK -> gateway (ultrarouter key travels as Authorization: Bearer)
export OPENAI_BASE_URL="http://localhost:8080/v1"      # or https://gateway.example.com/v1
export OPENAI_API_KEY="ur_sk_live_your_key"

# Anthropic SDK -> gateway (ultrarouter key travels as x-api-key)
export ANTHROPIC_BASE_URL="http://localhost:8080"      # or https://gateway.example.com
export ANTHROPIC_API_KEY="ur_sk_live_your_key"
```

Key placement: the OpenAI SDK sends the key as `Authorization: Bearer`; the Anthropic SDK sends it
as `x-api-key`. The gateway accepts the ultrarouter key either way (`Authorization: Bearer` **or**
`x-api-key`). Your own provider key is never forwarded upstream — the platform or BYOK key is
injected server-side.

With the environment set, the official SDKs call the gateway with no code change:

<!-- doctest: skip — the official openai and anthropic packages are not dependencies of this SDK; this block shows the call shape -->
```python
from anthropic import Anthropic
from openai import OpenAI

# OpenAI Responses API, forwarded verbatim through the gateway:
openai_client = OpenAI()  # reads OPENAI_BASE_URL and OPENAI_API_KEY
response = openai_client.responses.create(model="gpt-6-sol", input="Summarise this ticket.")

# Anthropic Messages API, forwarded verbatim through the gateway:
anthropic_client = Anthropic()  # reads ANTHROPIC_BASE_URL and ANTHROPIC_API_KEY
message = anthropic_client.messages.create(
    model="claude-opus-5-5",
    max_tokens=256,
    messages=[{"role": "user", "content": "Summarise this ticket."}],
)
```

## The ur extension headers

The ultrarouter extensions ride **request headers** so the body stays a pristine provider payload.
Pass them through the official SDK's per-request `extra_headers` (or `default_headers`):

| Request header | Purpose |
| --- | --- |
| `X-UR-Call-Type` | The call-type stage this call belongs to. |
| `X-UR-Trace` | JSON `{"run", "case", "stage", "attempt"}` tying the call to a run. |
| `X-UR-Timeout-Ms` | Upstream timeout in milliseconds, clamped to 1 s–600 s (default 300 s). |

Every non-streaming passthrough response carries two **response headers**:

| Response header | Purpose |
| --- | --- |
| `X-UR-Request-Id` | The ultrarouter request id; keep it for feedback, stats and support. |
| `X-UR-Cost-Micro-USD` | The booked cost of the call, in integer micro-USD. |

When the request sets `stream: true`, the upstream SSE bytes are forwarded frame by frame.

## Reach the passthrough routes from this SDK

The typed methods of `UltraRouter` do not wrap these routes (the whole point is to forward an opaque
body), but the client's raw request surface does. Build an
[`APIRequest`](api-reference.md#apirequest) and call `request` for the raw response (so you can read
the `X-UR-*` headers), `request_json` for the decoded body, or `request_model` to validate it into
a type. The SDK still adds authentication, the deadline, retries and the idempotency key for you.

```python
from ultrarouter import APIRequest, UltraRouter

client = UltraRouter()  # reads ULTRAROUTER_API_KEY and ULTRAROUTER_BASE_URL

response = client.request(
    APIRequest(
        "POST",
        "/v1/responses",
        body={"model": "gpt-6-sol", "input": "Summarise this ticket."},
        headers={
            "X-UR-Call-Type": "support-reply",
            "X-UR-Trace": '{"run": "r-7", "case": "c-3", "stage": "draft", "attempt": 1}',
            "X-UR-Timeout-Ms": "30000",
        },
    )
)
request_id = response.headers["X-UR-Request-Id"]
cost_micro_usd = int(response.headers["X-UR-Cost-Micro-USD"])
responses_object = response.json()  # the OpenAI Responses object, unchanged
print(request_id, cost_micro_usd, responses_object["output"][0]["content"][0]["text"])
client.close()
```

The Anthropic Messages route works the same way; `request_json` returns the decoded body:

```python
from ultrarouter import APIRequest, UltraRouter

client = UltraRouter()
message = client.request_json(
    APIRequest(
        "POST",
        "/v1/messages",
        body={
            "model": "claude-opus-5-5",
            "max_tokens": 256,
            "messages": [{"role": "user", "content": "Summarise this ticket."}],
        },
        headers={"X-UR-Call-Type": "support-reply"},
    )
)
print(message["role"], message["stop_reason"], message["content"][0]["text"])
client.close()
```

`AsyncUltraRouter` has the same `request`, `request_json` and `request_model` methods; `await` them.
A non-`None` `body` is sent as JSON automatically, so you rarely set `has_body` yourself.
