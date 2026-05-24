import json
import os
import http.client
import urllib.parse


class BookingHotelClient:
    def __init__(self, token: str = None, base_url: str = None):
        self.base_url = os.getenv("RAPIDAPI_HOST_BOOKING")
        self.client_secret = os.getenv("RAPIDAPI_KEY")

        if not self.base_url:
            raise ValueError("RAPIDAPI_HOST_BOOKING not found in environment variables")
        if not self.client_secret:
            raise ValueError("RAPIDAPI_KEY not found in environment variables")

        self.headers = {
            'x-rapidapi-key': self.client_secret,
            'x-rapidapi-host': self.base_url,
            'Content-Type': "application/json"
        }

    def search_locations(self, name: str) -> str | None:
        """Risolve il nome città → dest_id. Restituisce il dest_id o None."""
        conn = http.client.HTTPSConnection(self.base_url)
        params = urllib.parse.urlencode({
            "locale": "en-gb",
            "name": name,
        })
        conn.request("GET", f"/v1/hotels/locations?{params}", headers=self.headers)
        res = conn.getresponse()
        data = res.read()
        try:
            locations = json.loads(data.decode("utf-8"))
            if locations:
                return str(locations[0].get("dest_id"))
            return None
        except json.JSONDecodeError:
            return None

    def search_hotels(
        self,
        city_code: str,
        check_in: str,
        check_out: str,
        adults: int = 2,
        rooms: int = 1,
        currency: str = "EUR",
    ) -> dict:
        conn = http.client.HTTPSConnection(self.base_url)

        params = urllib.parse.urlencode({
            "dest_id":            city_code,
            "dest_type":          "city",
            "checkin_date":       check_in,
            "checkout_date":      check_out,
            "adults_number":      adults,
            "room_number":        rooms,
            "locale":             "en-gb",
            "filter_by_currency": currency,
            "order_by":           "price",
            "units":              "metric",
            "include_adjacency":  "true",

        })

        path = f"/v1/hotels/search?{params}"
        conn.request("GET", path, headers=self.headers)
        res = conn.getresponse()
        data = res.read()

        try:
            return json.loads(data.decode("utf-8"))
        except json.JSONDecodeError:
            return {"raw_response": data.decode("utf-8")}