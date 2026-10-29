# Plug-and-play learning

For tools described in prompt text, upload their actual schemas once per call type. Native tool
requests already carry schemas. This replaces the previous set (maximum 256 tools, 1 MiB); an empty
list clears it. Resolve the `ct_…` id with `client.call_types.list()` first.

```python
from ultrarouter import UltraRouter

with UltraRouter() as client:
    ct = client.call_types.list().data[0]
    client.learning.put_tool_documentation(
        ct.id,
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "set_order_status",
                    "parameters": {
                        "type": "object",
                        "properties": {"status": {"enum": ["reserved", "backordered"]}},
                    },
                },
            }
        ],
    )
    print(client.learning.tool_documentation(ct.id).tool_count)
```

The learning loop turns your agent's traffic plus trustworthy outcomes into candidate adaptations
of a call type, evaluates each candidate against the version serving now (the incumbent), and
promotes it only when the evaluation justifies it. Your part is small:

1. **Correlate**: know each call's request id, and group the steps of one task into an episode.
2. **Report outcomes**: say whether the task succeeded (`pass`, `fail` or `unknown`) and where the
   verdict came from. Report the moment you know, even before the gateway has stored the request.
3. **Control learning**: enable it per call type, pause, resume, inspect versions and evaluations,
   roll back.

A working integration (calls correlated, outcomes accepted) is not evidence that learning helps
your agent: that is decided by the evaluations, against the incumbent, on your own traffic.

Every response is a typed model generated from the API specification (`OutcomeReceiptRecord`,
`LearningStatus`, `LearningControl`, ... in `ultrarouter.types`); unknown fields are kept in
`model_extra`.

## Correlation

Every response carries its request id (`reply.ur.request_id`, and the `x-ur-request-id` header).
You can also mint the id yourself before the call, so you know it even if the answer is lost or
still streaming:

```python
from ultrarouter import UltraRouter, new_request_id

client = UltraRouter()
request_id = new_request_id()  # "req_c_" + a ULID; any [A-Za-z0-9_-]{1,64} works
reply = client.chat.completions.create(
    model="openai/gpt-5.2-mini",
    messages=[{"role": "user", "content": "Hi"}],
    request_id=request_id,  # sent as x-ur-request-id
    episode_key="order:A-100",  # sent as X-UR-Artifact
)
assert reply.ur.request_id == request_id
```

`UltraRouter(request_ids="client")` mints an id for every chat and embeddings call that does not
pass one. When a call fails without an answer (a timeout, a dropped connection), the error's
`request_id` is the id you sent.

A stream knows its request id as soon as it opens, from the response header:

```python
with client.chat.completions.create(
    model="openai/gpt-5.2-mini", messages=[{"role": "user", "content": "Hi"}], stream=True
) as stream:
    print(stream.request_id)  # before the first chunk
    stream.text()
```

**Episodes.** A multi-step task (an agent calling tools) is one episode: every step that carries
the same episode key belongs to it, and one terminal verdict covers all of them. Without a key the
gateway groups steps by their opening text, so **two tasks that open with identical text at the
same time must have distinct keys**, or their steps and verdicts are merged. `new_episode_key()`
mints a unique one; your own stable id (`"order:A-100"`) works too. A key is 1 to 256 printable
ASCII characters without leading or trailing spaces; any other key goes in the body as
`ur.artifact`.

`client.episode(key)` does the bookkeeping: each step gets the key and a freshly minted request
id, and `episode.report(...)` reports on the last step:

```python
from ultrarouter import UltraRouter

client = UltraRouter()
with client.episode("order:A-100") as episode:
    episode.chat.completions.create(
        model="openai/gpt-5.2-mini", messages=[{"role": "user", "content": "Process order A-100."}]
    )
    # ... more steps: tool calls and their results ...
    report = episode.report("pass", source="verifier")
print(len(episode.request_ids), report.request_id == episode.last_request_id)
```

**With the `openai` package.** Keep your OpenAI client; pass the correlation headers per call and
read the id back with `request_id_of` (it reads the `ur` block the gateway adds, or the header of
a raw response or stream):

