from crewai import Agent, Crew, Process, Task
from langchain_openai import ChatOpenAI

from travel_planner.tools import (
    DestinationSearchTool,
    FlightSearchTool,
    HotelSearchTool,
    ActivitySearchTool,
)

# =========================
# LLM
# =========================

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.7
)

# =========================
# AGENTS
# =========================

travel_planner_agent = Agent(
    role="Travel Planner Agent",
    goal=(
        "Create the best possible travel plan based on the user's preferences, "
        "budget, travel period, and desired experience."
    ),
    backstory=(
        "You are an expert AI travel planner specialized in organizing complete trips. "
        "You analyze user preferences and coordinate specialized travel agents "
        "to create coherent, optimized and personalized travel experiences. "
        "You are responsible for selecting the most suitable destination "
        "among different possible destinations."
    ),
    verbose=True,
    allow_delegation=True,
    llm=llm,
    tools=[DestinationSearchTool()]
)

flight_agent = Agent(
    role="Flight Search Specialist",
    goal=(
        "Find the best flight options according to destination, budget and dates."
    ),
    backstory=(
        "You are an expert in airline route planning and flight comparison. "
        "You search flights using Skyscanner APIs and identify the most convenient "
        "travel solutions considering cost, comfort and travel duration."
    ),
    verbose=True,
    allow_delegation=False,
    llm=llm,
    tools=[FlightSearchTool()]
)

hotel_agent = Agent(
    role="Hotel Specialist",
    goal=(
        "Find the best accommodation solutions for the selected destination."
    ),
    backstory=(
        "You are a travel accommodation expert specialized in finding hotels "
        "and stays optimized for budget, comfort and user preferences."
    ),
    verbose=True,
    allow_delegation=False,
    llm=llm,
    tools=[HotelSearchTool()]
)

activity_agent = Agent(
    role="Activity Specialist",
    goal=(
        "Suggest the best activities and attractions for the selected destination."
    ),
    backstory=(
        "You are a tourism and entertainment expert. "
        "You recommend activities based on the travel style requested "
        "by the user such as nightlife, relaxation, adventure, culture or food."
    ),
    verbose=True,
    allow_delegation=False,
    llm=llm,
    tools=[ActivitySearchTool()]
)

# =========================
# TASKS
# =========================

destination_task = Task(
    description=(
        """
        The user wants help organizing a trip.

        USER PREFERENCES:
        - Budget: {budget}
        - Travel period: {period}
        - Preferred travel style: {style}
        - Age group: {age_group}
        - Departure city: {origin}
        - Departure date: {departure_date}
        - Return date: {return_date}

        Your job is to:
        1. Analyze the user profile
        2. Use the destination search tool
        3. Select the BEST destination
        4. Explain clearly WHY this destination is suitable
        5. Provide a concise destination summary

        IMPORTANT:
        - The user DOES NOT initially choose the destination
        - You must autonomously decide the destination
        - Consider budget compatibility carefully
        - Consider the travel style carefully
        """
    ),
    expected_output=(
        "A complete destination recommendation including:\n"
        "- selected city and country\n"
        "- motivation of the choice\n"
        "- compatibility with user preferences\n"
        "- short destination overview"
    ),
    agent=travel_planner_agent
)

flight_task = Task(
    description=(
        """
        Find flight options for the destination selected by the planner agent.

        You must:
        1. Analyze the selected destination
        2. Search available flights
        3. Prioritize solutions compatible with the user's budget
        4. Suggest the best available option

        USER DATA:
        - Departure city: {origin}
        - Departure date: {departure_date}
        - Return date: {return_date}
        - Budget: {budget}

        IMPORTANT:
        - Use the flight search tool
        - Focus on realistic travel options
        - Explain why the suggested flight is appropriate
        """
    ),
    expected_output=(
        "A flight recommendation including:\n"
        "- airline or flight type\n"
        "- estimated price\n"
        "- travel dates\n"
        "- explanation of why the option fits the budget"
    ),
    agent=flight_agent,
    context=[destination_task]
)

hotel_task = Task(
    description=(
        """
        Find accommodation solutions for the destination selected by the planner.

        You must:
        1. Analyze the selected destination
        2. Search hotels or accommodations
        3. Match the user's budget and travel style
        4. Recommend the best accommodation option

        USER DATA:
        - Check-in date: {departure_date}
        - Check-out date: {return_date}
        - Budget: {budget}
        - Travel style: {style}

        IMPORTANT:
        - Use the hotel search tool
        - Prefer coherent solutions with the user profile
        """
    ),
    expected_output=(
        "A hotel recommendation including:\n"
        "- hotel/accommodation name\n"
        "- estimated price\n"
        "- accommodation style\n"
        "- explanation of why it fits the user"
    ),
    agent=hotel_agent,
    context=[destination_task]
)

activity_task = Task(
    description=(
        """
        Suggest activities and attractions for the selected destination.

        You must:
        1. Analyze the destination
        2. Understand the user's travel style
        3. Recommend suitable activities

        USER DATA:
        - Travel style: {style}
        - Age group: {age_group}

        IMPORTANT:
        - Use the activity tool
        - Activities must match the user's interests
        """
    ),
    expected_output=(
        "A list of recommended activities including:\n"
        "- attraction/activity name\n"
        "- short explanation\n"
        "- compatibility with user interests"
    ),
    agent=activity_agent,
    context=[destination_task]
)

final_plan_task = Task(
    description=(
        """
        Create the FINAL COMPLETE TRAVEL PLAN.

        You must combine:
        - selected destination
        - flight recommendation
        - hotel recommendation
        - activities and attractions

        The final result must be:
        - clear
        - well organized
        - realistic
        - personalized

        Structure the final response professionally.
        """
    ),
    expected_output=(
        "A complete travel plan containing:\n"
        "1. Destination overview\n"
        "2. Flight information\n"
        "3. Hotel information\n"
        "4. Activities and attractions\n"
        "5. Final travel summary"
    ),
    agent=travel_planner_agent,
    context=[
        destination_task,
        flight_task,
        hotel_task,
        activity_task
    ]
)

# =========================
# CREW
# =========================

travel_crew = Crew(
    agents=[
        travel_planner_agent,
        flight_agent,
        hotel_agent,
        activity_agent
    ],
    tasks=[
        destination_task,
        flight_task,
        hotel_task,
        activity_task,
        final_plan_task
    ],
    process=Process.sequential,
    verbose=True
)