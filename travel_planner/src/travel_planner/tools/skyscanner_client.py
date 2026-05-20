from __future__ import annotations

import json
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
    RapidAPI client for sky-scrapper.

    Required env vars:
      RAPIDAPI_KEY
      RAPIDAPI_HOST (default: sky-scrapper.p.rapidapi.com)

    Optional env vars:
      RAPIDAPI_BASE_URL
      RAPIDAPI_TIMEOUT
      RAPIDAPI_MAX_RETRIES
      RAPIDAPI_BACKOFF_SEC
    """

    def __init__(
            self,
            api_key: Optional[str] = None,
            host: Optional[str] = None,
            base_url: Optional[str] = None,
            timeout: Optional[int] = None,
            max_retries: Optional[int] = None,
            backoff_seconds: Optional[float] = None,
    ) -> None:
        self.api_key = (
                api_key
                or os.getenv("RAPIDAPI_KEY", "").strip()
                or os.getenv("SKYSCANNER_API_KEY", "").strip()
        )
        self.host = (
                host
                or os.getenv("RAPIDAPI_HOST", "").strip()
                or "sky-scrapper.p.rapidapi.com"
        )
        self.base_url = (
                base_url
                or os.getenv("RAPIDAPI_BASE_URL", "").strip()
                or f"https://{self.host}"
        )
        self.timeout = timeout or int(os.getenv("RAPIDAPI_TIMEOUT", "30"))
        self.max_retries = max_retries or int(os.getenv("RAPIDAPI_MAX_RETRIES", "2"))
        self.backoff_seconds = backoff_seconds or float(os.getenv("RAPIDAPI_BACKOFF_SEC", "2"))

    @property
    def enabled(self) -> bool:
        return bool(self.api_key and self.host)

    def _headers(self) -> dict[str, str]:
        return {
            "x-rapidapi-key": self.api_key,
            "x-rapidapi-host": self.host,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def request(
            self,
            method: str,
            path: str,
            *,
            params: Optional[dict[str, Any]] = None,
            json_body: Optional[dict[str, Any]] = None,
    ) -> Any:
        if not self.enabled:
            raise RuntimeError(
                "RapidAPI client disabled. Check RAPIDAPI_KEY and RAPIDAPI_HOST in .env."
            )

        url = f"{self.base_url}{path}"
        last_error: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                response = requests.request(
                    method=method.upper(),
                    url=url,
                    headers=self._headers(),
                    params=params,
                    json=json_body,
                    timeout=self.timeout,
                )

                if response.status_code in {429, 500, 502, 503, 504} and attempt < self.max_retries:
                    time.sleep(self.backoff_seconds * (attempt + 1))
                    continue

                response.raise_for_status()

                if not response.text.strip():
                    return {}

                try:
                    return response.json()
                except Exception:
                    return {"raw": response.text}

            except requests.HTTPError as exc:
                status_code = exc.response.status_code if exc.response is not None else None
                if status_code in {429, 500, 502, 503, 504} and attempt < self.max_retries:
                    time.sleep(self.backoff_seconds * (attempt + 1))
                    continue
                raise
            except requests.RequestException as exc:
                last_error = exc
                if attempt < self.max_retries:
                    time.sleep(self.backoff_seconds * (attempt + 1))
                    continue
                raise

        if last_error is not None:
            raise last_error

        return {}

    def search_flight_everywhere_details(
            self,
            *,
            currency: str = "EUR",
            one_way: bool = False,
    ) -> Any:
        return self.request(
            "GET",
            "/api/v1/flights/searchFlightEverywhereDetails",
            params={
                "currency": currency,
                "oneWay": str(one_way).lower(),
            },
        )

    def search_hotel_destination(
            self,
            query: str,
    ) -> Any:
        return self.request(
            "GET",
            "/api/v1/hotels/searchDestinationOrHotel",
            params={
                "query": query,
            },
        )

    def health_check(self) -> Any:
        return self.search_hotel_destination("new")