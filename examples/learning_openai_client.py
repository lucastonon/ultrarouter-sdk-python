"""Keep your existing OpenAI client; add one header and one outcome report.

The `openai` package talks to the gateway unchanged (base URL + key). Mint the request id before
the call, send it as `x-ur-request-id`, check the answer with your own business rule, and report
the verdict. Needs the `openai` package.

This example resolves or creates order-desk (config:read/write), and sends its slug on every call.
Enable learning separately for its ct_... ID after full workspace learning consent.

Run: ULTRAROUTER_API_KEY=... ULTRAROUTER_BASE_URL=... python examples/learning_openai_client.py

Expected output (mock gateway; ids differ):
    request id: req_c_...  (echoed by the gateway: True)
    verdict: pass (business_rule, teaches: True)
    gateway status: pending
"""

from __future__ import annotations

import os

import openai

from ultrarouter import UltraRouter, correlation_headers, new_request_id, request_id_of
from ultrarouter.adapters import run_verifier

MODEL = os.environ.get("ULTRAROUTER_MODEL", "openai/gpt-5.2-mini")


def main() -> int:
    base_url = os.environ["ULTRAROUTER_BASE_URL"].rstrip("/").removesuffix("/v1")
    chat = openai.OpenAI(base_url=f"{base_url}/v1", api_key=os.environ["ULTRAROUTER_API_KEY"])

    with UltraRouter() as client:
        call_type = next(
            (ct for ct in client.call_types.list().data if ct.slug == "order-desk"), None
        )
        if call_type is None:
            call_type = client.call_types.create(slug="order-desk")

    request_id = new_request_id()  # known before the call, even if the answer is lost
    reply = chat.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": "Write a one-line welcome for a new customer."}],
        extra_body={"call_type": call_type.slug},
        extra_headers=correlation_headers(request_id=request_id),
    )
    chat.close()
    text = reply.choices[0].message.content or ""
    echoed = request_id_of(reply) == request_id
    print(f"request id: {request_id}  (echoed by the gateway: {echoed})")

    # Your business rule: a non-empty, single-line welcome of at most 200 characters.
    result = run_verifier(lambda: 0 < len(text) <= 200 and "\n" not in text, source="business_rule")
    with UltraRouter() as client:
        report = client.outcomes.report(request_id, result.verdict, source=result.source)
    if not report.reported:
        print("verdict: unknown (nothing reported)")
        return 0
    print(f"verdict: {report.verdict} ({report.source}, teaches: {report.teaches})")
    print(f"gateway status: {report.outcome_status}")
    return 0 if report.status == "delivered" else 1


if __name__ == "__main__":
    raise SystemExit(main())
