# Assistant Exercises (Ollama + uv)

This folder contains three small, progressive exercises.

- `1-assistant.py`: one-turn terminal assistant with Ollama.
- `2-assistant.py`: adds short-term memory and summary command.
- `3-assistant.py`: adds simple planning + tool orchestration with confirmation for actions.

## Model and host

These exercises follow the same environment variable pattern as `assistant-app`.

- `TRIAGE_OLLAMA_HOST` default: `http://localhost:11434`
- `TRIAGE_OLLAMA_MODEL` default: `qwen2.5:1.5b`

## Run

1. Start Ollama:

```bash
ollama serve
ollama pull qwen2.5:1.5b
```

2. Install dependencies:

```bash
uv sync
```

3. Run each exercise:

```bash
uv run 1-assistant.py
uv run 2-assistant.py
uv run 3-assistant.py
```
