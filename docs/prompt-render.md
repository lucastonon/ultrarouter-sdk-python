# Prompt rendering

`render_prompt` and `render_hosted_prompt_result` fill a hosted prompt template exactly the way
the gateway does, so text rendered on your side matches what a proxied call would send. They are
pure functions (no network), available from `ultrarouter` and `ultrarouter.context`.

## Rules

1. Every `{{name}}` slot is replaced by `str(value)`. Whitespace inside the braces is allowed
   (`{{ name }}`); names are letters, digits and underscores only, so `{{user.name}}` is not a slot.
2. A declared **required** variable that is missing or `None` is a refusal listing every missing
   name (sorted). It is never rendered as an empty string.
3. A missing optional variable, and a slot that is not declared at all, render as `""`.

## `render_prompt`: text or an exception

```python
from ultrarouter import PromptVariablesMissingError, render_prompt

prompt = {
    "template": "You are a {{tone}} assistant for {{brand}}.",
    "variables": [{"name": "tone", "required": False}, {"name": "brand", "required": True}],
}

print(render_prompt(prompt, {"brand": "Northwind", "tone": "concise"}))
print(render_prompt(prompt, {"brand": "Northwind"}))  # optional tone renders as ""

try:
    render_prompt(prompt, {"tone": "concise"})
except PromptVariablesMissingError as exc:
    print(exc.code, exc.missing)  # prompt_variables_missing ['brand']
```

`prompt` can be the `PreflightPrompt` returned by `client.get_prompt(...)`, a hosted prompt
version from `client.call_types.prompts.get(...)`, or any mapping or object with `template` and
`variables`.

## `render_hosted_prompt_result`: a result value

```python
from ultrarouter import render_hosted_prompt_result

ok = render_hosted_prompt_result(
    "Hello {{name}}", [{"name": "name", "required": True}], {"name": "Ana"}
)
missing = render_hosted_prompt_result("Hello {{name}}", [{"name": "name", "required": True}], {})
print(ok)  # {'ok': True, 'text': 'Hello Ana'}
print(missing)  # {'ok': False, 'missing': ['name']}
```

The client-side `PromptVariablesMissingError` has `status == 0` (nothing was sent); the same
class is raised with `status == 400` when the gateway refuses a proxied request for the same
reason.
