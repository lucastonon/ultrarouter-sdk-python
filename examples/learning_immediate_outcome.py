"""Report the outcome the moment you have the answer: no sleep, no waiting for persistence.

The gateway writes request logs asynchronously. An outcome reported before that write lands is
accepted at once as `pending` with a durable receipt and applied when the request lands. This
example reports immediately, then follows the receipt (bounded polling of the public receipt
endpoint) to its final state.

Run: ULTRAROUTER_API_KEY=... ULTRAROUTER_BASE_URL=... python examples/learning_immediate_outcome.py

Expected output (mock gateway; ids differ):
    request: req_...
    reported at once: gateway status pending, receipt ork_...
    receipt final: applied (episode: not_applicable)
"""

from __future__ import annotations

import os

from ultrarouter import ReceiptWaitTimeoutError, UltraRouter

MODEL = os.environ.get("ULTRAROUTER_MODEL", "openai/gpt-5.2-mini")


def main() -> int:
    with UltraRouter() as client:
        reply = client.chat.completions.create(
            model=MODEL, messages=[{"role": "user", "content": "Say OK."}]
        )
        request_id = reply.ur.request_id
        print("request:", request_id)
        ok = (reply.choices[0].message.content or "").strip() != ""
        report = client.outcomes.report(request_id, "pass" if ok else "fail", source="verifier")
        if report.status != "delivered":
            print(f"not delivered ({report.status}): {report.error}")
            return 1
        print(f"reported at once: gateway status {report.outcome_status},", end=" ")
        print(f"receipt {report.receipt_id}")
        if report.receipt_id is None:
            return 0  # an older gateway that answers without receipts
        try:
            final = client.outcomes.wait_for_receipt(report, timeout=30)
        except ReceiptWaitTimeoutError as exc:
            print(f"still pending after the wait: {exc.receipt_id} (it keeps reconciling)")
            return 1
    print(f"receipt final: {final.status} (episode: {final.episode})")
    return 0 if final.status == "applied" else 1


if __name__ == "__main__":
    raise SystemExit(main())