```python
from ultrarouter import UltraRouter, correlation_headers, new_request_id, request_id_of

chat = UltraRouter().as_openai()  # or openai.OpenAI(base_url=".../v1", api_key=...)
request_id = new_request_id()
reply = chat.chat.completions.create(
    model="openai/gpt-5.2-mini",
    messages=[{"role": "user", "content": "Hi"}],
    extra_headers=correlation_headers(request_id=request_id, episode_key="order:A-100"),
)
assert request_id_of(reply) == request_id
```

## Reporting outcomes

`client.outcomes.report(request_id, verdict, source=...)` maps a verdict to an outcome event
through a table both official SDKs share:

| `source` | `pass` | `fail` | Teaches |
| --- | --- | --- | --- |
| `verifier` | `computable` / `oracle_pass` | `computable` / `oracle_fail` | yes |
| `business_rule` | `computable` / `oracle_pass` | `computable` / `oracle_fail` | yes |
| `webhook` | `resolution` / `resolved_true` | `resolution` / `resolved_false` | yes |
| `human_review` | `correction` / `accepted_unchanged` | `correction` / `rejected` | yes |
| `self_rating` | `proxy` / `thumbs` (+1) | `proxy` / `thumbs` (-1) | never |

`verdict="unknown"` sends nothing: missing feedback stays missing. A self-rating is a weak proxy:
it may rank, but it never teaches. The return type says so:

```python
from ultrarouter import (
    NotReportedOutcome,
    ProxyOutcomeReport,
    TeachingOutcomeReport,
    UltraRouter,
)

client = UltraRouter()
reply = client.chat.completions.create(
    model="openai/gpt-5.2-mini", messages=[{"role": "user", "content": "Hi"}]
)
request_id = reply.ur.request_id

checked = client.outcomes.report(request_id, "pass", source="verifier")
assert isinstance(checked, TeachingOutcomeReport) and checked.teaches
print(checked.channel, checked.kind, checked.outcome_status)  # computable oracle_pass pending

liked = client.outcomes.report(request_id, "pass", source="self_rating")
assert isinstance(liked, ProxyOutcomeReport) and not liked.teaches

silent = client.outcomes.report(request_id, "unknown", source="verifier")
assert isinstance(silent, NotReportedOutcome) and silent.status == "not_reported"
```

Optional arguments: `idempotency_key` (distinguishes two genuinely different reports with the
same verdict and source, for example a webhook's event id), `observed_at` (ISO-8601 or a
`datetime`; default: the first time the report is made), `evidence_hash` (a hash of the evidence,
never the evidence) and `supersedes` (the `source_event_id` of an earlier report this one revises).

**Never counted twice.** Each report has a stable identity: its `source_event_id` is
`"rpt_" + sha256("ur-outcome-report/v1\n" + request_id + "\n" + verdict + "\n" + source + "\n" +
(idempotency_key or ""))` (`report_source_event_id`), and it travels through the durable outcome
queue under that identity with a matching `Idempotency-Key`. So:

- a lost acknowledgement is retried with the identical event, which the gateway answers as a
  `duplicate`;
- calling `report` again with the same arguments replays the identical bytes (same
  `observed_at`); concurrent repeats share one send;
- a delivery whose outcome is unknown stays queued (`report.status == "queued"`) for
  `client.outcomes.flush()`;
- the same identity with a different payload is sent as its own entry and refused as a conflict,
  never silently replacing the first.

A report repeated from another process derives the same identity; pass `observed_at` explicitly
when that can happen, so the replay is byte-identical.

```python
first = client.outcomes.report(request_id, "fail", source="human_review", idempotency_key="r-1")
again = client.outcomes.report(request_id, "fail", source="human_review", idempotency_key="r-1")
assert again.source_event_id == first.source_event_id
print(again.outcome_status)  # duplicate
```

## Immediate outcomes and receipts

