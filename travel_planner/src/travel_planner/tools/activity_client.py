import json
import urllib.parse
import os
import http.client


class BookingAttractionClient:
    def __init__(self):
        # Utilizza l'host di Booking per le attrazioni se presente, altrimenti fa il fallback
        self.base_url = os.getenv("RAPIDAPI_HOST_BOOKING") or os.getenv("RAPIDAPI_HOST_KIWI")
        self.client_secret = os.getenv("RAPIDAPI_KEY")

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

    def search_attractions(self,
                           dest_id: str,
                           start_date: str,
                           end_date: str,
                           currency: str = "EUR") -> dict:

        if not self.base_url:
            return {"error": "L'host dell'API (RAPIDAPI_HOST_BOOKING) non è configurato nel file .env"}

        conn = http.client.HTTPSConnection(self.base_url)

        # Mappiamo i parametri esattamente come richiesto dall'endpoint /v1/attractions/search
        query_params = {
            "dest_id": str(dest_id),
            "start_date": str(start_date),
            "end_date": str(end_date),
            "locale": "en-gb",
            "page_number": "0",
            "currency": str(currency),
            "order_by": "attr_book_score"
        }

        # Pulizia preventiva dei parametri None
        query_params = {k: v for k, v in query_params.items() if v is not None}
        query_string = urllib.parse.urlencode(query_params)
        path = f"/v1/attractions/search?{query_string}"

        try:
            conn.request("GET", path, headers=self.headers)
            res = conn.getresponse()
            data = res.read()

            return json.loads(data.decode("utf-8"))
        except Exception as e:
            return {"error": f"Errore di rete o di parsing nel client attrazioni: {str(e)}"}