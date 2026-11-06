"""Decide which eligible listings receive Phase 1 draft emails."""
from agent import config
from agent.log import log_event
from agent.state import AgentState


def decide_node(state: AgentState) -> dict:
    selected_keys = {e["listing_key"] for e in state.get("ranked", [])[:config.MAX_DRAFTS]}
    eligible = [{**entry, "route": "draft_email" if entry["listing_key"] in selected_keys else "eligible_not_drafted"}
                for entry in state.get("ranked", [])]
    selected = [entry for entry in eligible if entry["route"] == "draft_email"]
    log_event(state["run_id"], "decide", "selected", count=len(selected), max_drafts=config.MAX_DRAFTS)
    return {"eligible": eligible, "selected": selected}


def after_decide(state: AgentState) -> str:
    return "draft" if state.get("selected") else "end"
