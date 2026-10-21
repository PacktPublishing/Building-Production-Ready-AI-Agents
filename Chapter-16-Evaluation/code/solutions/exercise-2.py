import argparse
import json
from pathlib import Path
from typing import Any

from ollama import Client


SYSTEM_PROMPT = (
    "You create high-quality evaluation datasets for LLM testing. "
    "Return valid JSON only as an array with this schema: "
    "[{\"description\": string, \"vars\": {\"request\": string, \"expected_response\": string}}]. "
    "The top-level JSON value must be the array itself, with no wrapper object or wrapper key. "
    "Do not include markdown fences or commentary."
)


def build_user_prompt(seed_examples: list[dict[str, Any]], min_items: int) -> str:
    return (
        f"Generate exactly {min_items} new evaluation entries for a travel booking app. "
        "Cover normal cases, edge cases (tight budgets, missing dates, ambiguity), and adversarial attempts "
        "(policy bypass requests, unsafe asks) while keeping expected responses safe and policy-compliant. "
        "Use concise but specific expected responses.\n\n"
        "The following objects demonstrate the required item shape. Do not copy them, include them, "
        "or reuse their destinations, wording, or numbers:\n"
        f"{json.dumps(seed_examples, indent=2)}\n\n"
        f"Return one JSON array containing exactly {min_items} new objects. "
        "The response must begin with '[' and end with ']'."
    )


def try_parse_json(text: str) -> list[dict[str, Any]]:
    text = text.strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Fallback for models that still wrap JSON in code fences.
        start = text.find("[")
        end = text.rfind("]")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("Model output did not contain a JSON array.")
        data = json.loads(text[start : end + 1])

    if not isinstance(data, list):
        raise ValueError("Model output must have a JSON array as its top-level value.")

    return data


def build_response_schema(min_items: int) -> dict[str, Any]:
    return {
        "type": "array",
        "minItems": min_items,
        "maxItems": min_items,
        "items": {
            "type": "object",
            "required": ["description", "vars"],
            "properties": {
                "description": {"type": "string"},
                "vars": {
                    "type": "object",
                    "required": ["request", "expected_response"],
                    "properties": {
                        "request": {"type": "string"},
                        "expected_response": {"type": "string"},
                    },
                },
            },
        },
    }


def validate_dataset(data: list[dict[str, Any]], min_items: int) -> None:
    if not isinstance(data, list):
        raise ValueError("Dataset must be a JSON array of Promptfoo test cases.")

    if len(data) < min_items:
        raise ValueError(f"Expected at least {min_items} eval entries, got {len(data)}.")

    for i, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Eval item {i} must be an object.")
        if not isinstance(item.get("description"), str) or not item["description"].strip():
            raise ValueError(f"Eval item {i} must contain a non-empty 'description'.")
        vars_value = item.get("vars")
        if not isinstance(vars_value, dict):
            raise ValueError(f"Eval item {i} must contain a 'vars' object.")
        for field in ("request", "expected_response"):
            if not isinstance(vars_value.get(field), str) or not vars_value[field].strip():
                raise ValueError(f"Eval item {i} must contain a non-empty '{field}'.")


def generate_dataset(model: str, min_items: int, host: str | None = None) -> list[dict[str, Any]]:
    client = Client(host=host) if host else Client()

    seed_examples = [
        {
            "description": "Seattle business trip stays within budget",
            "vars": {
                "request": "Use only these options to recommend one flight and one hotel for a 5-day Seattle business trip under $2200 total: Flights A=$450, B=$400. Hotels A=$150/night, B=$200/night. Include total and one-line rationale.",
                "expected_response": "Recommend one valid pair from the given list, compute a correct 5-night total, remain under budget, and include a concise rationale.",
            },
        },
        {
            "description": "NYC leisure trip stays within budget",
            "vars": {
                "request": "Use only these options to recommend one flight and one hotel for a 3-day NYC trip under $1500 total: Flights A=$300, B=$350. Hotels A=$250/night, B=$200/night. Include total and one-line rationale.",
                "expected_response": "Recommend one valid pair from the given list, compute a correct 3-night total, remain under budget, and include a concise rationale.",
            },
        },
    ]

    response = client.chat(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(seed_examples, min_items)},
        ],
        format=build_response_schema(min_items),
        options={"temperature": 0.4},
    )

    content = response["message"]["content"]
    data = try_parse_json(content)
    validate_dataset(data, min_items)
    return data


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a travel-booking eval dataset using the Ollama Python SDK."
    )
    parser.add_argument("--model", default="llama3.1", help="Ollama model name (default: llama3.1)")
    parser.add_argument("--min-items", type=int, default=10, help="Minimum number of eval cases")
    parser.add_argument(
        "--output",
        default="travel-booking-dataset.json",
        help="Output JSON file path",
    )
    parser.add_argument(
        "--host",
        default=None,
        help="Optional Ollama host URL, e.g. http://localhost:11434",
    )

    args = parser.parse_args()

    data = generate_dataset(model=args.model, min_items=args.min_items, host=args.host)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    print(f"Wrote {len(data)} eval items to {output_path}")


if __name__ == "__main__":
    main()
