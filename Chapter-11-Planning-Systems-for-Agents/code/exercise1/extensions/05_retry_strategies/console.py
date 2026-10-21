import os
from typing import List


class Colors:
    RESET = "\033[0m"
    CYAN = "\033[36m"
    GREEN = "\033[32m"
    RED = "\033[31m"
    YELLOW = "\033[33m"


def colorize(text: str, color: str) -> str:
    if os.getenv("NO_COLOR"):
        return text
    return f"{color}{text}{Colors.RESET}"


def agent_print(message: str) -> None:
    print(colorize(message, Colors.CYAN))


def user_print(message: str) -> None:
    print(colorize(message, Colors.GREEN))


def error_print(message: str) -> None:
    print(colorize(message, Colors.RED))


def warn_print(message: str) -> None:
    print(colorize(message, Colors.YELLOW))


def user_input(prompt: str) -> str:
    return input(colorize(f"[USER] {prompt}", Colors.GREEN))


def choose_numbered_option(prompt: str, options: List[str]) -> int:
    while True:
        user_print(f"[USER] {prompt}")
        for idx, option in enumerate(options, start=1):
            user_print(f"[USER]   {idx}) {option}")

        selected = user_input("Select a number: ").strip()
        if selected.isdigit():
            selected_idx = int(selected)
            if 1 <= selected_idx <= len(options):
                return selected_idx

        error_print(f"[PLANNER] Please choose a number between 1 and {len(options)}.")
