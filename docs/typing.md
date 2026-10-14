# Typing

The package ships a `py.typed` marker and is checked with `mypy --strict`. Your type checker sees
precise types for every method, argument and response.

## Response models

Every response is a pydantic v2 model deriving from `ultrarouter.BaseModel`. All models live in
`ultrarouter.types`; the most used ones are also exported from `ultrarouter`.

```python
from ultrarouter import ChatCompletion, UltraRouter
from ultrarouter.types import UrBlock


def served_model(reply: ChatCompletion) -> str:
    ur: UrBlock = reply.ur
    return ur.model_served


client = UltraRouter()
reply = client.chat.completions.create(
    model="openai/gpt-5.2-mini", messages=[{"role": "user", "content": "Hi"}]
)
print(served_model(reply))
```

Conventions:

- **Forward compatible.** Unknown fields from a newer gateway are kept, not rejected:
  `model.model_extra` holds them, and `model.to_dict()` includes them.
- **Enumerated values are `str`.** Fields with a fixed set of values (for example `status`) are
  typed `str`, with the known values listed in the field's documentation, so a new value never
  breaks parsing. Request arguments use `Literal` types instead.
- **Nullability follows the API.** A field the API may omit is `X | None = None`; a field it
  always sends is required. Required fields missing from a response raise
  `APIResponseValidationError`.
- **Python keywords** get a trailing underscore (`schema_`, `import_`), and still map to the wire
  name.

```python
models = client.models.list()
print(models.to_dict()["object"])  # wire-shaped dict
print(models.to_json(indent=None)[:40])  # wire-shaped JSON
print(models.model_extra)  # fields this SDK version does not know yet
```

## Request shapes

Arguments that take structured values are typed with `TypedDict`s from `ultrarouter.types`
(`ChatMessageParam`, `ProviderPreferencesParam`, `UrParams`, `OutcomeParams`, `ReviewerEvent`,
...). Plain dict literals type-check against them:

```python
from ultrarouter.types import ChatMessageParam, OutcomeParams

messages: list[ChatMessageParam] = [{"role": "user", "content": "Hi"}]
event: OutcomeParams = {"channel": "behavioral", "kind": "accepted"}
client.chat.completions.create(model="openai/gpt-5.2-mini", messages=messages)
```

`chat.completions.create(**kwargs)` and `embeddings.create(**kwargs)` are typed with
`ChatCompletionCreateKwargs` and `EmbeddingCreateKwargs`, so misspelled parameters are type
errors.

## Overloads

`chat.completions.create(stream=True)` is typed to return `Stream` (`AsyncStream` on the async
client) and `stream=False` (the default) to return `ChatCompletion`. `bench.report(format="json")`
returns `BenchReport`; `format="md"` or `"bundle"` returns `str`.

## Where the types come from

The response models and request shapes are generated from the API specification
(`openapi/openapi.yaml`) by `scripts/gen_types.py`, never edited by hand. A test fails if the
generated module is out of date with the specification.
