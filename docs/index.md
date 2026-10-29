# ultrarouter Python SDK documentation

The `ultrarouter` package is the Python client for the ultrarouter gateway. Start with
[Installation](installation.md) and the [quickstart in the README](../README.md), then use the
guides below. Every Python example in these pages is executed by the test suite against a local
mock gateway, so the snippets match the code.

## Getting started

| Guide | What it covers |
| --- | --- |
| [Installation](installation.md) | from a locally built wheel or the GitHub source (not on PyPI yet); the `openai` extra; supported Python versions |
| [Configuration and authentication](configuration.md) | API keys, base URL and self-hosted gateways, environment variables, client defaults, `autopilot`, Bench tagging |
| [Sync and async clients](clients.md) | `UltraRouter` vs `AsyncUltraRouter`, lifecycle, connection pools, `with_options`, concurrency |

## OpenAI-compatible surface

| Guide | What it covers |
| --- | --- |
| [Chat completions](chat-completions.md) | `client.chat.completions.create`, parameters, the `ur` response block |
| [Streaming](streaming.md) | `stream=True`, `Stream` / `AsyncStream`, final usage and `ur` |
| [Tools](tools.md) | function calling, tool results, streaming tool-call fragments |
| [Structured outputs](structured-outputs.md) | `response_format` with JSON schema, parsing into pydantic |
| [Embeddings](embeddings.md) | `client.embeddings.create`, float and base64 encodings |
| [Models and key info](models.md) | `client.models.list`, `client.models.retrieve`, `client.key.get` |
| [OpenAI compatibility](openai-compatibility.md) | `as_openai()`, migrating from the `openai` package |
| [Native passthrough](passthrough.md) | the official `openai` and `anthropic` SDKs through the gateway: `/v1/responses`, `/v1/messages`, the ur metering headers |

## ultrarouter surfaces

| Guide | What it covers |
| --- | --- |
| [Call types](call-types.md) | create, configure and evaluate call types; recommendations |
| [Hosted prompts](hosted-prompts.md) | versioned prompts, activation and rollback, `get_prompt` |
| [Prompt rendering](prompt-render.md) | `render_prompt` and `render_hosted_prompt_result` |
| [Verified memory](verified-memory.md) | enable, inspect and disable answering from verified cases |
| [Feedback](feedback.md) | thumbs up / down on a served request |
| [Generation lookup](generation.md) | tokens, cost, timing and routing for one request |
| [Autopilot](autopilot.md) | the routing intent and the readiness report |
| [Bench](bench.md) | capture, freeze, paired runs, reports and the compare gate |
| [Outcomes and artifacts](outcomes.md) | artifact types, artifacts, outcome events, finals, the durable queue |
| [Plug-and-play learning](learning.md) | request and episode correlation, verdict reports with receipts, outcome adapters, learning controls, the demonstration environment |
| [History imports](imports.md) | import usage exports or traces without proxying |
| [Flywheel](flywheel.md) | status, exposure grants, candidates, confirmations, plans, improvement reads |
| [Oracles and verdict sources](oracles.md) | register and qualify your own checks; source checks |
| [Reviewer adapter](reviewer.md) | signed human decisions, dead letters and repair |
| [Preflight and learned context](preflight.md) | `preflight`, `use_learned`, `messages` for case modules, caching |
| [Learned-module placement](learned-placement.md) | `learned_placement_index`, `apply_learned_context` |
| [Diff statistics](diff-stats.md) | `diff_stats` for reporting edits without sending text |
| [Context runtime](context-runtime.md) | `ultrarouter.context`: lift, compile, render, exit |

## Reliability and typing

| Guide | What it covers |
| --- | --- |
| [Errors](errors.md) | the error classes, codes, statuses and what to do about each |
| [Retries, timeouts and idempotency](retries-timeouts.md) | the request policy and how to tune it |
| [Typing](typing.md) | pydantic models, request `TypedDict`s, `mypy --strict` |
| [Testing and mocking](testing.md) | `respx`, `httpx.MockTransport`, testing code that uses the SDK |
| [Troubleshooting and FAQ](troubleshooting.md) | common problems and answers |

## Reference

| Page | What it covers |
| --- | --- |
| [API reference](api-reference.md) | every public class, method and function (generated from docstrings) |
| [Types reference](types-reference.md) | every response model and request shape (generated) |
| [API coverage](api-coverage.md) | every gateway endpoint the SDK calls, sync and async, and the test that proves it |

For AI agents: [AGENTS.md](../AGENTS.md) explains how to install and use the SDK correctly;
[llms.txt](../llms.txt) and [llms-full.txt](../llms-full.txt) package these docs for LLMs.
