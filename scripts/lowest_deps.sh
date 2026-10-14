#!/usr/bin/env bash
# Run the test suite against the lowest supported versions of the runtime dependencies.
#
# Scenarios (each in a fresh virtual environment on the oldest supported Python):
#   lowest          every direct dependency at its declared floor (uv --resolution lowest-direct),
#                   including the `openai` extra;
#   lowest-core     the same without the `openai` extra (whose own requirements would otherwise
#                   lift typing-extensions above its floor);
#   <dep>-floor     one dependency (httpx, pydantic, openai) at its floor, the others at their
#                   newest allowed versions, which catches incompatible mixed combinations.
# The development tools (pytest, ruff, ...) are pinned to the versions in uv.lock, so only the
# runtime dependencies move. The suite includes `as_openai()` construction with the real
# `openai` package.
#
# Usage: scripts/lowest_deps.sh [scenario ...]      (default: all; run from the repository root)
# Env:   LOWEST_PYTHON  Python version (default 3.10)
#        LOWEST_DIR     where the environments go (default: $TMPDIR/ultrarouter-sdk-lowest)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PYVER="${LOWEST_PYTHON:-3.10}"
WORK="${LOWEST_DIR:-${TMPDIR:-/tmp}/ultrarouter-sdk-lowest}"
DEV_PY="$ROOT/.venv/bin/python"
SCENARIOS=("$@")
[[ ${#SCENARIOS[@]} -gt 0 ]] || SCENARIOS=(lowest lowest-core httpx-floor pydantic-floor openai-floor)

# floors of the runtime dependencies and exact pins of the test tools, read from the project
SETTINGS="$("$DEV_PY" - <<'PYCODE'
import re, sys
if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib
project = tomllib.load(open("pyproject.toml", "rb"))
lock = {p["name"]: p.get("version") for p in tomllib.load(open("uv.lock", "rb"))["package"]}
requirements = project["project"]["dependencies"] + project["project"]["optional-dependencies"]["openai"]
floors = {}
for req in requirements:
    name, floor = re.match(r"([A-Za-z0-9_.-]+)\s*>=\s*([0-9][^,;\s]*)", req).groups()
    floors[name.lower()] = floor
runtime = set(floors) | {"pydantic-core"}
tools = []
for req in project["dependency-groups"]["dev"]:
    name = re.match(r"[A-Za-z0-9_.-]+", req).group(0).lower()
    if name in runtime or name in {"twine", "mypy", "types-pyyaml"}:
        continue  # runtime dependencies move; release and type-check tools are not needed
    tools.append(f"{name}=={lock[name]}")
for name, floor in sorted(floors.items()):
    print(f"FLOOR_{name.upper().replace('-', '_')}={floor}")
print(f"TOOLS=({' '.join(tools)})")
PYCODE
)"
eval "$SETTINGS"

log() { printf '\n==> %s\n' "$*"; }

check_floor() {  # name expected-version
  local actual
  actual="$("$ENV/bin/python" -I -c "import importlib.metadata as m; print(m.version('$1'))")"
  if [[ "$actual" != "$2" && "$actual" != "$2.0" && "$actual" != "$2.0.0" ]]; then
    echo "expected $1 at its floor $2, got $actual" >&2
    exit 1
  fi
}

for scenario in "${SCENARIOS[@]}"; do
  ENV="$WORK/$scenario"
  log "$scenario (Python $PYVER)"
  rm -rf "$ENV"
  uv venv --quiet --python "$PYVER" "$ENV"
  case "$scenario" in
    lowest) args=(--resolution lowest-direct -e ".[openai]") ;;
    lowest-core) args=(--resolution lowest-direct -e ".") ;;
    httpx-floor) args=(-e ".[openai]" "httpx==$FLOOR_HTTPX") ;;
    pydantic-floor) args=(-e ".[openai]" "pydantic==$FLOOR_PYDANTIC") ;;
    openai-floor) args=(-e ".[openai]" "openai==$FLOOR_OPENAI") ;;
    *) echo "unknown scenario: $scenario" >&2; exit 2 ;;
  esac
  uv pip install --quiet --python "$ENV/bin/python" "${args[@]}" "${TOOLS[@]}"
  "$ENV/bin/python" -I -c "
import importlib.metadata as m
def version(name):
    try:
        return m.version(name)
    except m.PackageNotFoundError:
        return 'absent'
print('resolved:', ', '.join(f'{n}=={version(n)}' for n in ('httpx', 'pydantic', 'pydantic-core', 'typing-extensions', 'openai')))"
  case "$scenario" in
    lowest) check_floor httpx "$FLOOR_HTTPX"; check_floor pydantic "$FLOOR_PYDANTIC"; check_floor openai "$FLOOR_OPENAI" ;;
    lowest-core)
      check_floor httpx "$FLOOR_HTTPX"; check_floor pydantic "$FLOOR_PYDANTIC"
      check_floor typing-extensions "$FLOOR_TYPING_EXTENSIONS" ;;
    httpx-floor) check_floor httpx "$FLOOR_HTTPX" ;;
    pydantic-floor) check_floor pydantic "$FLOOR_PYDANTIC" ;;
    openai-floor) check_floor openai "$FLOOR_OPENAI" ;;
  esac
  "$ENV/bin/python" -m pytest -q -p no:cacheprovider -m "not integration" \
    tests/ -o addopts="--strict-markers --strict-config"
done

log "lowest-dependency scenarios passed: ${SCENARIOS[*]}"
