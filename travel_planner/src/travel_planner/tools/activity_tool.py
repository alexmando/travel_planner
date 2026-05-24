from __future__ import annotations

from pathlib import Path
from typing import Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from travel_planner.tools.activity_client import BookingAttractionClient


class AttractionSearchInput(BaseModel):
    """Input schema for attraction search tools."""
    dest_id: str = Field(
        ...,
        description="The destination ID string code. Example: '20088325' or '90003942'."
    )
    start_date: str = Field(
        ...,
        description="The start date of the visit in YYYY-MM-DD format. Example: '2026-09-18'."
    )
    end_date: str = Field(
        ...,
        description="The end date of the visit in YYYY-MM-DD format. Example: '2026-09-19'."
    )
    currency: str = Field(
        default="EUR",
        description="Preferred currency code. Default: 'EUR'."
    )

class AttractionSearchTool(BaseTool):
    name: str = "attraction_search"
    description: str = (
        "Search for local attractions, tours, experiences and things to do at the destination. "
        "Requires the dest_id, start date, and end date. "
        "Returns a structured list of experiences with names, prices, and ratings."
    )
    args_schema: Type[BaseModel] = AttractionSearchInput

    def _run(self, dest_id: str, start_date: str, end_date: str, currency: str = "EUR") -> str:
        try:
            client = BookingAttractionClient()
            raw_results = client.search_attractions(
                dest_id=dest_id,
                start_date=start_date,
                end_date=end_date,
                currency=currency
            )

            if "error" in raw_results:
                return self._mock_fallback(dest_id, f"API Error: {raw_results['error']}")

            return self._format_output(raw_results, dest_id, currency)
        except Exception as e:
            return self._mock_fallback(dest_id, f"Internal Exception: {str(e)}")

    # ------------------------------------------------------------------------------
    # INTERPRETAZIONE ED ESTRAZIONE STRUTTURATA
    # ------------------------------------------------------------------------------
    def _format_output(self, data: dict, dest_id: str, currency: str) -> str:
        # Cerchiamo l'array dei prodotti provando le chiavi più usate dalle API di Booking/Tours
        items = data.get("data", []) or data.get("products", []) or data.get("attractions", [])

        # Se la risposta è vuota o ha una struttura imprevista, attiviamo il fallback
        if not items or not isinstance(items, list):
            return self._mock_fallback(dest_id, "Nessun dato strutturato trovato nella risposta dell'API.")

        lines = [
            f"🏛️  Local Attractions & Experiences Found (Dest ID: {dest_id})",
            f"   Total found: {len(items)}\n"
        ]

        for i, item in enumerate(items[:5], 1):
            name = item.get("name") or item.get("title") or "Activity"

            # Estrazione sicura del prezzo
            price_data = item.get("price") or item.get("representativePrice", {})
            if isinstance(price_data, dict):
                price = price_data.get("publicAmount") or price_data.get("amount") or "N/A"
            else:
                price = str(price_data)

            # Estrazione recensioni
            rating = item.get("rating") or item.get("reviewScore") or "N/A"
            reviews = item.get("reviewsCount") or item.get("reviewCount") or 0

            lines.append(f"{'-' * 50}")
            lines.append(f"Experience {i}: {name}")
            lines.append(f"  💰 Price   : {price} {currency}")
            lines.append(f"  ⭐️ Rating  : {rating}/5 ({reviews} reviews)")

            desc = item.get("shortDescription") or item.get("description")
            if desc:
                lines.append(f"  📝 Info    : {desc[:120]}...")

        return "\n".join(lines)