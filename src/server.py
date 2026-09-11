"""Minimal HTTP UI server for Research Atelier.

Thin FastAPI wrapper around ResearchOrchestrator.run_with_state().
Does not alter pipeline logic — only exposes PipelineResult to the frontend.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# Ensure project root is importable when launched as `python -m src.server`
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.orchestrator import ResearchOrchestrator

STATIC_DIR = project_root / "web"

app = FastAPI(title="Research Atelier", docs_url=None, redoc_url=None)


class ResearchRequest(BaseModel):
    topic: str = Field(..., min_length=1, description="User research question")


def _serialize_packet(obj: Any) -> Optional[Dict[str, Any]]:
    if obj is None:
        return None
    return obj.model_dump()


def _serialize_events(events: List[Any]) -> List[Dict[str, Any]]:
    return [e.model_dump() for e in events]


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.post("/api/research")
def run_research(body: ResearchRequest):
    """Invoke the existing orchestrator and return full PipelineResult JSON."""
    topic = body.topic.strip()
    if not topic:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Research topic cannot be empty.", "events": []},
        )

    orchestrator = ResearchOrchestrator()
    try:
        result = orchestrator.run_with_state(topic, save_output=True)
        return {
            "success": True,
            "error": None,
            "final_report": result.final_report.model_dump(),
            "research_packet": result.research_packet.model_dump(),
            "analysis_packet": result.analysis_packet.model_dump(),
            "events": _serialize_events(result.events),
        }
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(exc),
                "final_report": None,
                "research_packet": _serialize_packet(orchestrator.research_packet),
                "analysis_packet": _serialize_packet(orchestrator.analysis_packet),
                "events": _serialize_events(orchestrator.events),
            },
        )


if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def main():
    import uvicorn

    uvicorn.run("src.server:app", host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":
    main()
