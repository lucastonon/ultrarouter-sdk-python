"""Learning controls for one call type: status, enable, pause/resume, versions, evaluations.

Enabling is self-serve for a `config:write` key once the workspace's corrections consent is on;
learning reflects only with a workspace-owned model (no platform fallback). Every control returns
the resulting status; every refusal is a typed, actionable `LearningError` (`reason`, `refusal`,
`action`). Set `ULTRAROUTER_CALL_TYPE` and `ULTRAROUTER_REFLECTION_MODEL` for your own call type.

Run: ULTRAROUTER_API_KEY=... ULTRAROUTER_BASE_URL=... python examples/learning_controls.py

Expected output (mock gateway):
    before: off (not_enabled)
    enabled: learning (promotion evaluate, reflection provider available: True)
    paused: paused; resumed: learning
    versions: epb_3 evaluating, epb_2 active, epb_1 retired
    epb_3: 3 lessons, learned from 12 verified episodes
    evaluation lev_1: running (candidate 5/7 pass, incumbent 3/6)
    rolled back: active epb_1
    unknown call type: not_found -> Check the call type id (or slug) and the version id.
"""

from __future__ import annotations

import os

from ultrarouter import LearningError, LearningVersionConflictError, UltraRouter

CALL_TYPE = os.environ.get("ULTRAROUTER_CALL_TYPE", "order-desk")
REFLECTION_MODEL = os.environ.get("ULTRAROUTER_REFLECTION_MODEL", "openai/gpt-5.2-mini")


def main() -> int:
    with UltraRouter() as client:
        learning = client.learning
        try:
            before = learning.status(CALL_TYPE)
            print(f"before: {before.state} ({before.reason})")
            control = learning.enable(
                CALL_TYPE, reflection_model=REFLECTION_MODEL, promotion={"mode": "evaluate"}
            )
        except LearningError as exc:
            print(f"cannot enable ({exc.reason}, {exc.refusal}): {exc.action}")
            return 2
        status = control.learning
        mode = status.promotion.mode if status.promotion else None
        available = status.reflection.provider.available
        print(f"enabled: {status.state} (promotion {mode},", end=" ")
        print(f"reflection provider available: {available})")
        if status.state in ("unavailable", "quota_exhausted", "budget_exhausted"):
            print("learning is stopped:", status.reason)
            return 0

        paused = learning.pause(CALL_TYPE).learning
        resumed = learning.resume(CALL_TYPE).learning
        print(f"paused: {paused.state}; resumed: {resumed.state}")

        versions = learning.versions(CALL_TYPE).data
        print("versions:", ", ".join(f"{v.id} {v.state}" for v in versions) or "none yet")
        if versions:
            detail = learning.version(CALL_TYPE, versions[0].id)
            print(
                f"{detail.id}: {len(detail.lessons)} lessons, "
                f"learned from {detail.cohort.size} verified episodes"
            )
        for evaluation in learning.evaluations(CALL_TYPE).data[:1]:
            cand, inc = evaluation.arms.candidate, evaluation.arms.incumbent
            print(
                f"evaluation {evaluation.id}: {evaluation.decision} "
                f"(candidate {cand.pass_}/{cand.verified} pass, "
                f"incumbent {inc.pass_}/{inc.verified})"
            )
        try:  # back to the version active before the current one
            rolled = learning.rollback(CALL_TYPE).learning
            active = rolled.active_version.id if rolled.active_version else None
            print(f"rolled back: active {active}")
        except LearningVersionConflictError as exc:
            print(f"rollback: {exc.refusal} ({exc.action})")

        try:
            learning.status("ct_missing")
        except LearningError as exc:
            print(f"unknown call type: {exc.reason} -> {exc.action}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
