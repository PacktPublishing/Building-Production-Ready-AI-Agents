"""Exercise 2: Add short-term memory on top of Ollama chat.

Goal:
- Keep session turns in memory.
- Feed prior turns back into the model.
- Add `/history` and `/summary` commands.

Try this:
1. Add `/clear` to reset memory.
2. Keep only the latest N turns.
3. Tag each turn with an issue_id.
"""

import os

import ollama

OLLAMA_HOST = os.getenv("TRIAGE_OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("TRIAGE_OLLAMA_MODEL", "qwen2.5:1.5b")

SYSTEM_PROMPT = (
    "You are an IT support assistant for beginners. "
    "Give practical steps and keep answers concise."
)


def print_help() -> None:
    print("\nCommands:")
    print("  /help     - Show commands")
    print("  /history  - Show session turns")
    print("  /summary  - Ask model to summarize this session")
    print("  /quit     - Exit the assistant\n")


def print_history(memory: list[dict[str, str]]) -> None:
    if not memory:
        print("Assistant: No history yet.")
        return

    print("\nSession history:")
    for idx, turn in enumerate(memory, start=1):
        print(f"{idx}. {turn['role']}: {turn['content']}")
    print()


def chat_with_memory(client: ollama.Client, memory: list[dict[str, str]], user_input: str) -> str:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(memory)
    messages.append({"role": "user", "content": user_input})

    response = client.chat(model=OLLAMA_MODEL, messages=messages)
    return response.message.content.strip()


def summarize_memory(client: ollama.Client, memory: list[dict[str, str]]) -> str:
    if not memory:
        return "Nothing to summarize yet."

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(memory)
    messages.append(
        {"role": "user", "content": "Summarize this IT support session in 3 bullets."}
    )
    response = client.chat(model=OLLAMA_MODEL, messages=messages)
    return response.message.content.strip()


def main() -> None:
    client = ollama.Client(host=OLLAMA_HOST)
    memory: list[dict[str, str]] = []

    print("Exercise 2: Ollama Assistant with Short-Term Memory")
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
        if user_input == "/summary":
            try:
                print(f"Assistant: {summarize_memory(client, memory)}")
            except Exception as exc:
                print(f"Assistant: Summary failed: {exc}")
            continue

        try:
            answer = chat_with_memory(client, memory, user_input)
            memory.append({"role": "user", "content": user_input})
            memory.append({"role": "assistant", "content": answer})
            print(f"Assistant: {answer}")
        except Exception as exc:
            print(f"Assistant: Ollama request failed: {exc}")


if __name__ == "__main__":
    main()
