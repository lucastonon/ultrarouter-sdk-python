"""A deterministic toy tool environment for trying the learning loop end to end.

**A demonstration, not evidence.** ``OrderDesk`` shows an agent's tool episode, a real verifier
and outcome reporting working together through the public API. It is small and fully
deterministic; a run that passes or fails here says nothing about whether learning improves an
agent.

The environment (tools, exact rules, scenarios and verifier) is the ``toy_env.json`` fixture both
official SDKs ship byte for byte. An order desk holds stock per SKU and orders that must be either
reserved in full or backordered:

* ``lookup_order(order_id)`` returns ``{"ok": true, "order_id", "sku", "quantity", "status"}``;
* ``check_stock(sku)`` returns ``{"ok": true, "sku", "in_stock"}`` (``UNKNOWN_SKU``);
* ``reserve_stock(order_id, sku, quantity)`` reserves when ``quantity <= stock`` (stock decreases,
  the order's reserved quantity becomes ``quantity``, ``{"ok": true}``), otherwise returns
  ``{"ok": false, "error": "INSUFFICIENT_STOCK", "in_stock": n}`` (``UNKNOWN_ORDER``,
  ``SKU_MISMATCH`` when the SKU is not the order's, ``ALREADY_RESERVED`` when the order already
  has a reservation);
* ``set_order_status(order_id, status)`` sets ``reserved`` or ``backordered`` (``UNKNOWN_ORDER``).

An unknown tool (``UNKNOWN_TOOL``) or malformed arguments (``INVALID_ARGUMENTS``: exactly the
listed keys, strings, ``quantity`` an integer of at least 1) answer an error. Every error changes
nothing.
Tool results, verifier reasons and the evidence hash are identical to the TypeScript SDK's
``createOrderDesk``.

The verifier handles orders in the order the task names them (by first appearance in the task
text): an order passes when it ends ``reserved`` with its full quantity reserved if the stock left
after the earlier orders covered it, otherwise ``backordered`` with nothing reserved. A task passes
when every order it names passes **and** each SKU's final stock equals its starting stock minus the
quantities reserved for it.

Example::

    from ultrarouter.demo import OrderDesk

    desk = OrderDesk("s2")             # 3 units ordered, 1 in stock
    # {"ok": True, "sku": "SKU-BLUE", "in_stock": 1}
    desk.call("check_stock", {"sku": "SKU-BLUE"})
    desk.call("set_order_status", {"order_id": "B-200", "status": "backordered"})
    assert desk.verify().verdict == "pass"
"""

from __future__ import annotations

import copy
import json
from collections.abc import Mapping
from functools import lru_cache
from importlib import resources
from typing import Any

from ..adapters._verifier import VerifierResult, evidence_hash

__all__ = ["NOTICE", "OrderDesk", "order_desk_spec", "scenario_ids"]


@lru_cache(maxsize=1)
def _raw_spec() -> bytes:
    return (resources.files("ultrarouter") / "_data" / "toy_env.json").read_bytes()


def order_desk_spec() -> dict[str, Any]:
    """The shared environment fixture, parsed (a fresh copy on every call)."""
    parsed: dict[str, Any] = json.loads(_raw_spec())
    return parsed


#: The fixture's own notice: a demonstration, not evidence that learning improves an agent.
NOTICE: str = str(order_desk_spec()["notice"])


def scenario_ids() -> list[str]:
    """The scenario ids, in fixture order (``s1`` ... ``s6``)."""
    return [str(s["id"]) for s in order_desk_spec()["scenarios"]]


def _valid_arguments(schema: Mapping[str, Any], args: Mapping[str, Any]) -> bool:
    properties: Mapping[str, Any] = schema.get("properties", {})
    if any(name not in args for name in schema.get("required", ())):
        return False
    if schema.get("additionalProperties") is False and any(k not in properties for k in args):
        return False
    for name, value in args.items():
        spec = properties.get(name, {})
        kind = spec.get("type")
        if kind == "string" and not isinstance(value, str):
            return False
        if kind == "integer" and (isinstance(value, bool) or not isinstance(value, int)):
            return False
        if "minimum" in spec and isinstance(value, int) and value < spec["minimum"]:
            return False
        if "enum" in spec and value not in spec["enum"]:
            return False
    return True


