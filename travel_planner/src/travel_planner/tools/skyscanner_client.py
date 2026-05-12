from __future__ import annotations

import os
import time
from typing import Any, Optional

import requests

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass


class SkyscannerClient:
    """
    Thin client for Skyscanner Travel APIs.

    Required env vars:
      SKYSCANNER_API_KEY
      SKYSCANNER_MARKET   (default: IT)
      SKYSCANNER_LOCALE   (default: it-IT)
      SKYSCANNER_CURRENCY (default: EUR)
    """

    def __init__(
            self,
            api_key: Optional[str] = None,
            market: Optional[str] = None,
            locale: Optional[str] = None,
            currency: Optional[str] = None,
            timeout: int = 30,
    ) -> None:
        self.api_key = api_key or os.getenv("SKYSCANNER_API_KEY", "").strip()
        self.market = market or os.getenv("SKYSCANNER_MARKET", "IT").strip()
        self.locale = locale or os.getenv("SKYSCANNER_LOCALE", "it-IT").strip()
        self.currency = currency or os.getenv("SKYSCANNER_CURRENCY", "EUR").strip()
        self.timeout = timeout
        self.base_url = "https://partners.api.skyscanner.net"

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def _headers(self) -> dict[str, str]:
        return {
            "x-api-key": self.api_key,
            "accept": "application/json",
            "content-type": "application/json",
        }

    def request(
            self,
            method: str,
            path: str,
            *,
            json_body: Optional[dict[str, Any]] = None,
            params: Optional[dict[str, Any]] = None,
    ) -> Any:
        url = f"{self.base_url}{path}"
        response = requests.request(
            method=method.upper(),
            url=url,
            headers=self._headers(),
            json=json_body,
            params=params,
            timeout=self.timeout,
        )
        response.raise_for_status()
        if not response.text.strip():
            return {}
        try:
            return response.json()
        except Exception:
            return {"raw": response.text}

    def autosuggest_flights(self, search_term: str, *, limit: int = 5, is_destination: bool = True) -> Any:
        payload = {
            "query": {
                "market": self.market,
                "locale": self.locale,
                "searchTerm": search_term,
                "includedEntityTypes": ["PLACE_TYPE_CITY", "PLACE_TYPE_AIRPORT", "PLACE_TYPE_COUNTRY"],
            },
            "limit": limit,
            "isDestination": is_destination,
        }
        return self.request("POST", "/apiservices/v3/autosuggest/flights", json_body=payload)

    def autosuggest_hotels(self, search_term: str, *, limit: int = 5) -> Any:
        payload = {
            "query": {
                "market": self.market,
                "locale": self.locale,
                "searchTerm": search_term,
                "includedEntityTypes": ["PLACE_TYPE_CITY", "PLACE_TYPE_COUNTRY", "PLACE_TYPE_AREA"],
            },
            "limit": limit,
        }
        return self.request("POST", "/apiservices/v3/autosuggest/hotels", json_body=payload)

    def flights_live_create(self, query_legs: list[dict[str, Any]], adults: int = 1) -> Any:
        payload = {
            "market": self.market,
            "locale": self.locale,
            "currency": self.currency,
            "queryLegs": query_legs,
            "adults": adults,
        }
        return self.request("POST", "/apiservices/v3/flights/live/search/create", json_body=payload)

    def flights_live_poll(self, session_token: str, *, limit: int = 10, offset: int = 0) -> Any:
        payload = {
            "pagination": {"offset": offset, "limit": limit},
        }
        return self.request(
            "POST",
            f"/apiservices/v3/flights/live/search/poll/{session_token}",
            json_body=payload,
        )

    def flights_refresh_price(self, session_token: str, itinerary_id: str) -> Any:
        payload = {"itineraryId": itinerary_id}
        return self.request(
            "POST",
            f"/apiservices/v3/flights/live/itineraryrefresh/create/{session_token}",
            json_body=payload,
        )

    def hotels_live_create(self, query: dict[str, Any], initial_page_size: int = 10) -> Any:
        payload = {
            "query": query,
            "initialPageSize": initial_page_size,
        }
        return self.request("POST", "/apiservices/v1/hotels/live/search/create", json_body=payload)

    def hotels_live_poll(self, session_token: str, *, limit: int = 10, offset: int = 0) -> Any:
        payload = {
            "pagination": {"offset": offset, "limit": limit},
        }
        return self.request(
            "POST",
            f"/apiservices/v1/hotels/live/search/poll/{session_token}",
            json_body=payload,
        )

    def geo_flights(self) -> Any:
        return self.request("GET", f"/apiservices/v3/geo/hierarchy/flights/{self.locale}")

    def wait_and_poll(
            self,
            create_result: Any,
            poll_fn,
            *,
            max_polls: int = 3,
            sleep_seconds: float = 1.2,
    ) -> Any:
        """
        Helper for create/poll flows.
        """
        if not isinstance(create_result, dict):
            return create_result

        session_token = create_result.get("sessionToken") or create_result.get("session_token")
        if not session_token:
            return create_result

        last = create_result
        for _ in range(max_polls):
            time.sleep(sleep_seconds)
            try:
                last = poll_fn(session_token)
            except Exception:
                break
        return last