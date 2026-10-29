#!/usr/bin/env python3
"""A local mock of the ultrarouter gateway, for tests, documentation examples and smoke tests.

It serves every operation in ``openapi/openapi.yaml`` over real HTTP:

* a handful of endpoints have hand-written behaviour (chat completions incl. streaming, tools and
  structured output, embeddings, models, preflight with ETag/304 and grants, signed reviewer and
  oracle endpoints, artifacts and outcomes, bench runs, typed errors);
* every other endpoint answers with a deterministic sample synthesized from its response schema.

It never calls a model provider or any external service.

Run it standalone::

    python tests/support/mock_gateway.py --port 8787
    ULTRAROUTER_BASE_URL=http://127.0.0.1:8787 ULTRAROUTER_API_KEY=ur_sk_test_mock python app.py

Special inputs (to exercise error handling):

* model ``acme/unpriced-model`` → 403 ``model_unpriced``; ``acme/denied-model`` → 403
  ``model_denied_by_policy``; ``acme/missing-model`` → 404 ``not_found``; ``acme/rate-limited``
  → 429 ``rate_limited`` (``Retry-After: 0``);
* an API key containing ``invalid`` → 401 ``authentication``;
* ``GET /v1/generation?id=req_missing`` → 404.

The learning loop (hand-written, ahead of the specification): chat completions and embeddings
answer ``x-ur-request-id`` (the client's own valid id when it sent one) and remember the request;
a served request is "persisted" ``persist_delay_s`` (default 0.25 s) later. ``POST
/v1/requests/{id}/outcomes`` answers ``pending`` with a durable receipt before that, and
``accepted`` (receipt ``applied``) after; it is idempotent on ``(request, kind, source_event_id)``
(a replay is ``duplicate``, a different payload ``409 conflict``); an unknown id stays pending
until ``pending_ttl_s`` and then expires with ``request_not_found``; ``req_missing`` is refused at
once (404). ``GET /v1/outcome-receipts/{id}`` and ``GET /v1/requests/{id}/outcome-receipts`` read
receipts. ``/v1/call-types/{id}/learning*`` keeps a per-call-type learning state machine with
spec-shaped answers; the call types ``no-consent``, ``no-provider``, ``quota-out``,
``budget-out``, ``read-only`` and ``ct_missing`` exercise the refusals and stopped states, and
``support-reply`` starts enabled with versions ``epb_1`` (retired), ``epb_2`` (active) and
``epb_3`` (evaluating). ``GET /v1/outcome-receipts/ocr_sample`` answers a sample receipt.

Control endpoints (not part of the API): ``GET /__mock__/requests`` lists recorded requests,
``POST /__mock__/reset`` clears state, ``POST /__mock__/fail`` queues failures
(``{"path": "/v1/...", "status": 503, "code": "provider_unavailable", "times": 1}``) and
``POST /__mock__/drop`` processes the next ``times`` requests to a path and then closes the
connection without answering (a lost acknowledgement: ``{"path": "/v1/...", "times": 1}``),
``POST /__mock__/learning`` sets ``persist_delay_s`` / ``pending_ttl_s``, and
``POST /__mock__/slow`` makes responses slow
(``{"path": "/v1/...", "header_delay": 0.0, "chunk_delay": 0.1, "chunks": 8, "times": 1}``: wait
before the status line, then drip a JSON body in ``chunks`` pieces, or an event stream frame by
frame, with ``chunk_delay`` seconds between writes).
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import re
import struct
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))

from spec import load_spec, operations, path_regex, resolve, sample, success_schema

MOCK_REPLY = "Hello from the mock gateway."
ORACLE_SECRET = "orsec_mock_signing_secret"
_TAXONOMY = {
    "invalid_request": (400, False),
    "authentication": (401, False),
    "permission": (403, False),
    "not_found": (404, False),
    "model_denied_by_policy": (403, False),
    "model_unpriced": (403, False),
    "conflict": (409, False),
    "rate_limited": (429, True),
    "provider_unavailable": (502, True),
    "atomic_spend_guard_unavailable": (503, False),
    "internal": (500, False),
}


class MockState:
    """Mutable state shared by every request handler."""

    def __init__(self) -> None:
        self.lock = threading.RLock()
        self.reset()

    def reset(self) -> None:
        """Forget every recorded request and every piece of per-run state."""
        with getattr(self, "lock", threading.RLock()):
            self.requests: list[dict[str, Any]] = []
            self.failures: list[dict[str, Any]] = []
            self.slow: list[dict[str, Any]] = []
            self.counter = 0
            self.seen_events: set[str] = set()
            self.seen_callbacks: set[str] = set()
            self.seen_outcomes: set[str] = set()
            self.seen_verdicts: set[str] = set()
            self.drops: list[dict[str, Any]] = []
            self.served: dict[str, dict[str, Any]] = {}
            self.receipts: dict[str, dict[str, Any]] = {}
            self.receipt_keys: dict[str, tuple[str, str]] = {}
            self.learning: dict[str, dict[str, Any]] = {}
            self.persist_delay_s = 0.25
            self.pending_ttl_s = 900.0

    def next_id(self, prefix: str) -> str:
        with self.lock:
            self.counter += 1
            return f"{prefix}_{self.counter:06d}"


STATE = MockState()
_CURRENT = threading.local()
_REQUEST_ID = re.compile(r"[A-Za-z0-9_-]{1,64}")
_ROUTES = [
    (path_regex(path), method, op_id, op) for op_id, (method, path, op) in operations().items()
]


def _error(code: str, message: str, status: int | None = None) -> tuple[int, dict[str, Any]]:
    default_status, retryable = _TAXONOMY.get(code, (status or 400, False))
    return status or default_status, {
        "error": {
            "code": code,
            "message": message,
            "request_id": STATE.next_id("req"),
            "retryable": retryable,
        }
    }


def _ur_block(model: str, body: dict[str, Any]) -> dict[str, Any]:
    ur = body.get("ur") or {}
    block: dict[str, Any] = {
        "request_id": getattr(_CURRENT, "request_id", None) or STATE.next_id("req"),
        "call_type": body.get("call_type"),
        "model_served": model,
        "provider": model.split("/")[0] if "/" in model else "mock",
        "routing": {"mode": body.get("router") or "off", "fallback_used": False},
        "compression": {"applied": "off"},
        "cost_usd": 0.00012,
        "byok": False,
    }
    if ur.get("artifact"):
        block["artifact_id"] = _artifact_id(str(ur["artifact"]))
    if isinstance(ur.get("bench"), (str, dict)):
        suite = ur["bench"] if isinstance(ur["bench"], str) else ur["bench"].get("suite")
        block["bench"] = {"capture_status": "queued", "suite": suite, "run": None}
    return block


def _artifact_id(key: str) -> str:
    return "art_" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def _model_error(model: str | None) -> tuple[int, dict[str, Any]] | None:
    if not model:
        return _error("invalid_request", "model is required (pass model= or set default_model)")
    if model == "acme/unpriced-model":
        return _error("model_unpriced", f"model {model} has no usable price; it was not called")
    if model == "acme/denied-model":
        return _error("model_denied_by_policy", f"the workspace model policy denies {model}")
    if model == "acme/missing-model":
        return _error("not_found", f"unknown model {model}")
    if model == "acme/rate-limited":
        return _error("rate_limited", "rate limit exceeded")
    return None


def _reply_for(body: dict[str, Any]) -> tuple[str, list[dict[str, Any]] | None, str]:
    """(content, tool_calls, finish_reason) for a chat request."""
    tools = body.get("tools")
    messages = body.get("messages") or [{}]
    answered = isinstance(messages[-1], dict) and messages[-1].get("role") == "tool"
    if tools and body.get("tool_choice") != "none" and not answered:
        function = tools[0].get("function", {})
        args = sample(function.get("parameters") or {"type": "object", "properties": {}})
        call = {
            "id": "call_mock_1",
            "type": "function",
            "function": {"name": function.get("name", "tool"), "arguments": json.dumps(args)},
        }
        return "", [call], "tool_calls"
    fmt = body.get("response_format") or {}
    if fmt.get("type") == "json_schema":
        schema = (fmt.get("json_schema") or {}).get("schema") or {"type": "object"}
        return json.dumps(sample(schema)), None, "stop"
    if fmt.get("type") == "json_object":
        return json.dumps({"answer": MOCK_REPLY}), None, "stop"
    return MOCK_REPLY, None, "stop"


def _chat(body: dict[str, Any]) -> tuple[int, Any]:
    if not isinstance(body.get("messages"), list) or not body["messages"]:
        return _error("invalid_request", "messages is required")
    model = body.get("model")
    failure = _model_error(model)
    if failure is not None:
        return failure
    content, tool_calls, finish = _reply_for(body)
    message: dict[str, Any] = {"role": "assistant", "content": content or None}
    if tool_calls:
        message["tool_calls"] = tool_calls
    if body.get("stream"):
        return 200, ("sse", _sse_frames(str(model), body, content, tool_calls, finish))
    return 200, {
        "id": STATE.next_id("chatcmpl"),
        "object": "chat.completion",
        "created": 1_760_000_000,
        "model": model,
        "choices": [{"index": 0, "message": message, "finish_reason": finish}],
        "usage": {"prompt_tokens": 12, "completion_tokens": 7, "total_tokens": 19},
        "ur": _ur_block(str(model), body),
    }


def _sse_frames(
    model: str,
    body: dict[str, Any],
    content: str,
    tool_calls: list[dict[str, Any]] | None,
    finish: str,
) -> list[str]:
    chunk_id = STATE.next_id("chatcmpl")

    def chunk(delta: dict[str, Any], finish_reason: str | None = None) -> str:
        payload = {
            "id": chunk_id,
            "object": "chat.completion.chunk",
            "created": 1_760_000_000,
            "model": model,
            "choices": [{"index": 0, "delta": delta, "finish_reason": finish_reason}],
        }
        return f"data: {json.dumps(payload)}\n\n"

    frames = [chunk({"role": "assistant"}), ": heartbeat\n\n"]
    if tool_calls:
        call = tool_calls[0]
        frames.append(
            chunk(
                {
                    "tool_calls": [
                        {
                            "index": 0,
                            "id": call["id"],
                            "type": "function",
                            "function": {"name": call["function"]["name"], "arguments": ""},
                        }
                    ]
                }
            )
        )
        frames.append(
            chunk(
                {
                    "tool_calls": [
                        {"index": 0, "function": {"arguments": call["function"]["arguments"]}}
                    ]
                }
            )
        )
    else:
        words = content.split(" ")
        for index, word in enumerate(words):
            frames.append(chunk({"content": word if index == 0 else " " + word}))
    frames.append(chunk({}, finish))
    final = {
        "id": chunk_id,
        "object": "chat.completion.chunk",
        "created": 1_760_000_000,
        "model": model,
        "choices": [],
        "usage": {"prompt_tokens": 12, "completion_tokens": 7, "total_tokens": 19},
        "ur": _ur_block(model, body),
    }
    frames.append(f"data: {json.dumps(final)}\n\n")
    frames.append("data: [DONE]\n\n")
    return frames


def _embeddings(body: dict[str, Any]) -> tuple[int, Any]:
    model = body.get("model")
    failure = _model_error(model)
    if failure is not None:
        return failure
    raw = body.get("input")
    inputs = [raw] if isinstance(raw, str) else list(raw or [])
    if not inputs:
        return _error("invalid_request", "input is required")
    dims = int(body.get("dimensions") or 8)
    data = []
    for index, text in enumerate(inputs):
        seed = hashlib.sha256(str(text).encode("utf-8")).digest()
        vector = [round((seed[i % len(seed)] - 128) / 128, 6) for i in range(dims)]
        embedding: Any = vector
        if body.get("encoding_format") == "base64":
            embedding = base64.b64encode(struct.pack(f"<{dims}f", *vector)).decode("ascii")
        data.append({"object": "embedding", "index": index, "embedding": embedding})
    return 200, {
        "object": "list",
        "data": data,
        "model": model,
        "usage": {"prompt_tokens": 4 * len(inputs), "total_tokens": 4 * len(inputs)},
        "ur": {
            "request_id": getattr(_CURRENT, "request_id", None) or STATE.next_id("req"),
            "call_type": body.get("call_type"),
            "model_served": model,
            "provider": str(model).split("/")[0],
            "routing": {"mode": "off", "fallback_used": False},
            "cost_usd": 0.00001,
            "byok": False,
        },
    }


# ─────────────────────────────── native passthrough ───────────────────────────────


def _passthrough_headers(request_id: str, cost_micro_usd: int = 120) -> dict[str, str]:
    """The ur response headers a non-streaming passthrough call returns."""
    return {"X-UR-Request-Id": request_id, "X-UR-Cost-Micro-USD": str(cost_micro_usd)}


def _openai_responses(body: dict[str, Any]) -> tuple[int, Any, dict[str, str]]:
    """OpenAI Responses passthrough: a verbatim-looking Responses object + the ur headers."""
    model = str(body.get("model") or "gpt-6-sol")
    payload = {
        "id": STATE.next_id("resp"),
        "object": "response",
        "created_at": 1_760_000_000,
        "status": "completed",
        "model": model,
        "output": [
            {
                "type": "message",
                "id": STATE.next_id("msg"),
                "status": "completed",
                "role": "assistant",
                "content": [{"type": "output_text", "text": MOCK_REPLY, "annotations": []}],
            }
        ],
        "usage": {"input_tokens": 11, "output_tokens": 7, "total_tokens": 18},
    }
    return 200, payload, _passthrough_headers(STATE.next_id("req"))


def _anthropic_messages(body: dict[str, Any]) -> tuple[int, Any, dict[str, str]]:
    """Anthropic Messages passthrough: a verbatim-looking Message object + the ur headers."""
    model = str(body.get("model") or "claude-opus-5-5")
    payload = {
        "id": STATE.next_id("msg"),
        "type": "message",
        "role": "assistant",
        "model": model,
        "content": [{"type": "text", "text": MOCK_REPLY}],
        "stop_reason": "end_turn",
        "stop_sequence": None,
        "usage": {
            "input_tokens": 11,
            "cache_read_input_tokens": 0,
            "cache_creation_input_tokens": 0,
            "output_tokens": 7,
        },
    }
    return 200, payload, _passthrough_headers(STATE.next_id("req"))


_MODELS = [
    ("openai/gpt-5.2-mini", "GPT-5.2 mini", "openai", 250_000, 2_000_000),
    ("openai/gpt-5.2", "GPT-5.2", "openai", 1_250_000, 10_000_000),
    ("openai/text-embedding-3-small", "Text Embedding 3 Small", "openai", 20_000, 0),
]


def _model_row(model_id: str, name: str, provider: str, inp: int, out: int) -> dict[str, Any]:
    return {
        "id": model_id,
        "object": "model",
        "name": name,
        "provider": provider,
        "context_length": 128_000,
        "capabilities": {"tools": True, "json_schema": True},
        "pricing": {
            "input_micro_usd_per_1m": inp,
            "output_micro_usd_per_1m": out,
            "cached_input_micro_usd_per_1m": None,
            "input_usd_per_1m": inp / 1_000_000,
            "output_usd_per_1m": out / 1_000_000,
        },
        "active": True,
        "origin_jurisdiction": "us",
        "hosting_jurisdiction": "us",
        "hosting_region": None,
        "weights": "closed",
    }


def _models(query: dict[str, str]) -> dict[str, Any]:
    rows = [_model_row(*m) for m in _MODELS]
    if query.get("provider"):
        rows = [r for r in rows if r["provider"] == query["provider"]]
    return {"object": "list", "data": rows}


def _model_detail(model_id: str) -> tuple[int, Any]:
    for m in _MODELS:
        if m[0] == model_id:
            row = _model_row(*m)
            offer = {
                "provider": row["provider"],
                "model_id": model_id,
                "pricing": row["pricing"],
                "context_length": 128_000,
                "data_policy": None,
                "quantization": None,
                "throughput_rank": 1,
                "hosting_jurisdiction": "us",
                "hosting_region": None,
            }
            return 200, {
                "id": model_id,
                "object": "model",
                "name": row["name"],
                "context_length": 128_000,
                "capabilities": row["capabilities"],
                "offers": [offer],
                "origin_jurisdiction": "us",
                "weights": "closed",
            }
    return _error("not_found", f"unknown model {model_id}")


# ─────────────────────────────── preflight ───────────────────────────────


def _preflight(body: dict[str, Any], if_none_match: str | None) -> tuple[int, Any, dict[str, str]]:
    call_type = body.get("call_type")
    if not call_type:
        status, err = _error("invalid_request", "call_type is required")
        return status, err, {}
    messages = body.get("messages")
    knowledge: dict[str, Any] | None = None
    knowledge_reason: str | None = "no_learned_module"
    prompt: dict[str, Any] | None = None
    content: str | None = None
    if call_type == "support-reply":
        content = "Known fact: refunds are issued within 14 days of approval."
        prompt = {
            "version": 3,
            "template": "You are a {{tone}} support agent for {{brand}}.",
            "variables": [
                {"name": "tone", "required": False},
                {"name": "brand", "required": True},
            ],
            "sha256": hashlib.sha256(b"support-template-v3").hexdigest(),
        }
    elif call_type == "ticket-classifier":
        users = [m for m in (messages or []) if isinstance(m, dict) and m.get("role") == "user"]
        if not users:
            knowledge_reason = "case_query_missing"
        else:
            last = str(users[-1].get("content"))
            content = f"Verified similar case: {last[:40]!r} was labelled 'billing'."
    if content is not None:
        knowledge_reason = None
        knowledge = {
            "module": {
                "id": "lcm_mock",
                "version": "lcm1_" + hashlib.sha256(content.encode()).hexdigest()[:12],
                "kind": "ur:learned",
                "slot": "learned",
                "state": "screened",
                "content_hash": hashlib.sha256(content.encode()).hexdigest(),
                "tokens": max(1, len(content) // 4),
                "content": content,
                "lineage": {
                    "pack_hash": "lcp1_mock",
                    "epoch": 1,
                    "item_ids": ["fact_mock_1"],
                    "ranker_version": "lcr1_mock",
                    "k": 3,
                    "key_spec": "sit1",
                    "source_snapshot": "2026-01-01T00:00:00.000Z",
                },
            },
            "placement": "after_stable_prefix",
            "delivery": "off",
        }
    grant = None
    grant_reason: str | None = "no_cluster_key"
    if body.get("artifact_key") or body.get("trace_id"):
        key = str(body.get("artifact_key") or body.get("trace_id"))
        digest = hashlib.sha256(key.encode()).hexdigest()
        grant = {
            "grant_id": "grant_" + digest[:32],
            "arm": "treated" if int(digest[0], 16) % 2 == 0 else "holdout",
            "lever_id": None,
            "epoch": 1,
            "valid_until_epoch_close": "2026-12-31T00:00:00.000Z",
            "request_id": STATE.next_id("req"),
        }
        grant_reason = None
        if grant["arm"] == "holdout":
            knowledge, knowledge_reason = None, "holdout"
    response = {
        "object": "preflight",
        "config_version": 7,
        "routing": {
            "mode": "candidates",
            "model": {"id": "openai/gpt-5.2-mini", "evidence": "none", "score": None},
            "fallbacks": [{"id": "openai/gpt-5.2", "score": None}],
            "why": None,
            "max_age_s": 30,
        },
        "prompt": prompt,
        "knowledge": knowledge,
        "knowledge_reason": knowledge_reason,
        "grant": grant,
        "grant_reason": grant_reason,
        "provisional": True,
        "reason": "not_benchmarkable",
    }
    config_part = json.dumps(
        {
            k: response[k]
            for k in ("config_version", "routing", "prompt", "knowledge", "knowledge_reason")
        },
        sort_keys=True,
    )
    etag = '"' + hashlib.sha256(config_part.encode()).hexdigest() + '"'
    headers = {"etag": etag, "cache-control": "private, max-age=5", "x-ur-live-max-age": "30"}
    if grant is not None:
        headers["x-ur-grant"] = json.dumps(grant)
    if if_none_match is not None and if_none_match == etag:
        return 304, None, headers
    return 200, response, headers


# ─────────────────────────────── signed endpoints ───────────────────────────────


def _verify(raw: bytes, headers: dict[str, str], prefix: str, secret: str) -> bool:
    timestamp = headers.get(f"x-ur-{prefix}-timestamp", "")
    signature = headers.get(f"x-ur-{prefix}-signature", "")
    if not timestamp or not signature:
        return False
    if abs(time.time() - int(timestamp)) > 900:
        return False
    expected = (
        "sha256="
        + hmac.new(secret.encode(), timestamp.encode() + b"." + raw, hashlib.sha256).hexdigest()
    )
    return hmac.compare_digest(expected, signature)


def _reviewer_events(
    raw: bytes, body: dict[str, Any], headers: dict[str, str], api_key: str
) -> tuple[int, Any]:
    if not _verify(raw, headers, "reviewer", api_key):
        return _error("permission", "invalid_signature: the reviewer signature does not verify")
    rows = []
    counts = {"accepted": 0, "duplicate": 0, "rejected": 0, "unsupported": 0}
    for event in body.get("events", []):
        event_id = str(event.get("event_id"))
        row: dict[str, Any] = {
            "event_id": event_id,
            "artifact_id": event.get("artifact_id") or _artifact_id(str(event.get("artifact_key"))),
            "artifact_version": event.get("artifact_version"),
            "channel": "correction",
            "kind": event.get("decision"),
            "final_version": None,
            "latency_class": "instant",
            "learning_use": ["calibrate"],
            "outcome_event_id": None,
            "reason": "",
            "repairable": False,
        }
        if event.get("artifact_version") == 999:
            row.update(status="rejected", reason="version_mismatch:current=1", repairable=True)
        elif event_id in STATE.seen_events:
            row.update(status="duplicate", reason="already_recorded")
        else:
            STATE.seen_events.add(event_id)
            row.update(status="accepted", outcome_event_id=STATE.next_id("oev"))
        counts[row["status"]] += 1
        rows.append(row)
    return 200, {"object": "reviewer_events", "adapter": "standard", "data": rows, **counts}


def _candidate_decision(
    raw: bytes, body: dict[str, Any], headers: dict[str, str], api_key: str
) -> tuple[int, Any]:
    if not _verify(raw, headers, "appci", api_key):
        return _error("permission", "invalid_signature: the decision signature does not verify")
    callback_id = str(body.get("callback_id"))
    status = "duplicate" if callback_id in STATE.seen_callbacks else "accepted"
    STATE.seen_callbacks.add(callback_id)
    return 200, {"callback_id": callback_id, "learning_use": "audit", "status": status}


def _oracle_signed(
    op_id: str, raw: bytes, body: dict[str, Any], headers: dict[str, str]
) -> tuple[int, Any] | None:
    if not _verify(raw, headers, "oracle", ORACLE_SECRET):
        return _error("permission", "invalid_signature: the oracle signature does not verify")
    return None


# ─────────────────────────────── learning loop ───────────────────────────────


def _served(op_id: str, body: dict[str, Any], headers: dict[str, str]) -> tuple[int, Any, dict]:
    """Serve chat/embeddings with the correlation headers and remember the request."""
    sent = headers.get("x-ur-request-id")
    request_id = sent if sent and _REQUEST_ID.fullmatch(sent) else STATE.next_id("req")
    _CURRENT.request_id = request_id
    try:
        status, payload = _chat(body) if op_id == "createChatCompletion" else _embeddings(body)
    finally:
        _CURRENT.request_id = None
    extra = {"x-ur-request-id": request_id}
    if status == 429:
        extra["retry-after"] = "0"
    if 200 <= status < 300:
        ur = body.get("ur") if isinstance(body.get("ur"), dict) else {}
        episode = headers.get("x-ur-artifact") or ur.get("artifact")
        with STATE.lock:
            STATE.served[request_id] = {"at": time.time(), "episode": episode}
    return status, payload, extra


def _persisted(request_id: str) -> bool:
    served = STATE.served.get(request_id)
    return served is not None and time.time() - served["at"] >= STATE.persist_delay_s


def _iso(at: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(at)) + f".{int(at * 1000) % 1000:03d}Z"


def _component(name: str) -> Any:
    """A deterministic sample of a component schema (the base every hand-written answer
    overrides, so the answer always has the specification's shape)."""
    return sample(resolve(load_spec()["components"]["schemas"][name]), name)


def _op_sample(op_id: str) -> Any:
    _, schema = success_schema(operations()[op_id][2])
    return sample(resolve(schema)) if schema is not None else {}


def _refresh(receipt: dict[str, Any]) -> dict[str, Any]:
    """Reconcile a pending receipt: apply it once its request landed, or expire it."""
    if receipt["status"] != "pending":
        return receipt
    now = time.time()
    request_id = receipt["request_id"]
    if _persisted(request_id):
        served = STATE.served[request_id]
        teaching = receipt["channel"] != "proxy" and bool(served.get("episode"))
        receipt.update(
            status="applied",
            outcome_status="accepted",
            outcome_event_id=STATE.next_id("oev"),
            artifact_id="art_" + hashlib.sha256(request_id.encode()).hexdigest()[:16],
            applied_at=_iso(now),
            updated_at=_iso(now),
            expires_at=_iso(now + STATE.pending_ttl_s),
            episode={
                "status": "associated" if teaching else "not_applicable",
                "trace_id": "ept_"
                + hashlib.sha256(str(served.get("episode")).encode()).hexdigest()[:12]
                if teaching
                else None,
                "verdict": "recorded" if teaching else None,
            },
        )
    elif now >= receipt["_expires"]:
        receipt.update(
            status="expired",
            reason="request_not_found",
            updated_at=_iso(now),
            episode={"status": "not_applicable", "trace_id": None, "verdict": None},
        )
    return receipt


def _public(receipt: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in receipt.items() if not k.startswith("_")}


def _request_outcome(request_id: str, body: dict[str, Any]) -> tuple[int, Any]:
    if request_id == "req_missing":
        return _error(
            "not_found",
            f"request_not_found: '{request_id}' is too old (or too far ahead) to still be in flight",
        )
    if not body.get("channel") or not body.get("kind"):
        return _error("invalid_request", "channel and kind are required")
    key = json.dumps([request_id, body.get("kind"), body.get("source_event_id")])
    payload = json.dumps(body, sort_keys=True)
    with STATE.lock:
        known = STATE.receipt_keys.get(key)
        if known is not None:
            receipt_id, first_payload = known
            if first_payload != payload:
                return _error("conflict", "the same outcome identity with a different payload")
            receipt = _refresh(STATE.receipts[receipt_id])
            return 202, _outcome_answer(receipt, "duplicate")
        now = time.time()
        receipt = {
            "id": STATE.next_id("ocr"),
            "object": "outcome_receipt",
            "request_id": request_id,
            "status": "pending",
            "reason": None,
            "episode": {"status": "pending", "trace_id": None, "verdict": None},
            "channel": body.get("channel"),
            "kind": body.get("kind"),
            "source_event_id": body.get("source_event_id") or STATE.next_id("sev"),
            "outcome_event_id": None,
            "outcome_status": None,
            "artifact_id": None,
            "attempts": 0,
            "created_at": _iso(now),
            "updated_at": _iso(now),
            "applied_at": None,
            "expires_at": _iso(now + STATE.pending_ttl_s),
            "_expires": now + STATE.pending_ttl_s,
        }
        STATE.receipts[receipt["id"]] = receipt
        STATE.receipt_keys[key] = (receipt["id"], payload)
        _refresh(receipt)
        status = "accepted" if receipt["status"] == "applied" else "pending"
        return 202, _outcome_answer(receipt, status)


def _outcome_answer(receipt: dict[str, Any], status: str) -> dict[str, Any]:
    teaches = receipt["channel"] != "proxy"
    answer = _op_sample("recordRequestOutcome")
    answer.update(
        id=receipt["outcome_event_id"],
        status=status,
        source_event_id=receipt["source_event_id"],
        source="declared",
        latency_class="instant",
        learning_use=["train", "calibrate"] if teaches else ["rank"],
        target_kind="artifact",
        artifact_id=receipt["artifact_id"],
        canonical_target_id=receipt["artifact_id"],
        artifact_version=1 if receipt["artifact_id"] else None,
        reason=None,
        receipt=_public(receipt),
    )
    return answer


_LEARNING = re.compile(r"^/v1/call-types/([^/]+)/learning(?:/(.*))?$")
_RECEIPT = re.compile(r"^/v1/outcome-receipts/([^/]+)$")
_REQUEST_RECEIPTS = re.compile(r"^/v1/requests/([^/]+)/outcome-receipts$")


def _learning_routes(method: str, path: str, body: dict[str, Any]) -> tuple[int, Any] | None:
    """Stateful answers for the learning loop (receipts and learning controls)."""
    match = _RECEIPT.match(path)
    if match and method == "GET":
        if unquote(match.group(1)) == "ocr_sample":
            sample_receipt = _op_sample("getOutcomeReceipt")
            sample_receipt.update(id="ocr_sample", status="applied")
            return 200, sample_receipt
        with STATE.lock:
            receipt = STATE.receipts.get(unquote(match.group(1)))
            if receipt is None:
                return _error("not_found", "receipt not found")
            return 200, _public(_refresh(receipt))
    match = _REQUEST_RECEIPTS.match(path)
    if match and method == "GET":
        request_id = unquote(match.group(1))
        with STATE.lock:
            rows = [
                _public(_refresh(r))
                for r in STATE.receipts.values()
                if r["request_id"] == request_id
            ]
        return 200, {"object": "list", "data": rows}
    match = _LEARNING.match(path)
    if match is None:
        return None
    return _learning(method, unquote(match.group(1)), match.group(2) or "", body)


_DEFAULT_POLICY = {
    "mode": "evaluate",
    "objective": "success",
    "min_verified_per_arm": 30,
    "max_verified_per_arm": 200,
    "alpha": 0.05,
    "min_effect_pp": 0.0,
    "noninferiority_margin_pp": 5.0,
    "candidate_share": 0.5,
    "max_duration_hours": 720,
}


def _learning_state(call_type: str) -> dict[str, Any]:
    state = STATE.learning.get(call_type)
    if state is None:
        state = STATE.learning[call_type] = {
            "enabled": False,
            "governed": False,
            "paused": False,
            "disabled": False,
            "policy": None,
            "model": None,
            "recipe": None,
            "versions": [],
            "active": None,
            "evaluations": [],
        }
        if call_type == "support-reply":  # an already-enabled call type, for one-call examples
            state.update(
                enabled=True,
                governed=True,
                policy=dict(_DEFAULT_POLICY),
                model="openai/gpt-5.2-mini",
                recipe={
                    "validator": "elv2",
                    "generation": "atomic",
                    "observations": "elo2",
                    "legacy": False,
                },
            )
            _seed_versions(state)
    return state


def _version(state: dict[str, Any], version_id: str) -> dict[str, Any] | None:
    return next((v for v in state["versions"] if v["id"] == version_id), None)


def _version_ref(version: dict[str, Any] | None) -> dict[str, Any] | None:
    if version is None:
        return None
    return {
        k: version[k] for k in ("id", "version", "state", "digest", "active_lessons", "created_at")
    }


def _version_row(version: dict[str, Any]) -> dict[str, Any]:
    row = _component("LearningVersion")
    row.update({k: v for k, v in version.items() if k in row})
    return row


def _version_detail(version: dict[str, Any]) -> dict[str, Any]:
    detail = _component("LearningVersionDetail")
    detail.update({k: v for k, v in version.items() if k in detail})
    detail["lessons"] = version["lessons"]
    detail["transitions"] = version["transitions"]
    return detail


def _learning_status(call_type: str, state: dict[str, Any]) -> dict[str, Any]:
    status = _component("LearningStatus")
    running = next((e for e in state["evaluations"] if e["decision"] == "running"), None)
    candidate = next(
        (v for v in reversed(state["versions"]) if v["state"] in ("candidate", "evaluating")), None
    )
    if not state["enabled"]:
        code, reason = ("disabled", "disabled") if state["disabled"] else ("off", "not_enabled")
    elif call_type == "quota-out":
        code, reason = "quota_exhausted", "provider_quota_exhausted"
    elif call_type == "budget-out":
        code, reason = "budget_exhausted", "failure_ceiling_reached"
    elif state["paused"]:
        code, reason = "paused", "paused"
    elif running is not None:
        code, reason = "learning", "evaluation_running"
    else:
        code, reason = "collecting", "waiting_for_evidence"
    status.update(
        object="learning",
        call_type_id=call_type,
        enabled=state["enabled"],
        governed=state["governed"],
        self_serve=state["governed"],
        paused=state["paused"],
        state=code,
        reason=reason,
        active_version=_version_ref(_version(state, state["active"]) if state["active"] else None),
        latest_candidate=_version_ref(candidate),
        evaluation=running,
        last_evaluation=state["evaluations"][-1] if state["evaluations"] else None,
        promotion=state["policy"],
        recipe=state["recipe"],
    )
    status["budget"]["state"] = code if code in ("quota_exhausted", "budget_exhausted") else "ok"
    status["reflection"]["model"] = state["model"]
    status["reflection"]["provider"].update(
        available=state["enabled"], reason=None if state["enabled"] else "no_reflection_model"
    )
    status["evidence"].update(recorded=12, verified=9, verified_pass=6, verified_fail=3, unknown=3)
    return status


def _control(
    call_type: str,
    state: dict[str, Any],
    action: str,
    changed: bool = True,
    version_id: str | None = None,
    stopped: str | None = None,
) -> tuple[int, Any]:
    return 200, {
        "object": "learning_control",
        "action": action,
        "call_type_id": call_type,
        "changed": changed,
        "version_id": version_id,
        "stopped_evaluation_id": stopped,
        "learning": _learning_status(call_type, state),
    }


_SEEDED = ("epb_1", "retired"), ("epb_2", "active"), ("epb_3", "evaluating")


def _day(number: int) -> str:
    """Midnight UTC on day ``number`` of October 2026, ISO-8601 with milliseconds."""
    return time.strftime(
        "%Y-%m-%dT%H:%M:%S.000Z", time.gmtime(1_790_812_800 + 86_400 * (number - 1))
    )


_LESSONS = [
    {"id": "lsn_1", "text": "Check stock before reserving.", "evidence_cases": 4},
    {"id": "lsn_2", "text": "Backorder when stock is short.", "evidence_cases": 3},
    {"id": "lsn_3", "text": "Handle orders in the order the task names them.", "evidence_cases": 2},
]


def _seed_versions(state: dict[str, Any]) -> None:
    """Three versions (``epb_1`` retired, ``epb_2`` active, ``epb_3`` evaluating) and the running
    evaluation ``lev_1`` of ``epb_3`` against ``epb_2``."""
    if state["versions"]:
        return
    for number, (version_id, version_state) in enumerate(_SEEDED, start=1):
        version = _component("LearningVersionDetail")
        version.update(
            id=version_id,
            version=number,
            state=version_state,
            state_reason=None,
            parent_id=f"epb_{number - 1}" if number > 1 else None,
            active_lessons=number,
            digest=f"epb1_{number:032x}",
            created_at=_day(number),
            evaluation_id="lev_1" if version_state == "evaluating" else None,
            reflection_model=state["model"],
            recipe="elv2-atomic-elo2",
            lessons=_LESSONS[:number],
            transitions=[
                {
                    "state": version_state,
                    "reason": "published",
                    "at": _day(number),
                    "actor_type": "system",
                    "actor_id": None,
                    "evaluation_id": None,
                }
            ],
        )
        version["cohort"] = {"size": 4 * number, "pass": 3 * number, "fail": number}
        state["versions"].append(version)
    state["active"] = "epb_2"
    evaluation = _component("LearningEvaluation")
    evaluation.update(
        id="lev_1",
        object="learning_evaluation",
        candidate_version_id="epb_3",
        incumbent_version_id="epb_2",
        decision="running",
        decision_reason="window_open",
        decided_at=None,
        decided_by=None,
        difference={"lower": -0.125, "point": 0.2, "upper": 0.52},
    )
    evaluation["arms"] = {
        "candidate": {
            "verified": 7,
            "pass": 5,
            "unknown": 1,
            "success_rate": 5 / 7,
            "cost_micro_usd": None,
            "mean_cost_micro_usd": None,
        },
        "incumbent": {
            "verified": 6,
            "pass": 3,
            "unknown": 0,
            "success_rate": 0.5,
            "cost_micro_usd": None,
            "mean_cost_micro_usd": None,
        },
    }
    state["evaluations"] = [evaluation]


def _stop_running(state: dict[str, Any]) -> str | None:
    for evaluation in state["evaluations"]:
        if evaluation["decision"] == "running":
            evaluation.update(decision="stopped_manual", decision_reason="manual_decision")
            return str(evaluation["id"])
    return None


def _learning(method: str, call_type: str, rest: str, body: dict[str, Any]) -> tuple[int, Any]:
    if call_type == "ct_missing":
        return _error("not_found", f"call type '{call_type}' not found")
    if method == "POST" and call_type == "read-only":
        return _error("permission", "this key lacks the config:write scope")
    with STATE.lock:
        state = _learning_state(call_type)
        if rest == "tool-documentation" and method in {"GET", "PUT"}:
            if method == "PUT":
                state["tool_documentation"] = {
                    "object": "learning_tool_documentation",
                    "call_type_id": call_type,
                    "tool_count": len(body["tools"]),
                    "digest": "etd1_mock" if body["tools"] else None,
                    "updated_at": None,
                    "tools": [],
                    "changed": True,
                }
            return 200, state.get(
                "tool_documentation",
                {
                    "object": "learning_tool_documentation",
                    "call_type_id": call_type,
                    "tool_count": 0,
                    "digest": None,
                    "updated_at": None,
                    "tools": [],
                },
            )
        if method == "GET" and rest == "":
            return 200, _learning_status(call_type, state)
        if method == "POST" and rest == "enable":
            if call_type == "no-consent":
                return _error(
                    "conflict",
                    "corrections_consent_required: learning stores episode content, so the "
                    "workspace corrections consent must be on",
                )
            if call_type == "no-provider":
                return _error(
                    "invalid_request",
                    f"reflection_model_not_workspace_owned (no_workspace_key): "
                    f"'{body.get('reflection_model')}' must resolve to a workspace-owned offer",
                )
            promotion = body.get("promotion") or {}
            if int(promotion.get("min_verified_per_arm", 30)) < 1:
                return _error("invalid_request", "promotion_invalid (min_verified_per_arm_range)")
            policy = {**(state["policy"] or _DEFAULT_POLICY), **promotion}
            changed = not state["enabled"]
            state.update(
                enabled=True,
                governed=True,
                disabled=False,
                policy=policy,
                model=body.get("reflection_model"),
                recipe={
                    "validator": "elv1",
                    "generation": "bundled",
                    "observations": "legacy",
                    **(body.get("recipe") or {}),
                    "legacy": not body.get("recipe"),
                },
            )
            _seed_versions(state)
            return _control(call_type, state, "enable", changed)
        if method == "POST" and rest in ("pause", "resume", "disable"):
            if rest != "disable" and not state["governed"]:
                return _error(
                    "conflict",
                    "learning_not_enabled: learning is not enabled for this call type through "
                    "the learning API — POST …/learning/enable first",
                )
            before = (state["paused"], state["enabled"])
            if rest == "pause":
                state["paused"] = True
            elif rest == "resume":
                state["paused"] = False
            else:
                state.update(enabled=False, disabled=True)
            return _control(call_type, state, rest, (state["paused"], state["enabled"]) != before)
        if method == "GET" and rest == "versions":
            rows = [_version_row(v) for v in reversed(state["versions"])]
            return 200, {"object": "list", "data": rows}
        if method == "GET" and rest == "evaluations":
            return 200, {"object": "list", "data": list(reversed(state["evaluations"]))}
        if method == "POST" and rest == "rollback":
            if not state["governed"]:
                return _error("conflict", "learning_not_enabled: enable learning first")
            target_id = body.get("version_id")
            active = _version(state, state["active"]) if state["active"] else None
            target = _version(state, target_id) if target_id else None
            if target_id is None:
                earlier = [
                    v for v in state["versions"] if active and v["version"] < active["version"]
                ]
                target = earlier[-1] if earlier else None
                if target is None:
                    return _error("conflict", "no_rollback_target: there is no earlier version")
            if target is None:
                return _error("not_found", f"version '{target_id}' not found")
            if active is not None and target["version"] >= active["version"]:
                return _error(
                    "conflict",
                    "rollback_target_not_earlier: pick a version older than the active one",
                )
            stopped = _stop_running(state)
            if active is not None:
                active["state"] = "retired"
            target["state"] = "active"
            state["active"] = target["id"]
            return _control(call_type, state, "rollback", True, target["id"], stopped)
        parts = rest.split("/")
        if len(parts) >= 2 and parts[0] == "versions":
            version = _version(state, unquote(parts[1]))
            if version is None:
                return _error("not_found", f"version '{unquote(parts[1])}' not found")
            if method == "GET" and len(parts) == 2:
                return 200, _version_detail(version)
            if method == "POST" and len(parts) == 3 and parts[2] in ("promote", "reject"):
                if not state["governed"]:
                    return _error("conflict", "learning_not_enabled: enable learning first")
                if parts[2] == "promote":
                    if version["id"] == state["active"]:
                        return _error("conflict", "version_already_active: it is already active")
                    stopped = _stop_running(state)
                    for other in state["versions"]:
                        if other["state"] == "active":
                            other["state"] = "retired"
                    version.update(state="active", state_reason="manual_promote")
                    state["active"] = version["id"]
                else:
                    if version["id"] == state["active"]:
                        return _error("conflict", "version_active: roll back instead")
                    stopped = _stop_running(state)
                    version.update(state="rejected", state_reason="manual_reject")
                return _control(call_type, state, parts[2], True, version["id"], stopped)
    return _error("not_found", f"no learning route {method} {rest}")


# ─────────────────────────────── generic synthesis ───────────────────────────────


def _synthesize(op: dict[str, Any], params: list[str]) -> tuple[int, Any]:
    status, schema = success_schema(op)
    if schema is None:
        return status, {"object": "list", "data": []}
    payload = sample(resolve(schema))
    if isinstance(payload, dict) and params:
        # Echo path parameters into id-like fields where the shape has them.
        for key in ("id", "call_type_id", "oracle_id", "candidate_ref", "check_id", "bench_run_id"):
            if key in payload and isinstance(payload[key], str):
                payload[key] = unquote(params[0])
                break
    return status, payload


class Handler(BaseHTTPRequestHandler):
    """Routes one HTTP request to a mock behaviour."""

    server_version = "ultrarouter-mock/1"
    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args: Any) -> None:
        """Silence the default stderr access log."""

    # ── plumbing ──
    def _read(self) -> bytes:
        length = int(self.headers.get("content-length") or 0)
        return self.rfile.read(length) if length else b""

    def _take_slow(self, path: str) -> dict[str, Any] | None:
        with STATE.lock:
            for slow in STATE.slow:
                if slow.get("path") == path and int(slow.get("times", 1)) > 0:
                    slow["times"] = int(slow.get("times", 1)) - 1
                    return dict(slow)
        return None

    def _send(self, status: int, payload: Any, headers: dict[str, str] | None = None) -> None:
        try:
            self._send_inner(status, payload, headers)
        except (BrokenPipeError, ConnectionResetError):
            self.close_connection = True  # the client gave up (for example on its deadline)

    def _send_inner(self, status: int, payload: Any, headers: dict[str, str] | None) -> None:
        extra = dict(headers or {})
        slow = self._take_slow(getattr(self, "_current_path", ""))
        chunk_delay = float(slow.get("chunk_delay", 0.0)) if slow else 0.0
        if slow and float(slow.get("header_delay", 0.0)) > 0:
            time.sleep(float(slow["header_delay"]))
        if isinstance(payload, tuple) and payload and payload[0] == "sse":
            self.send_response(status)
            self.send_header("content-type", "text/event-stream")
            self.send_header("cache-control", "no-cache")
            self.send_header("connection", "close")
            for k, v in extra.items():
                self.send_header(k, v)
            self.end_headers()
            for frame in payload[1]:
                if chunk_delay:
                    time.sleep(chunk_delay)
                self.wfile.write(frame.encode("utf-8"))
                self.wfile.flush()
            self.close_connection = True
            return
        if status == 304 or payload is None:
            self.send_response(status)
            for k, v in extra.items():
                self.send_header(k, v)
            self.send_header("content-length", "0")
            self.end_headers()
            return
        if isinstance(payload, str):
            data = payload.encode("utf-8")
            content_type = extra.pop("content-type", "text/plain; charset=utf-8")
        else:
            data = json.dumps(payload).encode("utf-8")
            content_type = "application/json"
        self.send_response(status)
        self.send_header("content-type", content_type)
        self.send_header("content-length", str(len(data)))
        for k, v in extra.items():
            self.send_header(k, v)
        self.end_headers()
        if not chunk_delay:
            self.wfile.write(data)
            return
        pieces = max(1, int(slow.get("chunks", 8))) if slow else 1
        size = -(-len(data) // pieces)
        self.wfile.flush()
        for start in range(0, len(data), size):
            time.sleep(chunk_delay)
            self.wfile.write(data[start : start + size])
            self.wfile.flush()

    def do_GET(self) -> None:
        """Handle GET."""
        self._dispatch("GET")

    def do_POST(self) -> None:
        """Handle POST."""
        self._dispatch("POST")

    def do_PATCH(self) -> None:
        """Handle PATCH."""
        self._dispatch("PATCH")

    def do_PUT(self) -> None:
        """Handle PUT."""
        self._dispatch("PUT")

    def do_DELETE(self) -> None:
        """Handle DELETE."""
        self._dispatch("DELETE")

    def _dispatch(self, method: str) -> None:
        split = urlsplit(self.path)
        path = split.path
        query = {k: v[-1] for k, v in parse_qs(split.query).items()}
        raw = self._read()
        headers = {k.lower(): v for k, v in self.headers.items()}
        body: Any = None
        if raw:
            try:
                body = json.loads(raw)
            except ValueError:
                body = raw.decode("utf-8", "replace")
        self._current_path = "" if path.startswith("/__mock__/") else path
        if path.startswith("/__mock__/"):
            self._control(method, path, body)
            return
        with STATE.lock:
            STATE.requests.append(
                {"method": method, "path": path, "query": query, "headers": headers, "body": body}
            )
        status, payload, extra = self._route(method, path, query, headers, raw, body)
        if self._take_drop(path):
            self.close_connection = True  # processed, but the acknowledgement is lost
            return
        self._send(status, payload, extra)

    def _take_drop(self, path: str) -> bool:
        with STATE.lock:
            for drop in STATE.drops:
                if drop.get("path") == path and int(drop.get("times", 1)) > 0:
                    drop["times"] = int(drop.get("times", 1)) - 1
                    return True
        return False

    def _control(self, method: str, path: str, body: Any) -> None:
        if path == "/__mock__/requests" and method == "GET":
            with STATE.lock:
                self._send(200, {"data": list(STATE.requests)})
            return
        if path == "/__mock__/reset" and method == "POST":
            STATE.reset()
            self._send(200, {"ok": True})
            return
        if path == "/__mock__/fail" and method == "POST" and isinstance(body, dict):
            with STATE.lock:
                STATE.failures.append(dict(body))
            self._send(200, {"ok": True})
            return
        if path == "/__mock__/drop" and method == "POST" and isinstance(body, dict):
            with STATE.lock:
                STATE.drops.append(dict(body))
            self._send(200, {"ok": True})
            return
        if path == "/__mock__/learning" and method == "POST" and isinstance(body, dict):
            with STATE.lock:
                if "persist_delay_s" in body:
                    STATE.persist_delay_s = float(body["persist_delay_s"])
                if "pending_ttl_s" in body:
                    STATE.pending_ttl_s = float(body["pending_ttl_s"])
            self._send(200, {"ok": True})
            return
        if path == "/__mock__/slow" and method == "POST" and isinstance(body, dict):
            with STATE.lock:
                STATE.slow.append(dict(body))
            self._send(200, {"ok": True})
            return
        self._send(404, {"error": {"code": "not_found", "message": "unknown control endpoint"}})

    def _scripted_failure(self, path: str) -> tuple[int, Any, dict[str, str]] | None:
        with STATE.lock:
            for failure in STATE.failures:
                if failure.get("path") == path and int(failure.get("times", 1)) > 0:
                    failure["times"] = int(failure.get("times", 1)) - 1
                    code = str(failure.get("code", "provider_unavailable"))
                    status = int(failure.get("status", 503))
                    break
            else:
                return None
        message = failure.get("message") or f"scripted failure ({code})"
        status, payload = _error(code, str(message), status)
        headers = {"retry-after": str(failure["retry_after"])} if "retry_after" in failure else {}
        return status, payload, headers

    def _route(
        self,
        method: str,
        path: str,
        query: dict[str, str],
        headers: dict[str, str],
        raw: bytes,
        body: Any,
    ) -> tuple[int, Any, dict[str, str]]:
        auth = headers.get("authorization", "")
        api_key = auth[len("Bearer ") :] if auth.startswith("Bearer ") else ""
        if not api_key.startswith("ur_sk_") or "invalid" in api_key:
            status, payload = _error("authentication", "missing or invalid API key")
            return status, payload, {}
        failure = self._scripted_failure(path)
        if failure is not None:
            return failure
        learning = _learning_routes(method, path, body if isinstance(body, dict) else {})
        if learning is not None:
            return (*learning, {})
        for regex, op_method, op_id, op in _ROUTES:
            match = regex.match(path)
            if match is None or op_method != method:
                continue
            params = list(match.groups())
            data = body if isinstance(body, dict) else {}
            return self._operation(op_id, op, params, query, headers, raw, data)
        status, payload = _error("not_found", f"no route for {method} {path}")
        return status, payload, {}

    def _operation(
        self,
        op_id: str,
        op: dict[str, Any],
        params: list[str],
        query: dict[str, str],
        headers: dict[str, str],
        raw: bytes,
        body: dict[str, Any],
    ) -> tuple[int, Any, dict[str, str]]:
        api_key = headers.get("authorization", "")[len("Bearer ") :]
        if op_id in ("createChatCompletion", "createEmbeddings"):
            return _served(op_id, body, headers)
        if op_id == "recordRequestOutcome":
            return (*_request_outcome(unquote(params[0]), body), {})
        if op_id == "listModels":
            return 200, _models(query), {}
        if op_id == "getModel":
            return (*_model_detail(unquote(params[0])), {})
        if op_id == "createResponse":
            return _openai_responses(body)
        if op_id == "createMessage":
            return _anthropic_messages(body)
        if op_id == "preflight":
            return _preflight(body, headers.get("if-none-match"))
        if op_id == "recordReviewerEvents":
            return (*_reviewer_events(raw, body, headers, api_key), {})
        if op_id == "recordCandidateDecision":
            return (*_candidate_decision(raw, body, headers, api_key), {})
        if op_id in ("claimOracleJobs", "submitOracleVerdicts"):
            refused = _oracle_signed(op_id, raw, body, headers)
            if refused is not None:
                return (*refused, {})
        if op_id == "getGeneration":
            request_id = query.get("id", "")
            if not request_id or request_id == "req_missing":
                return (*_error("not_found", f"unknown request {request_id}"), {})
            status, payload = _synthesize(op, [])
            payload["id"] = request_id
            payload["status"] = "ok"
            return status, payload, {}
        if op_id == "getBenchRunReport" and query.get("format") in ("md", "bundle"):
            text = "# Bench report\n\nMock report for " + unquote(params[0]) + "\n"
            return 200, text, {"content-type": "text/markdown; charset=utf-8"}
        if op_id == "recordFlywheelExperimentExecutionOutcome" and query.get("dry_run") == "true":
            # The generic sampler always picks the first oneOf branch (the recorded shape); answer
            # the dry-run branch explicitly so the ?dry_run=true path is exercised end to end.
            return (
                200,
                {
                    "object": "flywheel_experiment_execution_outcome_dry_run",
                    "experiment_id": unquote(params[0]),
                    "execution_id": unquote(params[1]),
                    "status": "complete",
                    "refusal": None,
                    "detail": None,
                    "recorded_outcome": "none",
                    "outcome_hash": "0" * 64,
                    "trusted_recorded": [],
                    "missing_request_ids": [],
                    "unlisted_request_ids": [],
                    "open_holds": [],
                },
                {},
            )
        status, payload = _synthesize(op, params)
        self._shape(op_id, payload, params, body)
        return status, payload, {}

    def _shape(self, op_id: str, payload: Any, params: list[str], body: dict[str, Any]) -> None:
        """Make synthesized payloads coherent with the request where it matters."""
        if not isinstance(payload, dict):
            return
        if op_id == "createArtifact" and isinstance(payload.get("artifact"), dict):
            key = str(body.get("key"))
            payload["artifact"].update(key=key, id=_artifact_id(key))
            if body.get("grant_id"):
                payload["artifact"]["grant_id"] = body["grant_id"]
        if op_id == "getArtifact" and isinstance(payload.get("artifact"), dict):
            payload["artifact"]["id"] = unquote(params[0])
        if op_id in ("recordArtifactOutcomes", "recordOutcomesBatch"):
            rows = []
            template = payload["data"][0]
            for event in body.get("outcomes", []):
                row = dict(template)
                event_key = json.dumps([params, event.get("source_event_id"), event.get("kind")])
                row["status"] = "duplicate" if event_key in STATE.seen_outcomes else "accepted"
                STATE.seen_outcomes.add(event_key)
                row["source_event_id"] = event.get("source_event_id")
                rows.append(row)
            payload["data"] = rows
            if op_id == "recordOutcomesBatch":
                payload["accepted"] = sum(1 for r in rows if r["status"] == "accepted")
                payload["duplicate"] = sum(1 for r in rows if r["status"] == "duplicate")
                payload["conflict"] = payload["rejected"] = 0
        if op_id == "recordRequestOutcome":
            payload["status"] = "accepted"
            payload["source_event_id"] = body.get("source_event_id")
        if op_id == "triggerBenchRun":
            payload["dry_run"] = bool(body.get("dry_run"))
            payload["bench_run_id"] = None if body.get("dry_run") else "bench_run_000001"
        if op_id == "getBenchRun":
            payload["status"] = "complete"
            payload["id"] = unquote(params[0])
        if op_id == "getBenchCompareGate":
            payload["verdict"] = "pass"
        if op_id == "registerOracle":
            payload["secret"] = ORACLE_SECRET if body.get("transport") in ("push", "pull") else None
        if op_id == "submitFeedback" and isinstance(payload.get("feedback"), dict):
            payload["feedback"]["rating"] = body.get("rating", 1)
            payload["feedback"]["request_id"] = unquote(params[0])
            payload["feedback"]["tags"] = body.get("tags", [])
        if op_id == "enqueueCallTypeEval":
            payload.update(
                {
                    "object": "eval_run",
                    "enqueued": True,
                    "run_id": "evr_000001",
                    "candidate_count": 2,
                }
            )
            for key in ("deduped", "reason", "prior_run_id", "status", "trigger"):
                payload.pop(key, None)
        if op_id == "getHostedPrompt" and len(params) > 1:
            payload["version"] = int(unquote(params[1])) if unquote(params[1]).isdigit() else 1


def serve(port: int = 0, host: str = "127.0.0.1") -> ThreadingHTTPServer:
    """Create (not start) a mock server bound to ``host:port`` (``0`` picks a free port)."""
    server = ThreadingHTTPServer((host, port), Handler)
    server.daemon_threads = True
    return server


def start_in_thread(port: int = 0) -> tuple[ThreadingHTTPServer, str]:
    """Start a server on a background thread; return it and its base URL."""
    server = serve(port)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, bound = server.server_address[:2]
    return server, f"http://{host}:{bound}"


def main(argv: list[str] | None = None) -> int:
    """Run the mock gateway in the foreground."""
    parser = argparse.ArgumentParser(description="Local mock of the ultrarouter gateway.")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--print-url", action="store_true", help="print the base URL, then serve")
    args = parser.parse_args(argv)
    server = serve(args.port, args.host)
    host, bound = server.server_address[:2]
    url = f"http://{host}:{bound}"
    if args.print_url:
        print(url, flush=True)
    else:
        print(f"ultrarouter mock gateway listening on {url}", file=sys.stderr, flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
