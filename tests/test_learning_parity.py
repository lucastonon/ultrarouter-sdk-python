"""Cross-language parity of the learning surface with the TypeScript SDK.

Every expected value below was produced by the TypeScript SDK's own build (``@ultrarouter/sdk``
0.1.0: ``reportSourceEventId`` and ``mintRequestId`` from the main entry, ``createOrderDesk``,
``verdictFromCommand``, ``runVerifier``, ``validateOutput`` and ``signWebhook`` from the
``learning`` entry) on the same inputs. The Python SDK must reproduce each one exactly, so an outcome
reported, a verdict hashed or a webhook signed by either SDK is the same on the wire.
"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import BaseModel

from ultrarouter import new_request_id, report_source_event_id
from ultrarouter.adapters import (
    run_verifier,
    sign_webhook,
    validate_output,
    verdict_from_command,
)
from ultrarouter.demo import OrderDesk


def test_report_identity_and_minted_ids() -> None:
    assert (
        report_source_event_id("req_c_X", "fail", "webhook", "evt_9")
        == "rpt_0ed4652865495a308d130bff2b141c2c1fca27e248bc9878cb647b287bd5dce7"
    )
    assert new_request_id().startswith("req_c_")


#: (tool, arguments, the TypeScript order desk's answer), run in order on scenario s3.
S3_CALLS: list[tuple[str, dict[str, Any], dict[str, Any]]] = [
    (
        "lookup_order",
        {"order_id": "C-300"},
        {"ok": True, "order_id": "C-300", "sku": "SKU-GREEN", "quantity": 3, "status": "new"},
    ),
    ("check_stock", {"sku": "SKU-GREEN"}, {"ok": True, "sku": "SKU-GREEN", "in_stock": 4}),
    ("check_stock", {"sku": "SKU-NONE"}, {"ok": False, "error": "UNKNOWN_SKU"}),
    (
        "reserve_stock",
        {"order_id": "C-300", "sku": "SKU-PINK", "quantity": 1},
        {"ok": False, "error": "SKU_MISMATCH"},
    ),
    ("reserve_stock", {"order_id": "C-300", "sku": "SKU-GREEN", "quantity": 3}, {"ok": True}),
    (
        "reserve_stock",
        {"order_id": "C-301", "sku": "SKU-GREEN", "quantity": 3},
        {"ok": False, "error": "INSUFFICIENT_STOCK", "in_stock": 1},
    ),
    ("set_order_status", {"order_id": "C-300", "status": "reserved"}, {"ok": True}),
    (
        "set_order_status",
        {"order_id": "C-301", "status": "shipped"},
        {"ok": False, "error": "INVALID_ARGUMENTS"},
    ),
    ("lookup_order", {"order_id": "Z-1"}, {"ok": False, "error": "UNKNOWN_ORDER"}),
    ("cancel", {}, {"ok": False, "error": "UNKNOWN_TOOL"}),
    (
        "reserve_stock",
        {"order_id": "C-301", "sku": "SKU-GREEN", "quantity": 0},
        {"ok": False, "error": "INVALID_ARGUMENTS"},
    ),
]


def test_order_desk_tool_results_reasons_and_evidence() -> None:
    desk = OrderDesk("s3")
    for tool, arguments, expected in S3_CALLS:
        assert desk.call(tool, arguments) == expected, (tool, arguments)
    result = desk.verify()
    assert result.verdict == "fail"
    assert result.reasons == ("C-301: expected backordered, got new/0",)
    assert result.evidence_hash == (
        "sha256:37596964bf2ce70faa5a0526d9badf1d6b1be4ed9793a5897f94212a77722b4a"
    )
    solved = OrderDesk("s1")
    solved.call("reserve_stock", {"order_id": "A-100", "sku": "SKU-RED", "quantity": 2})
    solved.call("set_order_status", {"order_id": "A-100", "status": "reserved"})
    passed = solved.verify()
    assert passed.verdict == "pass" and passed.reasons == ()
    assert passed.evidence_hash == (
        "sha256:67bf83dd4774e0c290513ecd9e6a34df0612bcae1cacc86399eb2a28dcdecfb6"
    )


@pytest.mark.parametrize(
    ("exit_code", "stdout", "stderr", "signal", "verdict", "reasons", "digest"),
    [
        (
            1,
            "suite output\n",
            "",
            None,
            "fail",
            ("exit_code_1",),
            "sha256:fb7845e675fbf840b13bb26422e1f85db723a116e49f53892a2870679a3ffcd5",
        ),
        (
            0,
            "ok",
            "warn",
            None,
            "pass",
            (),
            "sha256:54a31531c35af6bd875f7cdca2d2f1eff27ed345702643b853efea830765a235",
        ),
        (
            None,
            "",
            "",
            "SIGKILL",
            "unknown",
            ("killed_by_SIGKILL",),
            "sha256:37527f7c8d9280502438cdb5f8f086bd996eb106d78c67a7255378bf69890dd8",
        ),
    ],
)
def test_verdict_from_command(
    exit_code: int | None,
    stdout: str,
    stderr: str,
    signal: str | None,
    verdict: str,
    reasons: tuple[str, ...],
    digest: str,
) -> None:
    result = verdict_from_command(exit_code, stdout=stdout, stderr=stderr, signal_name=signal)
    assert (result.verdict, result.reasons, result.evidence_hash) == (verdict, reasons, digest)


def test_run_verifier() -> None:
    checked = run_verifier(
        lambda: {
            "pass": False,
            "evidence": {"answer": 41, "expected": 42},
            "reasons": ["wrong_sum"],
        }
    )
    assert (checked.verdict, checked.reasons, checked.evidence_hash) == (
        "fail",
        ("wrong_sum",),
        "sha256:e1ba6d1470e1011747d463aa931b7dd9f91c620553c05e8ceeaaa7b3765af026",
    )

    def throws() -> bool:
        raise TypeError("x")

    crashed = run_verifier(throws)
    assert (crashed.verdict, crashed.reasons, crashed.evidence_hash) == (
        "unknown",
        ("verifier_error",),
        None,
    )
    failed = run_verifier(throws, on_error="fail")
    assert (failed.verdict, failed.reasons, failed.evidence_hash) == (
        "fail",
        ("check_threw",),
        "sha256:b2df0a617e9f6a88eae1e258a43c498c314c295d1d7ec39c28b415354607cb55",
    )


class Refund(BaseModel):
    """The structured output the rules check."""

    order_id: str
    amount: float
    approved: bool


def test_validate_output() -> None:
    ok = validate_output(
        '{"order_id": "A-100", "amount": 12.5, "approved": true}',
        Refund,
        rules={"amount is positive": lambda r: r.amount > 0},
    )
    assert (ok.verdict, ok.reasons, ok.evidence_hash) == (
        "pass",
        (),
        "sha256:3444c6f0efe5f95a0fd7590d8229bf3945ff24aa9024cbb6fc6433d3502b2eb6",
    )
    bad_json = validate_output("{not json", Refund)
    assert (bad_json.verdict, bad_json.reasons, bad_json.evidence_hash) == (
        "fail",
        ("invalid_json",),
        "sha256:9781db3e3394cf2afe8283a873c032cd1d842a7570a7e63d504a9bed96a242cd",
    )

    def boom(_refund: Refund) -> bool:
        raise ArithmeticError("r")

    failed = validate_output(
        '{"order_id": "B-1", "amount": -1, "approved": true}',
        Refund,
        rules={
            "amount is positive": lambda r: r.amount > 0,
            "known": lambda r: True if r.order_id.startswith("A-") else "not an A order",
            "boom": boom,
        },
    )
    assert failed.verdict == "fail"
    assert failed.reasons == (
        "amount is positive",
        "known: not an A order",
        "boom: ArithmeticError",
    )
    assert failed.evidence_hash == (
        "sha256:69f7f0cebad038250798de7c3a7060aabee81c05e217a0300f62709c053c33bd"
    )


def test_sign_webhook() -> None:
    assert sign_webhook('{"a":1}', secret="whsec_test_only_value", now_s=1_800_000_000) == {
        "x-webhook-timestamp": "1800000000",
        "x-webhook-signature": (
            "sha256=bf640dffac961e1bee429368361cbd6532771147510cbcead0189b8671422d2e"
        ),
    }
