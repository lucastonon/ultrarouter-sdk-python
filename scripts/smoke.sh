#!/usr/bin/env bash
# Build smoke test: build the wheel and sdist, validate them, scan them for leaks, then install each
# into fresh virtual environments for the oldest and newest supported Python and exercise the
# installed package against the local mock gateway (sync + async chat, streaming, embeddings,
# typed errors, the learning loop, one documented example) and type-check a consumer file with
# mypy --strict against the installed package.
#
# Usage: scripts/smoke.sh            (run from the repository root, after `uv sync`)
# Env:   SMOKE_DIR        where the throwaway environments go (default: $TMPDIR/ultrarouter-sdk-smoke)
#        SMOKE_PYTHONS    Python versions to test (default: "3.10 3.14")
#        SKIP_BUILD=1     reuse the artifacts already in dist/
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

SMOKE_DIR="${SMOKE_DIR:-${TMPDIR:-/tmp}/ultrarouter-sdk-smoke}"
SMOKE_PYTHONS="${SMOKE_PYTHONS:-3.10 3.14}"
PY="$ROOT/.venv/bin/python"
VERSION="$("$PY" -c 'import sys; sys.path.insert(0, "src"); from ultrarouter._version import __version__; print(__version__)')"
# Type-check the consumer with the same mypy the lockfile pins for development.
MYPY_VERSION="$("$PY" -c 'import importlib.metadata as m; print(m.version("mypy"))')"

log() { printf '\n==> %s\n' "$*"; }

if [[ "${SKIP_BUILD:-0}" != "1" ]]; then
  log "build"
  rm -rf dist
  uv build --out-dir dist
fi
ls -1 dist
WHEEL="$(ls dist/*.whl)"
SDIST="$(ls dist/*.tar.gz)"

log "twine check --strict"
"$ROOT/.venv/bin/twine" check --strict dist/*

log "leak scan of the built distributions"
"$PY" scripts/leak_scan.py --no-tree --no-history --dist dist

log "sdist contents"
for required in README.md LICENSE CHANGELOG.md AGENTS.md llms.txt llms-full.txt docs/index.md examples/quickstart.py examples/learning_tool_episode.py docs/learning.md openapi/openapi.yaml src/ultrarouter/py.typed src/ultrarouter/_data/outcome_verdicts.json src/ultrarouter/_data/toy_env.json tests/fixtures/outcome_verdicts.json tests/fixtures/toy_env.json; do
  tar -tzf "$SDIST" | grep -q "/$required\$" || { echo "sdist is missing $required" >&2; exit 1; }
done
echo "sdist ok: $(tar -tzf "$SDIST" | wc -l | tr -d ' ') entries"
"$PY" - "$WHEEL" <<'PYCODE'
import sys, zipfile
names = zipfile.ZipFile(sys.argv[1]).namelist()
assert "ultrarouter/py.typed" in names, "wheel is missing py.typed"
for data in ("ultrarouter/_data/outcome_verdicts.json", "ultrarouter/_data/toy_env.json"):
    assert data in names, f"wheel is missing {data}"
assert any(n.endswith("licenses/LICENSE") for n in names), "wheel is missing the license file"
assert not any(n.startswith(("tests/", "scripts/")) for n in names), "wheel contains repository files"
print(f"wheel ok: {len(names)} files")
PYCODE

log "start the mock gateway"
MOCK_LOG="$(mktemp)"
"$PY" tests/support/mock_gateway.py --port 0 --print-url >"$MOCK_LOG" 2>&1 &
MOCK_PID=$!
disown "$MOCK_PID"
trap 'kill "$MOCK_PID" 2>/dev/null || true; rm -f "$MOCK_LOG"' EXIT
# Up to 30 s: on a saturated host the interpreter start alone exceeded the old 5 s window (2026-10-20).
for _ in $(seq 1 300); do
  [[ -s "$MOCK_LOG" ]] && break
  sleep 0.1
done
MOCK_URL="$(head -n1 "$MOCK_LOG")"
[[ "$MOCK_URL" == http://* ]] || { echo "mock gateway did not start: $(cat "$MOCK_LOG")" >&2; exit 1; }
echo "mock gateway at $MOCK_URL"

rm -rf "$SMOKE_DIR"
mkdir -p "$SMOKE_DIR"
cp scripts/smoke_consumer.py "$SMOKE_DIR/smoke_consumer.py"
# One documented example, run from the installed copy (not the checkout), with no extra packages.
cp examples/learning_immediate_outcome.py "$SMOKE_DIR/learning_immediate_outcome.py"

for pyver in $SMOKE_PYTHONS; do
  for kind in wheel sdist; do
    artifact="$WHEEL"
    [[ "$kind" == "sdist" ]] && artifact="$SDIST"
    env_dir="$SMOKE_DIR/py$pyver-$kind"
    log "Python $pyver from the $kind"
    uv venv --quiet --python "$pyver" "$env_dir"
    uv pip install --quiet --python "$env_dir/bin/python" "$artifact" "mypy==$MYPY_VERSION"
    (
      cd "$SMOKE_DIR"
      ULTRAROUTER_BASE_URL="$MOCK_URL" ULTRAROUTER_API_KEY="ur_sk_test_smoke" EXPECTED_VERSION="$VERSION" \
        "$env_dir/bin/python" -I smoke_consumer.py
      "$env_dir/bin/python" -m mypy --strict --no-incremental --python-executable "$env_dir/bin/python" smoke_consumer.py
      ULTRAROUTER_BASE_URL="$MOCK_URL" ULTRAROUTER_API_KEY="ur_sk_test_smoke" \
        "$env_dir/bin/python" -I learning_immediate_outcome.py
    )
  done
done

log "smoke test passed for Python $SMOKE_PYTHONS (wheel and sdist)"
