"""Record what happened after an answer: artifacts, outcome events and the edited final.

Run: ULTRAROUTER_API_KEY=... ULTRAROUTER_BASE_URL=... python examples/outcomes.py
"""

from __future__ import annotations

import os

from ultrarouter import UltraRouter, diff_stats

MODEL = os.environ.get("ULTRAROUTER_MODEL", "openai/gpt-5.2-mini")


def main() -> None:
    with UltraRouter() as client:
        # Bind the generation to an artifact and record an outcome on it.
        with client.with_artifact("ticket:4812:reply") as scope:
            draft = scope.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "user", "content": "Draft a short apology for a late delivery."}
                ],
            )
            receipt = scope.record({"channel": "behavioral", "kind": "accepted"})
            print("outcome:", receipt.status)

            # The agent edited the draft before sending: report the edit without the text.
            draft_text = draft.choices[0].message.content or ""
            final_text = draft_text + " We have added a discount to your account."
            stats = diff_stats(draft_text, final_text)
            version = scope.final(diff_stats=stats, final_hash=stats["final_hash"])
            print("final stored as:", version.stored, "edit ratio:", round(stats["edit_ratio"], 3))

        # A delayed outcome, days later, against the request id.
        client.outcomes.record(
            {"request": draft.ur.request_id},
            {"channel": "resolution", "kind": "resolved", "value": {"customer_replied": True}},
        )
        report = client.outcomes.flush()
        print(f"delivered={report.delivered} pending={report.pending}")


if __name__ == "__main__":
    main()
