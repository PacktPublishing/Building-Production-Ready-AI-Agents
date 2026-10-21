# Chapter 10 Code

This folder contains the runnable reference implementations for Chapter 10. The goal of these scripts is to show the contrast between a pure LLM-driven agent loop and a workflow-first agent loop where step execution is deterministic.

Use this folder when you want to run the examples exactly as described in the chapter and inspect how architecture choices change behavior. You can run the pure-agent version with `00-agent.py` and the workflow-first version with `01-agent.py`.

The sections below walk you through prerequisites, setup, installation, and execution so you can get started quickly.

## Pre-req

Before running these scripts, make sure your local environment can execute Python and call Ollama. You should also have a model pulled locally that matches what the scripts expect.

- **Python**: Install Python 3.12 or later.
- **uv**: Install `uv` for environment and dependency management.
- **Ollama**: Install and run Ollama locally.
- **Model**: Pull the model used in these samples, for example `mistral`.

Once these prerequisites are in place, proceed with environment setup.

## Set up

Start by opening a terminal in this `code/` directory. Then create and activate your local virtual environment if you are not already inside one.

```bash
cd Chapter-10-Agent-Architecture-and-Planning-Systems/code
uv venv
```

After setup, install the project dependencies.

## Installation

Install Ollama first, then pull the model used by these scripts. After that, install Python dependencies from `pyproject.toml` and `uv.lock`.

Install Ollama:

```bash
# Windows (winget)
winget install Ollama.Ollama

# macOS (Homebrew)
brew install ollama

# Linux
curl -fsSL https://ollama.com/install.sh | sh
```

Start Ollama and pull the model:

```bash
ollama serve
```

In a second terminal:

```bash
ollama pull mistral
ollama list
```

Then install project dependencies:

```bash
uv sync
```

After installation completes, you are ready to run the chapter examples.

## Run

Run the pure-agent and workflow-agent scripts to compare how they behave. Use `--verbose` when you want to inspect intermediate steps and decisions.

```bash
uv run python 00-agent.py --verbose
uv run python 00-agent.py --prompt "Write a short guide on sourdough bread"

uv run python 01-agent.py --verbose
uv run python 01-agent.py --prompt "Order me a pepperoni pizza"
```

You can now edit prompts or workflows in this folder and rerun these commands to experiment with architecture tradeoffs.
