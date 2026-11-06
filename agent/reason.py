"""Phase 1 Reason: deterministic ordering, not subjective AI ranking.

We have no buyer preference profile. Sort eligible listings by price ascending,
then title, to make draft selection predictable and reproducible.
"""
from agent.log import log_event
from agent.state import AgentState


def reason_node(state: AgentState) -> dict:
    ranked = sorted(
        state.get("eligible", []),
        key=lambda e: (float(e["asking_price_usd"]), (e.get("title") or "").casefold(), e["listing_key"]),
    )
    log_event(state["run_id"], "reason", "sorted_by_price", count=len(ranked))
    return {"ranked": ranked}
