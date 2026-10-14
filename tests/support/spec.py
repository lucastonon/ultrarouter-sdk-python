"""Spec helpers for tests: load ``openapi/openapi.yaml``, synthesize sample payloads, validate.

* :func:`sample` builds a deterministic instance of any schema (every property filled), used by
  the mock gateway so each endpoint answers with a spec-shaped body.
* :func:`validate` checks an instance against a schema (the subset of OpenAPI 3.0 the spec uses:
  type, nullable, enum, required, properties, additionalProperties, items, anyOf/oneOf, $ref,
  min/max length and items). It is used to prove the SDK sends spec-valid request bodies.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
SPEC_PATH = ROOT / "openapi" / "openapi.yaml"
METHODS = ("get", "post", "put", "patch", "delete")


@lru_cache(maxsize=1)
def load_spec() -> dict[str, Any]:
    """The parsed specification (header comment lines are YAML comments)."""
    return yaml.safe_load(SPEC_PATH.read_text(encoding="utf-8"))


def resolve(schema: dict[str, Any]) -> dict[str, Any]:
    """Follow a top-level ``$ref``."""
    while "$ref" in schema:
        name = schema["$ref"].split("/")[-1]
        schema = load_spec()["components"]["schemas"][name]
    return schema


def operations() -> dict[str, tuple[str, str, dict[str, Any]]]:
    """operationId -> (METHOD, path template, operation object)."""
    out: dict[str, tuple[str, str, dict[str, Any]]] = {}
    for path, item in load_spec()["paths"].items():
        for method in METHODS:
            op = item.get(method)
            if op is not None:
                out[op["operationId"]] = (method.upper(), path, op)
    return out


def api_key_operations() -> dict[str, tuple[str, str, dict[str, Any]]]:
    """Operations callable with an API key (``bearerAuth`` in their security)."""
    return {
        op_id: value
        for op_id, value in operations().items()
        if any("bearerAuth" in s for s in (value[2].get("security") or []))
    }


def path_regex(template: str) -> re.Pattern[str]:
    """Regex for a path template; each ``{param}`` matches one (percent-encoded) segment."""
    parts = re.split(r"(\{[^}]+\})", template)
    pattern = "".join("([^/]+)" if part.startswith("{") else re.escape(part) for part in parts)
    return re.compile("^" + pattern + "$")


def success_schema(op: dict[str, Any]) -> tuple[int, dict[str, Any] | None]:
    """The first 2xx status and its JSON schema (``None`` when the spec has no body)."""
    for status, response in op.get("responses", {}).items():
        if status.startswith("2"):
            schema = response.get("content", {}).get("application/json", {}).get("schema")
            return int(status), schema
    return 200, None


def request_schema(op: dict[str, Any]) -> dict[str, Any] | None:
    """The JSON request-body schema, if the operation has one."""
    body = op.get("requestBody")
    if body is None:
        return None
    schema = body.get("content", {}).get("application/json", {}).get("schema")
    return schema if isinstance(schema, dict) else None


# ─────────────────────────────── sample synthesis ───────────────────────────────


def _is_null_marker(schema: Any) -> bool:
    return isinstance(schema, dict) and schema.get("nullable") is True and len(schema) == 1


def _string_for(name: str, schema: dict[str, Any]) -> str:
    if schema.get("enum"):
        return str(schema["enum"][0])
    if schema.get("format") == "uri" or name.endswith("url"):
        return "https://example.com/item"
    if name.endswith("_at") or name in ("as_of", "since", "valid_until_epoch_close", "lease_until"):
        return "2026-01-15T12:00:00.000Z"
    if name in ("id", "request_id") or name.endswith("_id"):
        prefix = name[:-3] if name.endswith("_id") else name
        return f"{prefix or 'id'}_sample01"
    if "hash" in name or "sha256" in name:
        return "0" * 64
    if name == "object":
        return "object"
    return f"sample-{name}" if name else "sample"


def sample(schema: Any, name: str = "", depth: int = 0) -> Any:
    """A deterministic instance of ``schema`` with every documented property present."""
    if not isinstance(schema, dict) or not schema:
        return None if depth > 0 else {}
    schema = resolve(schema)
    for key in ("anyOf", "oneOf"):
        if key in schema:
            variants = [v for v in schema[key] if not _is_null_marker(v)]
            return sample(variants[0], name, depth + 1) if variants else None
    if "enum" in schema and schema.get("type") != "string":
        return schema["enum"][0]
    typ = schema.get("type")
    if typ == "string":
        return _string_for(name, schema)
    if typ == "integer":
        minimum = schema.get("minimum")
        return int(minimum) + 1 if isinstance(minimum, (int, float)) else 1
    if typ == "number":
        return 0.5
    if typ == "boolean":
        return name not in ("dry_run", "deduped")
    if typ == "array":
        if depth > 12:
            return []
        return [sample(schema.get("items", {}), name.rstrip("s"), depth + 1)]
    if typ == "object" or "properties" in schema:
        props = schema.get("properties", {})
        if not props:
            return {}
        return {key: sample(value, key, depth + 1) for key, value in props.items()}
    return None


# ─────────────────────────────── validation ───────────────────────────────


def validate(instance: Any, schema: Any, path: str = "$") -> list[str]:
    """Return a list of human-readable violations of ``schema`` by ``instance``."""
    if not isinstance(schema, dict) or not schema:
        return []
    schema = resolve(schema)
    if instance is None:
        if schema.get("nullable"):
            return []
        for key in ("anyOf", "oneOf"):
            if any(
                _is_null_marker(v) or (isinstance(v, dict) and v.get("nullable"))
                for v in schema.get(key, [])
            ):
                return []
        if _is_null_marker(schema):
            return []
        return [f"{path}: null is not allowed"]
    for key in ("anyOf", "oneOf"):
        if key in schema:
            variants = [v for v in schema[key] if not _is_null_marker(v)]
            results = [validate(instance, v, path) for v in variants]
            if any(not r for r in results):
                return []
            best = min(results, key=len)
            return [f"{path}: matches no {key} variant", *best]
    errors: list[str] = []
    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{path}: {instance!r} not in {schema['enum']}")
    typ = schema.get("type")
    checks = {
        "string": lambda v: isinstance(v, str),
        "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
        "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
        "boolean": lambda v: isinstance(v, bool),
        "array": lambda v: isinstance(v, list),
        "object": lambda v: isinstance(v, dict),
    }
    if typ in checks and not checks[typ](instance):
        return [f"{path}: expected {typ}, got {type(instance).__name__}"]
    if typ == "string":
        if "minLength" in schema and len(instance) < schema["minLength"]:
            errors.append(f"{path}: shorter than {schema['minLength']}")
        if "maxLength" in schema and len(instance) > schema["maxLength"]:
            errors.append(f"{path}: longer than {schema['maxLength']}")
    if typ == "array":
        if "minItems" in schema and len(instance) < schema["minItems"]:
            errors.append(f"{path}: fewer than {schema['minItems']} items")
        if "maxItems" in schema and len(instance) > schema["maxItems"]:
            errors.append(f"{path}: more than {schema['maxItems']} items")
        for index, item in enumerate(instance):
            errors += validate(item, schema.get("items", {}), f"{path}[{index}]")
    if typ == "object" or (isinstance(instance, dict) and "properties" in schema):
        props = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in instance:
                errors.append(f"{path}: missing required {key!r}")
        extra = schema.get("additionalProperties")
        for key, value in instance.items():
            if key in props:
                errors += validate(value, props[key], f"{path}.{key}")
            elif extra is False:
                errors.append(f"{path}: unexpected property {key!r}")
            elif isinstance(extra, dict) and not _is_null_marker(extra):
                errors += validate(value, extra, f"{path}.{key}")
    return errors
