"""Fetch the active hosted prompt of a call type and render it locally.

Run: ULTRAROUTER_API_KEY=... ULTRAROUTER_BASE_URL=... python examples/hosted_prompt.py
"""

from __future__ import annotations

import os

from ultrarouter import PromptVariablesMissingError, UltraRouter, render_prompt

CALL_TYPE = os.environ.get("ULTRAROUTER_CALL_TYPE", "support-reply")


def main() -> None:
    with UltraRouter() as client:
        prompt = client.get_prompt(CALL_TYPE)
    if prompt is None:
        print(f"{CALL_TYPE} has no active hosted prompt (code-owned)")
        return
    print(f"version {prompt.version}: {prompt.template}")
    print(render_prompt(prompt, {"brand": "Northwind", "tone": "friendly"}))
    try:
        render_prompt(prompt, {})
    except PromptVariablesMissingError as exc:
        print("refused, missing:", exc.missing)


if __name__ == "__main__":
    main()
