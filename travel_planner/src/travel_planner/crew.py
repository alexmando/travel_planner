import os
from dotenv import load_dotenv
import litellm
from crewai.project import CrewBase, agent, crew, task
from travel_planner import AttractionSearchTool

load_dotenv()

original_completion = litellm.completion

def patched_completion(*args, **kwargs):
    if 'messages' in kwargs:
        for msg in kwargs['messages']:
            if 'cache_breakpoint' in msg:
                del msg['cache_breakpoint']
    return original_completion(*args, **kwargs)

litellm.completion = patched_completion

from crewai import Agent, Crew, Process, Task, LLM
from travel_planner.tools import (
    FlightSearchTool,
    HotelSearchTool,
    AttractionSearchTool,
)

@CrewBase
class TravelPlanner:
    llm = LLM(
        model=os.getenv("MODEL"),
        api_key=os.getenv("GROQ_API_KEY"),
        max_retries=3,
    )

    @agent
    def travel_planner(self) -> Agent:
        return Agent(config=self.agents_config["travel_planner"],
            llm=self.llm,
            max_iter=3,
            rate_limit=3,
            verbose=True)

    @agent
    def flight_agent(self) -> Agent:
        return Agent(config=self.agents_config["flight_agent"],
            llm=self.llm,
            tools=[FlightSearchTool()],
            max_iter=3,
            rate_limit=3,
            verbose=True,)

    @agent
    def hotel_agent(self) -> Agent:
        return Agent(config=self.agents_config["hotel_agent"],
            tools=[HotelSearchTool()],
            llm=self.llm,
            max_iter=3,
            rate_limit=3,
            verbose=True,)

    @agent
    def activity_agent(self) -> Agent:
        return Agent(config=self.agents_config["activity_agent"],
            verbose=False,
            max_iter=3,
            allow_delegation=False,
            rate_limit=3,
            llm=self.llm,
            tools=[AttractionSearchTool()])

    @task
    def destination_task(self) -> Task:
        return Task(config=self.tasks_config["destination_task"])

    @task
    def search_flights_task(self) -> Task:
        return Task(config=self.tasks_config["flight_task"])

    @task
    def search_hotels_task(self) -> Task:
        return Task(config=self.tasks_config["hotel_task"])

    @task
    def search_activity_task(self) -> Task:
        return Task(config=self.tasks_config["activity_task"])

    @task
    def final_plan_task_task(self) -> Task:
        return Task(config=self.tasks_config["final_plan_task"])

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=[
                self.travel_planner(),
                self.flight_agent(),
                self.hotel_agent(),
                self.activity_agent(),
            ],
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
            max_rpm=5,
        )