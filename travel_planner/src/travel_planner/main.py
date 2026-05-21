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
        "budget": "medium",
        "period": "summer",
        "style": "nightlife",
        "age_group": "18-25",
        "origin": "Milan",
        "departure_date": "2026-08-10",
        "return_date": "2026-08-17",
        "checkin_date": "2026-08-10",
        "checkout_date": "2026-08-17",
        "duration": "7 days",
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