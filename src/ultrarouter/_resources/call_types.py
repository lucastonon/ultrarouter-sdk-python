"""``client.call_types``: call types, their config, evals, hosted prompts and verified memory."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Literal

from .._base_client import RequestOptions
from .._types import NOT_GIVEN, NotGiven, compact, is_given
from ..types import (
    CallType,
    CallTypeList,
    EnqueueEvalResponse,
    EvalRunList,
    HostedPrompt,
    HostedPromptActivation,
    HostedPromptList,
    HostedPromptProposal,
    HostedPromptVariableParam,
    SelfImproveGuardrailsParams,
    VerifiedMemoryDisableResult,
    VerifiedMemoryEnableResult,
    VerifiedMemoryStatus,
)
from ._base import AsyncAPIResource, SyncAPIResource, build, seg

__all__ = [
    "AsyncCallTypes",
    "AsyncHostedPrompts",
    "AsyncVerifiedMemory",
    "CallTypes",
    "HostedPrompts",
    "VerifiedMemory",
]

CompressionModeParam = Literal["off", "semantic_safe", "adaptive", "lossless", "auto"]
RouterModeParam = Literal["pinned", "auto", "candidates", "off"]
LearnedContextDelivery = Literal["gateway_inject_after_stable_prefix", "off"]
SelfImproveMode = Literal["off", "assist", "autopilot"]


def _config_body(
    *,
    model_pin: str | NotGiven | None,
    router_mode: RouterModeParam | NotGiven | None,
    compression_mode: CompressionModeParam | NotGiven | None,
    fallbacks: Sequence[str] | NotGiven,
    provider_prefs: Mapping[str, Any] | NotGiven | None,
    learned_context_delivery: LearnedContextDelivery | NotGiven,
    case_precedents_enabled: bool | NotGiven,
    self_improve_mode: SelfImproveMode | NotGiven,
    self_improve_guardrails: SelfImproveGuardrailsParams | Mapping[str, Any] | NotGiven,
) -> dict[str, Any]:
    fields: dict[str, Any] = {
        "model_pin": model_pin,
        "router_mode": router_mode,
        "compression_mode": compression_mode,
        "fallbacks": NOT_GIVEN if isinstance(fallbacks, NotGiven) else list(fallbacks),
        "provider_prefs": provider_prefs,
        "learned_context_delivery": learned_context_delivery,
        "case_precedents_enabled": case_precedents_enabled,
        "self_improve_mode": self_improve_mode,
        "self_improve_guardrails": self_improve_guardrails,
    }
    # Explicit None is meaningful here (it clears a nullable setting), so keep it.
    return {k: v for k, v in fields.items() if is_given(v)}


class HostedPrompts(SyncAPIResource):
    """``client.call_types.prompts``: versioned hosted prompts for a call type."""

    def list(self, call_type: str, *, options: RequestOptions | None = None) -> HostedPromptList:
        """List every hosted prompt version of a call type (``GET .../prompts``)."""
        return self._client.request_model(
            build("GET", f"/v1/call-types/{seg(call_type)}/prompts", options=options),
            HostedPromptList,
        )

    def create(
        self,
        call_type: str,
        *,
        template: str,
        variables: Sequence[HostedPromptVariableParam | Mapping[str, Any]] | None = None,
        options: RequestOptions | None = None,
    ) -> HostedPrompt:
        """Append a new, inactive, immutable prompt version (``POST .../prompts``).

        Args:
            call_type: The call type id or slug.
            template: The template text with ``{{name}}`` slots.
            variables: Declared variables: ``[{"name": "tone", "required": False}, ...]``.
            options: Per-call request options.
        """
        body = compact(template=template, variables=list(variables) if variables else None)
        return self._client.request_model(
            build("POST", f"/v1/call-types/{seg(call_type)}/prompts", body=body, options=options),
            HostedPrompt,
        )

    def get(
        self, call_type: str, version: int, *, options: RequestOptions | None = None
    ) -> HostedPrompt:
        """Get one hosted prompt version (``GET .../prompts/{version}``)."""
        return self._client.request_model(
            build(
                "GET", f"/v1/call-types/{seg(call_type)}/prompts/{seg(version)}", options=options
            ),
            HostedPrompt,
        )

    def activate(
        self,
        call_type: str,
        version: int,
        *,
        gateway_apply: bool | None = None,
        options: RequestOptions | None = None,
    ) -> HostedPromptActivation:
        """Make ``version`` the active prompt (activating an older version is a rollback).

        Args:
            call_type: The call type id or slug.
            version: The version number to activate.
            gateway_apply: ``True`` makes the gateway apply the prompt to proxied requests;
                ``False`` only serves it through ``get_prompt``/preflight.
            options: Per-call request options.
        """
        return self._client.request_model(
            build(
                "POST",
                f"/v1/call-types/{seg(call_type)}/prompts/{seg(version)}/activate",
                body=compact(gateway_apply=gateway_apply),
                options=options,
            ),
            HostedPromptActivation,
        )

    def deactivate(
        self, call_type: str, *, options: RequestOptions | None = None
    ) -> HostedPromptActivation:
        """Deactivate the hosted prompt (the call type becomes code-owned again)."""
        return self._client.request_model(
            build("POST", f"/v1/call-types/{seg(call_type)}/prompts/deactivate", options=options),
            HostedPromptActivation,
        )

    def proposal(
        self, call_type: str, *, options: RequestOptions | None = None
    ) -> HostedPromptProposal:
        """Get the onboarding proposal: a template inferred from the system prompts you send."""
        return self._client.request_model(
            build("GET", f"/v1/call-types/{seg(call_type)}/prompts/proposal", options=options),
            HostedPromptProposal,
        )


class VerifiedMemory(SyncAPIResource):
    """``client.call_types.verified_memory``: answer from verified past cases when it is safe."""

    def get(self, call_type: str, *, options: RequestOptions | None = None) -> VerifiedMemoryStatus:
        """Read the verified-memory setting and whether it can be served right now."""
        return self._client.request_model(
            build("GET", f"/v1/call-types/{seg(call_type)}/verified-memory", options=options),
            VerifiedMemoryStatus,
        )

    def enable(
        self,
        call_type: str,
        *,
        target_precision: float | None = None,
        options: RequestOptions | None = None,
    ) -> VerifiedMemoryEnableResult:
        """Calibrate and enable verified memory; the result names why when it cannot be enabled.

        Args:
            call_type: The call type id or slug.
            target_precision: The precision the calibration must reach before enabling.
            options: Per-call request options.
        """
        return self._client.request_model(
            build(
                "POST",
                f"/v1/call-types/{seg(call_type)}/verified-memory/enable",
                body=compact(target_precision=target_precision),
                options=options,
            ),
            VerifiedMemoryEnableResult,
        )

    def disable(
        self, call_type: str, *, options: RequestOptions | None = None
    ) -> VerifiedMemoryDisableResult:
        """Turn verified memory off (the kill switch)."""
        return self._client.request_model(
            build(
                "POST", f"/v1/call-types/{seg(call_type)}/verified-memory/disable", options=options
            ),
            VerifiedMemoryDisableResult,
        )


class CallTypes(SyncAPIResource):
    """``client.call_types``: the units your traffic is grouped into, and their configuration."""

    def __init__(self, client: Any) -> None:
        super().__init__(client)
        self.prompts = HostedPrompts(client)
        """Hosted prompt versions."""
        self.verified_memory = VerifiedMemory(client)
        """Verified-memory controls."""

    def list(self, *, options: RequestOptions | None = None) -> CallTypeList:
        """List the workspace's call types (``GET /v1/call-types``)."""
        return self._client.request_model(
            build("GET", "/v1/call-types", options=options), CallTypeList
        )

    def create(
        self,
        *,
        slug: str,
        config: Mapping[str, Any] | None = None,
        options: RequestOptions | None = None,
    ) -> CallType:
        """Create a call type (``POST /v1/call-types``).

        Args:
            slug: The stable slug requests reference with ``call_type=``.
            config: Initial configuration (``model_pin``, ``router_mode``, ``fallbacks``, ...);
                see :class:`~ultrarouter.types.CallTypeConfigParams`.
            options: Per-call request options.
        """
        body: dict[str, Any] = {"slug": slug}
        if config is not None:
            body["config"] = dict(config)
        return self._client.request_model(
            build("POST", "/v1/call-types", body=body, options=options), CallType
        )

    def get(self, call_type: str, *, options: RequestOptions | None = None) -> CallType:
        """Get one call type by id or slug (``GET /v1/call-types/{id}``)."""
        return self._client.request_model(
            build("GET", f"/v1/call-types/{seg(call_type)}", options=options), CallType
        )

    def update(
        self,
        call_type: str,
        *,
        model_pin: str | NotGiven | None = NOT_GIVEN,
        router_mode: RouterModeParam | NotGiven | None = NOT_GIVEN,
        compression_mode: CompressionModeParam | NotGiven | None = NOT_GIVEN,
        fallbacks: Sequence[str] | NotGiven = NOT_GIVEN,
        provider_prefs: Mapping[str, Any] | NotGiven | None = NOT_GIVEN,
        learned_context_delivery: LearnedContextDelivery | NotGiven = NOT_GIVEN,
        case_precedents_enabled: bool | NotGiven = NOT_GIVEN,
        self_improve_mode: SelfImproveMode | NotGiven = NOT_GIVEN,
        self_improve_guardrails: SelfImproveGuardrailsParams
        | Mapping[str, Any]
        | NotGiven = NOT_GIVEN,
        options: RequestOptions | None = None,
    ) -> CallType:
        """Write a new config version (``PATCH /v1/call-types/{id}``).

        Only the arguments you pass are sent. For ``model_pin``, ``router_mode``,
        ``compression_mode`` and ``provider_prefs``, passing ``None`` clears the setting.
        """
        body = _config_body(
            model_pin=model_pin,
            router_mode=router_mode,
            compression_mode=compression_mode,
            fallbacks=fallbacks,
            provider_prefs=provider_prefs,
            learned_context_delivery=learned_context_delivery,
            case_precedents_enabled=case_precedents_enabled,
            self_improve_mode=self_improve_mode,
            self_improve_guardrails=self_improve_guardrails,
        )
        return self._client.request_model(
            build("PATCH", f"/v1/call-types/{seg(call_type)}", body=body, options=options), CallType
        )

    def enqueue_eval(
        self,
        call_type: str,
        *,
        mode: Literal["request", "task"] | None = None,
        options: RequestOptions | None = None,
    ) -> EnqueueEvalResponse:
        """Trigger an eval run now (``POST /v1/call-types/{id}/evals``).

        Returns the enqueued run (``enqueued=True``, ``run_id``) or a documented no-op
        (``enqueued=False`` and a ``reason``; a de-duplicated trigger names the run it joined in
        ``prior_run_id``).
        """
        return self._client.request_model(
            build(
                "POST",
                f"/v1/call-types/{seg(call_type)}/evals",
                body=compact(mode=mode),
                options=options,
            ),
            EnqueueEvalResponse,
        )

    def list_evals(self, call_type: str, *, options: RequestOptions | None = None) -> EvalRunList:
        """List the call type's eval runs, newest first (``GET /v1/call-types/{id}/evals``)."""
        return self._client.request_model(
            build("GET", f"/v1/call-types/{seg(call_type)}/evals", options=options), EvalRunList
        )

    def list_recommendations(
        self, call_type: str, *, options: RequestOptions | None = None
    ) -> dict[str, Any]:
        """List routing recommendations for the call type (``GET .../recommendations``).

        The response shape is not yet described by the API specification, so the decoded JSON
        is returned as a ``dict``.
        """
        data = self._client.request_json(
            build("GET", f"/v1/call-types/{seg(call_type)}/recommendations", options=options)
        )
        return data if isinstance(data, dict) else {"data": data}


