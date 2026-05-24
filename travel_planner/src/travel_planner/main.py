from dotenv import load_dotenv
import os
import litellm
litellm.disable_cache()

load_dotenv()

from travel_planner.crew import travel_crew


def main():
    print("\n==============================")
    print(" AI TRAVEL PLANNER CREW ")
    print("==============================\n")

    user_inputs = {
        "origin": "Milan",
        "destination": "nord_europe",
        "budget": "1300",
        "age_group": "18-25",
        "departure_date": "2026-08-10",
        "return_date": "2026-08-17",
        "checkin_date": "2026-08-10",
        "checkout_date": "2026-08-17",
        "adults": 2,
    }

    print("Starting CrewAI workflow...\n")

    try:
        result = travel_crew.kickoff(inputs=user_inputs)

        print("\n==============================")
        print(" FINAL TRAVEL PLAN ")
        print("==============================\n")

        print(result)

    except Exception as e:
        print("\n==============================")
        print(" ERROR DURING EXECUTION ")
        print("==============================\n")
        print(str(e))


if __name__ == "__main__":
    main()