class OrderDesk:
    """One scenario of the order desk, with its own mutable state.

    Args:
        scenario: A scenario id (``"s1"`` ... ``"s6"``).
    """

    def __init__(self, scenario: str = "s1") -> None:
        spec = order_desk_spec()
        found = [s for s in spec["scenarios"] if s["id"] == scenario]
        if not found:
            raise ValueError(f"unknown scenario {scenario!r}; choose one of {scenario_ids()}")
        self._scenario: dict[str, Any] = copy.deepcopy(found[0])
        self._schemas: dict[str, Mapping[str, Any]] = {
            str(t["name"]): t["parameters"] for t in spec["tools"]
        }
        self._tools: list[dict[str, Any]] = [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": copy.deepcopy(t["parameters"]),
                },
            }
            for t in spec["tools"]
        ]
        self.stock: dict[str, int] = dict(self._scenario["stock"])
        """Units in stock per SKU (changes as stock is reserved)."""
        self.orders: dict[str, dict[str, Any]] = {
            order_id: {**order, "reserved": 0}
            for order_id, order in self._scenario["orders"].items()
        }
        """Orders by id: ``sku``, ``quantity``, ``status`` and ``reserved``."""
        self.calls: list[dict[str, Any]] = []
        """Every tool call made, in order: ``name``, ``arguments`` and ``result``."""

    @property
    def scenario_id(self) -> str:
        """The scenario id."""
        return str(self._scenario["id"])

    @property
    def task(self) -> str:
        """The task text an agent receives."""
        return str(self._scenario["task"])

    @property
    def tools(self) -> list[dict[str, Any]]:
        """The tools in the OpenAI ``tools`` format, ready for ``chat.completions.create``."""
        return copy.deepcopy(self._tools)

    def call(self, name: str, arguments: str | Mapping[str, Any]) -> dict[str, Any]:
        """Run one tool call by the exact rules and return its JSON result.

        ``arguments`` is a mapping or the JSON text a model produced. An unknown tool, malformed
        arguments or an unknown order answer ``{"ok": false, "error": ...}`` and change nothing.
        """
        try:
            args = json.loads(arguments) if isinstance(arguments, str) else dict(arguments)
        except ValueError:
            args = None
        result = self._dispatch(name, args)
        self.calls.append({"name": name, "arguments": args, "result": result})
        return copy.deepcopy(result)

    def tool_message(self, tool_call: Any) -> dict[str, Any]:
        """Run a model's tool call (an SDK or ``openai`` tool-call object, or a mapping) and return
        the ``{"role": "tool", ...}`` message to send back."""
        call = tool_call if isinstance(tool_call, Mapping) else _as_mapping(tool_call)
        function = call.get("function") or {}
        result = self.call(str(function.get("name")), function.get("arguments") or "{}")
        return {"role": "tool", "tool_call_id": call.get("id"), "content": json.dumps(result)}

    def _dispatch(self, name: str, args: dict[str, Any] | None) -> dict[str, Any]:
        schema = self._schemas.get(name)
        if schema is None:
            return {"ok": False, "error": "UNKNOWN_TOOL"}
        if not isinstance(args, dict) or not _valid_arguments(schema, args):
            return {"ok": False, "error": "INVALID_ARGUMENTS"}
        if name == "check_stock":
            units = self.stock.get(args["sku"])
            if units is None:
                return {"ok": False, "error": "UNKNOWN_SKU"}
            return {"ok": True, "sku": args["sku"], "in_stock": units}
        order = self.orders.get(args["order_id"])
        if order is None:
            return {"ok": False, "error": "UNKNOWN_ORDER"}
        if name == "lookup_order":
            return {
                "ok": True,
                "order_id": args["order_id"],
                "sku": order["sku"],
                "quantity": order["quantity"],
                "status": order["status"],
            }
        if name == "reserve_stock":
            if order["sku"] != args["sku"]:
                return {"ok": False, "error": "SKU_MISMATCH"}
            if order["reserved"] > 0:
                return {"ok": False, "error": "ALREADY_RESERVED"}
            in_stock = self.stock.get(order["sku"], 0)
            if args["quantity"] > in_stock:
                return {"ok": False, "error": "INSUFFICIENT_STOCK", "in_stock": in_stock}
            self.stock[order["sku"]] = in_stock - args["quantity"]
            order["reserved"] = args["quantity"]
            return {"ok": True}
        order["status"] = args["status"]  # set_order_status
        return {"ok": True}

    def named_orders(self) -> list[str]:
        """The order ids the task names, in the order it names them."""
        task = self.task
        return sorted((oid for oid in self.orders if oid in task), key=task.index)

    def state(self) -> dict[str, Any]:
        """A copy of the current state: ``stock`` per SKU and each order with ``reserved``."""
        return copy.deepcopy({"stock": self.stock, "orders": self.orders})

    def verify(self) -> VerifierResult:
        """The scenario's verifier: ``pass`` when every named order ended correctly and every
        SKU's stock is consistent with what was reserved, else ``fail`` with one
        ``"<order>: expected <status>, got <status>/<reserved>"`` reason per wrong order (and
        ``"<sku>: expected stock <n>, got <m>"`` per inconsistent SKU). The evidence hash covers
        the scenario id and the final state."""
        remaining = dict(self._scenario["stock"])
        reasons: list[str] = []
        checks: list[dict[str, Any]] = []
        for order_id in self.named_orders():
            initial = self._scenario["orders"][order_id]
            final = self.orders[order_id]
            available = remaining.get(initial["sku"], 0)
            expected = "reserved" if available >= initial["quantity"] else "backordered"
            if expected == "reserved":
                remaining[initial["sku"]] = available - initial["quantity"]
                ok = final["status"] == "reserved" and final["reserved"] == initial["quantity"]
            else:
                ok = final["status"] == "backordered" and final["reserved"] == 0
            checks.append(
                {
                    "order_id": order_id,
                    "expected": expected,
                    "status": final["status"],
                    "reserved": final["reserved"],
                    "pass": ok,
                }
            )
            if not ok:
                reasons.append(
                    f"{order_id}: expected {expected}, got {final['status']}/{final['reserved']}"
                )
        reserved: dict[str, int] = {}
        for order in self.orders.values():
            reserved[order["sku"]] = reserved.get(order["sku"], 0) + order["reserved"]
        for sku, start in self._scenario["stock"].items():
            expected_stock = start - reserved.get(sku, 0)
            if self.stock.get(sku, 0) != expected_stock:
                reasons.append(
                    f"{sku}: expected stock {expected_stock}, got {self.stock.get(sku, 0)}"
                )
        return VerifierResult(
            "fail" if reasons else "pass",
            tuple(reasons),
            "verifier",
            evidence_hash({"scenario": self.scenario_id, **self.state()}),
            {"scenario": self.scenario_id, "orders": checks, "calls": len(self.calls)},
        )

    def solve(self) -> list[dict[str, Any]]:
        """Run the correct procedure with no model (a deterministic reference, for tests and
        demonstrations): look up each order, check stock, then reserve or backorder. Returns the
        calls made."""
        start = len(self.calls)
        for order_id in self.named_orders():
            order = self.call("lookup_order", {"order_id": order_id})
            stock = self.call("check_stock", {"sku": order["sku"]})
            if order["quantity"] <= stock["in_stock"]:
                self.call(
                    "reserve_stock",
                    {"order_id": order_id, "sku": order["sku"], "quantity": order["quantity"]},
                )
                self.call("set_order_status", {"order_id": order_id, "status": "reserved"})
            else:
                self.call("set_order_status", {"order_id": order_id, "status": "backordered"})
        return self.calls[start:]


def _as_mapping(tool_call: Any) -> dict[str, Any]:
    dump = getattr(tool_call, "model_dump", None)
    if callable(dump):
        dumped = dump()
        if isinstance(dumped, dict):
            return dumped
    function = getattr(tool_call, "function", None)
    return {
        "id": getattr(tool_call, "id", None),
        "function": {
            "name": getattr(function, "name", None),
            "arguments": getattr(function, "arguments", None),
        },
    }
