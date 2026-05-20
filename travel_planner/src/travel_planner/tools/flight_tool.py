from __future__ import annotations

import json
from typing import Any, Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from .skyscanner_client import SkyscannerClient


class FlightSearchInput(BaseModel):
    origin: str = Field(..., description="Origin city or airport code")
    destination: str = Field(..., description="Destination city or airport code")
    departure_date: str = Field(..., description="YYYY-MM-DD")
    return_date: str | None = Field(default=None, description="YYYY-MM-DD for round trip, or empty for one way")
    adults: int = Field(default=1, ge=1, le=9)
    budget: str = Field(default="medium", description="low, medium, high")


class FlightSearchTool(BaseTool):
    name: str = "flight_search_tool"
    description: str = (
        "Use RapidAPI sky-scrapper flight discovery endpoint and return a readable summary. "
        "Falls back to simulated options if the API key is missing."
    )
    args_schema: Type[BaseModel] = FlightSearchInput

    def _pretty(self, payload: Any) -> str:
        try:
            text = json.dumps(payload, indent=2, ensure_ascii=False)
        except Exception:
            text = str(payload)
        return text[:6000] if len(text) > 6000 else text

    def _mock_result(self, origin: str, destination: str, departure_date: str, return_date: str | None, budget: str) -> str:
        lines = [
            "RapidAPI flight endpoint not available or failed; using simulated flight options.",
            f"Route: {origin} -> {destination}",
            f"Departure: {departure_date}",
        ]
        if return_date:
            lines.append(f"Return: {return_date}")
        lines.append(f"Budget: {budget}")
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
            return self._mock_result(origin, destination, departure_date, return_date, budget)

        try:
            api_result = client.search_flight_everywhere_details(
                currency="EUR",
                one_way=return_date is None,
            )

            return (
                "RapidAPI flight endpoint reached successfully.\n"
                f"Requested route: {origin} -> {destination}\n"
                f"Departure date: {departure_date}\n"
                f"Return date: {return_date or 'one way'}\n"
                f"Adults: {adults}\n"
                f"Budget: {budget}\n\n"
                "Live API response:\n"
                f"{self._pretty(api_result)}"
            )
        except Exception as exc:
            return self._mock_result(origin, destination, departure_date, return_date, budget) + f"\n\nAPI error: {exc}"