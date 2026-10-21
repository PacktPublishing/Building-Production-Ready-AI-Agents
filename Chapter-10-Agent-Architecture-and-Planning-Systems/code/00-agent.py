"""
00-agent.py — The Naive Pure Agent

Demonstrates a minimal autonomous agent loop where the LLM decides
everything: what to do next, which tool to call, and whether the goal
is achieved.  This works well for low-risk, creative tasks (research,
writing) but quickly falls apart for multi-step business logic.

Run:
    uv run python 00-agent.py
    uv run python 00-agent.py --prompt "Write a short guide on how to make sourdough bread"
    uv run python 00-agent.py --verbose
"""

from __future__ import annotations

import argparse
import json
import time

from ollama import ChatResponse, chat

OLLAMA_MODEL = "mistral"
MAX_ITERATIONS = 10
VERBOSE = False

RESET = "\033[0m"
BOLD = "\033[1m"
COLORS = {
    "user": "\033[96m",
    "agent": "\033[93m",
    "tool": "\033[95m",
    "success": "\033[32m",
    "warn": "\033[33m",
    "error": "\033[91m",
}


def log(role: str, message: str) -> None:
    color = COLORS.get(role, "")
    label = role.capitalize()
    print(f"{color}{label}>{RESET} {message}")


def log_verbose(message: str) -> None:
    if VERBOSE:
        log("tool", message)


# ---------------------------------------------------------------------------
# Tools — simple stubs that simulate real work
# ---------------------------------------------------------------------------

def search_web(query: str) -> str:
    """Simulate a web search and return results."""
    return (
        f"Search results for '{query}':\n"
        f"1. '{query}' - Wikipedia overview with key facts and history.\n"
        f"2. '{query}' - Recent news article with current developments.\n"
        f"3. '{query}' - Expert blog post with practical tips."
    )


def take_notes(content: str) -> str:
    """Save a note for later use."""
    return f"Note saved: {content[:80]}..."


def write_summary(topic: str, notes: str) -> str:
    """Produce a final summary from collected notes."""
    return (
        f"Summary of '{topic}':\n"
        f"Based on research: {notes[:120]}...\n"
        f"Key takeaway: This topic has multiple interesting facets worth exploring."
    )


TOOLS = {
    "search_web": {
        "fn": search_web,
        "description": "Search the web for information. Params: query (str)",
    },
    "take_notes": {
        "fn": take_notes,
        "description": "Save a research note. Params: content (str)",
    },
    "write_summary": {
        "fn": write_summary,
        "description": "Write a final summary. Params: topic (str), notes (str)",
    },
}

TOOLS_DESCRIPTION = "\n".join(
    f"- {name}: {info['description']}" for name, info in TOOLS.items()
)


# ---------------------------------------------------------------------------
# LLM helpers
# ---------------------------------------------------------------------------

def llm_json(messages: list[dict], schema: dict, phase: str) -> dict:
    log_verbose(f"Thinking ({phase})...")
    start = time.perf_counter()
    response: ChatResponse = chat(
        model=OLLAMA_MODEL, messages=messages, format=schema
    )
    elapsed = time.perf_counter() - start
    log_verbose(f"Finished ({phase}) in {elapsed:.1f}s")
    return json.loads(response.message.content)


# ---------------------------------------------------------------------------
# Agent loop — the LLM drives every decision
# ---------------------------------------------------------------------------

def run_agent(user_input: str) -> None:
    log("user", user_input)

    # Step 1: LLM identifies the goal
    goal = llm_json(
        [
            {
                "role": "system",
                "content": (
                    "You are a planning assistant. Given the user's request, "
                    "produce a clear one-sentence goal and a short checklist "
                    "of 3-5 steps to achieve it. Each step should be a short phrase."
                ),
            },
            {"role": "user", "content": user_input},
        ],
        {
            "type": "object",
            "properties": {
                "goal": {"type": "string"},
                "steps": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
            "required": ["goal", "steps"],
        },
        "goal identification",
    )

    goal_text = goal.get("goal", user_input)
    steps = goal.get("steps", [])
    log("agent", f"Goal: {goal_text}")
    log("agent", "Plan:")
    for i, step in enumerate(steps, 1):
        print(f"  {i}. {step}")

    # Step 2: Agent loop — LLM picks the next action each iteration
    history: list[str] = []
    completed_steps: list[str] = []

    for iteration in range(1, MAX_ITERATIONS + 1):
        log("agent", f"\n--- Iteration {iteration}/{MAX_ITERATIONS} ---")

        # Ask the LLM: what tool should I call next?
        decision = llm_json(
            [
                {
                    "role": "system",
                    "content": (
                        f"You are an autonomous agent pursuing this goal: {goal_text}\n\n"
                        f"Original plan:\n"
                        + "\n".join(f"- {s}" for s in steps)
                        + "\n\n"
                        f"Completed so far:\n"
                        + ("\n".join(f"- {s}" for s in completed_steps) or "- Nothing yet")
                        + "\n\n"
                        f"Action history:\n"
                        + ("\n".join(history[-6:]) or "- None yet")
                        + "\n\n"
                        f"Available tools:\n{TOOLS_DESCRIPTION}\n\n"
                        "Decide the next action. Pick one tool and provide its "
                        "parameters. If the goal is fully achieved, set done=true."
                    ),
                },
                {"role": "user", "content": "What should I do next?"},
            ],
            {
                "type": "object",
                "properties": {
                    "done": {"type": "boolean"},
                    "reasoning": {"type": "string"},
                    "tool": {"type": "string"},
                    "params": {"type": "object"},
                    "completed_step": {"type": "string"},
                },
                "required": ["done", "reasoning", "tool"],
            },
            f"action decision (iter {iteration})",
        )

        reasoning = decision.get("reasoning", "")
        log("agent", f"Reasoning: {reasoning}")

        # Check if the LLM thinks we're done
        if decision.get("done", False):
            log("success", "Agent decided the goal is achieved.")
            break

        tool_name = decision.get("tool", "").strip()
        params = decision.get("params", {})

        if tool_name not in TOOLS:
            log("warn", f"LLM picked unknown tool '{tool_name}' — skipping.")
            history.append(f"Error: unknown tool '{tool_name}'")
            continue

        # Execute the tool
        tool_fn = TOOLS[tool_name]["fn"]
        log("tool", f"Calling {tool_name}({params})")
        try:
            result = tool_fn(**params)
            log("tool", f"Result: {result}")
            history.append(f"Called {tool_name}({params}) -> {result[:100]}")
        except TypeError as exc:
            log("error", f"Tool call failed: {exc}")
            history.append(f"Error calling {tool_name}: {exc}")
            continue

        # Track completed steps
        completed_step = decision.get("completed_step", "")
        if completed_step:
            completed_steps.append(completed_step)

    else:
        log("warn", f"Reached max iterations ({MAX_ITERATIONS}) without completing the goal.")

    # Final evaluation
    log("agent", "\n=== Final Status ===")
    log("agent", f"Goal: {goal_text}")
    log("agent", f"Steps completed: {len(completed_steps)}/{len(steps)}")
    for step in steps:
        marker = "✓" if step in completed_steps else "○"
        print(f"  {marker} {step}")
    log("agent", f"Total LLM calls: {iteration + 1}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Naive pure-agent loop")
    parser.add_argument(
        "--prompt",
        default="Research the history of coffee and write a short summary.",
        help="User prompt for the agent",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show LLM timing and debug info",
    )
    args = parser.parse_args()

    VERBOSE = args.verbose
    run_agent(args.prompt)
