# Solution

This project demonstrates a simple ReAct agent pattern with:

- Observe
- Reason with an LLM
- Act through tool calls
- Keep memory of past actions

Included examples:

- Stock trading
- Thermostat control
- Blackjack decision agent

## Prerequisites

- Python 3.10 or newer
- uv installed
- Ollama installed and running locally
- An Ollama model available locally, llama3.1:latest

> NOTE: Ollama needs to load the model into memory so the first time might be a bit slow but the other requests should go faster

## Setup

Make sure you've installed Ollama, Python and pulled down llama3.1:latest as you will need that for tool calling to work.

## Install

Install dependencies using uv:

```bash
uv sync
```

## Prepare Ollama

Start Ollama and make sure the model exists locally.

```bash
ollama pull llama3.1:latest
```

The examples are configured to use llama3.1:latest. If you want a different model, update the model name in example.py.

## How To Run

Run from the assignment folder.

Stock example:

```bash
uv run python example.py
```

Thermostat example:

```bash
uv run python example.py thermostat
```

Blackjack example:

```bash
uv run python example.py blackjack
```

## What You Should See

- Observation text per cycle
- LLM reasoning output
- Tool calls and tool results
- Final action history summary
- Tool call log path printed at startup

## Project Files

- **agent.py: core LLM ReAct loop and tool-call execution
- **state.py: per-cycle state plus cross-cycle action history
- **tools.py: shared Tool and ToolRegistry abstractions
- **stock_agent.py: stock tools and stock observations
- **thermostat_agent.py: thermostat tools and thermostat observations
- **blackjack_agent.py: blackjack tools and blackjack observations
- **example.py: command-line entrypoints for each example

## Troubleshooting

If no tool calls happen:

- Check Ollama is running.
- Confirm model name exists locally.
- Verify tool_call blocks are being produced in LLM responses.

If you see import errors:

- Make sure you are running from the assignment folder.
- Re-run dependency install with `uv sync`.

