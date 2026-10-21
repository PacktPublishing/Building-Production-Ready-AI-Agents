from __future__ import annotations

import uuid
from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from agents import BagelAgent, PizzaAgent
from app_models import ChatRequest, ChatResponse, Session


app = FastAPI(title="Chapter 11 Assignment: Pizza Ordering Agent")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

SESSIONS: dict[str, Session] = {}
AGENT = PizzaAgent()
BAGEL_AGENT = BagelAgent()


@app.get("/")
def index() -> FileResponse:
    return FileResponse(str(BASE_DIR / "static" / "index.html"))


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    flow = request.flow.strip().lower()
    if flow not in {"pizza", "bagel"}:
        flow = "pizza"

    session_id = request.session_id or str(uuid.uuid4())
    session = SESSIONS.get(session_id)
    if session is None or session.flow != flow:
        session = Session(flow=flow)
        SESSIONS[session_id] = session

    agent = BAGEL_AGENT if flow == "bagel" else AGENT
    reply = agent.run_turn(session, request.message)

    return ChatResponse(
        session_id=session_id,
        flow=flow,
        reply=reply,
        state=asdict(session.state),
        trace=session.trace[-5:],
    )


@app.get("/api/session/{session_id}", response_model=ChatResponse)
def get_session(session_id: str) -> ChatResponse:
    session = SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return ChatResponse(
        session_id=session_id,
        flow=session.flow,
        reply="Session loaded.",
        state=asdict(session.state),
        trace=session.trace[-5:],
    )
