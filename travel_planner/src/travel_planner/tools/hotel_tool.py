from __future__ import annotations

import http.client
import json
from datetime import date
from typing import Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field, ConfigDict

from .hotel_client import BookingHotelClient


class HotelSearchInput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    city_name: str = Field(..., description="City in English, e.g. 'Copenhagen', 'Rome'.")
    check_in: str = Field(..., description="Check-in date YYYY-MM-DD.")
    check_out: str = Field(..., description="Check-out date YYYY-MM-DD.")
    adults: int = Field(default=2, ge=1, le=9, description="Number of adult guests.")
    rooms: int = Field(default=1, ge=1, le=9, description="Number of rooms.")
    budget: str = Field(default="medium", description="Budget level: low, medium, high.")


class HotelSearchTool(BaseTool):
    name: str = "hotel_search"
    description: str = (
        "Search hotels via Booking.com. Runs 3 searches (by price, popularity, review score), "
        "cross-references results, and returns the best pick + top 3 per criteria. "
        "Pass city name in English, check-in/out as YYYY-MM-DD."
    )
    args_schema: Type[BaseModel] = HotelSearchInput

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

            dest_id = self._resolve_dest_id(client, city_name)
            if dest_id is None:
                return self._mock_result(city_name, check_in, check_out, budget)

            # 3 searches with different sort criteria
            results_by_sort: dict[str, list[dict]] = {}
            for sort in ("price", "popularity", "review_score"):
                raw = client.search_hotels(
                    city_code=dest_id,
                    check_in=check_in,
                    check_out=check_out,
                    adults=adults,
                    rooms=rooms,
                    order_by=sort,
                )
                if "raw_response" in raw or "error" in raw:
                    results_by_sort[sort] = []
                else:
                    hotels = raw.get("result") or raw.get("data") or raw.get("hotels") or []
                    results_by_sort[sort] = hotels[:5]

            best = self._cross_reference(results_by_sort)
            return self._format_output(results_by_sort, best, city_name, check_in, check_out, adults, budget)

        except Exception as exc:
            return self._mock_result(city_name, check_in, check_out, budget) + f"\nError: {exc}"

    # ── Helpers ────────────────────────────────────────────────

    def _resolve_dest_id(self, client: BookingHotelClient, city_name: str) -> str | None:
        try:
            conn = http.client.HTTPSConnection(client.base_url)
            conn.request("GET", f"/v1/hotels/locations?locale=en-gb&name={city_name}", headers=client.headers)
            locations = json.loads(conn.getresponse().read().decode("utf-8"))
            return str(locations[0].get("dest_id")) if locations else None
        except Exception:
            return None

    def _cross_reference(self, results_by_sort: dict[str, list[dict]]) -> dict | None:
        scores: dict[str, float] = {}
        index: dict[str, dict] = {}
        weights = {"price": 1.0, "popularity": 2.0, "review_score": 2.0}

        for sort, hotels in results_by_sort.items():
            for h in hotels:
                hid = str(h.get("hotel_id") or h.get("hotel_name", "?"))
                if hid not in scores:
                    scores[hid] = 0.0
                    index[hid] = h
                scores[hid] += weights.get(sort, 1.0)
                try:
                    scores[hid] += float(h.get("review_score") or 0) * 0.1
                except (ValueError, TypeError):
                    pass

        if not scores:
            return None

        # Bonus for appearing in all 3 lists
        sets = [
            {str(h.get("hotel_id") or h.get("hotel_name", "?")) for h in v}
            for v in results_by_sort.values() if v
        ]
        if len(sets) == 3:
            for hid in sets[0] & sets[1] & sets[2]:
                scores[hid] += 3.0

        best_id = max(scores, key=lambda k: scores[k])
        best = index[best_id].copy()
        best["_score"] = round(scores[best_id], 2)
        best["_in_lists"] = [
            s for s, hotels in results_by_sort.items()
            if any(str(h.get("hotel_id") or h.get("hotel_name", "?")) == best_id for h in hotels)
        ]
        return best

    def _hotel_line(self, h: dict) -> str:
        """Compact one-line summary of a hotel."""
        name = h.get("hotel_name") or h.get("name", "N/A")
        price = (
            h.get("min_total_price")
            or h.get("composite_price_breakdown", {}).get("gross_amount", {}).get("value")
            or "N/A"
        )
        currency = h.get("currencycode") or "DKK"
        review = h.get("review_score", "?")
        dist = h.get("distance_to_cc_formatted") or h.get("distance", "?")
        return f"{name} | {price} {currency} total | ⭐{review}/10 | {dist} from centre"

    def _format_output(
        self,
        results_by_sort: dict[str, list[dict]],
        best: dict | None,
        city_name: str,
        check_in: str,
        check_out: str,
        adults: int,
        budget: str,
    ) -> str:
        try:
            nights = (date.fromisoformat(check_out) - date.fromisoformat(check_in)).days
        except ValueError:
            nights = "?"

        lines = [f"🏨 Hotels in {city_name} | {check_in}→{check_out} ({nights}n) | {adults} adults | {budget}\n"]

        labels = {"price": "📉 By price", "popularity": "🔥 By popularity", "review_score": "⭐ By review"}
        for sort, hotels in results_by_sort.items():
            lines.append(f"{labels.get(sort, sort)}:")
            if not hotels:
                lines.append("  No results.")
            else:
                for i, h in enumerate(hotels[:3], 1):
                    lines.append(f"  {i}. {self._hotel_line(h)}")
            lines.append("")

        lines.append("── BEST PICK (cross-referenced) ──")
        if not best:
            lines.append("Could not determine best pick.")
        else:
            name     = best.get("hotel_name") or best.get("name", "N/A")
            address  = best.get("address") or best.get("address_trans", "N/A")
            price    = (
                best.get("min_total_price")
                or best.get("composite_price_breakdown", {}).get("gross_amount", {}).get("value")
                or "N/A"
            )
            currency = best.get("currencycode") or "DKK"
            review   = best.get("review_score", "N/A")
            review_w = best.get("review_score_word", "")
            reviews  = best.get("review_nr") or 0
            stars_n  = best.get("class") or best.get("stars")
            stars    = f"{'⭐'*int(stars_n)}" if stars_n else "N/A"
            dist     = best.get("distance_to_cc_formatted") or "N/A"
            in_lists = ", ".join(best.get("_in_lists", []))

            lines += [
                f"  {name} | {stars} | {address} | {dist} from centre",
                f"  {review}/10 {review_w} ({reviews} reviews)",
                f"  {price} {currency} total ({nights} nights)",
                f"  Ranked in: [{in_lists}] — score: {best.get('_score', '?')}",
            ]

        lines.append("\nPrices indicative. Verify on Booking.com before booking.")
        return "\n".join(lines)

    def _mock_result(self, city_name: str, check_in: str, check_out: str, budget: str) -> str:
        return (
            f"Booking.com unavailable for {city_name} ({check_in}→{check_out}, {budget}).\n"
            "Simulated options: €70/night budget | €140/night mid-range | €220/night comfort."
        )