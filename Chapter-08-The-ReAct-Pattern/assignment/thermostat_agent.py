"""Thermostat domain tools for the LLM ReAct agent."""
import random

from tools import Tool


def get_current_temperature() -> float:
    """Get current room temperature."""
    base = 68.0
    noise = random.uniform(-2, 2)
    return base + noise


def get_target_temperature() -> float:
    """Get target temperature setpoint."""
    return 72.0


def increase_heat(increment: int) -> str:
    """Increase heat level."""
    current_temp = get_current_temperature()
    estimated_next_temp = current_temp + random.uniform(0.5, 1.8)
    return (
        f"Heat increased by {increment}%. "
        f"Current temp: {current_temp:.1f}F, estimated next temp: {estimated_next_temp:.1f}F"
    )


def decrease_heat(decrement: int) -> str:
    """Decrease heat level."""
    current_temp = get_current_temperature()
    estimated_next_temp = current_temp - random.uniform(0.4, 1.4)
    return (
        f"Heat decreased by {decrement}%. "
        f"Current temp: {current_temp:.1f}F, estimated next temp: {estimated_next_temp:.1f}F"
    )


def get_heat_level() -> int:
    """Get current heat output level 0-100."""
    return random.randint(20, 80)


THERMOSTAT_TOOLS = [
    Tool(
        name="get_current_temperature",
        description="Get the current room temperature in Fahrenheit",
        fn=get_current_temperature,
        params={"type": "object", "properties": {}},
    ),
    Tool(
        name="get_target_temperature",
        description="Get the target temperature setpoint",
        fn=get_target_temperature,
        params={"type": "object", "properties": {}},
    ),
    Tool(
        name="get_heat_level",
        description="Get the current heat output level (0-100%)",
        fn=get_heat_level,
        params={"type": "object", "properties": {}},
    ),
    Tool(
        name="increase_heat",
        description="Increase the heat output",
        fn=increase_heat,
        params={
            "type": "object",
            "properties": {
                "increment": {"type": "integer", "description": "Amount to increase heat by (percentage)"}
            },
            "required": ["increment"],
        },
    ),
    Tool(
        name="decrease_heat",
        description="Decrease the heat output",
        fn=decrease_heat,
        params={
            "type": "object",
            "properties": {
                "decrement": {"type": "integer", "description": "Amount to decrease heat by (percentage)"}
            },
            "required": ["decrement"],
        },
    ),
]


THERMOSTAT_OBSERVATIONS = [
    (
        "You are a thermostat control agent. Your goal is to maintain a comfortable temperature. "
        "Check the current temperature and the target temperature. Adjust the heat as needed to reach the target."
    ),
    (
        "The temperature has changed. Monitor the current temperature and adjust the heat level "
        "if necessary to maintain the target temperature."
    ),
]
