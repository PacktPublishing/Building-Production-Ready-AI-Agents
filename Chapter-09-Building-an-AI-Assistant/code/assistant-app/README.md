# IT Support Triage System

AI-powered IT support ticket triage using **Ollama** (Mistral) + **FastAPI** + vanilla **HTML/CSS/JS**.

## Architecture

```
assistant-app/
├── backend/
│   ├── main.py               # FastAPI entry point + API routes
│   ├── assistant.py           # Orchestrator: classify → summarize → advise
│   ├── schemas.py             # Pydantic models & enums
│   ├── tools/
│   │   ├── classifier.py      # Determines category & priority
│   │   ├── summarizer.py      # Produces concise summaries
│   │   └── advisor.py         # Recommends actions & reasoning
│   ├── memory/
│   │   ├── short_term.py      # In-memory session context
│   │   └── long_term.py       # Persistent JSON history
│   ├── utils/
│   │   ├── config.py          # Settings (env vars)
│   │   └── llm_client.py      # Ollama SDK wrapper
│   └── tests/
│       ├── test_tools.py      # Unit tests for each tool
│       ├── test_assistant.py  # Orchestrator tests
│       ├── test_routes.py     # API endpoint tests
│       └── test_memory.py     # Memory module tests
├── frontend/
│   ├── index.html
│   ├── styles.css
│   └── app.js
├── data/
│   └── sample_tickets.json    # Sample ticket data
├── pyproject.toml
└── README.md
```

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- [Ollama](https://ollama.com/) running locally with `mistral:latest`

## Quick Start

### 1. Start Ollama

```bash
ollama serve
ollama pull mistral
```

### 2. Start the Backend

```bash
uv sync
uv run uvicorn backend.main:app --reload --port 8010
```

### 3. Open the Frontend

Open `frontend/index.html` in your browser.

### 4. Run Tests

```bash
uv run pytest -v
```

## API Endpoints

| Method | Path          | Description                        |
|--------|---------------|------------------------------------|
| GET    | `/api/health` | Health check + Ollama connectivity |
| POST   | `/api/triage` | Triage one or more tickets         |

## Configuration

Environment variables (prefix `TRIAGE_`):

| Variable             | Default                   | Description            |
|----------------------|---------------------------|------------------------|
| `TRIAGE_OLLAMA_HOST` | `http://localhost:11434`  | Ollama server URL      |
| `TRIAGE_OLLAMA_MODEL`| `mistral:latest`          | Model to use           |
| `TRIAGE_LOG_LEVEL`   | `INFO`                    | Logging level          |
