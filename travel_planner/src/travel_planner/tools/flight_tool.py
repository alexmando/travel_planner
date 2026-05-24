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
            "Flight origin. Can be a country code (e.g. 'GB', 'DE') "
            "or a city name (e.g. 'rome_it', 'milan_it', 'warsaw_pl'). "
            "Set origin_city=True if passing a city name, "
            "False if passing a country code."
        )
    )
    origin_city: bool = Field(
        default=False,
        description=(
            "True if 'origin' is a city name (e.g. 'rome_it', 'milan_it', 'warsaw_pl'), "
            "False if it is a country code (e.g. 'GB', 'DE'). Default: False."
        )
    )
    destination: str = Field(
        description=(
            "Flight destination. Can be a country code (e.g. 'GB', 'DE') "
            "or a city name (e.g. 'rome_it', 'milan_it', 'warsaw_pl'). "
            "Set destination_city=True if passing a city name."
            "False if passing a country code."
        )
    )
    destination_city: bool = Field(
        default=False,
        description=(
            "True if 'destination' is a city name (e.g. 'rome_it', 'milan_it', 'warsaw_pl'), "
            "False if it is a country code (e.g. 'GB', 'DE'). Default: False."
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
        Converts the raw Kiwi JSON response into structured text for the AI agent
        matching the true schema (itineraries -> priceEur, outbound/inbound -> duration).
        """
        # Estraiamo la lista degli itinerari dal JSON reale
        itineraries = data.get("itineraries", [])

        if not itineraries:
            return (
                f"Search completed but no flights found "
                f"for {origin} -> {destination} with the given parameters.\n"
                f"Raw response (first 300 characters):\n{str(data)[:300]}"
            )

        lines = [
            f"✈️  Round-trip flights found: {origin} -> {destination}",
            f"   Total results: {len(itineraries)}\n",
        ]

        for i, trip in enumerate(itineraries[:5], 1):  # Mostra al massimo 5 risultati

            # 1. Estrazione sicura del prezzo in EURO (usiamo priceEur dal tuo JSON)
            price_eur_info = trip.get("priceEur", {})
            price = price_eur_info.get("amount", "N/A")

            # Arrotonda il prezzo per renderlo più leggibile se è una stringa numerica
            try:
                price = f"{float(price):.2f}"
            except (ValueError, TypeError):
                pass
            currency = "EUR"

            # 2. Estrazione tratte (Outbound / Inbound)
            outbound = trip.get("outbound", {})
            inbound = trip.get("inbound", {})

            lines.append(f"{'-' * 50}")
            lines.append(f"Option {i}")
            lines.append(f"  💰 Total price   : {price} {currency}")

            # --- GESTIONE ANDATA (Outbound) ---
            if outbound:
                # Estraiamo i codici aeroporto e l'orario dai segmenti reali
                segments = outbound.get("sectorSegments", [])
                if segments and isinstance(segments, list):
                    seg_data = segments[0].get("segment", {})
                    src_iata = seg_data.get("source", {}).get("station", {}).get("code", "N/A")
                    dst_iata = seg_data.get("destination", {}).get("station", {}).get("code", "N/A")
                    time_str = seg_data.get("source", {}).get("localTime", "N/A")
                    carrier = seg_data.get("carrier", {}).get("name", "Unknown Airline")

                    # Puliamo la data per renderla leggibile (es. da 2026-08-25T22:15:00 a 2026-08-25 22:15)
                    time_clean = time_str.replace("T", " ")[:16] if time_str else "N/A"

                    lines.append(f"  🛫 Outbound ({carrier}): {src_iata} -> {dst_iata} | Departs: {time_clean}")

                # La durata nel tuo JSON è in SECONDI sotto la chiave "duration"
                duration_seconds = outbound.get("duration")
                lines.append(f"     Duration      : {self._format_duration(duration_seconds)}")

            # --- GESTIONE RITORNO (Inbound) ---
            if inbound:
                segments = inbound.get("sectorSegments", [])
                if segments and isinstance(segments, list):
                    seg_data = segments[0].get("segment", {})
                    src_iata = seg_data.get("source", {}).get("station", {}).get("code", "N/A")
                    dst_iata = seg_data.get("destination", {}).get("station", {}).get("code", "N/A")
                    time_str = seg_data.get("source", {}).get("localTime", "N/A")
                    carrier = seg_data.get("carrier", {}).get("name", "Unknown Airline")

                    time_clean = time_str.replace("T", " ")[:16] if time_str else "N/A"

                    lines.append(f"  🛬 Return ({carrier}): {src_iata} -> {dst_iata} | Departs: {time_clean}")

                duration_seconds = inbound.get("duration")
                lines.append(f"     Duration      : {self._format_duration(duration_seconds)}")

            # 3. Estrazione link di prenotazione reale
            # Nel tuo JSON è annidato dentro edges -> node -> bookingUrl
            booking_options = trip.get("bookingOptions", {})
            edges = booking_options.get("edges", [])
            if edges and isinstance(edges, list):
                link = edges[0].get("node", {}).get("bookingUrl")
                if link:
                    # Se il link è relativo, aggiungiamo il dominio di Kiwi
                    full_link = f"https://www.kiwi.com{link}" if link.startswith("/") else link
                    lines.append(f"  🔗 Book at       : {full_link}")

        lines.append(f"{'-' * 50}")
        lines.append("Note: Prices are retrieved in real-time from the Kiwi API via RapidAPI.")
        return "\n".join(lines)

    @staticmethod
    def _format_duration(seconds) -> str:
        """Converts seconds from the true JSON into a readable format, e.g. 7500 -> '2h 05min'."""
        if seconds is None or str(seconds).lower() == 'none':
            return "N/A"
        try:
            # Trasformiamo i secondi totali in minuti totali
            total_minutes = int(float(seconds)) // 60
            h = total_minutes // 60
            m = total_minutes % 60
            return f"{h}h {m:02d}min"
        except (ValueError, TypeError):
            return f"{seconds} sec"