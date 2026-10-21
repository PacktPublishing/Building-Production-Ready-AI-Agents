from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app import BASE_DIR, query_graph


class ChatRequest(BaseModel):
    prompt: str


app = FastAPI(title="GraphRAG Movie Chat")


@app.get("/")
def read_index() -> FileResponse:
    return FileResponse(Path(BASE_DIR) / "index.html")


@app.get("/api/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/chat")
def chat(request: ChatRequest) -> dict[str, object]:
    try:
        response = query_graph(request.prompt)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return response.model_dump()