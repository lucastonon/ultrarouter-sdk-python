"""Use the official openai package against the gateway via as_openai().

Needs the extra: pip install "ultrarouter[openai]".
Run: ULTRAROUTER_API_KEY=... ULTRAROUTER_BASE_URL=... python examples/openai_dropin.py
"""

from __future__ import annotations

import os

from ultrarouter import UltraRouter

MODEL = os.environ.get("ULTRAROUTER_MODEL", "openai/gpt-5.2-mini")


def main() -> None:
    openai_client = UltraRouter().as_openai()
    reply = openai_client.chat.completions.create(
        model=MODEL, messages=[{"role": "user", "content": "Say hello from the openai package."}]
    )
    print(reply.choices[0].message.content)
    print("ur block:", (reply.model_extra or {}).get("ur", {}).get("request_id"))
    openai_client.close()


if __name__ == "__main__":
    main()
