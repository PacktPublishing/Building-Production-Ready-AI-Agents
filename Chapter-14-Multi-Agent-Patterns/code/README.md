# Chapter 14 Code

This folder holds runnable examples and exercise solutions for Chapter 14: Multi-Agent Patterns.

## What is in this folder

- `solutions/README.md`: entry point for the exercise solution guides.
- `solutions/exercise-1-supervisor-worker/`: implement and test supervisor-worker pattern.
- `solutions/exercise-2-debate-pattern/`: implement and test debate pattern.
- `solutions/exercise-3-swarm-pattern/`: implement and test swarm pattern.
- `solutions/exercise-4-committee-pattern/`: implement and test committee pattern.
- `solutions/exercise-5-peer-to-peer-pattern/`: implement and test peer-to-peer pattern.

## Prerequisites

- Python 3.11+ available on your machine.
- `uv` installed.

## Ollama Prerequisite (For Tool-Calling + Chat Variants)

If a solution uses a live chat model to drive tool-calling or reasoning steps, use Ollama as the local model runtime.

1. Install Ollama: [https://ollama.com/download](https://ollama.com/download)
1. Start Ollama:

```bash
ollama serve
```

1. Pull a default model:

```bash
ollama pull llama3.1:latest
```

1. Install the Ollama Python SDK:

```bash
pip install ollama
```

1. Optional quick check:

```bash
ollama run llama3.1:latest "Respond with: Ollama ready"
```

Note: Exercise 1 includes a model-backed tool-calling variant (`exercise-1-supervisor-worker/tool_calling_solution.py`) that requires Ollama. Other current Exercises 2-5 run without Ollama.

## Install

Run from the Chapter 14 `code/` folder:

```bash
uv sync
```

## Run the solutions

Run the five exercise solutions referenced in the chapter README:

- Exercise 1 path: `python solutions/exercise-1-supervisor-worker/solution.py`
- Exercise 2 path: `python solutions/exercise-2-debate-pattern/solution.py`
- Exercise 3 path: `python solutions/exercise-3-swarm-pattern/solution.py`
- Exercise 4 path: `python solutions/exercise-4-committee-pattern/solution.py`
- Exercise 5 path: `python solutions/exercise-5-peer-to-peer-pattern/solution.py`

## Expected output signals

Use these checks to confirm the solution flow matches the chapter.

- **Exercise 1 path**: Supervisor routes tasks in parallel; aggregation output shows all results ranked.
- **Exercise 2 path**: Debate produces two opposing arguments and a judge's selection with reasoning.
- **Exercise 3 path**: Swarm produces 3+ independent solutions, merger ranks them by quality score.
- **Exercise 4 path**: Committee shows each agent's vote and the final decision with voting breakdown.
- **Exercise 5 path**: Peer-to-peer shows negotiation rounds until agreement or timeout.

## Troubleshooting

If a command fails, first confirm you are in the correct folder and that the Python environment is available.

Run `uv --version` to confirm `uv` is installed.

Run `python --version` to confirm Python is available.
