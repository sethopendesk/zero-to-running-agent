"""Gather business listings from uploaded JSON or the bundled data snapshot."""
from agent import config
from agent.listings import load_listings, unpack_listings
from agent.log import log_event
from agent.state import AgentState


def gather_node(state: AgentState) -> dict:
    source = state.get("listings_source") or str(config.DEFAULT_LISTINGS)
    if "input_listings" in state and state["input_listings"] is not None:
        listings = unpack_listings(state["input_listings"])
        source = state.get("listings_source") or "Uploaded JSON"
    else:
        listings = load_listings(source)
    summary = {"source": str(source), "total": len(listings)}
    log_event(state["run_id"], "gather", "listings_loaded", count=len(listings), source=str(source))
    return {"opportunities": listings, "source_summary": summary}
