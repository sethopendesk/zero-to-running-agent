"""Local Phase 1 FastAPI interface for business listing interest drafts.

    uvicorn main:app --reload
    Open http://127.0.0.1:8000

The API accepts parsed JSON arrays, never arbitrary local filesystem paths.
"""
import uuid
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from langgraph.types import Command
from pydantic import BaseModel, Field, field_validator

from agent import config
from agent.graph import build_graph
from agent.listings import MAX_RECORDS

app = FastAPI(title="Business Interest Agent — Phase 1")
graph = build_graph()  # MemorySaver: pending approvals disappear on server restart


class RunRequest(BaseModel):
    listings: list[dict[str, Any]] | None = None
    source_name: str = Field(default="Uploaded JSON", max_length=120)

    @field_validator("listings")
    @classmethod
    def max_records(cls, listings):
        if listings is not None and len(listings) > MAX_RECORDS:
            raise ValueError(f"Maximum {MAX_RECORDS} listings per run")
        return listings


class Decision(BaseModel):
    listing_key: str = Field(min_length=1, max_length=1600)
    action: Literal["approve", "edit", "reject"]
    subject: str | None = Field(default=None, max_length=200)
    body: str | None = Field(default=None, max_length=6000)


def config_for(run_id: str) -> dict:
    return {"configurable": {"thread_id": run_id}}


@app.post("/runs")
def start_run(req: RunRequest):
    run_id = uuid.uuid4().hex[:8]
    initial = {"run_id": run_id}
    if req.listings is not None:
        initial["input_listings"] = req.listings
        initial["listings_source"] = req.source_name
    result = graph.invoke(initial, config_for(run_id))
    return {
        "run_id": run_id,
        "waiting_for_review": "__interrupt__" in result,
        "source": result.get("source_summary", {}),
        "eligible": result.get("eligible", []),
        "selected": result.get("selected", []),
        "manual_review": result.get("manual_review", []),
        "rejected": result.get("rejected", []),
        "counts": {
            "eligible": len(result.get("eligible", [])),
            "selected": len(result.get("selected", [])),
            "manual_review": len(result.get("manual_review", [])),
            "rejected": len(result.get("rejected", [])),
        },
    }


@app.get("/runs/{run_id}/drafts")
def list_drafts(run_id: str):
    snapshot = graph.get_state(config_for(run_id))
    if not snapshot.values:
        raise HTTPException(404, "No run with that id; the server may have restarted")
    return {"run_id": run_id, "paused": bool(snapshot.next),
            "drafts": snapshot.values.get("drafts", [])}


@app.post("/runs/{run_id}/review")
def review(run_id: str, decisions: list[Decision]):
    snapshot = graph.get_state(config_for(run_id))
    if not snapshot.values:
        raise HTTPException(404, "No run with that id")
    if not snapshot.next:
        raise HTTPException(409, "This run isn't waiting for review")
    result = graph.invoke(Command(resume=[d.model_dump() for d in decisions]), config_for(run_id))
    return {"run_id": run_id, "drafts": result.get("drafts", [])}


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(Path(__file__).parent / "ui" / "index.html")


@app.get("/health")
def health():
    return {"ok": True, "model": config.MODEL_PROVIDER,
            "max_asking_price": config.MAX_ASKING_PRICE, "max_drafts": config.MAX_DRAFTS}
