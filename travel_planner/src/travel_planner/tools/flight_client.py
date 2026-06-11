import json
import urllib.parse
import os
import http.client
from datetime import datetime

class KiwiFlightClient:
    def __init__(self):
        self.base_url = os.getenv("RAPIDAPI_HOST_KIWI")
        self.client_secret = os.getenv("RAPIDAPI_KEY")
        self.headers = {
            'x-rapidapi-key': self.client_secret,
            'x-rapidapi-host': self.base_url,
            'Content-Type': "application/json"
        }

    def search_flights(self,
                       origin_city: bool,
                       origin: str,
                       destination_city: bool,
                       destination: str,
                       departure_date: str,
                       arrival_date: str,
                       adults: int = 1,
                       mode: str = "ECONOMY") -> dict:
        conn = http.client.HTTPSConnection(self.base_url)

        formatted_origin = f"City:{origin}" if origin_city else f"Country:{origin}"
        formatted_destination = f"City:{destination}" if destination_city else f"Country:{destination}"

        requested_adults = adults

        try:
            dep_obj = datetime.strptime(departure_date, "%Y-%m-%d")
            arr_obj = datetime.strptime(arrival_date, "%Y-%m-%d")
            fmt_departure = dep_obj.strftime("%Y-%m-%dT00:00:00")
            fmt_arrival = arr_obj.strftime("%Y-%m-%dT00:00:00")
        except ValueError:
            fmt_departure = f"{departure_date}T00:00:00"
            fmt_arrival = f"{arrival_date}T00:00:00"

        query_params = {
            "source": formatted_origin,
            "destination": formatted_destination,
            "outboundDepartureDate": fmt_departure,
            "inboundDepartureDate": fmt_arrival,
            "adults": 1,
            "cabinClass": mode,
        }

        query_string = urllib.parse.urlencode(query_params)
        path = f"/round-trip?{query_string}"

        conn.request("GET", path, headers=self.headers)

        res = conn.getresponse()
        data = res.read()

        try:
            response_data = json.loads(data.decode("utf-8"))

            if "price" in response_data and requested_adults > 1:
                if isinstance(response_data["price"], (int, float)):
                    response_data["price"] = response_data["price"] * requested_adults
                    response_data["note_budget"] = f"Prezzo calcolato per {requested_adults} adulti."

            return response_data

        except json.JSONDecodeError:
            print("Errore nella decodifica del JSON.")
            return {"raw_response": data.decode("utf-8")}