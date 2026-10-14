# Verified memory

Verified memory lets the gateway answer a request for a call type from the workspace's verified
past cases, when a calibrated rule says it is safe to do so. It is enabled per call type, can be
inspected at any time, and has a kill switch.

## Enable

Enabling calibrates the rule against the verified cases. If the call type does not qualify, the
response says why (`reason`, for example `pool_empty` or `calibration_below_target`) and nothing
is enabled.

```python
from ultrarouter import UltraRouter

client = UltraRouter()

result = client.call_types.verified_memory.enable("ticket-classifier", target_precision=0.95)
if result.enabled:
    print("enabled; calibration:", result.calibration)
else:
    print("not enabled:", result.reason, result.message)
```

## Inspect

```python
status = client.call_types.verified_memory.get("ticket-classifier")
print(status.enabled, status.config_version)
if status.servable is not None:
    print("servable:", status.servable.ok, status.servable.reason)
if status.setting is not None:
    print("target precision:", status.setting.target_precision)
```

`servable` is a live check: a stored setting that cannot be served right now (for example after
consent was revoked) is reported with a named reason rather than shown as off.

## Disable (kill switch)

```python
disabled = client.call_types.verified_memory.disable("ticket-classifier")
print(disabled.changed, disabled.previous_lever_version)
```

Responses served from verified memory carry `ur.verified_memory` (the rule version, pool hash,
agreement and the case ids used) on the chat completion.
