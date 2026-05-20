from __future__ import annotations

import json
from typing import Any, Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from .skyscanner_client import SkyscannerClient


class HotelSearchInput(BaseModel):
    destination: str = Field(..., description="City name or hotel search query")
    checkin_date: str = Field(..., description="YYYY-MM-DD")
    checkout_date: str = Field(..., description="YYYY-MM-DD")
    adults: int = Field(default=2, ge=1, le=9)
    rooms: int = Field(default=1, ge=1, le=9)
    budget: str = Field(default="medium", description="low, medium, high")


class HotelSearchTool(BaseTool):
    name: str = "hotel_search_tool"
    description: str = (
        "Use RapidAPI sky-scrapper hotel destination lookup and return a readable summary. "
        "Falls back to simulated hotel options if the API key is missing."
    )
    args_schema: Type[BaseModel] = HotelSearchInput

    def _pretty(self, payload: Any) -> str:
        try:
            text = json.dumps(payload, indent=2, ensure_ascii=False)
        except Exception:
            text = str(payload)
        return text[:6000] if len(text) > 6000 else text

    def _mock_result(self, destination: str, departure_date: str, return_date: str, budget: str) -> str:
        return "\n".join(
            [
                "RapidAPI hotel endpoint not available or failed; using simulated hotel options.",
                f"Destination: {destination}",
                f"Check-in: {departure_date}",
                f"Check-out: {return_date}",
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
            return self._mock_result(destination, departure_date, return_date, budget)

        try:
            lookup = client.search_hotel_destination(destination)

            return (
                "RapidAPI hotel destination lookup reached successfully.\n"
                f"Requested destination: {destination}\n"
                f"Check-in date: {departure_date}\n"
                f"Check-out date: {return_date}\n"
                f"Adults: {adults}\n"
                f"Rooms: {rooms}\n"
                f"Budget: {budget}\n\n"
                "Live API response:\n"
                f"{self._pretty(lookup)}"
            )
        except Exception as exc:
            return self._mock_result(destination, departure_date, return_date, budget) + f"\n\nAPI error: {exc}"