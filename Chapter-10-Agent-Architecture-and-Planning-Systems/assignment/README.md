# Chapter 10 Assignment

This folder contains the assignment implementation for Chapter 10. It is meant to help you practice workflow-first agent architecture by extending a deterministic execution engine with your own workflow.

The assignment version includes trip and pizza workflows, plus a meeting planner workflow so you can see how to add, register, and run new flows. The focus here is not just getting output, but understanding planner-executor boundaries, traceability, and recovery behavior.

The sections below give you a clean path from prerequisites to running the assignment agent.

## Pre-req

Before you run the assignment, make sure your machine can run Python tooling and local LLM calls. You should also have the model available locally.

- **Python**: Install Python 3.12 or later.
- **uv**: Install `uv` to manage dependencies and execution.
- **Ollama**: Install and run Ollama locally.
- **Model**: Pull `mistral` (or adjust the model constant in the agent file).

With prerequisites ready, you can initialize the folder environment.

## Set up

Open a terminal in this `assignment/` folder and initialize a local virtual environment. Keeping setup local helps you isolate assignment dependencies from other chapters.

```bash
cd Chapter-10-Agent-Architecture-and-Planning-Systems/assignment
uv venv
```

After setup, install the dependencies for this assignment project.

## Installation

Install Ollama first, pull the required model, and then install Python dependencies. This ensures both the runtime and local LLM model are ready before you run the assignment.

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

Once installation finishes, you can run the assignment agent and test workflows.

## Run

Run the assignment agent with different prompts to trigger different workflows. Use a meeting-oriented prompt to validate the meeting planner flow.

```bash
uv run python agent.py --verbose
uv run python agent.py --prompt "Plan a project kickoff meeting next Tuesday with Alice and Bob"
uv run python agent.py --prompt "I need to plan a trip to Paris next month"
```

You can now modify `meeting-planner-workflow.py` or add new workflows, then rerun the same commands to verify behavior.
