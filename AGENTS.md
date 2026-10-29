# AGENTS.md: using and changing the ultrarouter Python SDK

This file is for AI coding agents (and humans in a hurry). Part 1 is for agents writing code that
**uses** the SDK; part 2 is for agents **changing** this repository.

## Part 1: using the SDK

### Install

`ultrarouter` is **not on PyPI** (or any registry) yet: `pip install ultrarouter` fails. Install a
wheel built from the repository, or the GitHub source:

```bash
uv build && pip install dist/ultrarouter-0.1.0-py3-none-any.whl   # "...whl[openai]" for as_openai()
pip install "ultrarouter @ git+https://github.com/lucastonon/ultrarouter-sdk-python.git@feat/learning-loop"
```

Python 3.10+. Import name: `ultrarouter`. Never tell a user `pip install ultrarouter` works.

### Configure from the environment

Never hardcode keys. The client reads `ULTRAROUTER_API_KEY` and `ULTRAROUTER_BASE_URL`:

```python
from ultrarouter import UltraRouter

client = UltraRouter()  # create once, reuse; close with client.close() or use `with`
```

### Canonical patterns

```python
from ultrarouter import AsyncUltraRouter, UltraRouter, UltraRouterError

client = UltraRouter(default_model="openai/gpt-5.2-mini")

# Chat
reply = client.chat.completions.create(messages=[{"role": "user", "content": "Hello"}])
text = reply.choices[0].message.content
request_id = reply.ur.request_id  # keep it: feedback, stats and support use it

# Streaming
with client.chat.completions.create(
    messages=[{"role": "user", "content": "Hi"}], stream=True
) as stream:
    streamed = stream.text()

# Embeddings
vectors = client.embeddings.create(model="openai/text-embedding-3-small", input=["a", "b"])

# Errors: catch the base class, branch on subclasses or .code
try:
    client.chat.completions.create(
        model="acme/unpriced-model", messages=[{"role": "user", "content": "Hi"}]
    )
except UltraRouterError as exc:
    print(exc.code, exc.status, exc.retryable, exc.request_id)

# Outcomes: what happened after the answer (durably queued, never raises on delivery failure)
receipt = client.outcomes.record(
    {"request": request_id}, {"channel": "behavioral", "kind": "accepted"}
)
client.outcomes.flush()

# Learning loop: correlate, then report whether the task succeeded (see docs/learning.md)
call_type = next((ct for ct in client.call_types.list().data if ct.slug == "support-reply"), None)
if call_type is None:
    call_type = client.call_types.create(slug="support-reply")
with client.episode("order:A-100") as episode:  # key -> X-UR-Artifact; ids minted per step
    episode.chat.completions.create(
        call_type=call_type.slug, messages=[{"role": "user", "content": "Process A-100"}]
    )
    report = episode.report("pass", source="verifier")  # pass | fail | unknown
if report.reported and report.receipt_id:
    final = client.outcomes.wait_for_receipt(report)  # pending -> applied
status = client.learning.status(call_type.id)  # learning requires the ct_… id, not the slug
```

Async: `AsyncUltraRouter` has the same methods; `await` them and use `async with`.

### Pitfalls

- **Model ids are provider-prefixed**: `openai/gpt-5.2-mini`, not `gpt-5.2-mini`. List them with
  `client.models.list()`.
- **One client per process**, not per request; it owns a connection pool.
- **Do not retry what the SDK already retried.** It retries 408/429/5xx (unless the gateway says
  `retryable: false`) and connection errors, within the total `timeout`. `ModelUnpricedError`
  (`model_unpriced`, 403) and other 4xx are never retried: change the request instead.
- **Streams are not retried** and have no idempotency key.
- **`bench.run(wait=True)` returns `BenchRunTrigger | BenchRun`**: narrow with
  `isinstance(run, BenchRun)` before using `run.id`.
- **Preflight for case-based modules needs `messages=`**; otherwise `knowledge` is `None` with
  `knowledge_reason == "case_query_missing"`.
- **Outcome events and reviewer events never contain prompt or completion text.** Without
  corrections consent, report edits with `ultrarouter.diff_stats(draft, final)`.
- **Bench capture is for test keys** (`ur_sk_test_...`).
- **Unknown response fields are kept** in `model.model_extra`; do not assume a field is absent
  because the model class lacks it.
- **Enumerated response fields are `str`**, so compare against string literals.
- **Do not log the client's key** (`client.api_key`) or request/response bodies.
- **Report outcomes with `client.outcomes.report(request_id, verdict, source=...)`**; never sleep
  before reporting (an early report is held as `pending` with a durable receipt). `unknown`
  sends nothing; `self_rating` never teaches; HTTP or tool success is not task success.
- **Concurrent episodes need distinct `episode_key`s**: without one the gateway groups steps by
  their opening text, so identical concurrent tasks would merge.
- **A report is idempotent by identity** (`request_id`, `verdict`, `source`, `idempotency_key`):
  repeats replay the same event; give two genuinely different verdicts different
  `idempotency_key`s, and pass `observed_at` when a report may be repeated from another process.
