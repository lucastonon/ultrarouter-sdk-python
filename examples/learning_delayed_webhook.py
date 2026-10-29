"""A delayed outcome from a signed webhook: verified, deduplicated, reported once.

Your business system learns days later whether the task succeeded and calls your webhook route.
`WebhookOutcomeHandler` verifies the HMAC-SHA256 signature and timestamp, deduplicates on the
event id and reports with `source="webhook"`, and tells you what to answer the sender: 200 for a
report or a redelivery (a no-op), 401/400 for a forged, stale or malformed delivery (nothing is
reported), 503 when the gateway has not acknowledged yet (the sender redelivers). The secret comes
from `ULTRAROUTER_WEBHOOK_SECRET` (this demo generates a throwaway one when it is unset; it is
never printed). The payment event is simulated here; a real sender must derive its verdict from
the authoritative business result.

This example resolves or creates order-desk (config:read/write), and sends its slug on every call.
Enable learning separately for its ct_... ID after full workspace learning consent.

Run: ULTRAROUTER_API_KEY=... ULTRAROUTER_BASE_URL=... python examples/learning_delayed_webhook.py

Expected output (mock gateway):
    first delivery: reported, answer 200 (resolution/resolved_true)
    redelivery: duplicate, answer 200
    forged signature: rejected, answer 401 (bad_signature)
    stale timestamp: rejected, answer 401 (stale_timestamp)
    receipts for the request: 1 (pending)
"""

from __future__ import annotations

import json
import os
import secrets
import time

from ultrarouter import UltraRouter
from ultrarouter.adapters import (
    WEBHOOK_SIGNATURE_HEADER,
    WebhookOutcomeHandler,
    WebhookVerifier,
    sign_webhook,
)

MODEL = os.environ.get("ULTRAROUTER_MODEL", "openai/gpt-5.2-mini")


def main() -> int:
    # Demo only: in production the sender and your app share this secret through configuration.
    os.environ.setdefault("ULTRAROUTER_WEBHOOK_SECRET", secrets.token_hex(32))
    handler = WebhookOutcomeHandler(WebhookVerifier())  # secret from the environment

    with UltraRouter() as client:
        call_type = next(
            (ct for ct in client.call_types.list().data if ct.slug == "order-desk"), None
        )
        if call_type is None:
            call_type = client.call_types.create(slug="order-desk")
        reply = client.chat.completions.create(
            call_type=call_type.slug,
            model=MODEL,
            messages=[{"role": "user", "content": "Draft a refund approval for order A-100."}],
        )
        request_id = reply.ur.request_id

        # ... later, the payment system resolves the refund and calls your webhook route:
        body = json.dumps(
            {"event_id": "evt_refund_A100", "request_id": request_id, "verdict": "pass"}
        )
        headers = sign_webhook(body)

        first = handler.handle(client, body, headers)  # answer the sender first.http_status
        report = first.report
        mapped = f"{report.channel}/{report.kind}" if report and report.reported else "-"
        print(f"first delivery: {first.status}, answer {first.http_status} ({mapped})")
        again = handler.handle(client, body, headers)
        print(f"redelivery: {again.status}, answer {again.http_status}")

        forged = {**headers, WEBHOOK_SIGNATURE_HEADER: "sha256=" + "0" * 64}
        stale = sign_webhook(body, now_s=time.time() - 3600)
        for label, attempt in (("forged signature", forged), ("stale timestamp", stale)):
            refused = handler.handle(client, body, attempt)
            print(f"{label}: {refused.status}, answer {refused.http_status} ({refused.reason})")
            if refused.status != "rejected":
                return 1

        receipts = client.outcomes.receipts_for_request(request_id).data
        statuses = ", ".join(r.status for r in receipts)
        print(f"receipts for the request: {len(receipts)} ({statuses})")
    return 0 if first.status == "reported" and len(receipts) == 1 else 1


if __name__ == "__main__":
    raise SystemExit(main())
