"""A lost acknowledgement and a repeated report never count twice.

A transport wrapper lets the first outcome request reach the gateway, then drops its answer (as a
network failure after the gateway processed it would). The SDK retries the identical event with
the same Idempotency-Key; the gateway recognises it. Reporting the same verdict again (an
application-level retry) derives the same event identity too. In the end the request has exactly
one outcome.

The verifier requires the trimmed answer to equal OK; a non-empty wrong answer fails.

This example resolves or creates order-desk (config:read/write), and sends its slug on every call.
Enable learning separately for its ct_... ID after full workspace learning consent.

Run: ULTRAROUTER_API_KEY=... ULTRAROUTER_BASE_URL=... python examples/learning_ack_loss.py

Expected output (mock gateway):
    acknowledgement lost once; the SDK retried
    first report: delivered, gateway status duplicate
    repeated report: same event True
    outcomes recorded for the request: 1
"""

from __future__ import annotations

import os

import httpx

from ultrarouter import UltraRouter

MODEL = os.environ.get("ULTRAROUTER_MODEL", "openai/gpt-5.2-mini")


class DropFirstOutcomeAck(httpx.BaseTransport):
    """Forward every request; lose the answer to the first outcome report after it was processed."""

    def __init__(self) -> None:
        self._inner = httpx.HTTPTransport()
        self.dropped = 0

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        response = self._inner.handle_request(request)
        if self.dropped == 0 and request.url.path.endswith("/outcomes"):
            response.read()
            response.close()
            self.dropped += 1
            raise httpx.ReadError("connection lost after the gateway processed the report")
        return response

    def close(self) -> None:
        self._inner.close()


def main() -> int:
    transport = DropFirstOutcomeAck()
    with httpx.Client(transport=transport) as http, UltraRouter(http_client=http) as client:
        call_type = next(
            (ct for ct in client.call_types.list().data if ct.slug == "order-desk"), None
        )
        if call_type is None:
            call_type = client.call_types.create(slug="order-desk")
        reply = client.chat.completions.create(
            call_type=call_type.slug, model=MODEL, messages=[{"role": "user", "content": "Say OK."}]
        )
        request_id = reply.ur.request_id
        verdict = "pass" if (reply.choices[0].message.content or "").strip() == "OK" else "fail"
        first = client.outcomes.report(request_id, verdict, source="verifier")
        if transport.dropped == 1:
            print("acknowledgement lost once; the SDK retried")
        print(f"first report: {first.status}, gateway status {first.outcome_status}")

        again = client.outcomes.report(request_id, verdict, source="verifier")
        print(f"repeated report: same event {again.source_event_id == first.source_event_id}")

        receipts = client.outcomes.receipts_for_request(request_id).data
        print(f"outcomes recorded for the request: {len(receipts)}")
    return 0 if transport.dropped == 1 and len(receipts) == 1 else 1


if __name__ == "__main__":
    raise SystemExit(main())
