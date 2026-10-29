# Contributing

Thanks for helping improve the ultrarouter Python SDK.

## Setup

You need [uv](https://docs.astral.sh/uv/) and GNU Make. Node.js is only needed to regenerate the
cross-language parity fixtures.

```bash
git clone https://github.com/lucastonon/ultrarouter-sdk-python.git
cd ultrarouter-sdk-python
uv sync          # creates .venv with the package (editable) and the dev tools
make check       # the full gate (the ci workflow runs the same list on manual dispatch)
```

## The checks

| Command | What it runs |
| --- | --- |
| `make lint` | `ruff check` |
| `make format` / `make format-check` | `ruff format` (write / verify) |
| `make typecheck` | `mypy --strict` on the package |
| `make test` | the pytest suite (unit, endpoint coverage, parity, timeouts, docs, examples, repository and leak-scanner checks) |
| `make test-lowest` | the suite in fresh Python 3.10 environments with `httpx`, `pydantic`, `typing-extensions` and the `openai` extra at their lowest supported versions, and with each of `httpx`, `pydantic` and `openai` alone at its floor (`scripts/lowest_deps.sh`) |
| `make generated-check` | generated files are up to date |
| `make build` | `uv build` and `twine check` |
| `make smoke` | installs the built wheel and sdist into fresh Python 3.10 and 3.14 environments and exercises them against the mock gateway (sync and async chat, streaming, embeddings, and `mypy` on a consumer file) |
| `make leak-scan` | scans the working tree, every commit in the git history (messages, changed paths and introduced file contents) and the built distributions for secrets, local paths and any extra patterns (see below) |
| `make check` | all of the above |
| `make parity-check` | regenerates the parity goldens from the TypeScript SDK (`TS_SDK=path`, built `dist/`) and fails on drift |

The `ci` workflow (`.github/workflows/ci.yml`) runs lint, format, types, the generated-file checks,
the tests, doctests and examples on Python 3.10, 3.11, 3.12, 3.13 and 3.14, runs the
lowest-dependency scenarios, then builds, smoke-tests and leak-scans the distributions and the full
history. When the repository variable `TS_SDK_REPOSITORY` (`owner/name`) is set, a further job
builds that TypeScript SDK and runs the parity-golden check against it. The workflow runs on manual
dispatch only (`gh workflow run ci.yml`): `make check` on the maintainer's machine is the gate
before every push.

Every third-party action in the workflows is pinned to a full commit SHA with its version in a
comment (`uses: owner/action@<40-hex sha> # vX.Y.Z`); a repository test enforces it. To update
one, resolve the new tag to its commit (dereferencing an annotated tag) with
`gh api repos/<owner>/<repo>/git/ref/tags/<tag>` and replace both the SHA and the comment.

### The leak scan

`scripts/leak_scan.py` ships generic rules only: credential formats (Anthropic, OpenAI, GitHub
classic and fine-grained, npm, PyPI, Slack, AWS, Google, Stripe, Hugging Face and ultrarouter
keys, private-key blocks), absolute local paths and committed secret files such as `.env`. It
scans the working tree, every commit reachable from any ref and, with `--dist`, every file inside
the built wheel and sdist. For history it lists every path each commit changes from git's raw
output (so binary, empty and deleted files, such as a key bundle that was committed and later
removed, are name-checked), scans every commit message, and reads the content of every distinct
blob from the object store, so `.gitattributes` diff settings cannot hide it.

Organisation-specific rules never live in this repository. Maintainers keep them in a private
JSON file and point the scanner at it with `--patterns-file PATH` or
`ULTRAROUTER_LEAK_PATTERNS_FILE`; `make check` and `make leak-scan` then apply them, and without
the variable they run the generic rules only. The format is a JSON array of
`{"id", "regex", "flags"?, "description"}` objects (`flags` may contain `i`, `m`, `s`, `u`). A
configured file that is missing or invalid fails the scan. In the workflows the file comes from the
`LEAK_PATTERNS_JSON` secret (optional for `ci`, required by `publish`), and
`--redact-external` keeps matches of those rules out of public logs. `scripts/leak_scan_allowlist.txt`
masks exact substrings (`<path glob>:<substring>  # reason`) and must stay minimal.

## Changing things

- **API changes.** Sync the specification with
  `uv run python scripts/sync_openapi.py --from /path/to/openapi.yaml`, run `make generate`, and
  update the hand-written resource methods in `src/ultrarouter/_resources/`. Map any new API-key
  endpoint in `tests/coverage_map.py`; `tests/test_api_coverage.py` then exercises it sync and
  async and validates the request body against the specification.
- **Generated files.** Never edit `src/ultrarouter/types/_generated.py`, `docs/api-reference.md`,
  `docs/types-reference.md`, `docs/api-coverage.md`, `llms.txt` or `llms-full.txt` by hand; run
  `make generate`.
- **Docs.** Every Python block in `README.md`, `AGENTS.md` and `docs/` runs in the test suite
  against a local mock gateway. If a block genuinely cannot run, put
  `<!-- doctest: skip — <reason> -->` on the line before it (this should be rare).
- **Docstrings.** Every public symbol needs one; `tests/test_repository.py` checks.
- **Parity fixtures.** Behaviour shared with the TypeScript SDK is pinned by
  `tests/fixtures/parity/`. After changing shared behaviour, regenerate the expected values from
  the TypeScript SDK: `node scripts/gen_parity_goldens.mjs --ts-sdk ../ultrarouter-sdk-typescript`.
- **Queue retention fixture.** `tests/fixtures/queue_retention_cases.json` is a byte-for-byte copy
  of the TypeScript SDK's `test/fixtures/queue-retention-cases.json`: 273 response cases that both
  SDKs must keep or drop identically (`tests/test_queue_retention_fixture.py` runs each one through
  the sync and the async client). Never edit it here: copy the new version and update the pinned
  sha256 in that test.
- **Changelog.** Add an entry under `[Unreleased]` in `CHANGELOG.md`.

## Integration tests against a real gateway

`tests/integration/` is skipped unless both `ULTRAROUTER_API_KEY` and `ULTRAROUTER_BASE_URL` are
set. Use a **test** key against a non-production gateway:

```bash
ULTRAROUTER_API_KEY=ur_sk_test_... ULTRAROUTER_BASE_URL=https://your-dev-gateway.example.com \
  uv run pytest tests/integration -m integration
```

Optional: `ULTRAROUTER_TEST_MODEL` and `ULTRAROUTER_TEST_EMBEDDING_MODEL` choose the models.

## Commits and pull requests

Use clear, imperative commit messages. Keep pull requests focused, include tests and docs, and
make sure `make check` passes.

## Releasing (maintainers)

1. Update `src/ultrarouter/_version.py` and `CHANGELOG.md`.
2. Run `make check`.
3. Publish a GitHub release whose tag is `v<version>`; the `publish` workflow re-runs the checks,
   builds, smoke-tests and leak-scans the distributions, and uploads them to PyPI with trusted
   publishing (no stored token). A manual run of the workflow uploads to TestPyPI by default.
   Both indexes need a trusted publisher for this repository, the workflow file `publish.yml` and
   the environment `pypi` (or `testpypi`).
