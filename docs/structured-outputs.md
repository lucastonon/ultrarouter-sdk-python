# Structured outputs

Ask for JSON with `response_format`. Two forms are supported:

- `{"type": "json_object"}`: any valid JSON object;
- `{"type": "json_schema", "json_schema": {"name": ..., "schema": {...}}}`: JSON that follows
  your schema.

```python
import json

from ultrarouter import UltraRouter

client = UltraRouter()

response_format = {
    "type": "json_schema",
    "json_schema": {
        "name": "ticket_triage",
        "schema": {
            "type": "object",
            "properties": {
                "category": {"type": "string", "enum": ["billing", "shipping", "other"]},
                "urgent": {"type": "boolean"},
            },
            "required": ["category", "urgent"],
        },
    },
}

reply = client.chat.completions.create(
    model="openai/gpt-5.2-mini",
    messages=[{"role": "user", "content": "My package never arrived and I need it today."}],
    response_format=response_format,
)
data = json.loads(reply.choices[0].message.content or "{}")
print(data["category"], data["urgent"])
```

## Parsing into pydantic

Validate the content with your own pydantic model to get typed data and a clear error when the
output does not match:

```python
from typing import Literal

from pydantic import BaseModel


class Triage(BaseModel):
    category: Literal["billing", "shipping", "other"]
    urgent: bool


triage = Triage.model_validate_json(reply.choices[0].message.content or "{}")
print(triage.category)
```

You can generate the schema from the model instead of writing it by hand:

```python
schema_format = {
    "type": "json_schema",
    "json_schema": {"name": "triage", "schema": Triage.model_json_schema()},
}
reply = client.chat.completions.create(
    model="openai/gpt-5.2-mini",
    messages=[{"role": "user", "content": "Refund my double charge."}],
    response_format=schema_format,
)
print(Triage.model_validate_json(reply.choices[0].message.content or "{}"))
```

## When the model cannot do it

If the selected model does not support the requested format, the gateway refuses before calling
it and the SDK raises `CapabilityUnsupportedError`. It never downgrades the format silently. Pick
a model whose `capabilities` (from `client.models.retrieve(model_id)`) include structured output.
