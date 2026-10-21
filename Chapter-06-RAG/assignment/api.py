from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from rag import ingest, search, get_chunks
from ai import generate_response_stream
import json
import os

app = FastAPI()

vector_store = None

@app.on_event("startup")
async def startup():
    global vector_store
    vector_store = ingest()

class SearchRequest(BaseModel):
    prompt: str

@app.get("/")
async def get_index():
    return FileResponse("index.html")

@app.get("/api/chunks")
async def list_chunks():
    chunks = get_chunks()
    return {"chunks": chunks}

@app.post("/api/search")
async def search_docs(request: SearchRequest):
    context, chunk_index = search(request.prompt, vector_store)
    if not context:
        return {"result": "No relevant content found", "query": request.prompt, "matched_chunk": -1}

    def stream():
        yield json.dumps({"matched_chunk": chunk_index}) + "\n"
        for chunk in generate_response_stream(request.prompt, context):
            yield chunk

    return StreamingResponse(stream(), media_type="text/plain")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
