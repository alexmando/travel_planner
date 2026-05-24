from dotenv import load_dotenv
load_dotenv()
import json
from travel_planner.tools.hotel_client import BookingHotelClient

client = BookingHotelClient()
dest_id = client.search_locations("Stockholm")
print(f"dest_id: {dest_id}")

result = client.search_hotels(
    city_code=dest_id,
    check_in="2026-08-10",
    check_out="2026-08-17",
    adults=2,
    rooms=1,
)
print(json.dumps(result, indent=2))