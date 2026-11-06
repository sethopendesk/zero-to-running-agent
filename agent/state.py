"""State shared across Phase 1's LangGraph stages."""
from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    run_id: str
    listings_source: str | None          # CLI path; API supplies input_listings instead
    input_listings: list[dict[str, Any]] # parsed JSON, never a server-side path from HTTP
    source_summary: dict
    opportunities: list[dict]
    eligible: list[dict]
    manual_review: list[dict]
    rejected: list[dict]
    ranked: list[dict]
    selected: list[dict]
    drafts: list[dict]
    decisions: list[dict]
