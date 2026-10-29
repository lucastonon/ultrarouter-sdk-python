# Installation

The package is named `ultrarouter` and supports Python 3.10 through 3.14.

> **Not on PyPI yet.** `pip install ultrarouter` does not work today: the package has not been
> published to any package registry. Install it from a wheel you build from the repository, or
> straight from the public GitHub source.

## From a locally built wheel

```bash
git clone https://github.com/lucastonon/ultrarouter-sdk-python.git
cd ultrarouter-sdk-python
uv build                                    # writes dist/ultrarouter-<version>-py3-none-any.whl and the sdist
pip install dist/ultrarouter-0.1.0-py3-none-any.whl
```

Copy the wheel wherever you need it; it has no build-time requirements. With uv or Poetry, add the
file path the same way (`uv add ./dist/ultrarouter-0.1.0-py3-none-any.whl`,
`poetry add ./dist/ultrarouter-0.1.0-py3-none-any.whl`).

## From the GitHub source

```bash
pip install "ultrarouter @ git+https://github.com/lucastonon/ultrarouter-sdk-python.git"
uv add "ultrarouter @ git+https://github.com/lucastonon/ultrarouter-sdk-python.git"
```

Pin a commit for reproducible installs (`...ultrarouter-sdk-python.git@<commit>`).

## The `openai` extra

`client.as_openai()` returns an `openai.OpenAI` (or `openai.AsyncOpenAI`) preconfigured for the
gateway. It needs the `openai` package, which the extra installs:

```bash
pip install "dist/ultrarouter-0.1.0-py3-none-any.whl[openai]"
pip install "ultrarouter[openai] @ git+https://github.com/lucastonon/ultrarouter-sdk-python.git"
```

Or install `openai` yourself (`pip install "openai>=1.55.3"`). Without it, `as_openai()` raises an
`UltraRouterError` with code `dependency_missing` explaining what to install. Everything else works
without it. The extra requires `openai>=1.55.3`: older `openai` releases cannot construct a client
with `httpx` 0.28 or newer.

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

The context runtime (`ultrarouter.context`), the outcome adapters (`ultrarouter.adapters`), the
demonstration environment (`ultrarouter.demo`) and the pure helpers (`diff_stats`,
`render_prompt`, learned placement) use only the standard library and pydantic.

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
