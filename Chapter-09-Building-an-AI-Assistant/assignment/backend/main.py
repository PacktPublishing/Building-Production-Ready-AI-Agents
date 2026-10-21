from __future__ import annotations

from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.assistant import Assistant
from backend.memory.short_term import ShortTermMemoryStore
from backend.schemas import AssistantResponse, ChatRequest, ConfirmRequest, HealthResponse, SessionStateResponse
from backend.utils.config import Settings, get_settings
from backend.utils.llm_client import LLMClient

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

app = FastAPI(title="Chapter 9 Assistant", version="0.1.0")
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

memory_store = ShortTermMemoryStore()
assistant = Assistant(LLMClient(settings), memory_store)


def get_assistant() -> Assistant:
    return assistant


@app.get("/")
def root() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/api/health", response_model=HealthResponse)
async def health_check(current: Assistant = Depends(get_assistant)) -> HealthResponse:
    connected = await current.check_health()
    return HealthResponse(
        status="healthy" if connected else "degraded",
        model=current.model_name,
        ollama_connected=connected,
    )


@app.post("/api/chat", response_model=AssistantResponse)
def chat(request: ChatRequest, current: Assistant = Depends(get_assistant)) -> AssistantResponse:
    return current.handle_message(request.session_id, request.message)


@app.post("/api/confirm", response_model=AssistantResponse)
def confirm(request: ConfirmRequest, current: Assistant = Depends(get_assistant)) -> AssistantResponse:
    return current.confirm_action(request.session_id, request.approve)


@app.get("/api/session/{session_id}", response_model=SessionStateResponse)
def session_state(session_id: str, current: Assistant = Depends(get_assistant)) -> SessionStateResponse:
    return current.session_state(session_id)
