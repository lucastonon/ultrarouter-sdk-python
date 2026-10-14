"""Ask for JSON that follows a schema and validate it with pydantic.

Run: ULTRAROUTER_API_KEY=... ULTRAROUTER_BASE_URL=... python examples/structured_output.py
"""

from __future__ import annotations

import os
from typing import Literal

from pydantic import BaseModel

from ultrarouter import UltraRouter

MODEL = os.environ.get("ULTRAROUTER_MODEL", "openai/gpt-5.2-mini")


class Triage(BaseModel):
    """The structured answer we want back."""

    category: Literal["billing", "shipping", "other"]
    urgent: bool


def main() -> None:
    with UltraRouter() as client:
        reply = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": "I was charged twice for the same order!"}],
            response_format={
                "type": "json_schema",
                "json_schema": {"name": "triage", "schema": Triage.model_json_schema()},
            },
        )
    triage = Triage.model_validate_json(reply.choices[0].message.content or "{}")
    print(triage)


if __name__ == "__main__":
    main()
