# Installation

The package is published as `ultrarouter` and supports Python 3.10 through 3.14.

## pip

```bash
pip install ultrarouter
```

## uv

```bash
uv add ultrarouter
```

## Poetry

```bash
poetry add ultrarouter
```

## The `openai` extra

`client.as_openai()` returns an `openai.OpenAI` (or `openai.AsyncOpenAI`) preconfigured for the
gateway. It needs the `openai` package, which the extra installs:

```bash
pip install "ultrarouter[openai]"
```

Without the extra, `as_openai()` raises an `UltraRouterError` with code `dependency_missing`
explaining what to install. Everything else works without it. The extra requires
`openai>=1.55.3`: older `openai` releases cannot construct a client with `httpx` 0.28 or newer.

## Dependencies

| Package | Why |
| --- | --- |
| `httpx` (>=0.27, <1) | HTTP transport, connection pooling, sync and async |
| `pydantic` (>=2.7, <3) | typed response models |
| `typing-extensions` (>=4.12) | `TypedDict`, `Required` and `Unpack` on Python 3.10 |
| `openai` (>=1.55.3, optional) | `as_openai()` |

Every lower bound is tested: the suite runs with all dependencies at their floors, and with each
of `httpx`, `pydantic` and `openai` at its floor while the others are at their newest versions
(`make test-lowest`).

The context runtime (`ultrarouter.context`) and the pure helpers (`diff_stats`,
`render_prompt`, learned placement) use only the standard library.

## Verify the installation

```python
import ultrarouter

print(ultrarouter.__version__)
```

To check your credentials and the gateway URL in one call, ask the gateway to describe your key:

```python
from ultrarouter import UltraRouter

info = UltraRouter().key.get()
print(info.mode, info.scopes, info.workspace_id)
```

## Next steps

- [Configuration and authentication](configuration.md)
- [Chat completions](chat-completions.md)