class AsyncHostedPrompts(AsyncAPIResource):
    """``client.call_types.prompts`` on :class:`~ultrarouter.AsyncUltraRouter`."""

    async def list(
        self, call_type: str, *, options: RequestOptions | None = None
    ) -> HostedPromptList:
        """List hosted prompt versions; async twin of :meth:`HostedPrompts.list`."""
        return await self._client.request_model(
            build("GET", f"/v1/call-types/{seg(call_type)}/prompts", options=options),
            HostedPromptList,
        )

    async def create(
        self,
        call_type: str,
        *,
        template: str,
        variables: Sequence[HostedPromptVariableParam | Mapping[str, Any]] | None = None,
        options: RequestOptions | None = None,
    ) -> HostedPrompt:
        """Append a prompt version; async twin of :meth:`HostedPrompts.create`."""
        body = compact(template=template, variables=list(variables) if variables else None)
        return await self._client.request_model(
            build("POST", f"/v1/call-types/{seg(call_type)}/prompts", body=body, options=options),
            HostedPrompt,
        )

    async def get(
        self, call_type: str, version: int, *, options: RequestOptions | None = None
    ) -> HostedPrompt:
        """Get one prompt version; async twin of :meth:`HostedPrompts.get`."""
        return await self._client.request_model(
            build(
                "GET", f"/v1/call-types/{seg(call_type)}/prompts/{seg(version)}", options=options
            ),
            HostedPrompt,
        )

    async def activate(
        self,
        call_type: str,
        version: int,
        *,
        gateway_apply: bool | None = None,
        options: RequestOptions | None = None,
    ) -> HostedPromptActivation:
        """Activate a prompt version; async twin of :meth:`HostedPrompts.activate`."""
        return await self._client.request_model(
            build(
                "POST",
                f"/v1/call-types/{seg(call_type)}/prompts/{seg(version)}/activate",
                body=compact(gateway_apply=gateway_apply),
                options=options,
            ),
            HostedPromptActivation,
        )

    async def deactivate(
        self, call_type: str, *, options: RequestOptions | None = None
    ) -> HostedPromptActivation:
        """Deactivate the hosted prompt; async twin of :meth:`HostedPrompts.deactivate`."""
        return await self._client.request_model(
            build("POST", f"/v1/call-types/{seg(call_type)}/prompts/deactivate", options=options),
            HostedPromptActivation,
        )

    async def proposal(
        self, call_type: str, *, options: RequestOptions | None = None
    ) -> HostedPromptProposal:
        """Get the onboarding proposal; async twin of :meth:`HostedPrompts.proposal`."""
        return await self._client.request_model(
            build("GET", f"/v1/call-types/{seg(call_type)}/prompts/proposal", options=options),
            HostedPromptProposal,
        )


