"""
Exercise 4: Swarm Pattern

Implement a swarm where multiple agents independently plan a trip with different
priorities, then a merger ranks and selects the best plan.

Planners:
- CostPlanner: minimize total cost
- ComfortPlanner: maximize comfort and convenience
- ExperiencePlanner: prioritize local experience and activities
"""

import json
import time


class TripPlanner:
    """Base planner for trips."""

    def __init__(self, name: str, priority: str):
        self.name = name
        self.priority = priority

    def plan(self, destination: str, budget: float, nights: int) -> dict:
        """Create a trip plan based on planner's priority."""
        raise NotImplementedError


class CostPlanner(TripPlanner):
    """Plans trips with cost minimization."""

    def __init__(self):
        super().__init__("Cost Planner", "minimize_cost")

    def plan(self, destination: str, budget: float, nights: int) -> dict:
        time.sleep(0.1)
        return {
            "planner": self.name,
            "destination": destination,
            "nights": nights,
            "flight": {"airline": "Budget Air", "price": 280, "quality": 6},
            "hotel": {"name": "Budget Hostel", "price_per_night": 60, "rating": 3.8},
            "activities": [
                {"name": "Free walking tour", "cost": 0},
                {"name": "Public museums (cheap days)", "cost": 10},
            ],
            "total_cost": 280 + (60 * nights) + 10,
            "quality_score": 6.5,
            "rationale": "Maximum savings without sacrificing basics. Local transit and free activities.",
        }


class ComfortPlanner(TripPlanner):
    """Plans trips with comfort maximization."""

    def __init__(self):
        super().__init__("Comfort Planner", "maximize_comfort")

    def plan(self, destination: str, budget: float, nights: int) -> dict:
        time.sleep(0.1)
        return {
            "planner": self.name,
            "destination": destination,
            "nights": nights,
            "flight": {"airline": "SAS", "price": 450, "quality": 9},
            "hotel": {"name": "Downtown Luxury", "price_per_night": 200, "rating": 4.8},
            "activities": [
                {"name": "Private city tour", "cost": 150},
                {"name": "Fine dining reservation", "cost": 200},
            ],
            "total_cost": 450 + (200 * nights) + 350,
            "quality_score": 9.2,
            "rationale": "Direct flights, luxury accommodation, curated experiences. No compromises.",
        }


class ExperiencePlanner(TripPlanner):
    """Plans trips with experience prioritization."""

    def __init__(self):
        super().__init__("Experience Planner", "maximize_experience")

    def plan(self, destination: str, budget: float, nights: int) -> dict:
        time.sleep(0.1)
        return {
            "planner": self.name,
            "destination": destination,
            "nights": nights,
            "flight": {"airline": "Lufthansa", "price": 520, "quality": 8},
            "hotel": {"name": "Boutique Local Hotel", "price_per_night": 140, "rating": 4.5},
            "activities": [
                {"name": "Food tour with local chef", "cost": 120},
                {"name": "Workshop (traditional crafts)", "cost": 80},
                {"name": "Jazz club evening", "cost": 60},
            ],
            "total_cost": 520 + (140 * nights) + 260,
            "quality_score": 8.5,
            "rationale": "Balance of comfort and authentic local experiences. Deep cultural immersion.",
        }


class TripMerger:
    """Evaluates multiple trip plans and selects the best."""

    def merge(self, plans: list[dict], user_priority: str = "balanced") -> dict:
        """Merges and ranks multiple plans."""
        time.sleep(0.15)

        print("\n[Merger] Evaluating all plans...")
        print(f"  Cost Planner: ${plans[0]['total_cost']} (score: {plans[0]['quality_score']})")
        print(f"  Comfort Planner: ${plans[1]['total_cost']} (score: {plans[1]['quality_score']})")
        print(f"  Experience Planner: ${plans[2]['total_cost']} (score: {plans[2]['quality_score']})")

        # Score each plan based on user priority
        if user_priority == "cost":
            best = min(plans, key=lambda p: p["total_cost"])
        elif user_priority == "comfort":
            best = max(plans, key=lambda p: p["quality_score"])
        else:  # balanced
            # Balanced score: quality/cost ratio
            plans_with_score = [
                (p, p["quality_score"] / (p["total_cost"] / 100)) for p in plans
            ]
            best = max(plans_with_score, key=lambda x: x[1])[0]

        return {
            "selected_plan": best,
            "all_plans": [
                {
                    "planner": p["planner"],
                    "total_cost": p["total_cost"],
                    "quality_score": p["quality_score"],
                }
                for p in plans
            ],
            "merge_reasoning": f"Selected {best['planner']} based on '{user_priority}' priority.",
        }


def main():
    destination = "Copenhagen"
    budget = 2200
    nights = 3

    print(f"[Swarm] Planning trip to {destination} for {nights} nights (budget: ${budget})")
    print("Running 3 planners in parallel...\n")

    # Run planners in parallel (simulated)
    cost_planner = CostPlanner()
    comfort_planner = ComfortPlanner()
    experience_planner = ExperiencePlanner()

    plans = [
        cost_planner.plan(destination, budget, nights),
        comfort_planner.plan(destination, budget, nights),
        experience_planner.plan(destination, budget, nights),
    ]

    # Merger selects best
    merger = TripMerger()
    result = merger.merge(plans, user_priority="balanced")

    print("\n" + "=" * 50)
    print("Swarm Result:")
    print(json.dumps({
        "selected_plan": {
            "planner": result["selected_plan"]["planner"],
            "hotel": result["selected_plan"]["hotel"],
            "total_cost": result["selected_plan"]["total_cost"],
            "quality_score": result["selected_plan"]["quality_score"],
        },
        "all_options": result["all_plans"],
    }, indent=2))


if __name__ == "__main__":
    main()
