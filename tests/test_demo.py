"""The deterministic order-desk demonstration environment, from the fixture shared with the
TypeScript SDK."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from ultrarouter.demo import NOTICE, OrderDesk, order_desk_spec, scenario_ids

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "toy_env.json"
PACKAGED = ROOT / "src" / "ultrarouter" / "_data" / "toy_env.json"
#: The sha256 of the fixture shared byte for byte with the TypeScript SDK.
FIXTURE_SHA256 = "c868940d540331a66d0120ee54f071e6f0c1f9728bf43cf51445ba429c0a51d5"
SPEC = json.loads(FIXTURE.read_text("utf-8"))


def test_fixture_is_the_shared_copy_and_the_package_ships_it_unchanged() -> None:
    assert hashlib.sha256(FIXTURE.read_bytes()).hexdigest() == FIXTURE_SHA256
    assert PACKAGED.read_bytes() == FIXTURE.read_bytes()
    assert order_desk_spec() == SPEC
    assert SPEC["notice"] == NOTICE and "not evidence" in NOTICE
    assert scenario_ids() == ["s1", "s2", "s3", "s4", "s5", "s6"]


def test_tools_are_openai_tools() -> None:
    desk = OrderDesk("s1")
    assert [t["function"]["name"] for t in desk.tools] == [t["name"] for t in SPEC["tools"]]
    for tool, spec in zip(desk.tools, SPEC["tools"], strict=True):
        assert tool["type"] == "function"
        assert tool["function"]["parameters"] == spec["parameters"]
    desk.tools[0]["function"]["name"] = "mutated"
    assert desk.tools[0]["function"]["name"] == "lookup_order"  # a copy each time
    assert desk.task == "Please process order A-100." and desk.scenario_id == "s1"
    with pytest.raises(ValueError, match="unknown scenario"):
        OrderDesk("s99")


@pytest.mark.parametrize("scenario", scenario_ids())
def test_reference_procedure_passes_and_doing_nothing_fails(scenario: str) -> None:
    untouched = OrderDesk(scenario).verify()
    assert untouched.verdict == "fail" and untouched.reasons
    desk = OrderDesk(scenario)
    calls = desk.solve()
    result = desk.verify()
    assert result.verdict == "pass" and result.reasons == ()
    assert result.source == "verifier" and result.evidence_hash
    assert calls and all(c["result"]["ok"] for c in calls)


EXPECTED = {
    "s1": {"A-100": ("reserved", 2)},
    "s2": {"B-200": ("backordered", 0)},
    "s3": {"C-300": ("reserved", 3), "C-301": ("backordered", 0)},
    "s4": {"D-400": ("backordered", 0)},
    "s5": {"E-500": ("reserved", 10)},
    "s6": {"F-600": ("reserved", 2), "F-601": ("backordered", 0)},
}


@pytest.mark.parametrize("scenario", scenario_ids())
def test_the_reference_ends_in_the_expected_state(scenario: str) -> None:
    desk = OrderDesk(scenario)
    desk.solve()
    assert {k: (v["status"], v["reserved"]) for k, v in desk.orders.items()} == EXPECTED[scenario]


def test_exact_tool_rules() -> None:
    desk = OrderDesk("s3")
    assert desk.call("lookup_order", {"order_id": "C-300"}) == {
        "ok": True,
        "order_id": "C-300",
        "sku": "SKU-GREEN",
        "quantity": 3,
        "status": "new",
    }
    assert desk.call("check_stock", {"sku": "SKU-GREEN"}) == {
        "ok": True,
        "sku": "SKU-GREEN",
        "in_stock": 4,
    }
    reserve = '{"order_id": "C-300", "sku": "SKU-GREEN", "quantity": 3}'
    assert desk.call("reserve_stock", reserve) == {"ok": True}
    assert desk.stock["SKU-GREEN"] == 1 and desk.orders["C-300"]["reserved"] == 3
    refused = desk.call("reserve_stock", {"order_id": "C-301", "sku": "SKU-GREEN", "quantity": 3})
    assert refused == {"ok": False, "error": "INSUFFICIENT_STOCK", "in_stock": 1}
    assert desk.stock["SKU-GREEN"] == 1 and desk.orders["C-301"]["reserved"] == 0
    assert desk.call("set_order_status", {"order_id": "C-301", "status": "backordered"}) == {
        "ok": True
    }
    assert len(desk.calls) == 5


@pytest.mark.parametrize(
    ("name", "arguments", "error"),
    [
        ("cancel_order", {"order_id": "A-100"}, "UNKNOWN_TOOL"),
        ("lookup_order", {}, "INVALID_ARGUMENTS"),
        ("lookup_order", {"order_id": 7}, "INVALID_ARGUMENTS"),
        ("lookup_order", {"order_id": "A-100", "extra": 1}, "INVALID_ARGUMENTS"),
        ("lookup_order", "{not json", "INVALID_ARGUMENTS"),
        ("lookup_order", "[1]", "INVALID_ARGUMENTS"),
        (
            "reserve_stock",
            {"order_id": "A-100", "sku": "SKU-RED", "quantity": 0},
            "INVALID_ARGUMENTS",
        ),
        (
            "reserve_stock",
            {"order_id": "A-100", "sku": "SKU-RED", "quantity": True},
            "INVALID_ARGUMENTS",
        ),
        (
            "reserve_stock",
            {"order_id": "A-100", "sku": "SKU-RED", "quantity": 1.5},
            "INVALID_ARGUMENTS",
        ),
        ("reserve_stock", {"order_id": "A-100", "sku": "SKU-RED"}, "INVALID_ARGUMENTS"),
        ("reserve_stock", {"order_id": "Z-9", "sku": "SKU-RED", "quantity": 1}, "UNKNOWN_ORDER"),
        ("reserve_stock", {"order_id": "A-100", "sku": "SKU-BLUE", "quantity": 1}, "SKU_MISMATCH"),
        ("set_order_status", {"order_id": "A-100", "status": "shipped"}, "INVALID_ARGUMENTS"),
        ("lookup_order", {"order_id": "Z-999"}, "UNKNOWN_ORDER"),
        ("check_stock", {"sku": "SKU-NONE"}, "UNKNOWN_SKU"),
        ("set_order_status", {"order_id": "Z-999", "status": "reserved"}, "UNKNOWN_ORDER"),
    ],
)
def test_bad_calls_change_nothing(name: str, arguments: Any, error: str) -> None:
    desk = OrderDesk("s1")
    before = desk.state()
    assert desk.call(name, arguments) == {"ok": False, "error": error}
    assert desk.state() == before


def test_a_second_reservation_is_refused_and_changes_nothing() -> None:
    desk = OrderDesk("s5")  # 10 units of SKU-GRAY, E-500 orders 10
    assert desk.call("reserve_stock", {"order_id": "E-500", "sku": "SKU-GRAY", "quantity": 4}) == {
        "ok": True
    }
    before = desk.state()
    again = desk.call("reserve_stock", {"order_id": "E-500", "sku": "SKU-GRAY", "quantity": 6})
    assert again == {"ok": False, "error": "ALREADY_RESERVED"}
    assert desk.state() == before


def test_orders_are_judged_in_the_order_the_task_names_them() -> None:
    desk = OrderDesk("s3")  # 4 units: C-300 (3) first, then C-301 (3)
    assert desk.named_orders() == ["C-300", "C-301"]
    desk.call("reserve_stock", {"order_id": "C-301", "sku": "SKU-GREEN", "quantity": 3})
    desk.call("set_order_status", {"order_id": "C-301", "status": "reserved"})
    desk.call("set_order_status", {"order_id": "C-300", "status": "backordered"})
    result = desk.verify()
    assert result.verdict == "fail"
    assert result.reasons == (
        "C-300: expected reserved, got backordered/0",
        "C-301: expected backordered, got reserved/3",
    )
    assert [check["pass"] for check in result.details["orders"]] == [False, False]


def test_partial_or_wrong_status_fails() -> None:
    desk = OrderDesk("s1")
    desk.call("reserve_stock", {"order_id": "A-100", "sku": "SKU-RED", "quantity": 2})
    assert desk.verify().reasons == ("A-100: expected reserved, got new/2",)
    desk.call("set_order_status", {"order_id": "A-100", "status": "reserved"})
    assert desk.verify().verdict == "pass"
    backorder = OrderDesk("s2")
    backorder.call("set_order_status", {"order_id": "B-200", "status": "reserved"})
    assert backorder.verify().verdict == "fail"


def test_the_verifier_also_checks_each_skus_stock() -> None:
    desk = OrderDesk("s1")
    desk.solve()
    assert desk.verify().verdict == "pass"
    desk.stock["SKU-RED"] = 5  # stock that no reservation explains
    result = desk.verify()
    assert result.verdict == "fail"
    assert result.reasons == ("SKU-RED: expected stock 3, got 5",)


def test_tool_message_accepts_dicts_and_objects() -> None:
    desk = OrderDesk("s1")
    as_dict = {
        "id": "call_1",
        "type": "function",
        "function": {"name": "check_stock", "arguments": '{"sku": "SKU-RED"}'},
    }
    message = desk.tool_message(as_dict)
    assert message["role"] == "tool" and message["tool_call_id"] == "call_1"
    assert json.loads(message["content"]) == {"ok": True, "sku": "SKU-RED", "in_stock": 5}

    class Function:
        name = "lookup_order"
        arguments = '{"order_id": "A-100"}'

    class Call:
        id = "call_2"
        function = Function()

    assert json.loads(desk.tool_message(Call())["content"])["quantity"] == 2

    class Dumpable:
        def model_dump(self) -> dict[str, Any]:
            return {"id": "call_3", "function": {"name": "check_stock", "arguments": None}}

    assert json.loads(desk.tool_message(Dumpable())["content"]) == {
        "ok": False,
        "error": "INVALID_ARGUMENTS",
    }


def test_independent_instances() -> None:
    first, second = OrderDesk("s5"), OrderDesk("s5")
    first.solve()
    assert second.stock == {"SKU-GRAY": 10} and second.verify().verdict == "fail"
