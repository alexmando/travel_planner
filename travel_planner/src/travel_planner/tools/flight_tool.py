from typing import Type
from crewai.tools import BaseTool
from pydantic import BaseModel, Field, ConfigDict

from .flight_client import KiwiFlightClient


class FlightSearchInput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    origin: str = Field(description="City name in format 'city_countrycode', e.g. 'milan_it', 'copenhagen_dk'.")
    destination: str = Field(description="City name in format 'city_countrycode', e.g. 'copenhagen_dk', 'berlin_de'.")
    departure_date: str = Field(description="Outbound date YYYY-MM-DD.")
    arrival_date: str = Field(description="Return date YYYY-MM-DD.")
    adults: int = Field(default=2, description="Number of adult passengers.")
    mode: str = Field(default="ECONOMY", description="Cabin class: ECONOMY, BUSINESS, FIRST.")


class FlightSearchTool(BaseTool):
    name: str = "flight_search"
    description: str = (
        "Search round-trip flights via Kiwi API. "
        "Pass city names as 'city_countrycode' (e.g. 'milan_it', 'copenhagen_dk'). "
        "Returns top 3 cheapest options with price, route, and booking link."
    )
    args_schema: Type[BaseModel] = FlightSearchInput

    def _run(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        arrival_date: str,
        adults: int = 2,
        mode: str = "ECONOMY",
    ) -> str:
        try:
            client = KiwiFlightClient()
            raw = client.search_flights(
                origin_city=True,
                origin=origin,
                destination_city=True,
                destination=destination,
                departure_date=departure_date,
                arrival_date=arrival_date,
                adults=adults,
                mode=mode,
            )

            if "raw_response" in raw:
                return f"API returned invalid response: {raw['raw_response'][:150]}"
            if "error" in raw:
                return f"Kiwi API error: {raw['error']}"

            return self._format_output(raw, origin, destination, adults)

        except Exception as e:
            return f"Flight search error: {str(e)}"

    def _format_output(self, data: dict, origin: str, destination: str, adults: int) -> str:
        itineraries = data.get("itineraries", [])

        if not itineraries:
            return (
                f"No flights found for {origin} → {destination}. "
                f"API hint: {str(data)[:150]}"
            )

        lines = [f"✈ Flights {origin} → {destination} | {len(itineraries)} results\n"]

        for i, trip in enumerate(itineraries[:3], 1):
            # Price
            price_raw = trip.get("priceEur", {}).get("amount", "N/A")
            try:
                price_per_person = float(price_raw)
                price_total = price_per_person * adults
                price_str = f"{price_per_person:.2f} EUR/person | {price_total:.2f} EUR total"
            except (ValueError, TypeError):
                price_str = str(price_raw)

            # Outbound
            outbound = trip.get("outbound", {})
            out_str = self._leg_summary(outbound)

            # Inbound
            inbound = trip.get("inbound", {})
            in_str = self._leg_summary(inbound)

            # Booking link — truncated
            link = ""
            edges = trip.get("bookingOptions", {}).get("edges", [])
            if edges:
                raw_link = edges[0].get("node", {}).get("bookingUrl", "")
                if raw_link:
                    full = f"https://www.kiwi.com{raw_link}" if raw_link.startswith("/") else raw_link
                    link = full[:80] + "..."

            lines.append(
                f"[{i}] {price_str}\n"
                f"    OUT: {out_str}\n"
                f"    RET: {in_str}\n"
                + (f"    🔗 {link}\n" if link else "")
            )

        lines.append("Prices from Kiwi via RapidAPI. Verify before booking.")
        return "\n".join(lines)

    def _leg_summary(self, leg: dict) -> str:
        """Returns a compact one-line summary of a flight leg."""
        if not leg:
            return "N/A"

        segments = leg.get("sectorSegments", [])
        carrier = "?"
        src = dst = departs = "N/A"

        if segments:
            seg = segments[0].get("segment", {})
            carrier = seg.get("carrier", {}).get("name", "?")
            src = seg.get("source", {}).get("station", {}).get("code", "N/A")
            dst = seg.get("destination", {}).get("station", {}).get("code", "N/A")
            t = seg.get("source", {}).get("localTime", "")
            departs = t.replace("T", " ")[:16] if t else "N/A"

        duration = self._fmt_duration(leg.get("duration"))
        return f"{carrier} {src}→{dst} dep {departs} ({duration})"

    @staticmethod
    def _fmt_duration(seconds) -> str:
        if seconds is None:
            return "N/A"
        try:
            m = int(float(seconds)) // 60
            return f"{m // 60}h{m % 60:02d}m"
        except (ValueError, TypeError):
            return "N/A"