"""
Exercise 3: Debate Pattern

Implement a debate where two agents take opposing views on a flight choice,
then a judge selects the stronger argument.

Debaters:
- CostDebater: argues for the cheapest option
- ComfortDebater: argues for the most comfortable option
Judge: evaluates both arguments and selects the winner
"""

import json
import time


class FlightDebater:
    """Base debater for flights."""

    def __init__(self, name: str, priority: str):
        self.name = name
        self.priority = priority

    def argue(self, flights: list[dict]) -> dict:
        """Make an argument for a specific flight choice."""
        raise NotImplementedError


class CostDebater(FlightDebater):
    """Argues for the cheapest option."""

    def __init__(self):
        super().__init__("Cost Debater", "minimize_cost")

    def argue(self, flights: list[dict]) -> dict:
        """Selects cheapest and argues for it."""
        time.sleep(0.05)
        best = min(flights, key=lambda f: f["price"])
        return {
            "debater": self.name,
            "choice": best,
            "argument": f"The {best['airline']} flight at ${best['price']} is the clear choice. "
            "We save money that can be allocated elsewhere. "
            f"Yes, it has {best['connections']} connections, but the cost savings justify it.",
            "reasoning": ["Cost efficiency", "Maximize budget for other needs", "Reasonable travel time"],
        }


class ComfortDebater(FlightDebater):
    """Argues for the most comfortable option."""

    def __init__(self):
        super().__init__("Comfort Debater", "maximize_comfort")

    def argue(self, flights: list[dict]) -> dict:
        """Selects most comfortable and argues for it."""
        time.sleep(0.05)
        best = max(flights, key=lambda f: f["quality_score"])
        return {
            "debater": self.name,
            "choice": best,
            "argument": f"The {best['airline']} flight is the better choice despite the price. "
            f"Direct flights ({best['connections']} connections) mean we arrive refreshed. "
            "A tired traveler is less productive. The comfort premium is worth the investment.",
            "reasoning": ["Minimize fatigue", "Direct routing saves time", "Professional impression"],
        }


class FlightJudge:
    """Evaluates both arguments and selects the stronger one."""

    def judge(self, cost_argument: dict, comfort_argument: dict, trip_context: dict) -> dict:
        """Judges both arguments and returns a decision."""
        time.sleep(0.1)

        print(f"\n[Judge] Evaluating both arguments...")
        print(f"  Cost Debater: {cost_argument['argument'][:60]}...")
        print(f"  Comfort Debater: {comfort_argument['argument'][:60]}...")

        # Decision logic: if budget allows and trip is important, prefer comfort
        budget_ratio = trip_context.get("total_budget", 2200) / cost_argument["choice"]["price"]
        is_important = trip_context.get("importance", "normal") == "high"

        if is_important and budget_ratio > 4:
            winner = "Comfort"
            reasoning = (
                "This is an important trip. Given the budget, "
                "arriving rested justifies the comfort premium."
            )
        else:
            winner = "Cost"
            reasoning = (
                "Given the constraints, cost efficiency wins. "
                "The cheaper flight is acceptable for this trip."
            )

        return {
            "winner": winner,
            "selected_flight": comfort_argument["choice"] if winner == "Comfort" else cost_argument["choice"],
            "reasoning": reasoning,
            "cost_argument": cost_argument,
            "comfort_argument": comfort_argument,
        }


def main():
    # Sample flights
    flights = [
        {"airline": "SAS", "price": 450, "connections": 0, "quality_score": 9},
        {"airline": "Lufthansa", "price": 520, "connections": 1, "quality_score": 8},
        {"airline": "Budget Air", "price": 280, "connections": 2, "quality_score": 6},
    ]

    trip_context = {
        "destination": "Copenhagen",
        "total_budget": 2200,
        "importance": "high",
    }

    print("[Debate] Evaluating flight options...")
    print(f"Available flights: {len(flights)}")

    # Run debate
    cost_debater = CostDebater()
    comfort_debater = ComfortDebater()
    judge = FlightJudge()

    cost_arg = cost_debater.argue(flights)
    comfort_arg = comfort_debater.argue(flights)

    print(f"\n[Cost Debater] {cost_arg['argument']}")
    print(f"\n[Comfort Debater] {comfort_arg['argument']}")

    decision = judge.judge(cost_arg, comfort_arg, trip_context)

    print("\n" + "=" * 50)
    print("Judge's Decision:")
    print(json.dumps({
        "winner": decision["winner"],
        "selected_flight": decision["selected_flight"],
        "reasoning": decision["reasoning"],
    }, indent=2))


if __name__ == "__main__":
    main()
