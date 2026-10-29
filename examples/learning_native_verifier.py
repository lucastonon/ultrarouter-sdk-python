"""Native SDK plus a real, computable verifier: the answer is checked, not trusted.

The model must return `{"sum": <int>}` for two numbers; the verifier recomputes the sum and the
verdict is reported with `source="verifier"`. A crashed verifier would be `unknown` (nothing sent),
never a `fail`; a malformed answer fails the structured-output validation first.

Run: ULTRAROUTER_API_KEY=... ULTRAROUTER_BASE_URL=... python examples/learning_native_verifier.py

Expected output (mock gateway; its sample JSON is not the right sum, so the verifier fails it):
    model answered: {"sum": ...}
    verifier: fail
    reported: fail via verifier -> computable/oracle_fail, gateway status: pending
"""

from __future__ import annotations

import json
import os

from pydantic import BaseModel

from ultrarouter import UltraRouter
from ultrarouter.adapters import run_verifier, validate_output

MODEL = os.environ.get("ULTRAROUTER_MODEL", "openai/gpt-5.2-mini")
A, B = 17, 25


class Sum(BaseModel):
    """The structured answer."""

    sum: int


def main() -> int:
    with UltraRouter() as client:
        reply = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": f"Add {A} and {B}. Answer as JSON."}],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "sum",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "properties": {"sum": {"type": "integer"}},
                        "required": ["sum"],
                        "additionalProperties": False,
                    },
                },
            },
        )
        raw = reply.choices[0].message.content or ""
        print("model answered:", json.dumps(json.loads(raw)) if raw.startswith("{") else raw)

        parsed = validate_output(raw, Sum)  # malformed output is a fail with reasons
        result = (
            run_verifier(lambda: parsed.value is not None and parsed.value.sum == A + B)
            if parsed.value is not None
            else parsed
        )
        reasons = f" ({'; '.join(result.reasons)})" if result.reasons else ""
        print(f"verifier: {result.verdict}{reasons}")

        report = client.outcomes.report(
            reply.ur.request_id,
            result.verdict,
            source="verifier",
            evidence_hash=parsed.evidence_hash,
        )
    if not report.reported:
        print("reported: nothing (verdict unknown)")
        return 0
    print(
        f"reported: {report.verdict} via {report.source} -> {report.channel}/{report.kind}, "
        f"gateway status: {report.outcome_status}"
    )
    return 0 if report.status == "delivered" else 1


if __name__ == "__main__":
    raise SystemExit(main())