The gateway records requests asynchronously. An outcome reported before that write lands is
accepted at once with `status: "pending"` and a durable receipt (`ocr_...`), then applied when the
request lands, so you never sleep before reporting. Every answer carries the receipt; a retry with
the same identity returns the same receipt. A receipt moves from `pending` to `applied` (with
`outcome_status` `accepted` or `duplicate`), `rejected` (see `reason`), `failed` (recording kept
hitting an internal error) or `expired` (no such request appeared in your workspace within 15
minutes: `reason` is `request_not_found`). Its `episode` says how an applied teaching outcome
relates to the request's episode: `status` is `associated`, `pending`, `not_recorded` or
`not_applicable`, with the episode's `trace_id` and what the outcome did to its `verdict`
(`recorded`, `kept_earlier`, `revised`, `revised_after_incorporation`).

The report call itself can be refused: a gateway-minted id too old to still be in flight is a 404
(the report comes back `rejected`); the same identity with a different payload is a 409; when the
workspace already holds 5,000 pending receipts the gateway answers 429 `outcome_backlog_full`
(`OutcomeBacklogFullError`) with `Retry-After`, which the SDK honours, and the report stays queued.

```python
from ultrarouter import UltraRouter

client = UltraRouter()
reply = client.chat.completions.create(
    model="openai/gpt-5.2-mini", messages=[{"role": "user", "content": "Say OK."}]
)
report = client.outcomes.report(reply.ur.request_id, "pass", source="verifier")
print(report.is_pending, report.receipt_id)

final = client.outcomes.wait_for_receipt(report, timeout=30)  # bounded backoff polling
print(final.status, final.outcome_status, final.episode.status)

for receipt in client.outcomes.receipts_for_request(reply.ur.request_id).data:
    print(receipt.id, receipt.status)
```

`wait_for_receipt` reads the public receipt endpoint with a doubling interval (0.25 s up to 4 s by
default) for at most `timeout` seconds, retrying transient read failures; on the deadline it raises
`ReceiptWaitTimeoutError` with `receipt_id` and `last_receipt`. The outcome is not lost: the
receipt keeps reconciling on the gateway. On `AsyncUltraRouter` the wait is cancellable:

```python
import asyncio

from ultrarouter import AsyncUltraRouter


async def main() -> None:
    async with AsyncUltraRouter() as client:
        reply = await client.chat.completions.create(
            model="openai/gpt-5.2-mini", messages=[{"role": "user", "content": "Say OK."}]
        )
        report = await client.outcomes.report(reply.ur.request_id, "pass", source="verifier")
        waiting = asyncio.ensure_future(client.outcomes.wait_for_receipt(report))
        waiting.cancel()  # stops at once; the outcome is unaffected
        final = await asyncio.wait_for(client.outcomes.wait_for_receipt(report), timeout=35)
        print(final.status)


asyncio.run(main())
```

## Outcome adapters

`ultrarouter.adapters` turns checks you already have into verdicts, with the same semantics,
reasons and hashes as the TypeScript SDK's `@ultrarouter/sdk/learning` entry. A check that cannot
decide (it crashed, timed out, the process was killed) is `unknown`, never a `fail`. Reasons and
outputs stay local; only the verdict, its source and an optional evidence hash are sent.
`evidence_hash(value)` is `"sha256:"` plus the hex SHA-256 of the canonical JSON of the evidence
(keys sorted, no whitespace, UTF-8).

**A computable check, a command or a test suite** (`source="verifier"`):

```python
import sys

from ultrarouter.adapters import run_test_suite, run_verifier, verdict_from_command

answer = 42
check = run_verifier(lambda: answer == 17 + 25)
print(check.verdict)  # pass

detailed = run_verifier(lambda: {"pass": answer == 41, "evidence": {"answer": answer}})
print(detailed.verdict, detailed.evidence_hash)  # fail sha256:...

suite = run_test_suite([sys.executable, "-c", "raise SystemExit(0)"])  # e.g. ["pytest", "-q"]
print(suite.verdict)  # pass; exit code 1 would be ('fail', ('exit_code_1',))

print(verdict_from_command(None, signal_name="SIGKILL").verdict)  # unknown
```

