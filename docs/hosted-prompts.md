# Hosted prompts

A hosted prompt is a versioned template stored on a call type. Versions are immutable; one
version at most is *active*. The gateway can apply the active prompt to proxied requests, and
any caller can fetch it to render it locally.

Templates use `{{name}}` slots. Each declared variable is `required` or optional; a missing
required variable is a named refusal (`prompt_variables_missing`), never a silent blank.

## Create, activate, roll back

```python
from ultrarouter import UltraRouter

client = UltraRouter()

version = client.call_types.prompts.create(
    "support-reply",
    template="You are a {{tone}} support agent for {{brand}}.",
    variables=[{"name": "tone", "required": False}, {"name": "brand", "required": True}],
)
print(version.version, version.active, version.content_sha256)

activation = client.call_types.prompts.activate(
    "support-reply", version.version, gateway_apply=True
)
print(activation.active_version, activation.gateway_apply)
```

`gateway_apply=True` makes the gateway apply the prompt to proxied requests for this call type;
`False` serves it only through `get_prompt` and preflight. Activating an older version is the
rollback. `deactivate` returns the call type to code-owned prompts.

```python
history = client.call_types.prompts.list("support-reply")
print(history.active_version, [v.version for v in history.data])

older = client.call_types.prompts.get("support-reply", 1)
print(older.template)

client.call_types.prompts.deactivate("support-reply")
```

## Supplying variables on proxied requests

When the gateway applies a hosted prompt, pass the variable values in `ur.prompt_vars`:

```python
reply = client.chat.completions.create(
    model="openai/gpt-5.2-mini",
    call_type="support-reply",
    ur={"prompt_vars": {"brand": "Northwind", "tone": "friendly"}},
    messages=[{"role": "user", "content": "Where is my order?"}],
)
```

A missing required variable raises `PromptVariablesMissingError` (HTTP 400) before any model is
called.

## Fetching and rendering locally

If you call your model provider yourself, fetch the active version and render it with the same
rule the gateway uses:

```python
from ultrarouter import render_prompt

prompt = client.get_prompt("support-reply")  # None when the call type is code-owned
if prompt is not None:
    system = render_prompt(prompt, {"brand": "Northwind", "tone": "friendly"})
    print(prompt.version, system)
```

`get_prompt` reuses the cached preflight read, so calling it often is cheap. See
[Prompt rendering](prompt-render.md) for the exact rules.

## Onboarding proposal

The gateway can propose a template inferred from the system prompts you already send:

```python
proposal = client.call_types.prompts.proposal("support-reply")
if proposal.available:
    print(proposal.template, [v.name for v in proposal.variables])
else:
    print("no proposal:", proposal.reason)
```
