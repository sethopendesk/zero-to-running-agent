"""Phase 1 CLI.

    python run.py                               # bundled business_listings.json
    python run.py path/to/business_listings.json # another JSON array

Run from the project root with your virtual environment active.
"""
import sys
import uuid

from langgraph.types import Command

from agent import config
from agent.graph import build_graph


def show_results(state: dict) -> None:
    summary = state.get("source_summary", {})
    eligible = state.get("eligible", [])
    manual = state.get("manual_review", [])
    rejected = state.get("rejected", [])
    selected = state.get("selected", [])
    print(f"\nLoaded {summary.get('total', 0)} business listings from {summary.get('source', 'unknown')}.")
    print(f"Eligible below ${config.MAX_ASKING_PRICE:,}: {len(eligible)} (snapshot only; not live-verified)")
    print(f"Requires manual price/status review: {len(manual)}; rejected: {len(rejected)}")
    print(f"\nSelected {len(selected)} lowest-priced eligible listings for email drafts:")
    for item in selected:
        print(f"  ${item['asking_price_usd']:>10,.0f}  {item['title']}  [{item['source']}]")
    if manual:
        print("\nManual review sample (first 10):")
        for item in manual[:10]:
            print(f"  {item['title']}: {item['why']}")


def read_body(original: str) -> str:
    print("Paste replacement body, ending with a line containing only END. Enter immediately to keep original.")
    first = input()
    if not first:
        return original
    lines = [first]
    while lines[-1] != "END":
        lines.append(input())
    return "\n".join(lines[:-1]).strip() or original


def ask_human(drafts: list[dict]) -> list[dict]:
    decisions = []
    for draft in drafts:
        print(f"\n--- {draft['title']} ---")
        print(f"Listing: {draft.get('listing_url')}")
        print(f"Subject: {draft['subject']}\n\n{draft['body']}\n")
        if draft.get("generation_note"):
            print(draft["generation_note"])
        choice = input("Approve and save, edit, or reject? [a/e/r, default r] ").strip().lower()
        if choice.startswith("e"):
            subject = input("New subject (Enter to keep original): ").strip() or draft["subject"]
            body = read_body(draft["body"])
            decisions.append({"listing_key": draft["listing_key"], "action": "edit", "subject": subject, "body": body})
        elif choice.startswith("a"):
            decisions.append({"listing_key": draft["listing_key"], "action": "approve"})
        else:
            decisions.append({"listing_key": draft["listing_key"], "action": "reject"})
    return decisions


def main() -> None:
    source = sys.argv[1] if len(sys.argv) > 1 else str(config.DEFAULT_LISTINGS)
    run_id = uuid.uuid4().hex[:8]
    graph = build_graph()
    context = {"configurable": {"thread_id": run_id}}
    result = graph.invoke({"run_id": run_id, "listings_source": source}, context)
    show_results(result)
    if "__interrupt__" in result:
        drafts = result["__interrupt__"][0].value["drafts"]
        result = graph.invoke(Command(resume=ask_human(drafts)), context)
        count = sum(d.get("status") == "approved" for d in result["drafts"])
        print(f"\nSaved {count} approved email draft(s) in outputs/. Nothing was emailed.")
    else:
        print("\nNo eligible listings were selected for email drafting.")
    print(f"Run {run_id} finished. Logs: logs/runs.jsonl")


if __name__ == "__main__":
    main()
