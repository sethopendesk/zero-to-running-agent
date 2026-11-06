"""Check the snapshot's status and price without asking an LLM.

No network requests in Phase 1; 'eligible' does not mean live-verified.
"""
from agent import config
from agent.listings import filter_listings
from agent.log import log_event
from agent.state import AgentState


def check_node(state: AgentState) -> dict:
    groups = filter_listings(state["opportunities"], max_price=config.MAX_ASKING_PRICE)
    log_event(state["run_id"], "check", "classified", **{k: len(v) for k, v in groups.items()})
    return groups
