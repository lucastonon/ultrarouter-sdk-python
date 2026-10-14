"""Send reviewer decisions through the signed, durable reviewer adapter.

Run: ULTRAROUTER_API_KEY=... ULTRAROUTER_BASE_URL=... python examples/reviewer.py
"""

from __future__ import annotations

from ultrarouter import UltraRouter, diff_stats


def main() -> None:
    with UltraRouter() as client:
        setup = client.reviewer.setup()
        print("post to:", setup.endpoint, "signature header:", setup.signature.header)

        stats = diff_stats("Thanks for waiting.", "Thanks for waiting, your refund is on its way.")
        client.reviewer.record(
            {
                "event_id": "review-1001",
                "artifact_key": "ticket:4812:reply",
                "artifact_version": 1,
                "decision": "approved_with_edits",
                "effective_at": "2026-01-15T12:00:00Z",
                "final": {"diff_stats": stats, "hash": stats["final_hash"]},
            },
            reviewer_system="helpdesk",
        )
        report = client.reviewer.flush()
        print(f"accepted={report.accepted} duplicate={report.duplicate}")
        print(f"dead_lettered={report.dead_lettered}")
        for letter in client.reviewer.dead_letters():
            print("repairing", letter["event"]["event_id"], client.reviewer.repair(letter).result)
        print("next repair action:", client.reviewer.health().next_repair.action)


if __name__ == "__main__":
    main()