class AsyncVerifiedMemory(AsyncAPIResource):
    """``client.call_types.verified_memory`` on :class:`~ultrarouter.AsyncUltraRouter`."""

    async def get(
        self, call_type: str, *, options: RequestOptions | None = None
    ) -> VerifiedMemoryStatus:
        """Read the verified-memory status; async twin of :meth:`VerifiedMemory.get`."""
        return await self._client.request_model(
            build("GET", f"/v1/call-types/{seg(call_type)}/verified-memory", options=options),
            VerifiedMemoryStatus,
        )

    async def enable(
        self,
        call_type: str,
        *,
        target_precision: float | None = None,
        options: RequestOptions | None = None,
    ) -> VerifiedMemoryEnableResult:
        """Enable verified memory; async twin of :meth:`VerifiedMemory.enable`."""
        return await self._client.request_model(
            build(
                "POST",
                f"/v1/call-types/{seg(call_type)}/verified-memory/enable",
                body=compact(target_precision=target_precision),
                options=options,
            ),
            VerifiedMemoryEnableResult,
        )

    async def disable(
        self, call_type: str, *, options: RequestOptions | None = None
    ) -> VerifiedMemoryDisableResult:
        """Disable verified memory; async twin of :meth:`VerifiedMemory.disable`."""
        return await self._client.request_model(
            build(
                "POST", f"/v1/call-types/{seg(call_type)}/verified-memory/disable", options=options
            ),
            VerifiedMemoryDisableResult,
        )


