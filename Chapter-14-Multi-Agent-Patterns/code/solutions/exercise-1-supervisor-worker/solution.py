"""
Exercise 2: Supervisor-Worker Pattern

Implement a supervisor that routes travel booking tasks to specialist workers
and aggregates their results.

Workers:
- FlightWorker: find flights based on destination and dates
- HotelWorker: find hotels based on destination and dates
- PolicyWorker: check if total cost meets policy constraints
"""

import json
import time
from dataclasses import dataclass


@dataclass
class TravelRequest:
    destination: str
    depart: str
    return_date: str
    budget: float
    policy_threshold: float


@dataclass
class FlightOption:
    airline: str
    departure: str
    arrival: str
    price: float
    connections: int


@dataclass
class HotelOption:
    name: str
    location: str
    price_per_night: float
    nights: int
    rating: float


class FlightWorker:
    """Specialist worker that finds flights."""

    def find_flights(self, destination: str, depart: str, budget: float) -> list[FlightOption]:
        """Simulates flight search."""
        print(f"[Flight Worker] Searching flights to {destination} on {depart}...")
        time.sleep(0.1)  # Simulate API call

        options = [
            FlightOption("SAS", depart, destination, 450, 0),
            FlightOption("Lufthansa", depart, destination, 520, 1),
            FlightOption("Budget Air", depart, destination, 280, 2),
        ]

        # Filter by budget
        return [o for o in options if o.price <= budget]


class HotelWorker:
    """Specialist worker that finds hotels."""

    def find_hotels(self, destination: str, nights: int, budget: float) -> list[HotelOption]:
        """Simulates hotel search."""
        print(f"[Hotel Worker] Searching hotels in {destination} for {nights} nights...")
        time.sleep(0.1)  # Simulate API call

        options = [
            HotelOption("Downtown Luxury", "City Center", 200, nights, 4.8),
            HotelOption("Mid-Range Hotel", "Near Airport", 120, nights, 4.2),
            HotelOption("Budget Hostel", "Suburbs", 60, nights, 3.8),
        ]

        total_per_option = [(o, o.price_per_night * nights) for o in options]
        return [o for o, total in total_per_option if total <= budget]


class PolicyWorker:
    """Specialist worker that checks policy constraints."""

    def check_policy(self, total_cost: float, policy_threshold: float) -> dict:
        """Checks if cost violates policy."""
        print(f"[Policy Worker] Checking policy (threshold: ${policy_threshold})...")
        time.sleep(0.05)  # Simulate policy check

        return {
            "compliant": total_cost <= policy_threshold,
            "total_cost": total_cost,
            "threshold": policy_threshold,
            "requires_approval": total_cost > policy_threshold,
        }


class TravelSupervisor:
    """Supervisor that routes work to specialists and aggregates results."""

    def __init__(self):
        self.flight_worker = FlightWorker()
        self.hotel_worker = HotelWorker()
        self.policy_worker = PolicyWorker()

    def book_trip(self, request: TravelRequest) -> dict:
        """Routes tasks to workers and aggregates results."""
        print(f"\n[Supervisor] Received request: {request.destination}")
        print(f"[Supervisor] Routing tasks to workers...\n")

        # Route tasks in parallel (simulated)
        flights = self.flight_worker.find_flights(
            request.destination, request.depart, request.budget
        )
        hotels = self.hotel_worker.find_hotels(
            request.destination, 3, request.budget  # Assume 3 nights
        )

        # Aggregate results
        print(f"\n[Supervisor] Aggregating results...")
        best_option = self._select_best_option(flights, hotels)

        # Check policy
        total_cost = best_option["flight_price"] + best_option["hotel_total"]
        policy_check = self.policy_worker.check_policy(total_cost, request.policy_threshold)

        print(f"\n[Supervisor] Final recommendation:")
        print(f"  Flight: {best_option['flight_airline']} (${best_option['flight_price']})")
        print(f"  Hotel: {best_option['hotel_name']} (${best_option['hotel_total']})")
        print(f"  Total: ${total_cost}")
        print(
            f"  Policy Status: {'Approved' if policy_check['compliant'] else 'Requires Review'}"
        )

        return {
            "recommendation": best_option,
            "total_cost": total_cost,
            "policy_check": policy_check,
        }

    def _select_best_option(self, flights: list[FlightOption], hotels: list[HotelOption]) -> dict:
        """Selects the best flight-hotel combination."""
        if not flights or not hotels:
            return {"error": "No flights or hotels found within budget"}

        best_flight = min(flights, key=lambda f: f.price)
        best_hotel = min(hotels, key=lambda h: h.price_per_night)

        return {
            "flight_airline": best_flight.airline,
            "flight_price": best_flight.price,
            "flight_connections": best_flight.connections,
            "hotel_name": best_hotel.name,
            "hotel_location": best_hotel.location,
            "hotel_total": best_hotel.price_per_night * best_hotel.nights,
            "hotel_rating": best_hotel.rating,
        }


def main():
    request = TravelRequest(
        destination="Copenhagen",
        depart="2026-08-12",
        return_date="2026-08-15",
        budget=2200,
        policy_threshold=1800,
    )

    supervisor = TravelSupervisor()
    result = supervisor.book_trip(request)

    print("\n" + "=" * 50)
    print("Final Result:")
    print(json.dumps(
        {
            "recommendation": result["recommendation"],
            "total_cost": result["total_cost"],
            "policy_compliant": result["policy_check"]["compliant"],
        },
        indent=2,
    ))


if __name__ == "__main__":
    main()
