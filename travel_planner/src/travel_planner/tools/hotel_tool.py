from __future__ import annotations

from datetime import datetime
from typing import Any, Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from .skyscanner_client import SkyscannerClient


class HotelSearchInput(BaseModel):
    destination: str = Field(..., description="City name or Skyscanner entityId")
    checkin_date: str = Field(..., description="YYYY-MM-DD")
    checkout_date: str = Field(..., description="YYYY-MM-DD")
    adults: int = Field(default=2, ge=1, le=9)
    rooms: int = Field(default=1, ge=1, le=9)
    budget: str = Field(default="medium", description="low, medium, high")


class HotelSearchTool(BaseTool):
    name: str = "hotel_search_tool"
    description: str = (
        "Search hotels with Skyscanner Autosuggest + Hotels Live Prices API; "
        "falls back to simulated results if the API key is missing."
    )
    args_schema: Type[BaseModel] = HotelSearchInput

    def _parse_date(self, value: str) -> dict[str, int]:
        dt = datetime.strptime(value, "%Y-%m-%d")
        return {"year": dt.year, "month": dt.month, "day": dt.day}

    def _entity_from_autosuggest(self, client: SkyscannerClient, term: str) -> dict[str, Any] | None:
        if term and term.isdigit():
            return {"entityId": term}

        try:
            result = client.autosuggest_hotels(term, limit=1)
            places = result.get("places", []) if isinstance(result, dict) else []
            return places[0] if places else None
        except Exception:
            return None

    def _mock_result(self, destination: str, budget: str) -> str:
        return "\n".join(
            [
                "Skyscanner API not available or failed; using simulated hotel options.",
                f"Destination: {destination}",
                f"Budget: {budget}",
                "- Budget stay: €70/night | central location",
                "- Mid-range hotel: €140/night | breakfast included",
                "- Comfort hotel: €220/night | near main attractions",
            ]
        )

    def _run(
            self,
            destination: str,
            checkin_date: str,
            checkout_date: str,
            adults: int = 2,
            rooms: int = 1,
            budget: str = "medium",
    ) -> str:
        client = SkyscannerClient()

        if not client.enabled:
            return self._mock_result(destination, budget)

        try:
            place = self._entity_from_autosuggest(client, destination)
            if not place:
                return f"Could not resolve destination via Autosuggest. Destination provided: {destination}"

            entity_id = place.get("entityId") or destination

            query = {
                "market": client.market,
                "locale": client.locale,
                "currency": client.currency,
                "entityId": entity_id,
                "checkinDate": self._parse_date(checkin_date),
                "checkoutDate": self._parse_date(checkout_date),
                "adults": adults,
                "childrenAges": [],
                "rooms": rooms,
            }

            create_response = client.hotels_live_create(query=query, initial_page_size=10)
            final_response = client.wait_and_poll(
                create_response,
                lambda token: client.hotels_live_poll(token, limit=10, offset=0),
            )

            return (
                "Skyscanner hotel search completed.\n"
                f"Resolved destination: {place.get('name', destination)} | entityId={place.get('entityId')}\n\n"
                f"Raw response:\n{final_response}"
            )
        except Exception as exc:
            return self._mock_result(destination, budget) + f"\n\nAPI error: {exc}"