"""Learning controls for one call type: status, enable, pause/resume, versions, evaluations.

Enabling is self-serve for a `config:write` key once the workspace's corrections consent is on;
learning runs only on a provider the workspace configured. Every refusal is a typed, actionable
`LearningError` (`reason` + `action`). Set `ULTRAROUTER_CALL_TYPE` and
`ULTRAROUTER_REFLECTION_MODEL` to point it at your own call type.

Run: ULTRAROUTER_API_KEY=... ULTRAROUTER_BASE_URL=... python examples/learning_controls.py

Expected output (mock gateway):
    before: not_enabled
    enabled: active (promotion evaluate, provider ready)
    paused: paused; resumed: active
    versions: lv_2 evaluating, lv_1 active
    lv_2: 2 lessons, from 12 episodes
    evaluation lev_1: running (candidate 5/7, incumbent 3/6)
    rolled back to lv_1: active lv_1
    unknown call type: not_found -> Check the call type id (or slug) and the version id.
"""

from __future__ import annotations

import os

from ultrarouter import LearningError, UltraRouter

CALL_TYPE = os.environ.get("ULTRAROUTER_CALL_TYPE", "order-desk")
REFLECTION_MODEL = os.environ.get("ULTRAROUTER_REFLECTION_MODEL", "openai/gpt-5.2-mini")


def main() -> int:
    with UltraRouter() as client:
        learning = client.learning
        try:
            print("before:", learning.status(CALL_TYPE).state)
            status = learning.enable(
                CALL_TYPE, reflection_model=REFLECTION_MODEL, promotion="evaluate"
            )
        except LearningError as exc:
            print(f"cannot enable ({exc.reason}): {exc.action}")
            return 2
        mode = status.promotion.mode if status.promotion else None
        provider = status.provider.state if status.provider else None
        print(f"enabled: {status.state} (promotion {mode}, provider {provider})")
        if status.state != "active":
            print("learning is stopped:", status.reason)
            return 0

        paused = learning.pause(CALL_TYPE)
        resumed = learning.resume(CALL_TYPE)
        print(f"paused: {paused.state}; resumed: {resumed.state}")

        versions = learning.versions(CALL_TYPE).data
        print("versions:", ", ".join(f"{v.id} {v.state}" for v in versions) or "none yet")
        if versions:
            detail = learning.version(CALL_TYPE, versions[0].id)
            episodes = detail.provenance.episodes if detail.provenance else None
            print(f"{detail.id}: {len(detail.lessons or [])} lessons, from {episodes} episodes")
        for evaluation in learning.evaluations(CALL_TYPE).data[:1]:
            cand, inc = evaluation.candidate, evaluation.incumbent
            print(
                f"evaluation {evaluation.id}: {evaluation.decision} "
                f"(candidate {cand.passed if cand else '?'}/{cand.verified if cand else '?'}, "
                f"incumbent {inc.passed if inc else '?'}/{inc.verified if inc else '?'})"
            )
        if resumed.active is not None:  # a safe demonstration: point at the active version
            rolled = learning.rollback(CALL_TYPE, version_id=resumed.active.id, reason="example")
            now_active = rolled.active.id if rolled.active else None
            print(f"rolled back to {resumed.active.id}: active {now_active}")

        try:
            learning.status("ct_missing")
        except LearningError as exc:
            print(f"unknown call type: {exc.reason} -> {exc.action}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
