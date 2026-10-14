# Call types

A *call type* groups requests that do the same job (for example `support-reply` or
`ticket-classifier`). Routing configuration, evals, recommendations, hosted prompts and
learned context are all attached to a call type. Send `call_type="<slug>"` on requests (or set it
in the client `defaults`) to attribute traffic.

Reading call types needs a key with `config:read`; changing them needs `config:write`.

## Create, list, get

```python
from ultrarouter import UltraRouter

client = UltraRouter()

created = client.call_types.create(
    slug="support-reply",
    config={"model_pin": "openai/gpt-5.2-mini", "fallbacks": ["openai/gpt-5.2"]},
)
print(created.id, created.slug, created.lifecycle_state)

for call_type in client.call_types.list().data:
    print(call_type.slug, call_type.current_config_version)

same = client.call_types.get("support-reply")  # by slug or by id
print(same.config.model_pin if same.config else None)
```

## Update the configuration

`update` writes a new configuration version. Only the arguments you pass are sent; for
`model_pin`, `router_mode`, `compression_mode` and `provider_prefs`, passing `None` clears the
setting.

```python
updated = client.call_types.update(
    "support-reply",
    router_mode="candidates",
    compression_mode="off",
    fallbacks=["openai/gpt-5.2"],
)
cleared = client.call_types.update("support-reply", model_pin=None)  # unpin the model
print(updated.config.version if updated.config else None)
```

| Setting | Values |
| --- | --- |
| `model_pin` | a model id, or `None` to unpin |
| `router_mode` | `off`, `pinned`, `candidates`, `auto`, or `None` |
| `compression_mode` | `off`, `semantic_safe`, `adaptive` (legacy aliases `lossless` and `auto` are accepted), or `None` |
| `fallbacks` | ordered fallback model ids |
| `provider_prefs` | provider preferences mapping, or `None` |
| `learned_context_delivery` | `gateway_inject_after_stable_prefix` or `off` |
| `case_precedents_enabled` | `True` / `False` |
| `self_improve_mode` | `off`, `assist`, `autopilot` |
| `self_improve_guardrails` | `{"surfaces": [...], "max_cost_per_success_micro_usd": ...}` |

## Evals

Trigger an eval run now, or list past runs:

```python
run = client.call_types.enqueue_eval("support-reply", mode="request")
if run.enqueued:
    print("enqueued", run.run_id, run.candidate_count)
else:
    print("not enqueued:", run.reason, run.prior_run_id)

for eval_run in client.call_types.list_evals("support-reply").data:
    print(eval_run.id, eval_run.status, eval_run.item_count)
```

An eval trigger that is not enqueued returns a documented reason (`no_golden_set`,
`no_candidates`, `deduped`, ...). A de-duplicated trigger names the run it joined in
`prior_run_id`, so you can follow it.

## Recommendations

```python
recommendations = client.call_types.list_recommendations("support-reply")
print(recommendations.keys())
```

The recommendation payload is not described by the API specification yet, so it is returned as
a plain `dict`.

## Related

- [Hosted prompts](hosted-prompts.md) (`client.call_types.prompts`)
- [Verified memory](verified-memory.md) (`client.call_types.verified_memory`)
- [Preflight](preflight.md): what the gateway would decide for a call type
