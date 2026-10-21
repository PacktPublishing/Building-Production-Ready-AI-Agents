import json
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


def _build_tracer() -> trace.Tracer:
    provider = TracerProvider(
        resource=Resource.create({"service.name": "exercise-4-weather-agent"})
    )
    provider.add_span_processor(
        SimpleSpanProcessor(
            OTLPSpanExporter(endpoint="http://127.0.0.1:4318/v1/traces")
        )
    )
    return provider.get_tracer(__name__)


tracer = _build_tracer()


def get_weather(location: str) -> dict[str, Any]:
    """Get the current weather for a location.

    Args:
        location: City whose weather should be retrieved.
    """
    return {
        "location": location,
        "condition": "partly cloudy",
        "temperature_f": 68,
        "source": "frozen exercise fixture",
    }


TOOLS: dict[str, Callable[..., dict[str, Any]]] = {
    "get_weather": get_weather,
}


def _run_agent(prompt: str, model: str) -> str:
    messages: list[Any] = [
        {
            "role": "system",
            "content": (
                "You are a weather assistant. Always use get_weather before answering a "
                "weather question. Pass only the city name from the user's request as the "
                "location argument. Base the final answer only on the tool result."
            ),
        },
        {"role": "user", "content": prompt},
    ]

    first_response = ollama.chat(model=model, messages=messages, tools=[get_weather])
    messages.append(first_response.message)

    tool_calls = first_response.message.tool_calls or []
    if not tool_calls:
        raise RuntimeError("The model did not call get_weather")

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

        messages.append(
            {
                "role": "tool",
                "tool_name": tool_name,
                "content": json.dumps(result),
            }
        )

    final_response = ollama.chat(model=model, messages=messages, tools=[get_weather])
    return final_response.message.content or ""


def call_api(prompt: str, options: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    model = options.get("config", {}).get("model", MODEL)
    trace_headers = {}
    if context.get("traceparent"):
        trace_headers["traceparent"] = context["traceparent"]
    if context.get("tracestate"):
        trace_headers["tracestate"] = context["tracestate"]

    parent_context = extract(trace_headers)
    try:
        with tracer.start_as_current_span(
            "agent weather workflow", context=parent_context
        ) as agent_span:
            agent_span.set_attribute("agent.name", "weather_agent")
            agent_span.set_attribute("gen_ai.request.model", model)
            output = _run_agent(prompt, model)
        return {"output": output}
    except Exception as error:
        return {"output": "", "error": str(error)}
