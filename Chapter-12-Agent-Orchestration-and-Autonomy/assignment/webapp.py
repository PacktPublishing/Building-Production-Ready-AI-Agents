from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app_models import ApprovalRequest, ChatRequest, ResumeRequest, SessionResponse, SessionState
from checkpoint_store import CheckpointStore
from orchestration import create_session, handle_approval, handle_chat, handle_resume, response_for_session


app = FastAPI(title="Chapter 12 Assignment - Travel Workflow")
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")

sessions: dict[str, SessionState] = {}
checkpoint_store = CheckpointStore()


@app.get("/")
def index() -> FileResponse:
    return FileResponse(static_dir / "index.html")


@app.post("/api/session", response_model=SessionResponse)
def create_workflow_session() -> SessionResponse:
    session = create_session()
    sessions[session.session_id] = session
    return response_for_session(session)


@app.get("/api/session/{session_id}", response_model=SessionResponse)
def get_workflow_session(session_id: str) -> SessionResponse:
    session = sessions.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return response_for_session(session)


@app.post("/api/chat", response_model=SessionResponse)
def chat(payload: ChatRequest) -> SessionResponse:
    session = sessions.get(payload.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return handle_chat(session, payload.message, checkpoint_store)


@app.post("/api/approval", response_model=SessionResponse)
def approval(payload: ApprovalRequest) -> SessionResponse:
    session = sessions.get(payload.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return handle_approval(session, payload.approve, checkpoint_store)


@app.post("/api/resume", response_model=SessionResponse)
def resume(payload: ResumeRequest) -> SessionResponse:
    session = sessions.get(payload.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return handle_resume(session, checkpoint_store)