"""``from_messages``: lift a plain OpenAI ``messages`` list into a labelled manifest.

The labels come from the same segmentation rules the gateway uses. The manifest records how
each message was built, so :func:`ultrarouter.context.to_messages` can rebuild the exact input:
leaving the runtime is always a pure function.
"""

from __future__ import annotations

import math
from typing import Any

from ._hash import hash_context_value, sha256_hex
from ._manifest import scaffold_subject
from ._profile import encode_ultrarouter_manifest
from ._segment import segment, utf16_length

__all__ = ["from_messages"]

_SLOT_BY_KIND: dict[str, str] = {
    "system_instructions": "instruction",
    "user_question": "instruction",
    "reference_context": "reference",
    "few_shot_examples": "exemplar",
    "tool_schemas": "reference",
    "tool_results": "reference",
    "history": "reference",
    "output_contract": "instruction",
}

_MEMORY_CLASS_BY_KIND: dict[str, str] = {
    "system_instructions": "procedural",
    "user_question": "working",
    "reference_context": "semantic",
    "few_shot_examples": "episodic",
    "tool_schemas": "procedural",
    "tool_results": "working",
    "history": "episodic",
    "output_contract": "procedural",
}


def _estimate_tokens(text: str | None) -> int:
    if text is None:
        return 0
    return math.ceil(utf16_length(text) / 4)


def _build_message_record(index: int, source: dict[str, Any] | None) -> dict[str, Any]:
    if source is None:
        return {
            "index": index,
            "keyOrder": ["role", "content"],
            "scaffold": {},
            "contentIsString": False,
            "rawContent": None,
        }
    key_order = list(source.keys())
    scaffold = {key: source[key] for key in key_order if key != "content"}
    return {
        "index": index,
        "keyOrder": key_order,
        "scaffold": scaffold,
        "contentIsString": isinstance(source.get("content"), str),
        "rawContent": source.get("content"),
    }


def from_messages(
    messages: list[dict[str, Any]], hints: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    """Lift an OpenAI ``messages`` array into a labelled manifest via the gateway segmenter.
    ``hints`` are the SDK ``ur.segments`` labels (same input the gateway honours). Pure.

    Returns ``{"manifest", "labels", "unparseable", "warnings"?}``."""
    request: dict[str, Any] = {"messages": messages}
    if hints is not None:
        request["segments"] = hints
    segments = segment(request)

    labels: list[dict[str, Any]] = []
    entries: list[dict[str, Any]] = []
    message_records: dict[int, dict[str, Any]] = {}

    order = 0
    for part in segments["parts"]:
        if part["origin"] != "message":
            continue
        message_index = part["messageIndex"]
        text = part["text"]
        start = part.get("spanStart", 0)
        span_end = part.get("spanEnd")
        end = span_end if span_end is not None else (utf16_length(text) if text is not None else 0)

        label: dict[str, Any] = {
            "messageIndex": message_index,
            "kind": part["kind"],
            "eligible": part["eligible"],
        }
        if text is not None:
            label["range"] = {"start": start, "end": end}
        labels.append(label)

        is_instruction_source = part["kind"] in ("system_instructions", "user_question")
        entries.append(
            {
                "moduleId": f"seg:{order}",
                "version": "1",
                "kind": part["kind"],
                "memoryClass": _MEMORY_CLASS_BY_KIND[part["kind"]],
                "trustClass": "approved_derived" if is_instruction_source else "untrusted",
                "privacyClass": "workspace_private",
                "contentHash": sha256_hex(text if text is not None else ""),
                "order": order,
                "mandatory": is_instruction_source,
                "tokenEstimate": _estimate_tokens(text),
                "slot": _SLOT_BY_KIND[part["kind"]],
                "range": {"messageIndex": message_index, "start": start, "end": end},
                "ext": {
                    "origin": "message",
                    "messageIndex": message_index,
                    "role": part["role"],
                    "text": text,
                },
            }
        )
        order += 1

        if message_index not in message_records:
            source = messages[message_index] if message_index < len(messages) else None
            message_records[message_index] = _build_message_record(message_index, source)

    lift_ext = {"messages": sorted(message_records.values(), key=lambda record: record["index"])}
    ext = {"lift": lift_ext}
    envelope_hash = hash_context_value(
        {"lift": [record["index"] for record in lift_ext["messages"]]}
    )
    scaffold_hash = hash_context_value(scaffold_subject(entries))
    encoder_input: dict[str, Any] = {
        "envelopeId": "lift",
        "stage": "lift",
        "entries": entries,
        "refused": [],
        "budgets": {
            "tokensAdmitted": sum(entry["tokenEstimate"] for entry in entries),
            "tokenLimit": None,
            "admitted": len(entries),
            "refused": 0,
        },
        "envelopeHash": envelope_hash,
        "scaffoldHash": scaffold_hash,
        "ext": ext,
    }
    encoded = encode_ultrarouter_manifest(encoder_input)

    manifest = dict(encoder_input)
    manifest["manifestHash"] = encoded["hash"]

    result: dict[str, Any] = {
        "manifest": manifest,
        "labels": labels,
        "unparseable": segments["unparseable"],
    }
    if "warnings" in segments:
        result["warnings"] = segments["warnings"]
    return result
