# Tools (function calling)

Tools use the OpenAI format: describe functions in `tools`, let the model choose with
`tool_choice`, run the function yourself, and send the result back as a `tool` message.

```python
import json

from ultrarouter import UltraRouter

client = UltraRouter()

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_order_status",
            "description": "Look up the shipping status of an order.",
            "parameters": {
                "type": "object",
                "properties": {"order_id": {"type": "string"}},
                "required": ["order_id"],
            },
        },
    }
]

messages = [{"role": "user", "content": "Where is order 1001?"}]
first = client.chat.completions.create(
    model="openai/gpt-5.2-mini", messages=messages, tools=tools, tool_choice="auto"
)
message = first.choices[0].message
print(first.choices[0].finish_reason)  # "tool_calls"
```

`message.tool_calls` is a list of plain dicts in the OpenAI shape
(`{"id", "type": "function", "function": {"name", "arguments"}}`); `arguments` is a JSON string.

```python
def get_order_status(order_id: str) -> dict[str, str]:
    return {"order_id": order_id, "status": "shipped"}


messages.append({"role": "assistant", "content": message.content, "tool_calls": message.tool_calls})
for call in message.tool_calls or []:
    arguments = json.loads(call["function"]["arguments"])
    result = get_order_status(**arguments)
    messages.append({"role": "tool", "tool_call_id": call["id"], "content": json.dumps(result)})

final = client.chat.completions.create(model="openai/gpt-5.2-mini", messages=messages, tools=tools)
print(final.choices[0].message.content)
```

`tool_choice` accepts `"auto"`, `"none"`, `"required"` or `{"type": "function", "function":
{"name": "get_order_status"}}`.

If the selected model cannot use tools, the gateway refuses before calling it and the SDK raises
`CapabilityUnsupportedError` (code `capability_unsupported`) naming the missing capability; it
does not silently switch models.

## Streaming tool calls

When streaming, tool calls arrive in fragments on `choice.delta.tool_calls`
([`ChunkDeltaToolCall`](types-reference.md#chunkdeltatoolcall)); the first fragment of each call
carries its `id` and `function.name`, later fragments append to `function.arguments`.

```python
calls: dict[int, dict[str, str]] = {}
stream = client.chat.completions.create(
    model="openai/gpt-5.2-mini",
    messages=[{"role": "user", "content": "Where is order 1001?"}],
    tools=tools,
    stream=True,
)
for chunk in stream:
    for choice in chunk.choices:
        for fragment in choice.delta.tool_calls or []:
            entry = calls.setdefault(fragment.index, {"id": "", "name": "", "arguments": ""})
            entry["id"] = fragment.id or entry["id"]
            if fragment.function is not None:
                entry["name"] = fragment.function.name or entry["name"]
                entry["arguments"] += fragment.function.arguments or ""

for call in calls.values():
    print(call["name"], json.loads(call["arguments"]))
```
