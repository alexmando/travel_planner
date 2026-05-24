import json
import urllib.parse
import os
import http.client

class KiwiFlightClient:
    def __init__(self):
        self.base_url = "kiwi-com-cheap-flights.p.rapidapi.com"
        self.client_secret = os.getenv("KIWI_API_KEY")
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


        formatted_origin = f"City:{origin}" if origin_city else origin
        formatted_destination = f"City:{destination}" if destination_city else destination

        query_params = {
            "source": formatted_origin,
            "destination": formatted_destination,
            "outboundDepartureDate": departure_date,
            "inboundDepartureDate": arrival_date,
            "adults": adults,
            "cabinClass": mode
        }

        query_string = urllib.parse.urlencode(query_params)
        path = f"/round-trip?{query_string}"

        conn.request("GET", path, headers=self.headers)

        res = conn.getresponse()
        data = res.read()

        try:
            return json.loads(data.decode("utf-8"))
        except json.JSONDecodeError:
            print("Errore nella decodifica del JSON.")
            return {"raw_response": data.decode("utf-8")}