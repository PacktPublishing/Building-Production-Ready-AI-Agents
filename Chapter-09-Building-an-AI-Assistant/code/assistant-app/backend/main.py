"""FastAPI application — entry point for the IT support triage API."""

import json
import logging
from pathlib import Path

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from starlette.responses import StreamingResponse

from backend.schemas import HealthResponse, TriageRequest, TriageResponse
from backend.assistant import Assistant
from backend.utils.config import Settings, get_settings

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

settings = get_settings()

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="IT Support Triage System",
    description="AI-powered IT support ticket triage using Ollama LLMs",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _get_assistant(s: Settings = Depends(get_settings)) -> Assistant:
    return Assistant(s)


app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/")
async def root():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/api/health", response_model=HealthResponse)
async def health_check(
    assistant: Assistant = Depends(_get_assistant),
) -> HealthResponse:
    """Check API and Ollama connectivity."""
    connected = await assistant.check_health()
    return HealthResponse(
        status="healthy" if connected else "degraded",
        model=assistant.model_name,
        ollama_connected=connected,
    )


@app.post("/api/triage", response_model=TriageResponse)
async def triage_tickets(
    request: TriageRequest,
    assistant: Assistant = Depends(_get_assistant),
) -> TriageResponse:
    """Triage one or more IT support tickets."""
    try:
        results, elapsed_ms = assistant.triage_batch(request.tickets)
        return TriageResponse(
            results=results,
            model_used=assistant.model_name,
            processing_time_ms=round(elapsed_ms, 2),
        )
    except Exception as exc:
        logger.exception("Triage request failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/triage/stream")
async def triage_tickets_stream(
    request: TriageRequest,
    assistant: Assistant = Depends(_get_assistant),
):
    """Stream triage results via SSE — each ticket result sent as it completes."""

    def event_generator():
        total = len(request.tickets)
        for i, result in enumerate(assistant.triage_stream(request.tickets)):
            event_data = {
                "result": result.model_dump(mode="json"),
                "progress": {"current": i + 1, "total": total},
                "model_used": assistant.model_name,
            }
            yield f"data: {json.dumps(event_data)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
