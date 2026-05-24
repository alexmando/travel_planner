from typing import Optional, Type
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

# Make sure the import path matches your project structure
# e.g.: from travel_planner.tools.flight_client import KiwiFlightClient
from .flight_client import KiwiFlightClient


# ══════════════════════════════════════════════════════════════
# 1. INPUT SCHEMA
#    Pydantic validates and documents every parameter before it
#    reaches the _run() method. The LLM reads the descriptions
#    to understand how to correctly fill in each field.
# ══════════════════════════════════════════════════════════════
class FlightSearchInput(BaseModel):
    """Input schema for round-trip flight search via Kiwi API."""

    origin: str = Field(
        description=(
            "Flight origin. Can be an IATA code (e.g. 'FCO', 'MXP') "
            "or a city name (e.g. 'Rome', 'Milan'). "
            "Set origin_city=True if passing a city name, "
            "False if passing an IATA code."
        )
    )
    origin_city: bool = Field(
        default=False,
        description=(
            "True if 'origin' is a city name (e.g. 'Rome'), "
            "False if it is an IATA code (e.g. 'FCO'). Default: False."
        )
    )
    destination: str = Field(
        description=(
            "Flight destination. Can be an IATA code (e.g. 'BCN', 'CDG') "
            "or a city name (e.g. 'Barcelona', 'Paris'). "
            "Set destination_city=True if passing a city name."
        )
    )
    destination_city: bool = Field(
        default=False,
        description=(
            "True if 'destination' is a city name (e.g. 'Barcelona'), "
            "False if it is an IATA code (e.g. 'BCN'). Default: False."
        )
    )
    departure_date: str = Field(
        description=(
            "Outbound flight date in YYYY-MM-DD format. "
            "Example: '2025-08-10'."
        )
    )
    arrival_date: str = Field(
        description=(
            "Return flight date in YYYY-MM-DD format. "
            "Example: '2025-08-17'."
        )
    )
    adults: int = Field(
        default=1,
        description="Number of adult passengers. Default: 1."
    )
    mode: str = Field(
        default="ECONOMY",
        description=(
            "Flight cabin class. Accepted values: "
            "'ECONOMY', 'PREMIUM_ECONOMY', 'BUSINESS', 'FIRST'. "
            "Default: 'ECONOMY'."
        )
    )


# ══════════════════════════════════════════════════════════════
# 2. TOOL CLASS
# ══════════════════════════════════════════════════════════════
class FlightSearchTool(BaseTool):
    name: str = "flight_search"
    description: str = (
        "Search for round-trip flights using the Kiwi API. "
        "Use this when you need to find flights between two cities or airports, "
        "specifying the outbound and return dates, number of passengers, "
        "and cabin class (Economy, Business, etc.). "
        "Returns available flight options with prices, schedules, and route details. "
        "Example: flight from Rome (FCO) to Barcelona (BCN), "
        "outbound 10/08/2025, return 17/08/2025, 2 adults in Economy."
    )
    args_schema: Type[BaseModel] = FlightSearchInput

    # ──────────────────────────────────────────────────────────
    # 3. _run METHOD — main logic
    #    MUST always return a string (never raise exceptions).
    # ──────────────────────────────────────────────────────────
    def _run(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        arrival_date: str,
        origin_city: bool = False,
        destination_city: bool = False,
        adults: int = 1,
        mode: str = "ECONOMY",
    ) -> str:
        try:
            client = KiwiFlightClient()

            raw_results = client.search_flights(
                origin_city=origin_city,
                origin=origin,
                destination_city=destination_city,
                destination=destination,
                departure_date=departure_date,
                arrival_date=arrival_date,
                adults=adults,
                mode=mode,
            )

            # If the API returned an error or unstructured response
            if "raw_response" in raw_results:
                return (
                    f"The API returned an invalid response: "
                    f"{raw_results['raw_response'][:300]}"
                )

            if "error" in raw_results:
                return f"Kiwi API error: {raw_results['error']}"

            return self._format_output(raw_results, origin, destination)

        except Exception as e:
            # crewAI tools must never propagate exceptions:
            # the agent will read this message and react accordingly.
            return f"Error during flight search: {str(e)}"

    # ──────────────────────────────────────────────────────────
    # Helper: extract and format results as readable text
    # ──────────────────────────────────────────────────────────
    def _format_output(self, data: dict, origin: str, destination: str) -> str:
        """
        Converts the raw Kiwi JSON response into structured text
        for the AI agent.

        NOTE: adapt the field names (e.g. 'itineraries', 'price', etc.)
        to the actual structure returned by your version of the Kiwi API.
        You can discover it by printing `raw_results` with an isolated
        client test.
        """

        # ── Attempt parsing for common Kiwi RapidAPI structures ──
        # Case 1: list of itineraries under the "itineraries" key
        itineraries = data.get("itineraries", [])

        # Case 2: list of offers under the "data" key
        if not itineraries:
            itineraries = data.get("data", [])

        # Case 3: flat response with no recognised list
        if not itineraries:
            return (
                "Search completed but no flights found "
                f"for {origin} → {destination} with the given parameters.\n"
                f"Raw response (first 500 characters):\n{str(data)[:500]}"
            )

        lines = [
            f"✈️  Round-trip flights found: {origin} ⇄ {destination}",
            f"   Total results: {len(itineraries)}\n",
        ]

        for i, trip in enumerate(itineraries[:5], 1):  # show max 5 results

            # ── Price ──
            price_info = trip.get("price", {})
            if isinstance(price_info, dict):
                price = price_info.get("formatted") or price_info.get("amount", "N/A")
                currency = price_info.get("currency", "EUR")
            else:
                price = str(price_info)
                currency = "EUR"

            # ── Outbound / inbound legs ──
            legs = trip.get("legs", [])
            outbound = legs[0] if len(legs) > 0 else {}
            inbound  = legs[1] if len(legs) > 1 else {}

            lines.append(f"{'─' * 50}")
            lines.append(f"Option {i}")
            lines.append(f"  💶 Total price   : {price} {currency}")

            if outbound:
                lines.append(
                    f"  🛫 Outbound      : {outbound.get('departure', 'N/A')} → "
                    f"{outbound.get('arrival', 'N/A')}"
                )
                lines.append(
                    f"     Duration      : {self._format_duration(outbound.get('durationInMinutes'))}"
                )
                lines.append(
                    f"     Stops         : {outbound.get('stopCount', 0)}"
                )

            if inbound:
                lines.append(
                    f"  🛬 Return        : {inbound.get('departure', 'N/A')} → "
                    f"{inbound.get('arrival', 'N/A')}"
                )
                lines.append(
                    f"     Duration      : {self._format_duration(inbound.get('durationInMinutes'))}"
                )
                lines.append(
                    f"     Stops         : {inbound.get('stopCount', 0)}"
                )

            # ── Booking link (if present) ──
            link = trip.get("deepLink") or trip.get("url") or trip.get("bookingUrl")
            if link:
                lines.append(f"  🔗 Book at       : {link}")

        lines.append(f"{'─' * 50}")
        lines.append(
            "Note: prices are indicative. Please verify up-to-date fares "
            "directly on the booking link before purchasing."
        )

        return "\n".join(lines)

    @staticmethod
    def _format_duration(minutes) -> str:
        """Converts minutes to a readable format, e.g. 125 → '2h 05min'."""
        if minutes is None:
            return "N/A"
        try:
            m = int(minutes)
            return f"{m // 60}h {m % 60:02d}min"
        except (ValueError, TypeError):
            return str(minutes)