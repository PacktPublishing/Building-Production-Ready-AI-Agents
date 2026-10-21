"""
Tool-calling Supervisor-Worker example.

This version uses Ollama-backed tool methods that call a chat model.
The supervisor orchestrates workers, aggregates results, and runs a policy check.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass

from ollama import Client


@dataclass
class TravelRequest:
    destination: str
    depart_date: str
    return_date: str
    budget: float
    policy_threshold: float
    preferred_departure: str = "morning"
    nights: int = 3


@dataclass
class FlightOption:
    airline: str
    depart_time: str
    arrive_time: str
    price: float
    stops: int


@dataclass
class HotelOption:
    name: str
    location: str
    nightly_price: float
    rating: float


@dataclass
class PolicyResult:
    compliant: bool
    total_cost: float
    threshold: float
    requires_approval: bool


class OllamaClient:
    """Ollama SDK wrapper with model-driven tool-calling and JSON fallback."""

    def __init__(self, model: str | None = None, host: str | None = None):
        self.model = model or os.getenv("OLLAMA_MODEL", "llama3.1:latest")
        self.host = host or os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.client = Client(host=self.host)

    def chat_with_tools_or_json(
        self,
        system_prompt: str,
        user_prompt: str,
        tools: list[dict],
        handlers: dict,
    ) -> tuple[bool, str | None, object]:
        """
        Returns: (tool_used, tool_name, result)

        - If the model emits `tool_calls`, dispatches the first call and returns handler output.
        - If no tool call is emitted, falls back to parsing JSON from model content.
        """
        try:
            response = self.client.chat(
                model=self.model,
                stream=False,
                options={"temperature": 0},
                tools=tools,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
        except Exception as exc:
            raise RuntimeError(
                "Failed to call Ollama SDK. Ensure `ollama serve` is running, model "
                f"`{self.model}` is pulled, and Python package `ollama` is installed."
            ) from exc

        message = response.get("message", {})
        tool_calls = message.get("tool_calls") or []

        if tool_calls:
            first_call = tool_calls[0]
            function_meta = first_call.get("function", {})
            function_name = function_meta.get("name")
            raw_args = function_meta.get("arguments", {})

            if isinstance(raw_args, str):
                try:
                    args = json.loads(raw_args)
                except json.JSONDecodeError:
                    args = {}
            elif isinstance(raw_args, dict):
                args = raw_args
            else:
                args = {}

            if function_name in handlers:
                result = handlers[function_name](**args)
                return True, function_name, result

        content = message.get("content", "")
        parsed = self._parse_json_content(content)
        return False, None, parsed

    @staticmethod
    def _parse_json_content(content: str) -> dict | list:
        text = content.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        if text.startswith("```"):
            lines = [line for line in text.splitlines() if not line.strip().startswith("```")]
            text = "\n".join(lines).strip()
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass

        object_start = text.find("{")
        object_end = text.rfind("}")
        if object_start != -1 and object_end > object_start:
            return json.loads(text[object_start: object_end + 1])

        array_start = text.find("[")
        array_end = text.rfind("]")
        if array_start != -1 and array_end > array_start:
            return json.loads(text[array_start: array_end + 1])

        raise ValueError(f"Unable to parse JSON from Ollama response: {content[:200]}")


class FlightApiClient:
    """Deterministic backend flight API used by tool-calling dispatch."""

    def search_flights(
        self,
        destination: str,
        depart_date: str,
        return_date: str,
        preferred_departure: str,
    ) -> list[dict]:
        options = [
            {"airline": "SAS", "depart_time": "07:00", "arrive_time": "09:05", "price": 450, "stops": 0},
            {"airline": "Norwegian", "depart_time": "08:15", "arrive_time": "10:25", "price": 390, "stops": 0},
            {"airline": "Lufthansa", "depart_time": "06:40", "arrive_time": "10:20", "price": 420, "stops": 1},
            {"airline": "BudgetFly", "depart_time": "13:10", "arrive_time": "16:30", "price": 260, "stops": 2},
        ]
        if preferred_departure == "morning":
            return [o for o in options if int(o["depart_time"].split(":")[0]) < 12]
        return options


class HotelApiClient:
    """Deterministic backend hotel API used by tool-calling dispatch."""

    def search_hotels(
        self,
        destination: str,
        check_in: str,
        check_out: str,
        max_nightly_price: float,
    ) -> list[dict]:
        options = [
            {"name": "Wakeup Copenhagen - Borgergade", "location": "Borgergade, Indre By", "nightly_price": 200, "rating": 4.1},
            {"name": "Scandic Spectrum", "location": "Kalvebod Brygge", "nightly_price": 260, "rating": 4.5},
            {"name": "CABINN City", "location": "Tietgensgade", "nightly_price": 140, "rating": 3.9},
            {"name": "CityHub Copenhagen", "location": "Vesterbro", "nightly_price": 180, "rating": 4.2},
        ]
        return [o for o in options if float(o["nightly_price"]) <= max_nightly_price]


class PolicyApiClient:
    """Deterministic policy service used by tool-calling dispatch."""

    def evaluate_total(self, total_cost: float, threshold: float) -> PolicyResult:
        compliant = total_cost <= threshold
        return PolicyResult(
            compliant=compliant,
            total_cost=float(total_cost),
            threshold=float(threshold),
            requires_approval=not compliant,
        )


class TravelTools:
    """Tool catalog. These are the methods workers can call."""

    def __init__(self):
        self.llm = OllamaClient()
        self.flight_api = FlightApiClient()
        self.hotel_api = HotelApiClient()
        self.policy_api = PolicyApiClient()

    def search_flights_api(
        self,
        destination: str,
        depart_date: str,
        return_date: str,
        preferred_departure: str,
    ) -> list[dict]:
        return self.flight_api.search_flights(
            destination=destination,
            depart_date=depart_date,
            return_date=return_date,
            preferred_departure=preferred_departure,
        )

    def search_hotels_api(
        self,
        destination: str,
        check_in: str,
        check_out: str,
        max_nightly_price: float,
    ) -> list[dict]:
        return self.hotel_api.search_hotels(
            destination=destination,
            check_in=check_in,
            check_out=check_out,
            max_nightly_price=max_nightly_price,
        )

    def check_policy_api(self, total_cost: float, threshold: float) -> dict:
        policy = self.policy_api.evaluate_total(total_cost, threshold)
        return asdict(policy)

    def find_flights(self, request: TravelRequest) -> list[FlightOption]:
        return [
            FlightOption(
                airline=str(item["airline"]),
                depart_time=str(item["depart_time"]),
                arrive_time=str(item["arrive_time"]),
                price=float(item["price"]),
                stops=int(item["stops"]),
            )
            for item in self.search_flights_api(
                destination=request.destination,
                depart_date=request.depart_date,
                return_date=request.return_date,
                preferred_departure=request.preferred_departure,
            )
        ]

    def find_hotels(self, request: TravelRequest) -> list[HotelOption]:
        max_nightly = (request.budget * 0.40) / max(1, request.nights)
        return [
            HotelOption(
                name=str(item["name"]),
                location=str(item["location"]),
                nightly_price=float(item["nightly_price"]),
                rating=float(item["rating"]),
            )
            for item in self.search_hotels_api(
                destination=request.destination,
                check_in=request.depart_date,
                check_out=request.return_date,
                max_nightly_price=max_nightly,
            )
        ]

    def check_policy(self, total_cost: float, threshold: float) -> PolicyResult:
        return self.policy_api.evaluate_total(total_cost, threshold)


class FlightWorker:
    def __init__(self, tools: TravelTools):
        self.tools = tools

    def run(self, request: TravelRequest) -> list[FlightOption]:
        print("[FlightWorker] Calling tool: find_flights")
        tool_spec = [
            {
                "type": "function",
                "function": {
                    "name": "search_flights_api",
                    "description": "Search flight options for a trip request.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "destination": {"type": "string"},
                            "depart_date": {"type": "string"},
                            "return_date": {"type": "string"},
                            "preferred_departure": {"type": "string"},
                        },
                        "required": ["destination", "depart_date", "return_date", "preferred_departure"],
                    },
                },
            }
        ]
        system_prompt = (
            "You are a flight-search worker. Prefer tool calls. "
            "If you cannot call a tool, return ONLY JSON with schema: "
            "{'options':[{'airline':str,'depart_time':str,'arrive_time':str,'price':number,'stops':int}]}"
        )
        user_prompt = (
            f"Find flights to {request.destination} departing {request.depart_date} and returning "
            f"{request.return_date}. Preferred departure: {request.preferred_departure}."
        )

        used_tool, tool_name, result = self.tools.llm.chat_with_tools_or_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            tools=tool_spec,
            handlers={"search_flights_api": self.tools.search_flights_api},
        )

        raw_options = result if used_tool else result.get("options", [])
        if used_tool:
            print(f"[FlightWorker] Model emitted tool call: {tool_name}")
        else:
            print("[FlightWorker] No tool call emitted; using JSON fallback parsing")

        parsed: list[FlightOption] = []
        for item in raw_options:
            try:
                parsed.append(
                    FlightOption(
                        airline=str(item["airline"]),
                        depart_time=str(item["depart_time"]),
                        arrive_time=str(item["arrive_time"]),
                        price=float(item["price"]),
                        stops=int(item["stops"]),
                    )
                )
            except (KeyError, TypeError, ValueError):
                continue

        if not parsed:
            raise ValueError("FlightWorker received no valid options")
        return parsed


class HotelWorker:
    def __init__(self, tools: TravelTools):
        self.tools = tools

    def run(self, request: TravelRequest) -> list[HotelOption]:
        print("[HotelWorker] Calling tool: find_hotels")
        max_nightly = (request.budget * 0.40) / max(1, request.nights)
        tool_spec = [
            {
                "type": "function",
                "function": {
                    "name": "search_hotels_api",
                    "description": "Search hotels for a trip request.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "destination": {"type": "string"},
                            "check_in": {"type": "string"},
                            "check_out": {"type": "string"},
                            "max_nightly_price": {"type": "number"},
                        },
                        "required": ["destination", "check_in", "check_out", "max_nightly_price"],
                    },
                },
            }
        ]
        system_prompt = (
            "You are a hotel-search worker. Prefer tool calls. "
            "If you cannot call a tool, return ONLY JSON with schema: "
            "{'options':[{'name':str,'location':str,'nightly_price':number,'rating':number}]}"
        )
        user_prompt = (
            f"Find hotels in {request.destination} from {request.depart_date} to {request.return_date}. "
            f"Max nightly price: {max_nightly}."
        )

        used_tool, tool_name, result = self.tools.llm.chat_with_tools_or_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            tools=tool_spec,
            handlers={"search_hotels_api": self.tools.search_hotels_api},
        )

        raw_options = result if used_tool else result.get("options", [])
        if used_tool:
            print(f"[HotelWorker] Model emitted tool call: {tool_name}")
        else:
            print("[HotelWorker] No tool call emitted; using JSON fallback parsing")

        parsed: list[HotelOption] = []
        for item in raw_options:
            try:
                parsed.append(
                    HotelOption(
                        name=str(item["name"]),
                        location=str(item["location"]),
                        nightly_price=float(item["nightly_price"]),
                        rating=float(item["rating"]),
                    )
                )
            except (KeyError, TypeError, ValueError):
                continue

        if not parsed:
            raise ValueError("HotelWorker received no valid options")
        return parsed


class PolicyWorker:
    def __init__(self, tools: TravelTools):
        self.tools = tools

    def run(self, total_cost: float, threshold: float) -> PolicyResult:
        print("[PolicyWorker] Calling tool: check_policy")
        tool_spec = [
            {
                "type": "function",
                "function": {
                    "name": "check_policy_api",
                    "description": "Check policy compliance based on total cost and threshold.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "total_cost": {"type": "number"},
                            "threshold": {"type": "number"},
                        },
                        "required": ["total_cost", "threshold"],
                    },
                },
            }
        ]
        system_prompt = (
            "You are a policy worker. Prefer tool calls. "
            "If you cannot call a tool, return ONLY JSON with schema: "
            "{'compliant':bool,'total_cost':number,'threshold':number,'requires_approval':bool}"
        )
        user_prompt = f"Check policy for total_cost={total_cost} and threshold={threshold}."

        used_tool, tool_name, result = self.tools.llm.chat_with_tools_or_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            tools=tool_spec,
            handlers={"check_policy_api": self.tools.check_policy_api},
        )

        policy_obj = result if used_tool else result
        if used_tool:
            print(f"[PolicyWorker] Model emitted tool call: {tool_name}")
        else:
            print("[PolicyWorker] No tool call emitted; using JSON fallback parsing")

        return PolicyResult(
            compliant=bool(policy_obj.get("compliant", total_cost <= threshold)),
            total_cost=float(policy_obj.get("total_cost", total_cost)),
            threshold=float(policy_obj.get("threshold", threshold)),
            requires_approval=bool(policy_obj.get("requires_approval", total_cost > threshold)),
        )


class TravelSupervisor:
    def __init__(self):
        self.tools = TravelTools()
        self.flight_worker = FlightWorker(self.tools)
        self.hotel_worker = HotelWorker(self.tools)
        self.policy_worker = PolicyWorker(self.tools)

    def book_trip(self, request: TravelRequest) -> dict:
        trace: list[dict] = []
        trace.append({"event": "request_received", "destination": request.destination})

        flights = self.flight_worker.run(request)
        trace.append({"event": "flights_found", "count": len(flights)})

        hotels = self.hotel_worker.run(request)
        trace.append({"event": "hotels_found", "count": len(hotels)})

        recommendation = self._pick_best_combination(flights, hotels, request.nights)
        total_cost = recommendation["flight_price"] + recommendation["hotel_total"]
        trace.append({"event": "aggregation_complete", "total_cost": total_cost})

        policy = self.policy_worker.run(total_cost, request.policy_threshold)
        trace.append(
            {
                "event": "policy_checked",
                "compliant": policy.compliant,
                "requires_approval": policy.requires_approval,
            }
        )

        return {
            "request": asdict(request),
            "recommendation": recommendation,
            "policy": asdict(policy),
            "trace": trace,
        }

    @staticmethod
    def _pick_best_combination(
        flights: list[FlightOption], hotels: list[HotelOption], nights: int
    ) -> dict:
        if not flights:
            raise ValueError("No flight options returned by flight tool")
        if not hotels:
            raise ValueError("No hotel options returned by hotel tool")

        best_flight = min(flights, key=lambda x: x.price)
        best_hotel = min(hotels, key=lambda x: x.nightly_price)

        return {
            "flight_airline": best_flight.airline,
            "flight_depart_time": best_flight.depart_time,
            "flight_stops": best_flight.stops,
            "flight_price": best_flight.price,
            "hotel_name": best_hotel.name,
            "hotel_location": best_hotel.location,
            "hotel_rating": best_hotel.rating,
            "hotel_total": best_hotel.nightly_price * nights,
        }


def main() -> None:
    request = TravelRequest(
        destination="Copenhagen",
        depart_date="2026-08-12",
        return_date="2026-08-15",
        budget=2200,
        policy_threshold=1800,
        preferred_departure="morning",
        nights=3,
    )
    supervisor = TravelSupervisor()
    result = supervisor.book_trip(request)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
