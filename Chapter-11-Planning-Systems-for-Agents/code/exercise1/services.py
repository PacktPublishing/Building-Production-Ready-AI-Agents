from typing import Dict


class PrimaryTravelService:
    """Mock primary provider: always fails to mimic outage."""

    def book_flight(self, destination: str) -> Dict[str, str]:
        return {
            "success": "false",
            "message": "Failed to connect to flight booking service.",
            "destination": destination,
        }


class AlternativeTravelService:
    """Mock fallback provider: succeeds."""

    def book_flight(self, destination: str) -> Dict[str, str]:
        return {
            "success": "true",
            "message": "Booked successfully with alternative carrier.",
            "destination": destination,
            "provider": "SkyBridge Air",
            "routing": "One stop via Amsterdam",
            "stopovers": "1",
        }


class HotelService:
    def get_hotel_options(self, destination: str) -> list[Dict[str, str]]:
        return [
            {
                "name": f"{destination} City Central Hotel",
                "area": "City Center",
                "price_per_night": "$180",
            },
            {
                "name": f"{destination} Riverside Suites",
                "area": "Riverside",
                "price_per_night": "$220",
            },
            {
                "name": f"{destination} Budget Inn",
                "area": "Old Town",
                "price_per_night": "$120",
            },
        ]

    def reserve_hotel(self, destination: str, selected_hotel: Dict[str, str]) -> Dict[str, str]:
        return {
            "success": "true",
            "message": f"Reserved hotel in central {destination}.",
            "hotel_name": selected_hotel["name"],
            "hotel_area": selected_hotel["area"],
            "hotel_price_per_night": selected_hotel["price_per_night"],
        }


class ItineraryService:
    def build_itinerary(self, destination: str, start_date: str, trip_type: str) -> Dict[str, str]:
        duration_days = 7 if trip_type == "1 week" else 3
        return {
            "success": "true",
            "message": "Daily itinerary prepared.",
            "summary": (
                f"{duration_days}-day plan for {destination} starting {start_date}: "
                "arrival/orientation, city highlights, local food and culture."
            ),
        }
