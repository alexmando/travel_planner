from __future__ import annotations

from pathlib import Path
from typing import Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class ActivitySearchInput(BaseModel):
    destination: str = Field(..., description="Destination city")
    style: str = Field(default="mixed", description="nightlife, relax, culture, adventure, food, nature, family, mixed")
    age_group: str = Field(default="any", description="18-25, 26-35, 36-50, 50+, any")


ACTIVITIES = {
    "barcelona": [
        {"name": "Sagrada Familia visit", "tags": ["culture", "art"]},
        {"name": "Gothic Quarter walking tour", "tags": ["culture", "history"]},
        {"name": "Beach afternoon at Barceloneta", "tags": ["beach", "relax"]},
        {"name": "Nightlife in El Born", "tags": ["nightlife"]},
    ],
    "lisbon": [
        {"name": "Tram 28 tour", "tags": ["culture", "scenic"]},
        {"name": "Fado night", "tags": ["culture", "relax"]},
        {"name": "Miradouros viewpoints", "tags": ["relax", "scenic"]},
        {"name": "Pastel de nata tasting", "tags": ["food"]},
    ],
    "prague": [
        {"name": "Old Town walking tour", "tags": ["culture", "history"]},
        {"name": "Prague Castle", "tags": ["culture", "history"]},
        {"name": "Vltava river cruise", "tags": ["relax", "scenic"]},
        {"name": "Beer tasting evening", "tags": ["nightlife", "food"]},
    ],
    "amsterdam": [
        {"name": "Canal boat tour", "tags": ["culture", "scenic"]},
        {"name": "Van Gogh Museum", "tags": ["culture", "art"]},
        {"name": "Cycling around the city", "tags": ["outdoor", "nature"]},
        {"name": "Nightlife in Leidseplein", "tags": ["nightlife"]},
    ],
    "new york": [
        {"name": "Broadway show", "tags": ["culture", "nightlife"]},
        {"name": "Central Park day", "tags": ["relax", "nature"]},
        {"name": "Museum Mile", "tags": ["culture"]},
        {"name": "Shopping in Manhattan", "tags": ["shopping", "citylife"]},
    ],
    "tokyo": [
        {"name": "Shibuya nightlife", "tags": ["nightlife"]},
        {"name": "Asakusa temple area", "tags": ["culture"]},
        {"name": "Street food tour", "tags": ["food"]},
        {"name": "Akihabara tech walk", "tags": ["tech", "citylife"]},
    ],
    "bangkok": [
        {"name": "Temple hopping", "tags": ["culture"]},
        {"name": "Street food tour", "tags": ["food"]},
        {"name": "Rooftop nightlife", "tags": ["nightlife"]},
        {"name": "Floating market visit", "tags": ["culture", "scenic"]},
    ],
    "bali": [
        {"name": "Beach relaxation", "tags": ["relax", "beach"]},
        {"name": "Yoga retreat", "tags": ["relax", "wellness"]},
        {"name": "Rice terraces hike", "tags": ["nature", "adventure"]},
        {"name": "Temple visit", "tags": ["culture"]},
    ],
    "cape town": [
        {"name": "Table Mountain hike", "tags": ["nature", "adventure"]},
        {"name": "Cape Peninsula drive", "tags": ["scenic", "outdoor"]},
        {"name": "Wine tasting", "tags": ["food", "relax"]},
        {"name": "Beach time", "tags": ["beach", "relax"]},
    ],
    "sydney": [
        {"name": "Opera House visit", "tags": ["culture"]},
        {"name": "Bondi Beach", "tags": ["beach", "relax"]},
        {"name": "Harbour walk", "tags": ["scenic", "outdoor"]},
        {"name": "City nightlife", "tags": ["nightlife"]},
    ],
    "marrakech": [
        {"name": "Jemaa el-Fnaa evening", "tags": ["culture", "nightlife"]},
        {"name": "Souk shopping", "tags": ["shopping", "culture"]},
        {"name": "Riad relaxation", "tags": ["relax"]},
        {"name": "Desert excursion", "tags": ["adventure", "nature"]},
    ],
    "rio de janeiro": [
        {"name": "Copacabana beach", "tags": ["beach", "relax"]},
        {"name": "Christ the Redeemer", "tags": ["culture"]},
        {"name": "Samba nightlife", "tags": ["nightlife"]},
        {"name": "Sugarloaf cable car", "tags": ["scenic"]},
    ],
}


class ActivitySearchTool(BaseTool):
    name: str = "activity_search_tool"
    description: str = "Suggest activities and attractions for the selected destination."
    args_schema: Type[BaseModel] = ActivitySearchInput

    def _run(self, destination: str, style: str = "mixed", age_group: str = "any") -> str:
        destination_key = destination.lower().strip()
        style = style.lower().strip()
        age_group = age_group.lower().strip()

        options = ACTIVITIES.get(
            destination_key,
            [
                {"name": "City walking tour", "tags": ["culture"]},
                {"name": "Local food experience", "tags": ["food"]},
                {"name": "Main attraction visit", "tags": ["relax", "culture"]},
            ],
        )

        filtered = []
        for item in options:
            tags = [t.lower() for t in item["tags"]]
            if style == "mixed" or style == "any" or style in tags:
                filtered.append(item)

        if not filtered:
            filtered = options

        lines = [f"Suggested activities for {destination.title()}:"]
        if age_group != "any":
            lines.append(f"Target age group: {age_group}")

        for item in filtered[:5]:
            lines.append(f"- {item['name']} | tags: {', '.join(item['tags'])}")

        return "\n".join(lines)