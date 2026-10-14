# Generation lookup

`client.generation.get(request_id)` (`GET /v1/generation?id=...`) returns the post-hoc record
of one request: tokens, cost, timing, the routing decision (including fallback attempts),
compression details, exposure and any outcomes recorded against it.

```python
from ultrarouter import UltraRouter

client = UltraRouter()
reply = client.chat.completions.create(
    model="openai/gpt-5.2-mini",
    models=["openai/gpt-5.2"],
    messages=[{"role": "user", "content": "Hello"}],
)

stats = client.generation.get(reply.ur.request_id)
print(stats.status, stats.model_requested, stats.model_served, stats.provider)
print(stats.tokens.input, stats.tokens.output, stats.tokens.cached, stats.tokens.total)
print(stats.cost.total_usd, stats.cost.total_micro_usd)
print(stats.timing.ttfb_ms, stats.timing.latency_ms)
print(stats.routing_decision)  # e.g. {"attempts": [...]} when fallbacks were tried
```

| Field | Meaning |
| --- | --- |
| `status` | `ok`, `error` or `cancelled` |
| `error_class` | the error class when the request failed |
| `tokens` | `input`, `output`, `cached`, `total` |
| `cost` | `total_usd` and `total_micro_usd` (integer micro-USD) |
| `timing` | `ttfb_ms` and `latency_ms` |
| `routing_decision` | the routing record, including fallback attempts |
| `compression` | what compression did, if anything |
| `exposure`, `lever` | experiment arm and learned-context details, when applicable |
| `outcomes` | outcome events recorded against the request |

The record is written asynchronously, so a lookup right after the call can raise
`NotFoundError`; retry briefly:

```python
import time

from ultrarouter import NotFoundError


def generation_with_retry(request_id: str, attempts: int = 5):
    for attempt in range(attempts):
        try:
            return client.generation.get(request_id)
        except NotFoundError:
            time.sleep(0.2 * (attempt + 1))
    raise TimeoutError(f"no generation record for {request_id}")


print(generation_with_retry(reply.ur.request_id).status)
```