A check returns `True` / `False`, or `{"pass": bool, "evidence": ..., "reasons": [...]}`. One that
raises is `unknown` (`verifier_error`) unless `on_error="fail"`; a failing `assert` is always a
`fail` (`check_threw`). A command passes on exit code 0 and fails on any other (list "could not
decide" codes in `unknown_codes`, such as pytest's 5).

**Structured output and business rules** (`source="business_rule"`), with pydantic. A validator
always decides, so the verdict is `pass` or `fail`:

```python
from pydantic import BaseModel

from ultrarouter.adapters import validate_output


class Refund(BaseModel):
    order_id: str
    amount: float


result = validate_output(
    '{"order_id": "A-100", "amount": -5}',
    Refund,
    rules={
        "amount is positive": lambda refund: refund.amount > 0,
        "known order": lambda refund: True if refund.order_id.startswith("A-") else "unknown order",
    },
)
print(result.verdict, result.reasons)  # fail ('amount is positive',)
```

Output that is not JSON fails with `invalid_json`; a field problem gives `"$.<field>: <message>"`;
a rule returning `False` gives its name, a rule returning a string `"<name>: <string>"`, a rule that
raises `"<name>: <exception class>"`. Reasons never quote the output's values. Report either
result with `client.outcomes.report(request_id, result.verdict, source=result.source,
evidence_hash=result.evidence_hash)`.

**A signed, delayed webhook** (`source="webhook"`). When a business system learns the outcome later
(a refund settled, a ticket reopened), it calls your webhook route. The sender signs
`"<timestamp>.<raw body>"` with HMAC-SHA256 under a shared secret and sends
`x-webhook-signature: sha256=<hex>` and `x-webhook-timestamp` (Unix seconds); `sign_webhook`
builds them. `WebhookOutcomeHandler` checks, in order: both headers present and well formed, the
timestamp within ±300 s, the signature in constant time (`hmac.compare_digest`; several secrets
are accepted for rotation), then the payload (`event_id`, `request_id`, `verdict`, optional
`observed_at` and `evidence_hash`). It claims the `event_id` in a `DedupeStore` (in memory by
default, held 7 days; back it with a unique database row to share it across processes) and
reports once, with the event id as the `idempotency_key`. The secret comes from
`ULTRAROUTER_WEBHOOK_SECRET` (or `secret=`) and is never logged.

```python
import json
import time

from ultrarouter import UltraRouter
from ultrarouter.adapters import WebhookOutcomeHandler, WebhookVerifier, sign_webhook

secret = "demo-only-secret"  # in production: WebhookVerifier() reads ULTRAROUTER_WEBHOOK_SECRET
handler = WebhookOutcomeHandler(WebhookVerifier(secret))
client = UltraRouter()

# What the business system sends:
body = json.dumps({"event_id": "evt_42", "request_id": "req_c_example", "verdict": "fail"})
headers = sign_webhook(body, secret=secret, now_s=time.time())

first = handler.handle(client, body, headers)
print(first.status, first.http_status)  # reported 200
again = handler.handle(client, body, headers)
print(again.status, again.http_status)  # duplicate 200: a redelivery is a no-op
```

Answer the sender with `result.http_status`:

| `status` | `http_status` | Meaning |
| --- | --- | --- |
| `reported` | 200 | reported with `source="webhook"` (an `unknown` verdict reports nothing) |
| `duplicate` | 200 | this event id was already handled |
| `rejected` | 401 / 400 | refused before anything was reported; `reason` is `missing_signature`, `missing_timestamp`, `malformed_signature`, `malformed_timestamp`, `stale_timestamp`, `bad_signature` or `malformed_payload` (400) |
| `deferred` | 503 | the gateway has not acknowledged the report yet; the claim was released so the sender's redelivery reports again, under the same identity |

When the payload has no `observed_at`, the signed timestamp is used, so processes racing on one
delivery send byte-identical events. Use `ahandle` with `AsyncUltraRouter`, and `parse=` for
another payload shape; `WebhookVerifier.verify(body, headers)` alone raises a
`WebhookVerificationError` subclass (with `reason`) for a refused delivery.

## Learning controls

`client.learning` steers learning for one call type at a time (reads need `config:read`, controls
`config:write`; manual promote and reject need an owner or admin). Every control returns a
`LearningControl`: the `action`, whether it `changed` anything (controls are idempotent), the
version it acted on, an evaluation it stopped, and the resulting `learning` status.

Before enabling learning, an owner or admin must grant the workspace's full self-learning
opt-in: **knowledge and corrections consent**. Use the dashboard Learning page or a signed-in
session calling `PUT /v1/workspaces/{id}/self-learning` with `{"enabled":true}`. An API key
cannot grant consent, and corrections consent alone is insufficient. The reflection model must
resolve to a workspace-owned provider; learning has no platform or paid fallback.

```python
from ultrarouter import UltraRouter

client = UltraRouter()
learning = client.learning
call_type = next((ct for ct in client.call_types.list().data if ct.slug == "support-reply"), None)
if call_type is None:
    call_type = client.call_types.create(slug="support-reply")
call_type_id = call_type.id  # learning endpoints require the ct_… id, not the slug

control = learning.enable(
    call_type_id,
    reflection_model="openai/gpt-5.2-mini",  # must resolve to a workspace-owned offer
    promotion={"mode": "evaluate", "objective": "success", "min_verified_per_arm": 30},
    recipe={"validator": "elv2", "generation": "atomic", "observations": "elo2"},
)
status = control.learning
print(status.state, status.reason, status.active_version.id if status.active_version else None)

learning.pause(call_type_id)  # stop reflecting and deciding; the active version keeps serving
learning.resume(call_type_id)

for version in learning.versions(call_type_id).data:
    print(version.id, version.version, version.state)
detail = learning.version(call_type_id, "epb_3")  # lessons, reflection receipt, transitions
for evaluation in learning.evaluations(call_type_id).data:
    print(evaluation.id, evaluation.decision, evaluation.arms.candidate.verified)

learning.promote(call_type_id, "epb_3")  # an owner/admin decision; a running evaluation stops
learning.rollback(call_type_id, version_id="epb_1")  # point the active version at an earlier one
learning.disable(call_type_id)  # stop serving learned lessons (the kill switch)
```

`status(...)` reports the `state` with a `reason`: `off`, `collecting` (enabled, waiting for
evidence), `learning` (a reflection is due or an evaluation runs), `paused`, `disabled`,
`unavailable` (no workspace-owned reflection provider; `reflection.provider.reason` says why),
`quota_exhausted` or `budget_exhausted`; a stopped learner always says why. It also carries the
active version and the latest candidate, the running and the latest evaluation (frozen rule,
arms, the interval on the difference, the decision), the promotion policy, the learner recipe,
the `evidence` (recorded, verified pass / fail, unknown, consumed, incorporated by the active
version, backlog), the `outcome_receipts` by state, the `budget` and the subscription `usage`
(recorded apart from cash). With promotion mode `evaluate` a candidate becomes active only by
winning a prospective randomized evaluation against the incumbent; every other decision keeps
the incumbent.

The gateway names each refusal with a code at the start of its message
(`corrections_consent_required: ...`, `promotion_invalid (alpha_range)`). The SDK raises an
actionable `LearningError` subclass (the TypeScript SDK's vocabulary) whose `reason` names the
problem, `refusal` the gateway's named refusal (else the error code), `detail` the sub-reason in
parentheses, and `action` (also appended to the message) what to do:

| Exception | `reason` | Gateway refusal |
| --- | --- | --- |
| `LearningConsentRequiredError` | `missing_consent` | 409 `corrections_consent_required` |
| `LearningProviderUnavailableError` | `provider_unavailable` | 400 `reflection_model_not_workspace_owned (<detail>)`: `no_offer`, `platform_offer_only`, `no_workspace_key`, `model_denied_by_policy`, `workspace_funding_not_byok` or `workspace_funding_frozen` |
| `LearningPolicyInvalidError` | `invalid_promotion` | 400 `promotion_invalid (<field>)` |
| `LearningNotEnabledError` | `not_enabled` | 409 `learning_not_enabled` |
| `LearningVersionConflictError` | `version_conflict` | 409 `version_already_active` (promote), `version_active` (reject: roll back instead), `no_rollback_target` / `rollback_target_not_earlier` (rollback) |
| `LearningQuotaExhaustedError` | `quota_exhausted` | the learning provider refused for quota |
| `LearningBudgetExhaustedError` | `budget_exhausted` | the learning budget is spent |
| `LearningNotFoundError` (also a `NotFoundError`) | `not_found` | 404 `not_found`: unknown call type or version |
| `LearningForbiddenError` (also a `PermissionDeniedError`) | `forbidden` | 403 `permission`: the key lacks the scope |

```python
from ultrarouter import LearningError, UltraRouter

client = UltraRouter()
try:
    client.learning.status("ct_missing")
except LearningError as exc:
    print(exc.reason, "->", exc.action)
```

`client.call_types.episode_memory` (`get`, `enable`, `disable`) reads and switches the lower-level
episode-memory setting learning writes; `enable` there is a lab-authorised lever, so use
`client.learning.enable` for learning.

## A demonstration environment

`ultrarouter.demo.OrderDesk` is a small, deterministic tool environment (an order desk with
stock, orders and four tools) whose exact rules and verifier come from a fixture shared byte for
byte with the TypeScript SDK; tool results, verifier reasons and evidence hashes are identical in
both. It exists to show the loop working end to end; **it is a demonstration, not evidence that
learning improves an agent**.

```python
from ultrarouter.demo import NOTICE, OrderDesk

desk = OrderDesk("s3")  # "Process orders C-300 and C-301." with 4 units for 6 ordered
print(desk.task, [tool["function"]["name"] for tool in desk.tools])
print(
    desk.call("check_stock", {"sku": "SKU-GREEN"})
)  # {'ok': True, 'sku': 'SKU-GREEN', 'in_stock': 4}
print(desk.verify().verdict)  # fail: nothing done yet
desk.solve()  # the deterministic reference procedure, no model
print(desk.verify().verdict)  # pass
print(NOTICE)
```

The tools answer `{"ok": false, "error": ...}` with `UNKNOWN_ORDER`, `UNKNOWN_SKU`,
`SKU_MISMATCH`, `ALREADY_RESERVED`, `INSUFFICIENT_STOCK` (with `in_stock`), `INVALID_ARGUMENTS`
or `UNKNOWN_TOOL`, and an error changes nothing. As in JSON Schema, `"quantity": 2.0` is the
integer 2, while `2.5`, `true` and `"2"` are `INVALID_ARGUMENTS`. The verifier handles orders in the order the
task names them: each must end `reserved` with its full quantity if the stock left covered it,
otherwise `backordered` with nothing reserved, and each SKU's final stock must equal its starting
stock minus what was reserved for it.

Hand `desk.tools` to `chat.completions.create(tools=...)`, run each tool call with
`desk.tool_message(call)`, then report `desk.verify()` on the episode's last step; see
`examples/learning_tool_episode.py`.

## Examples

Runnable scripts (each takes `ULTRAROUTER_API_KEY` and `ULTRAROUTER_BASE_URL`, prints a short
result and exits non-zero on failure):

| Script | Shows |
| --- | --- |
| [`learning_openai_client.py`](../examples/learning_openai_client.py) | the `openai` package unchanged, plus a minted request id and an outcome report |
| [`learning_native_verifier.py`](../examples/learning_native_verifier.py) | the native SDK with a real, computable verifier |
| [`learning_tool_episode.py`](../examples/learning_tool_episode.py) | a multi-step tool episode, correlated, with one terminal verdict |
| [`learning_immediate_outcome.py`](../examples/learning_immediate_outcome.py) | reporting at once (pending receipt), then following the receipt |
| [`learning_delayed_webhook.py`](../examples/learning_delayed_webhook.py) | a signed delayed webhook: deduplicated, refused when forged or stale |
| [`learning_ack_loss.py`](../examples/learning_ack_loss.py) | a lost acknowledgement and a repeated report, recorded once |
| [`learning_controls.py`](../examples/learning_controls.py) | enable, pause, resume, versions, evaluations, rollback, typed errors |
| [`learning_async.py`](../examples/learning_async.py) | the async client, with a cancellable receipt wait |
