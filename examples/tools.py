"""Call a function tool and send its result back to the model.

Run: ULTRAROUTER_API_KEY=... ULTRAROUTER_BASE_URL=... python examples/tools.py
"""

from __future__ import annotations

import json
import os
from typing import Any

from ultrarouter import UltraRouter

MODEL = os.environ.get("ULTRAROUTER_MODEL", "openai/gpt-5.2-mini")

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Current weather for a city.",
            "parameters": {
                "type": "object",
                "properties": {"city": {"type": "string"}},
                "required": ["city"],
            },
        },
    }
]


def get_weather(city: str) -> dict[str, Any]:
    """A stand-in for a real weather lookup."""
    return {"city": city, "temp_c": 21, "conditions": "sunny"}


def main() -> None:
    messages: list[dict[str, Any]] = [{"role": "user", "content": "What's the weather in Lisbon?"}]
    with UltraRouter() as client:
        first = client.chat.completions.create(model=MODEL, messages=messages, tools=TOOLS)
        message = first.choices[0].message
        if not message.tool_calls:
            print(message.content)
            return
        messages.append(
            {"role": "assistant", "content": message.content, "tool_calls": message.tool_calls}
        )
        for call in message.tool_calls:
            result = get_weather(**json.loads(call["function"]["arguments"]))
            messages.append(
                {"role": "tool", "tool_call_id": call["id"], "content": json.dumps(result)}
            )
        final = client.chat.completions.create(model=MODEL, messages=messages, tools=TOOLS)
    print(final.choices[0].message.content)


if __name__ == "__main__":
    main()
