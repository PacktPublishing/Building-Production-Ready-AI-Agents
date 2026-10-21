"""
Exercise 5: Committee Pattern

Implement a committee where multiple agents discuss a trip decision,
voice concerns, and vote on the final choice.

Committee members:
- Planner: focuses on logistics and itinerary
- PolicyAgent: checks budget and policy compliance
- ExperienceAgent: advocates for quality and comfort
- CostAgent: advocates for fiscal responsibility
"""

import json
import time
from enum import Enum


class VoteChoice(Enum):
    """Vote options."""
    BUDGET_OPTION = "budget"
    BALANCED_OPTION = "balanced"
    PREMIUM_OPTION = "premium"


class CommitteeMember:
    """Base class for committee members."""

    def __init__(self, name: str, weight: float = 1.0):
        self.name = name
        self.weight = weight

    def assess(self, options: list[dict]) -> dict:
        """Assess options and return a vote + reasoning."""
        raise NotImplementedError


class PlannerAgent(CommitteeMember):
    """Focuses on logistics and itinerary."""

    def __init__(self):
        super().__init__("Travel Planner", weight=1.2)

    def assess(self, options: list[dict]) -> dict:
        time.sleep(0.05)
        return {
            "member": self.name,
            "vote": VoteChoice.BALANCED_OPTION.value,
            "confidence": 0.8,
            "rationale": "The balanced option provides good logistics without excess cost. "
            "It allows us to focus on the itinerary rather than managing constraints.",
            "concerns": ["Premium is over-engineered", "Budget risks quality issues"],
        }


class PolicyAgent(CommitteeMember):
    """Checks budget and policy compliance."""

    def __init__(self):
        super().__init__("Policy Agent", weight=1.5)  # Higher weight

    def assess(self, options: list[dict]) -> dict:
        time.sleep(0.05)
        return {
            "member": self.name,
            "vote": VoteChoice.BUDGET_OPTION.value,
            "confidence": 0.9,
            "rationale": "Budget option complies with all policies and spending limits. "
            "Premium option exceeds our policy threshold and requires exception approvals.",
            "concerns": [
                "Premium option needs executive review",
                "Budget risk for later requests",
            ],
        }


class ExperienceAgent(CommitteeMember):
    """Advocates for quality and comfort."""

    def __init__(self):
        super().__init__("Experience Agent", weight=1.0)

    def assess(self, options: list[dict]) -> dict:
        time.sleep(0.05)
        return {
            "member": self.name,
            "vote": VoteChoice.PREMIUM_OPTION.value,
            "confidence": 0.7,
            "rationale": "Premium option delivers the best traveler experience. "
            "A well-rested, comfortable traveler is more productive and satisfied.",
            "concerns": ["Higher cost", "Policy concerns"],
        }


class CostAgent(CommitteeMember):
    """Advocates for fiscal responsibility."""

    def __init__(self):
        super().__init__("Cost Agent", weight=1.0)

    def assess(self, options: list[dict]) -> dict:
        time.sleep(0.05)
        return {
            "member": self.name,
            "vote": VoteChoice.BUDGET_OPTION.value,
            "confidence": 0.85,
            "rationale": "Budget option is fiscally responsible. "
            "We can deliver the trip for less while maintaining acceptable quality.",
            "concerns": ["Balanced option sneaks in unnecessary costs", "Premium is wasteful"],
        }


class CommitteeVoting:
    """Manages committee discussion and voting."""

    def run_discussion(self, members: list[CommitteeMember], options: list[dict]) -> dict:
        """Runs a committee discussion and returns the vote."""
        print("\n[Committee] Starting discussion...\n")

        assessments = []
        for member in members:
            assessment = member.assess(options)
            assessments.append(assessment)
            print(f"[{member.name}] {assessment['rationale'][:80]}...")

        # Count votes
        votes = {}
        for assessment in assessments:
            vote = assessment["vote"]
            member_weight = next(
                m.weight for m in members if m.name == assessment["member"]
            )
            votes[vote] = votes.get(vote, 0) + member_weight

        # Determine winner
        winner = max(votes, key=votes.get)

        print(f"\n[Committee] Vote tally:")
        for vote_choice, count in votes.items():
            print(f"  {vote_choice}: {count:.1f} points")

        return {
            "decision": winner,
            "vote_breakdown": votes,
            "assessments": assessments,
            "reasoning": f"Committee selected {winner} option based on weighted voting.",
        }


def main():
    # Sample options
    options = [
        {"name": "Budget Option", "cost": 700, "quality": 6},
        {"name": "Balanced Option", "cost": 1200, "quality": 8},
        {"name": "Premium Option", "cost": 1800, "quality": 9.5},
    ]

    print("[Committee] Trip Decision Discussion")
    print(f"Options under consideration: {len(options)}")

    # Setup committee
    committee = [
        PlannerAgent(),
        PolicyAgent(),
        ExperienceAgent(),
        CostAgent(),
    ]

    # Run voting
    voting = CommitteeVoting()
    result = voting.run_discussion(committee, options)

    print("\n" + "=" * 50)
    print("Committee Decision:")
    print(json.dumps({
        "final_decision": result["decision"],
        "vote_breakdown": {k: f"{v:.1f}" for k, v in result["vote_breakdown"].items()},
        "dissenting_votes": [
            a for a in result["assessments"]
            if a["vote"] != result["decision"]
        ],
    }, indent=2))


if __name__ == "__main__":
    main()
