"""Exercise 1: Tiny terminal assistant backed by Ollama.

Goal:
- Use `uv` + `ollama` in a minimal terminal app.
- Send one user message to the model and print the reply.

Try this:
1. Change the system prompt tone.
2. Cap response length harder.
3. Add one command that injects extra context.
"""

import os

import ollama

OLLAMA_HOST = os.getenv("TRIAGE_OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("TRIAGE_OLLAMA_MODEL", "qwen2.5:1.5b")


def ask_model(client: ollama.Client, user_input: str) -> str:
    response = client.chat(
        model=OLLAMA_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a helpful IT support assistant for beginners. "
                    "Be concise and practical. Use at most 4 short bullets when useful."
                ),
            },
            {"role": "user", "content": user_input},
        ],
    )
    return response.message.content.strip()


def print_help() -> None:
    print("\nCommands:")
    print("  /help  - Show commands")
    print("  /model - Show model and host")
    print("  /quit  - Exit the assistant\n")


def main() -> None:
    client = ollama.Client(host=OLLAMA_HOST)

    print("Exercise 1: Tiny Ollama Assistant")
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
        if user_input == "/model":
            print(f"Assistant: host={OLLAMA_HOST}, model={OLLAMA_MODEL}")
            continue

        try:
            answer = ask_model(client, user_input)
            print(f"Assistant: {answer}")
        except Exception as exc:
            print(f"Assistant: Ollama request failed: {exc}")


if __name__ == "__main__":
    main()