class AsyncCallTypes(AsyncAPIResource):
    """``client.call_types`` on :class:`~ultrarouter.AsyncUltraRouter`."""

    def __init__(self, client: Any) -> None:
        super().__init__(client)
        self.prompts = AsyncHostedPrompts(client)
        """Hosted prompt versions."""
        self.verified_memory = AsyncVerifiedMemory(client)
        """Verified-memory controls."""

    async def list(self, *, options: RequestOptions | None = None) -> CallTypeList:
        """List call types; async twin of :meth:`CallTypes.list`."""
        return await self._client.request_model(
            build("GET", "/v1/call-types", options=options), CallTypeList
        )

    async def create(
        self,
        *,
        slug: str,
        config: Mapping[str, Any] | None = None,
        options: RequestOptions | None = None,
    ) -> CallType:
        """Create a call type; async twin of :meth:`CallTypes.create`."""
        body: dict[str, Any] = {"slug": slug}
        if config is not None:
            body["config"] = dict(config)
        return await self._client.request_model(
            build("POST", "/v1/call-types", body=body, options=options), CallType
        )

    async def get(self, call_type: str, *, options: RequestOptions | None = None) -> CallType:
        """Get a call type; async twin of :meth:`CallTypes.get`."""
        return await self._client.request_model(
            build("GET", f"/v1/call-types/{seg(call_type)}", options=options), CallType
        )

    async def update(
        self,
        call_type: str,
        *,
        model_pin: str | NotGiven | None = NOT_GIVEN,
        router_mode: RouterModeParam | NotGiven | None = NOT_GIVEN,
        compression_mode: CompressionModeParam | NotGiven | None = NOT_GIVEN,
        fallbacks: Sequence[str] | NotGiven = NOT_GIVEN,
        provider_prefs: Mapping[str, Any] | NotGiven | None = NOT_GIVEN,
        learned_context_delivery: LearnedContextDelivery | NotGiven = NOT_GIVEN,
        case_precedents_enabled: bool | NotGiven = NOT_GIVEN,
        self_improve_mode: SelfImproveMode | NotGiven = NOT_GIVEN,
        self_improve_guardrails: SelfImproveGuardrailsParams
        | Mapping[str, Any]
        | NotGiven = NOT_GIVEN,
        options: RequestOptions | None = None,
    ) -> CallType:
        """Write a new config version; async twin of :meth:`CallTypes.update`."""
        body = _config_body(
            model_pin=model_pin,
            router_mode=router_mode,
            compression_mode=compression_mode,
            fallbacks=fallbacks,
            provider_prefs=provider_prefs,
            learned_context_delivery=learned_context_delivery,
            case_precedents_enabled=case_precedents_enabled,
            self_improve_mode=self_improve_mode,
            self_improve_guardrails=self_improve_guardrails,
        )
        return await self._client.request_model(
            build("PATCH", f"/v1/call-types/{seg(call_type)}", body=body, options=options), CallType
        )

    async def enqueue_eval(
        self,
        call_type: str,
        *,
        mode: Literal["request", "task"] | None = None,
        options: RequestOptions | None = None,
    ) -> EnqueueEvalResponse:
        """Trigger an eval run; async twin of :meth:`CallTypes.enqueue_eval`."""
        return await self._client.request_model(
            build(
                "POST",
                f"/v1/call-types/{seg(call_type)}/evals",
                body=compact(mode=mode),
                options=options,
            ),
            EnqueueEvalResponse,
        )

    async def list_evals(
        self, call_type: str, *, options: RequestOptions | None = None
    ) -> EvalRunList:
        """List eval runs; async twin of :meth:`CallTypes.list_evals`."""
        return await self._client.request_model(
            build("GET", f"/v1/call-types/{seg(call_type)}/evals", options=options), EvalRunList
        )

    async def list_recommendations(
        self, call_type: str, *, options: RequestOptions | None = None
    ) -> dict[str, Any]:
        """List routing recommendations; async twin of :meth:`CallTypes.list_recommendations`."""
        data = await self._client.request_json(
            build("GET", f"/v1/call-types/{seg(call_type)}/recommendations", options=options)
        )
        return data if isinstance(data, dict) else {"data": data}
