import json
import re
from collections.abc import Callable
from typing import Any

import ollama
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.propagate import extract
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor


MODEL = "qwen3-vl:2b"
MAX_TOOL_ROUNDS = 3


def _build_tracer() -> trace.Tracer:
    provider = TracerProvider(
        resource=Resource.create({"service.name": "assignment-travel-agent"})
    )
    provider.add_span_processor(
        SimpleSpanProcessor(
            OTLPSpanExporter(endpoint="http://127.0.0.1:4318/v1/traces")
        )
    )
    return provider.get_tracer(__name__)


tracer = _build_tracer()


def get_trips(destination: str) -> dict[str, Any]:
    """Get available trips to a destination.

    Args:
        destination: Destination city.
    """
    return {
        "destination": destination,
        "trips": [
            {"name": "Trip A", "transport": "train", "price_usd": 180},
            {"name": "Trip B", "transport": "flight", "price_usd": 260},
        ],
        "source": "frozen assignment fixture",
    }


def get_hotels(destination: str) -> dict[str, Any]:
    """Get available hotels in a destination.

    Args:
        destination: Destination city.
    """
    return {
        "destination": destination,
        "hotels": [
            {"name": "Hotel A", "price_per_night_usd": 140},
            {"name": "Hotel B", "price_per_night_usd": 190},
        ],
        "source": "frozen assignment fixture",
    }


TOOLS: dict[str, Callable[..., dict[str, Any]]] = {
    "get_trips": get_trips,
    "get_hotels": get_hotels,
}
TOOL_DEFINITIONS = [get_trips, get_hotels]
REQUIRED_TOOLS = set(TOOLS)


def _is_travel_request(prompt: str) -> bool:
    prompt_lower = prompt.lower()
    action_match = re.search(r"\b(plan|book|find|recommend|arrange)\b", prompt_lower)
    subject_match = re.search(r"\b(trip|travel|hotel|flight)\b", prompt_lower)
    return bool(action_match and subject_match)


def _run_agent(prompt: str, model: str) -> str:
    messages: list[Any] = [
        {
            "role": "system",
            "content": (
                "You are a travel assistant. For every trip-planning request, call both "
                "get_trips and get_hotels with only the destination city. Base the final "
                "recommendation only on the tool results. Respond with exactly four lines, "
                "one per line, and no other text. The lines must be labeled exactly "
                "'Destination', 'Trip', 'Hotel', and 'Rationale'. The Trip and Hotel line "
                "values must come only from the tool results. Recommend exactly one trip "
                "and one hotel, and do not claim that anything has been booked. For "
                "requests outside travel planning, explain that you can only help plan "
                "trips."
            ),
        },
        {"role": "user", "content": prompt},
    ]

    if not _is_travel_request(prompt):
        return "I can only help with travel planning."

    called_tools: set[str] = set()

    for _ in range(MAX_TOOL_ROUNDS):
        response = ollama.chat(
            model=model,
            messages=messages,
            tools=TOOL_DEFINITIONS,
        )
        messages.append(response.message)
        tool_calls = response.message.tool_calls or []

        if not tool_calls:
            missing_tools = REQUIRED_TOOLS - called_tools
            if missing_tools:
                missing = ", ".join(sorted(missing_tools))
                raise RuntimeError(f"The model did not call required tools: {missing}")
            return response.message.content or ""

        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            arguments = dict(tool_call.function.arguments)
            function = TOOLS.get(tool_name)
            if function is None:
                raise RuntimeError(f"Unknown tool requested: {tool_name}")

            with tracer.start_as_current_span(f"tool {tool_name}") as tool_span:
                tool_span.set_attribute("tool.name", tool_name)
                tool_span.set_attribute("tool.arguments", json.dumps(arguments))
                result = function(**arguments)
                tool_span.set_attribute("tool.result", json.dumps(result))

            called_tools.add(tool_name)
            messages.append(
                {
                    "role": "tool",
                    "tool_name": tool_name,
                    "content": json.dumps(result),
                }
            )

        if REQUIRED_TOOLS.issubset(called_tools):
            final_response = ollama.chat(model=model, messages=messages)
            return final_response.message.content or ""

    missing = ", ".join(sorted(REQUIRED_TOOLS - called_tools))
    raise RuntimeError(f"Tool loop exceeded {MAX_TOOL_ROUNDS} rounds; missing: {missing}")


def call_api(
    prompt: str, options: dict[str, Any], context: dict[str, Any]
) -> dict[str, Any]:
    model = options.get("config", {}).get("model", MODEL)
    trace_headers = {}
    if context.get("traceparent"):
        trace_headers["traceparent"] = context["traceparent"]
    if context.get("tracestate"):
        trace_headers["tracestate"] = context["tracestate"]

    parent_context = extract(trace_headers)
    try:
        with tracer.start_as_current_span(
            "agent travel workflow", context=parent_context
        ) as agent_span:
            agent_span.set_attribute("agent.name", "travel_agent")
            agent_span.set_attribute("gen_ai.request.model", model)
            output = _run_agent(prompt, model)
        return {"output": output}
    except Exception as error:
        return {"output": "", "error": str(error)}
