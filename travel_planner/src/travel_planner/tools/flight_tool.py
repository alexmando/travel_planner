from __future__ import annotations

from datetime import datetime
from typing import Any, Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from .skyscanner_client import SkyscannerClient


class FlightSearchInput(BaseModel):
    origin: str = Field(..., description="Origin city, airport IATA code or Skyscanner entityId")
    destination: str = Field(..., description="Destination city, airport IATA code or Skyscanner entityId")
    departure_date: str = Field(..., description="YYYY-MM-DD")
    return_date: str | None = Field(default=None, description="YYYY-MM-DD for round trip, or empty for one way")
    adults: int = Field(default=1, ge=1, le=9)
    budget: str = Field(default="medium", description="low, medium, high")


class FlightSearchTool(BaseTool):
    name: str = "flight_search_tool"
    description: str = (
        "Search flights with Skyscanner Autosuggest + Flights Live Prices API; "
        "falls back to a simulated result if the API key is missing."
    )
    args_schema: Type[BaseModel] = FlightSearchInput

    def _parse_date(self, value: str) -> dict[str, int]:
        dt = datetime.strptime(value, "%Y-%m-%d")
        return {"year": dt.year, "month": dt.month, "day": dt.day}

    def _entity_from_autosuggest(self, client: SkyscannerClient, term: str) -> dict[str, Any] | None:
        # If the user already passed an entityId / IATA-like code, keep it.
        if term and (term.isdigit() or len(term) in (3, 4)):
            return {"entityId": term}

        try:
            result = client.autosuggest_flights(term, limit=1, is_destination=True)
            places = result.get("places", []) if isinstance(result, dict) else []
            return places[0] if places else None
        except Exception:
            return None

    def _mock_result(self, origin: str, destination: str, departure_date: str, return_date: str | None) -> str:
        lines = [
            "Skyscanner API not available or failed; using simulated flight options.",
            f"Route: {origin} -> {destination}",
            f"Departure: {departure_date}",
        ]
        if return_date:
            lines.append(f"Return: {return_date}")
        lines.extend(
            [
                "- Low cost option: €149 | 1 stop | baggage extra",
                "- Standard option: €239 | direct if available",
                "- Flexible option: €349 | refundable fare",
            ]
        )
        return "\n".join(lines)

    def _run(
            self,
            origin: str,
            destination: str,
            departure_date: str,
            return_date: str | None = None,
            adults: int = 1,
            budget: str = "medium",
    ) -> str:
        client = SkyscannerClient()

        if not client.enabled:
            return self._mock_result(origin, destination, departure_date, return_date)

        try:
            origin_place = self._entity_from_autosuggest(client, origin)
            destination_place = self._entity_from_autosuggest(client, destination)

            if not origin_place or not destination_place:
                return (
                    "Could not resolve origin or destination via Autosuggest. "
                    "Provide a city/airport name or a Skyscanner entityId. "
                    f"Origin resolved: {bool(origin_place)} | Destination resolved: {bool(destination_place)}"
                )

            origin_entity = origin_place.get("entityId") or origin_place.get("iataCode") or origin
            destination_entity = destination_place.get("entityId") or destination_place.get("iataCode") or destination

            query_leg: dict[str, Any] = {
                "origin_place_id": origin_entity,
                "destination_place_id": destination_entity,
                "date": self._parse_date(departure_date),
            }

            if return_date:
                query_leg["returnDate"] = self._parse_date(return_date)

            create_payload = [{"queryLegs": [query_leg], "adults": adults}]
            # If the live endpoint expects a slightly different shape in your contract,
            # this is the only place you should adapt.
            create_response = client.flights_live_create(query_leg.get("queryLegs", [query_leg]), adults=adults)
            final_response = client.wait_and_poll(
                create_response,
                lambda token: client.flights_live_poll(token, limit=10, offset=0),
            )

            return (
                "Skyscanner flight search completed.\n"
                f"Resolved origin: {origin_place.get('name', origin)} | entityId={origin_place.get('entityId')}\n"
                f"Resolved destination: {destination_place.get('name', destination)} | entityId={destination_place.get('entityId')}\n\n"
                f"Raw response:\n{final_response}"
            )
        except Exception as exc:
            return self._mock_result(origin, destination, departure_date, return_date) + f"\n\nAPI error: {exc}"