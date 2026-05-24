from __future__ import annotations

import http.client
import json
from datetime import date
from typing import Any, Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from .hotel_client import BookingHotelClient


# ══════════════════════════════════════════════════════════════
# 1. INPUT SCHEMA
# ══════════════════════════════════════════════════════════════
class HotelSearchInput(BaseModel):
    """Input schema for hotel search via Booking.com RapidAPI."""

    city_name: str = Field(
        ...,
        description=(
            "City name to search hotels in, in English. "
            "Examples: 'Barcelona', 'Rome', 'Paris', 'Amsterdam'. "
            "Used to automatically resolve the Booking.com dest_id."
        )
    )
    check_in: str = Field(
        ...,
        description="Check-in date in YYYY-MM-DD format. Example: '2025-08-10'."
    )
    check_out: str = Field(
        ...,
        description="Check-out date in YYYY-MM-DD format. Example: '2025-08-15'."
    )
    adults: int = Field(
        default=2,
        ge=1,
        le=9,
        description="Number of adult guests. Default: 2."
    )
    rooms: int = Field(
        default=1,
        ge=1,
        le=9,
        description="Number of rooms required. Default: 1."
    )
    budget: str = Field(
        default="medium",
        description=(
            "Preferred budget level used to label the search context. "
            "Accepted values: 'low', 'medium', 'high'. Default: 'medium'."
        )
    )


