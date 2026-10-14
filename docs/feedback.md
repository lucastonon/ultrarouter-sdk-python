# Feedback

Attach a thumbs-up (`1`) or thumbs-down (`-1`) to a served request, with optional tags and a
comment. Use the request id from `response.ur.request_id`.

```python
from ultrarouter import UltraRouter

client = UltraRouter()
reply = client.chat.completions.create(
    model="openai/gpt-5.2-mini", messages=[{"role": "user", "content": "Summarize my invoice."}]
)

feedback = client.requests.feedback(
    reply.ur.request_id,
    rating=-1,
    tags=["wrong-total"],
    comment="The total did not include tax.",
)
print(feedback.id, feedback.rating, feedback.tags, feedback.created_at)
```

`POST /v1/requests/{id}/feedback` answers with `{"feedback": {...}}`; the SDK unwraps it and
returns the [`Feedback`](types-reference.md#feedback) record.

Feedback is a lightweight signal attached to one request. To record what happened to the thing
your application produced (accepted, edited, resolved later), use
[Outcomes and artifacts](outcomes.md), which also supports delayed and batched events.

The request row is written asynchronously after the response; feedback sent immediately after
the call can briefly raise `NotFoundError`. Retry after a short delay in that case.

```python
import asyncio

from ultrarouter import AsyncUltraRouter


async def rate(request_id: str) -> None:
    async with AsyncUltraRouter() as client:
        await client.requests.feedback(request_id, rating=1)


asyncio.run(rate(reply.ur.request_id))
```
