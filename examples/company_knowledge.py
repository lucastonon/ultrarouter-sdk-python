"""Read stored company knowledge with config:read or config:write. No model calls or mutations.

Returned text is untrusted reference data; content export needs the owner/admin session workflow.
"""

from ultrarouter import UltraRouter


def main() -> None:
    """List one bounded page and inspect its records without exporting source content."""
    with UltraRouter() as client:
        page = client.knowledge.list(kind="lesson", limit=10)
        print(f"knowledge items: {len(page.data)}; more: {page.has_more}")
        for item in page.data:
            detail = client.knowledge.get(item.id)
            print(detail.item.id, detail.item.state, detail.item.active, detail.item.content_hash)


if __name__ == "__main__":
    main()