# ══════════════════════════════════════════════════════════════
# 2. TOOL CLASS
# ══════════════════════════════════════════════════════════════
class HotelSearchTool(BaseTool):
    name: str = "hotel_search"
    description: str = (
        "Search for available hotels in a city using the Booking.com RapidAPI. "
        "Use this when you need to find accommodation for a stay, "
        "specifying the city, check-in and check-out dates, "
        "number of adult guests, number of rooms, and budget level. "
        "The tool automatically resolves the Booking.com destination code "
        "from the city name. "
        "Returns hotel name, star rating, price, review score, and address. "
        "Falls back to simulated hotel options if the API is unavailable. "
        "Example: hotels in Barcelona from 2025-08-10 to 2025-08-15, "
        "2 adults, 1 room, medium budget."
    )
    args_schema: Type[BaseModel] = HotelSearchInput

    # ──────────────────────────────────────────────────────────
    # 3. _run METHOD
    # ──────────────────────────────────────────────────────────
    def _run(
        self,
        city_name: str,
        check_in: str,
        check_out: str,
        adults: int = 2,
        rooms: int = 1,
        budget: str = "medium",
    ) -> str:
        try:
            client = BookingHotelClient(token=None, base_url=None)

            # Step 1: resolve city name → Booking.com dest_id
            dest_id = self._resolve_dest_id(client, city_name)
            if dest_id is None:
                return self._mock_result(city_name, check_in, check_out, budget)

            raw_results = client.search_hotels(
                city_code=dest_id,
                check_in=check_in,
                check_out=check_out,
                adults=adults,
                rooms=rooms,
            )

            if "raw_response" in raw_results:
                return self._mock_result(city_name, check_in, check_out, budget)

            if "error" in raw_results:
                return (
                    self._mock_result(city_name, check_in, check_out, budget)
                    + f"\n\nAPI error: {raw_results['error']}"
                )

            return self._format_output(
                raw_results, city_name, check_in, check_out, adults, rooms, budget
            )

        except Exception as exc:
            # crewAI tools must never propagate exceptions.
            return (
                self._mock_result(city_name, check_in, check_out, budget)
                + f"\n\nAPI error: {exc}"
            )

    # ──────────────────────────────────────────────────────────
    # Helper: resolve city name → dest_id
    # ──────────────────────────────────────────────────────────
    def _resolve_dest_id(self, client: BookingHotelClient, city_name: str) -> str | None:
        """
        Calls the /v1/hotels/locations endpoint and returns the dest_id
        of the first result. The original client method only prints the
        value without returning it, so we replicate the HTTP call here
        and handle the response properly.
        """
        try:
            conn = http.client.HTTPSConnection(client.base_url)
            conn.request(
                "GET",
                f"/v1/hotels/locations?locale=en-gb&name={city_name}",
                headers=client.headers,
            )
            res = conn.getresponse()
            locations = json.loads(res.read().decode("utf-8"))
        except Exception:
            return None

        if not locations:
            return None

        return str(locations[0].get("dest_id"))

    # ──────────────────────────────────────────────────────────
    # Helper: mock result used as fallback
    # ──────────────────────────────────────────────────────────
    def _mock_result(
        self,
        city_name: str,
        check_in: str,
        check_out: str,
        budget: str,
    ) -> str:
        """
        Returns simulated hotel options when the API is unavailable
        or the city could not be resolved.
        """
        return "\n".join([
            "Booking.com API not available or city not found; using simulated hotel options.",
            f"Destination : {city_name}",
            f"Check-in    : {check_in}",
            f"Check-out   : {check_out}",
            f"Budget      : {budget}",
            "─" * 50,
            "- Budget option  : €70/night  | central location",
            "- Mid-range hotel: €140/night | breakfast included",
            "- Comfort hotel  : €220/night | near main attractions",
        ])

    # ──────────────────────────────────────────────────────────
    # Helper: format API response as readable text
    # ──────────────────────────────────────────────────────────
    def _format_output(
        self,
        data: dict,
        city_name: str,
        check_in: str,
        check_out: str,
        adults: int,
        rooms: int,
        budget: str,
    ) -> str:
        """
        Converts the raw Booking.com JSON response into structured text
        for the AI agent.

        NOTE: adapt field names to the actual structure returned by your
        API version. Print `raw_results` in an isolated client test to
        inspect the real JSON shape.
        """
        # Calculate number of nights
        try:
            nights = (date.fromisoformat(check_out) - date.fromisoformat(check_in)).days
        except ValueError:
            nights = "?"

        # Booking.com RapidAPI v1 returns results under "result"
        hotels = (
            data.get("result")
            or data.get("data")
            or data.get("hotels")
            or []
        )

        if not hotels:
            return (
                self._mock_result(city_name, check_in, check_out, budget)
                + f"\n\nRaw response (first 500 chars):\n{str(data)[:500]}"
            )

        lines = [
            f"🏨  Hotels available in {city_name}",
            f"   Check-in : {check_in}  →  Check-out : {check_out}  ({nights} nights)",
            f"   Adults   : {adults}  |  Rooms: {rooms}  |  Budget: {budget}",
            f"   Results  : {len(hotels)} found\n",
        ]

        for i, hotel in enumerate(hotels[:5], 1):  # show max 5 results

            # ── Name ──
            name = hotel.get("hotel_name") or hotel.get("name", "N/A")

            # ── Review score ──
            review_score = hotel.get("review_score") or hotel.get("rating", "N/A")
            review_label = hotel.get("review_score_word", "")
            review_count = hotel.get("review_nr") or hotel.get("review_count", 0)

            # ── Price ──
            price = (
                hotel.get("min_total_price")
                or hotel.get("composite_price_breakdown", {})
                    .get("gross_amount", {}).get("value")
                or hotel.get("price_breakdown", {}).get("gross_price")
                or "N/A"
            )
            currency = hotel.get("currencycode") or hotel.get("currency", "EUR")

            # ── Address & distance ──
            address  = hotel.get("address") or hotel.get("address_trans", "N/A")
            distance = hotel.get("distance_to_cc_formatted") or hotel.get("distance", "")

            # ── Star rating ──
            stars_num = hotel.get("class") or hotel.get("stars")
            stars = "⭐" * int(stars_num) if stars_num else "N/A"

            lines.append(f"{'─' * 50}")
            lines.append(f"Hotel {i} — {name}")
            lines.append(f"  Stars         : {stars}")
            lines.append(f"  Address       : {address}")
            if distance:
                lines.append(f"  From centre   : {distance}")
            if review_score != "N/A":
                lines.append(
                    f"  Review score  : {review_score}/10 — {review_label} "
                    f"({review_count} reviews)"
                )
            lines.append(
                f"  Total price   : {price} {currency} "
                f"({nights} nights)" if nights != "?" else f"  Total price   : {price} {currency}"
            )

        lines.append(f"{'─' * 50}")
        lines.append(
            "Note: prices are indicative. Verify availability and current "
            "conditions on Booking.com before booking."
        )

        return "\n".join(lines)