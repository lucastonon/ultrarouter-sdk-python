"""Every API-key operation in ``openapi/openapi.yaml`` is reachable from the SDK, sync and async.

For each operation the mapped SDK call (``tests/coverage_map.py``) runs against the mock gateway;
the request it sends must hit the operation's method and path, carry every required query
parameter, and have a JSON body that validates against the operation's request schema. The
response must parse into the typed model the generated ``OPERATIONS`` table declares.
"""

from __future__ import annotations

import contextlib
from typing import Any

import pytest
from spec import api_key_operations, operations, path_regex, request_schema, validate

import ultrarouter
from conftest import TEST_KEY, MockGateway
from coverage_map import COVERAGE, EXCLUDED, PROVISIONAL
from ultrarouter import AsyncUltraRouter, BaseModel, OutcomeReceipt, UltraRouter
from ultrarouter import types as types_module
from ultrarouter.types import OPERATIONS


def test_every_api_key_operation_is_covered_or_explicitly_excluded() -> None:
    reachable = set(api_key_operations())
    assert reachable == set(COVERAGE) | set(EXCLUDED), (
        f"uncovered: {sorted(reachable - set(COVERAGE) - set(EXCLUDED))}; "
        f"stale: {sorted((set(COVERAGE) | set(EXCLUDED)) - reachable)}"
    )
    assert not set(COVERAGE) & set(EXCLUDED)


def test_generated_scope_matches_the_coverage_map() -> None:
    assert set(OPERATIONS) == set(COVERAGE)


def _acceptable_types(op_id: str) -> tuple[type[Any], ...]:
    response_name = OPERATIONS[op_id][3]
    if response_name is None:
        return (dict,)
    declared = getattr(types_module, response_name)
    accepted: list[type[Any]] = [declared]
    fields = declared.model_fields
    if len(fields) == 1:  # an envelope ({"artifact": {...}}) the SDK unwraps
        (inner,) = fields.values()
        if isinstance(inner.annotation, type) and issubclass(inner.annotation, BaseModel):
            accepted.append(inner.annotation)
    if op_id == "preflight":
        accepted.append(types_module.PreflightResponse)
    return tuple(accepted)


def _check_result(op_id: str, result: Any) -> None:
    if op_id in ("recordArtifactOutcomes", "recordRequestOutcome"):
        assert isinstance(result, OutcomeReceipt)
        assert result.status == "delivered", result.error
        return
    assert isinstance(result, _acceptable_types(op_id)), type(result)


def _check_request(op_id: str, gateway: MockGateway) -> None:
    method, template, op = operations()[op_id]
    regex = path_regex(template)
    matching = [r for r in gateway.requests if r["method"] == method and regex.match(r["path"])]
    assert len(matching) == 1, f"expected one {method} {template}, saw {gateway.requests}"
    request = matching[0]
    for param in op.get("parameters", []):
        if param["in"] == "query" and param.get("required"):
            assert param["name"] in request["query"], f"missing required query {param['name']}"
    schema = request_schema(op)
    if schema is not None:
        errors = validate(request["body"], schema)
        assert not errors, f"{op_id} request body violates the spec: {errors}"
    assert request["headers"]["authorization"] == f"Bearer {TEST_KEY}"
    assert request["headers"]["user-agent"].startswith("ultrarouter-python/")
    if method == "POST":
        assert request["headers"].get("idempotency-key"), "POSTs carry an idempotency key"


@pytest.mark.parametrize("op_id", sorted(COVERAGE))
def test_operation_sync(op_id: str, mock_gateway: MockGateway) -> None:
    client = UltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url, max_retries=0)
    try:
        result = eval(COVERAGE[op_id], {"client": client, "ultrarouter": ultrarouter})  # noqa: S307
        _check_result(op_id, result)
        _check_request(op_id, mock_gateway)
    finally:
        client.close()


@pytest.mark.parametrize("op_id", sorted(COVERAGE))
async def test_operation_async(op_id: str, mock_gateway: MockGateway) -> None:
    client = AsyncUltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url, max_retries=0)
    try:
        result = await eval(COVERAGE[op_id], {"client": client, "ultrarouter": ultrarouter})  # noqa: S307
        _check_result(op_id, result)
        _check_request(op_id, mock_gateway)
    finally:
        await client.close()


def _template(path: str) -> str:
    """A path template with every parameter name replaced by ``{}`` (names differ by source)."""
    import re

    return re.sub(r"\{[^}]+\}", "{}", path)


def test_provisional_learning_endpoints_are_not_in_the_spec_yet() -> None:
    """The learning-loop endpoints the SDK calls with hand-written models. Once the synced
    specification describes one, map it in COVERAGE (and reconcile its model) instead."""
    in_spec = {(method, _template(path)) for method, path, _ in operations().values()}
    for method, path, _expression, _tests in PROVISIONAL:
        if path == "/v1/requests/{id}/outcomes":
            assert (method, _template(path)) in in_spec  # the existing route, extended
            continue
        assert (method, _template(path)) not in in_spec, (
            f"{method} {path} is now in the specification: map it in COVERAGE"
        )


@pytest.mark.parametrize("entry", PROVISIONAL, ids=[f"{m} {p}" for m, p, _, _ in PROVISIONAL])
def test_provisional_expressions_call_their_endpoint(
    entry: tuple[str, str, str, str], mock_gateway: MockGateway
) -> None:
    """Each listed expression sends exactly its request (a refusal from the mock is fine: only the
    request is checked here; the behaviour is tested in the files the table names)."""
    method, template, expression, _tests = entry
    client = UltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url, max_retries=0)
    try:
        with contextlib.suppress(ultrarouter.UltraRouterError):
            eval(expression, {"client": client})  # noqa: S307
        regex = path_regex(template)
        assert [(r["method"], bool(regex.match(r["path"]))) for r in mock_gateway.requests] == [
            (method, True)
        ]
    finally:
        client.close()
