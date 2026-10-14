# Autopilot

Autopilot is a one-argument way to state how much routing autonomy your application allows:

```python
from ultrarouter import UltraRouter

client = UltraRouter(autopilot="audit")
print(client.autopilot.mode)  # "audit"
```

| Intent | Router mode | Behaviour |
| --- | --- | --- |
| `"audit"` | `off` | observe traffic; always serve the requested model |
| `"recommend"` | `candidates` | rank an approved list of candidate models |
| `"auto"` | `auto` | let the router choose where the gateway allows it |

The intent is a ceiling for the call's `router` parameter: a call may lower autonomy (for
example `router="off"` under `"auto"`) but a request for more is clamped down to the intent.
The gateway enforces the same rule and its own readiness requirements, so `"auto"` expresses what
you allow, not a bypass.

```python
auto = UltraRouter(autopilot="auto")
reply = auto.chat.completions.create(
    model="openai/gpt-5.2-mini",
    router="off",  # this call opts out of routing
    messages=[{"role": "user", "content": "Hi"}],
)
print(reply.ur.routing.mode)
```

## Readiness report

`client.autopilot.status()` (`GET /v1/audit/readiness`) is a read-only report of what the gateway
has observed: per call type, the request count, spend, models and providers seen, lifecycle
state, confidence and the evidence still missing. It changes nothing.

```python
report = client.autopilot.status()
print(report.state, report.total_requests, report.total_spend_micro_usd)
for row in report.call_types:
    print(row.slug, row.lifecycle_state, row.confidence, row.requests, row.evidence_gaps)
```

`report.opportunities` lists candidate model changes as discovery hints; they are estimates
from list prices, not results. Use [Bench](bench.md) or evals to compare candidates on your own
traffic before changing anything.
