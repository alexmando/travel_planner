from __future__ import annotations
from typing import Type
from crewai.tools import BaseTool
from pydantic import BaseModel, Field, ConfigDict
from travel_planner.tools.activity_client import BookingAttractionClient


class AttractionSearchInput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    dest_id: str = Field(..., description="Booking.com destination ID, e.g. '20088325'.")
    start_date: str = Field(..., description="Visit start date YYYY-MM-DD.")
    end_date: str = Field(..., description="Visit end date YYYY-MM-DD.")
    currency: str = Field(default="EUR", description="Currency code. Default: EUR.")


class AttractionSearchTool(BaseTool):
    name: str = "attraction_search"
    description: str = (
        "Search local attractions and experiences via Booking.com. "
        "Requires dest_id, start_date, end_date. "
        "Returns top 5 activities with name, price, and rating."
    )
    args_schema: Type[BaseModel] = AttractionSearchInput

    def _run(self, dest_id: str, start_date: str, end_date: str, currency: str = "EUR") -> str:
        try:
            client = BookingAttractionClient()
            raw = client.search_attractions(
                dest_id=dest_id,
                start_date=start_date,
                end_date=end_date,
                currency=currency,
            )
            if "error" in raw:
                return self._mock_fallback(dest_id, raw["error"])
            return self._format_output(raw, dest_id, currency)
        except Exception as e:
            return self._mock_fallback(dest_id, str(e))

    def _format_output(self, data: dict, dest_id: str, currency: str) -> str:
        items = data.get("data") or data.get("products") or data.get("attractions") or []

        if not items or not isinstance(items, list):
            return self._mock_fallback(dest_id, "No structured data in API response.")

        lines = [f"🎯 Attractions (dest: {dest_id}) | {len(items)} found\n"]

        for i, item in enumerate(items[:5], 1):
            name = item.get("name") or item.get("title", "N/A")

            price_data = item.get("price") or item.get("representativePrice", {})
            price = (
                price_data.get("publicAmount") or price_data.get("amount", "N/A")
                if isinstance(price_data, dict) else str(price_data)
            )

            rating  = item.get("rating") or item.get("reviewScore", "?")
            reviews = item.get("reviewsCount") or item.get("reviewCount", 0)

            desc = item.get("shortDescription") or item.get("description", "")
            desc_short = (desc[:80] + "…") if desc and len(desc) > 80 else desc

            lines.append(
                f"{i}. {name} | {price} {currency} | ⭐{rating}/5 ({reviews} reviews)"
                + (f"\n   {desc_short}" if desc_short else "")
            )

        return "\n".join(lines)

    def _mock_fallback(self, dest_id: str, reason: str) -> str:
        return (
            f"Attractions API unavailable (dest: {dest_id}). Reason: {reason}\n"
            "Simulated options: City walking tour ~€15 | Museum visit ~€20 | Food tour ~€45."
        )