- **Learning controls return a `LearningControl`**; the status is `control.learning`. A refusal
  is a `LearningError` subclass: branch on `reason`, show `action`.
- **Learning needs the full workspace self-learning opt-in** (knowledge and corrections consent).
  An owner/admin grants it on the dashboard Learning page or through the signed-in session
  `PUT /v1/workspaces/{id}/self-learning` with `{"enabled":true}`. An API key cannot grant consent;
  corrections consent alone is insufficient.
- **`ultrarouter.demo` is a demonstration**, not evidence that learning improves an agent.

### Where to look

| Need | Location |
| --- | --- |
| Every guide | [docs/index.md](docs/index.md) |
| Every public symbol with signature and docstring | [docs/api-reference.md](docs/api-reference.md) |
| Every response/request type and its fields | [docs/types-reference.md](docs/types-reference.md) |
| Which endpoint each method calls | [docs/api-coverage.md](docs/api-coverage.md) |
| Errors and what to do | [docs/errors.md](docs/errors.md) |
| Runnable scripts | [examples/](examples/) (`learning_*.py` for the learning loop) |
| The learning loop | [docs/learning.md](docs/learning.md) |
| All docs in one file for an LLM | [llms-full.txt](llms-full.txt) (index: [llms.txt](llms.txt)) |

## Part 2: changing this repository

### Setup and commands

```bash
uv sync                      # creates .venv with dev dependencies
make check                   # the full gate: lint, format, types, tests, docs, build, smoke, leak scan
make test                    # pytest only
make lint format typecheck   # individual gates
make generate                # regenerate types, API/types reference, coverage table, llms files
make smoke                   # build wheel + sdist, install into fresh 3.10 and 3.14 venvs, exercise them
make test-lowest             # the suite with httpx, pydantic, typing-extensions and openai at their floors
make leak-scan               # scan the tree, git history and dist/ for secrets (+ $ULTRAROUTER_LEAK_PATTERNS_FILE)
make parity-check            # regenerate the parity goldens from the TypeScript SDK and diff (TS_SDK=path)
```

The `ci` workflow (`.github/workflows/ci.yml`, manual dispatch only; `make check` is the gate) runs the
same gates on Python 3.10 to 3.14; `publish.yml` uploads to PyPI with trusted publishing, only from a
published release or a manual run.

### Rules

- `openapi/openapi.yaml` is a synced artifact: update it only with
  `python scripts/sync_openapi.py --from <spec>`, then `make generate`.
- `src/ultrarouter/types/_generated.py` is generated by `scripts/gen_types.py`; never edit it.
  Change names in the tables at the top of the generator.
- Every public module, class, function and method needs a docstring (a test enforces it).
- Every ```` ```python ```` block in `README.md`, `AGENTS.md` and `docs/*.md` is executed against
  the mock gateway by `tests/test_docs.py`. Keep examples runnable.
- `docs/api-reference.md`, `docs/types-reference.md`, `docs/api-coverage.md`, `llms.txt` and
  `llms-full.txt` are generated; tests fail when they drift.
- Every API-key endpoint in the spec must be mapped in `tests/coverage_map.py` (or explicitly
  excluded with a reason); `tests/test_api_coverage.py` calls each one sync and async and validates
  the request body against the spec.
- `src/ultrarouter/_data/outcome_verdicts.json` and `_data/toy_env.json` are byte-for-byte copies
  of fixtures shared with the TypeScript SDK (also under `tests/fixtures/`, sha256 pinned in
  `tests/test_outcome_report.py` and `tests/test_demo.py`). Never edit them here.
- After a spec sync adds operations, run `make generate`, give new response and request models
  public names in the tables at the top of `scripts/gen_types.py`, and map each new API-key
  operation in `tests/coverage_map.py`.
- Cross-language behaviour (context runtime, placement, rendering, diff stats, canonical JSON) is
  pinned by `tests/fixtures/parity/`; regenerate with
  `node scripts/gen_parity_goldens.mjs --ts-sdk <path to the TypeScript SDK>`.
- `mypy --strict` and `ruff` must stay clean. No new runtime dependencies without a strong reason.
- Run `make leak-scan` before committing. Never add organisation-specific patterns or names to
  this repository (not even in tests); they belong in the private patterns file the scanner
  reads from `ULTRAROUTER_LEAK_PATTERNS_FILE`. Test the scanner with synthetic patterns.

### Layout

```
src/ultrarouter/          the package (clients, transport, resources, helpers)
  types/_generated.py     generated models and request shapes
  _data/                  shared fixtures shipped in the package (verdict mapping, toy environment)
  adapters/               outcome adapters (verifiers, business rules, signed webhooks)
  demo/                   the deterministic demonstration environment
  context/                the pure context runtime
tests/                    unit, coverage, parity, docs and example tests; support/ has the mock gateway
docs/                     guides (tested) and generated references
examples/                 runnable scripts (tested)
scripts/                  generators, leak scan, smoke test
openapi/openapi.yaml      the synced API specification
```
