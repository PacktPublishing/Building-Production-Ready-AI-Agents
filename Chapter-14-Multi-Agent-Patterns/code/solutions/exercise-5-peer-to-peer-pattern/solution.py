"""
Exercise 6: Peer-to-Peer Pattern

Implement negotiation between two agents with conflicting interests.
They negotiate until reaching agreement or timeout.

Agents:
- CostAgent: wants to minimize spending
- ExperienceAgent: wants to maximize comfort and experience
"""

import json
import time


class NegotiationAgent:
    """Base class for negotiating agents."""

    def __init__(self, name: str, priority: str, initial_offer: dict):
        self.name = name
        self.priority = priority
        self.initial_offer = initial_offer
        self.last_received_offer = None

    def make_offer(self, round_number: int) -> dict:
        """Create a negotiation offer."""
        raise NotImplementedError

    def respond_to_offer(self, received_offer: dict, round_number: int) -> dict:
        """Respond to a received offer."""
        raise NotImplementedError


class CostNegotiator(NegotiationAgent):
    """Wants to minimize spending."""

    def __init__(self):
        super().__init__(
            "Cost Agent",
            "minimize_cost",
            {"hotel": "Budget", "flight": "Direct", "max_total": 700},
        )

    def make_offer(self, round_number: int) -> dict:
        time.sleep(0.05)
        if round_number == 1:
            offer = self.initial_offer.copy()
        else:
            # Slightly increase offer in later rounds
            offer = {
                "hotel": "Budget to Mid-range",
                "flight": "Direct",
                "max_total": 900 + (round_number * 100),
                "rationale": "I can stretch budget slightly, but we need to stay fiscally responsible.",
            }
        return offer

    def respond_to_offer(self, received_offer: dict, round_number: int) -> dict:
        time.sleep(0.05)
        self.last_received_offer = received_offer

        # Check if offer is acceptable
        max_acceptable = 1100
        received_total = (
            received_offer.get("suggested_total")
            or received_offer.get("min_total")
            or received_offer.get("max_total")
        )

        if received_total is None:
            return {
                "agent": self.name,
                "status": "COUNTER",
                "response": "No usable total found in offer. I can go to $1100.",
                "counter_offer": {"max_total": max_acceptable},
            }

        if received_total <= max_acceptable:
            return {
                "agent": self.name,
                "status": "ACCEPT",
                "response": f"I can accept up to ${max_acceptable}. Your offer of ${received_total} works.",
                "agreed_total": received_total,
            }
        else:
            # Counter offer
            counter = int(received_total * 0.8)  # Offer 80% of what they asked
            return {
                "agent": self.name,
                "status": "COUNTER",
                "response": f"${received_total} is too high. I can go to ${counter}.",
                "counter_offer": {"max_total": counter},
            }


class ExperienceNegotiator(NegotiationAgent):
    """Wants to maximize comfort and experience."""

    def __init__(self):
        super().__init__(
            "Experience Agent",
            "maximize_experience",
            {"hotel": "Luxury", "flight": "Premium", "min_total": 1500},
        )

    def make_offer(self, round_number: int) -> dict:
        time.sleep(0.05)
        if round_number == 1:
            offer = self.initial_offer.copy()
        else:
            # Willing to compromise in later rounds
            offer = {
                "hotel": "Mid-range to Comfort",
                "flight": "Comfortable",
                "min_total": 1200 - (round_number * 50),
                "rationale": "I can accept less luxury, but we need quality to make the trip worthwhile.",
            }
        return offer

    def respond_to_offer(self, received_offer: dict, round_number: int) -> dict:
        time.sleep(0.05)
        self.last_received_offer = received_offer

        # Check if offer is acceptable
        min_acceptable = 900
        received_total = (
            received_offer.get("suggested_total")
            or received_offer.get("max_total")
            or received_offer.get("min_total")
            or 0
        )

        if received_total >= min_acceptable:
            return {
                "agent": self.name,
                "status": "ACCEPT",
                "response": f"I need at least ${min_acceptable} for quality. Your offer of ${received_total} works.",
                "agreed_total": received_total,
            }
        else:
            # Counter offer
            counter = int(received_total * 1.3)  # Ask for 30% more
            return {
                "agent": self.name,
                "status": "COUNTER",
                "response": f"${received_total} is too low for good quality. I need ${counter}.",
                "counter_offer": {"min_total": counter},
            }


class PeerNegotiator:
    """Orchestrates negotiation between peers."""

    def negotiate(
        self, agent1: NegotiationAgent, agent2: NegotiationAgent, max_rounds: int = 5
    ) -> dict:
        """Runs negotiation until agreement or timeout."""
        print(f"\n[Negotiation] {agent1.name} vs {agent2.name}")
        print(f"Initial positions:")
        print(f"  {agent1.name}: max ${agent1.initial_offer.get('max_total', 'N/A')}")
        print(f"  {agent2.name}: min ${agent2.initial_offer.get('min_total', 'N/A')}")

        negotiation_log = []

        def _normalize_offer(offer: dict) -> dict:
            if "suggested_total" in offer:
                return offer
            if "max_total" in offer:
                return {"suggested_total": offer["max_total"], **offer}
            if "min_total" in offer:
                return {"suggested_total": offer["min_total"], **offer}
            return offer

        for round_num in range(1, max_rounds + 1):
            print(f"\n[Round {round_num}]")

            # Agent 1 makes offer
            offer1 = agent1.make_offer(round_num)
            print(f"  {agent1.name} offers: max_total ${offer1.get('max_total', 'N/A')}")

            # Agent 2 responds
            response2 = agent2.respond_to_offer(_normalize_offer(offer1), round_num)
            negotiation_log.append({
                "round": round_num,
                "agent1_offer": offer1,
                "agent2_response": response2,
            })

            if response2["status"] == "ACCEPT":
                return {
                    "status": "AGREEMENT",
                    "agreed_total": response2["agreed_total"],
                    "round": round_num,
                    "log": negotiation_log,
                    "summary": f"Reached agreement at ${response2['agreed_total']} on round {round_num}",
                }

            # Agent 1 responds to counter
            if response2["status"] == "COUNTER":
                offer2 = _normalize_offer(response2.get("counter_offer", {}))
                response1 = agent1.respond_to_offer(offer2, round_num)

                if response1["status"] == "ACCEPT":
                    return {
                        "status": "AGREEMENT",
                        "agreed_total": response1["agreed_total"],
                        "round": round_num,
                        "log": negotiation_log,
                        "summary": f"Reached agreement at ${response1['agreed_total']} on round {round_num}",
                    }

        return {
            "status": "TIMEOUT",
            "round": max_rounds,
            "log": negotiation_log,
            "summary": f"Failed to reach agreement after {max_rounds} rounds. Escalating to supervisor.",
        }


def main():
    cost_agent = CostNegotiator()
    experience_agent = ExperienceNegotiator()

    negotiator = PeerNegotiator()
    result = negotiator.negotiate(cost_agent, experience_agent, max_rounds=5)

    print("\n" + "=" * 50)
    print("Negotiation Result:")
    print(json.dumps({
        "status": result["status"],
        "summary": result["summary"],
        "agreed_total": result.get("agreed_total", "N/A"),
        "rounds": result["round"],
    }, indent=2))


if __name__ == "__main__":
    main()
