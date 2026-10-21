"""Exercise 3: Add planning + tool orchestration with Ollama.

Goal:
- Use the model for intent classification.
- Run read-only tools and optionally one action tool.
- Require confirmation before action execution.

Try this:
1. Add one more category and tool.
2. Add retries around the classify call.
3. Persist session history to JSON.
"""

import json
import os

import ollama

OLLAMA_HOST = os.getenv("TRIAGE_OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("TRIAGE_OLLAMA_MODEL", "qwen2.5:1.5b")

CLASSIFIER_PROMPT = (
    "Classify IT support input into one category: network_issue, software_issue, account_issue, unknown. "
    "Return JSON with keys: category (string), needs_action (boolean), reason (string)."
)


def tool_network_check() -> str:
    return "Network check: packet loss 1%, latency 28ms, DNS stable."


def tool_installation_check() -> str:
    return "Install check: permissions ok, dependency mismatch found."


def tool_account_check() -> str:
    return "Account check: account unlocked, MFA required, recent failed login found."


def tool_apply_network_fix() -> str:
    return "Action simulated: DNS cache flush + adapter reset queued."


def classify(client: ollama.Client, user_input: str) -> dict[str, object]:
    response = client.chat(
        model=OLLAMA_MODEL,
        messages=[
            {"role": "system", "content": CLASSIFIER_PROMPT},
            {"role": "user", "content": user_input},
        ],
        format="json",
    )
    content = response.message.content.strip()
    payload = json.loads(content)

    category = str(payload.get("category", "unknown"))
    if category not in {"network_issue", "software_issue", "account_issue", "unknown"}:
        category = "unknown"

    return {
        "category": category,
        "needs_action": bool(payload.get("needs_action", False)),
        "reason": str(payload.get("reason", "")),
    }


def build_findings(category: str, needs_action: bool) -> list[str]:
    findings: list[str] = []

    if category == "network_issue":
        findings.append(tool_network_check())
        if needs_action:
            confirm = input("Assistant: Simulate network fix? (yes/no): ").strip().lower()
            findings.append(tool_apply_network_fix() if confirm == "yes" else "Action skipped by user.")
    elif category == "software_issue":
        findings.append(tool_installation_check())
    elif category == "account_issue":
        findings.append(tool_account_check())
    else:
        findings.append("No tool flow selected. Provide more context and exact error messages.")

    return findings


def generate_answer(client: ollama.Client, user_input: str, classification: dict[str, object], findings: list[str]) -> str:
    prompt = (
        f"User request: {user_input}\n"
        f"Category: {classification['category']}\n"
        f"Reason: {classification['reason']}\n"
        f"Findings: {findings}\n"
        "Write a concise response with next steps."
    )
    response = client.chat(
        model=OLLAMA_MODEL,
        messages=[
            {
                "role": "system",
                "content": "You are an IT support assistant. Be clear, practical, and concise.",
            },
            {"role": "user", "content": prompt},
        ],
    )
    return response.message.content.strip()


def print_help() -> None:
    print("\nCommands:")
    print("  /help     - Show commands")
    print("  /history  - Show session turns")
    print("  /model    - Show model and host")
    print("  /quit     - Exit the assistant\n")


def print_history(memory: list[dict[str, str]]) -> None:
    if not memory:
        print("Assistant: No history yet.")
        return

    print("\nSession history:")
    for idx, turn in enumerate(memory, start=1):
        print(f"{idx}. category={turn['category']} | user={turn['user']}")
    print()


def main() -> None:
    client = ollama.Client(host=OLLAMA_HOST)
    memory: list[dict[str, str]] = []

    print("Exercise 3: Ollama Assistant with Planning + Tools")
    print("Type '/help' for commands.\n")

    while True:
        user_input = input("You: ").strip()

        if not user_input:
            continue
        if user_input == "/quit":
            print("Assistant: Bye.")
            break
        if user_input == "/help":
            print_help()
            continue
        if user_input == "/history":
            print_history(memory)
            continue
        if user_input == "/model":
            print(f"Assistant: host={OLLAMA_HOST}, model={OLLAMA_MODEL}")
            continue

        try:
            classification = classify(client, user_input)
            category = str(classification["category"])
            findings = build_findings(category, bool(classification["needs_action"]))
            answer = generate_answer(client, user_input, classification, findings)

            memory.append(
                {
                    "user": user_input,
                    "category": category,
                    "assistant": answer,
                }
            )

            print(f"Assistant: {answer}")
        except Exception as exc:
            print(f"Assistant: Request failed: {exc}")


if __name__ == "__main__":
    main()
