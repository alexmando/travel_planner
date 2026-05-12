from __future__ import annotations

import json
from pathlib import Path
from typing import Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


DATA_PATH = Path(__file__).resolve().parents[1] / "knowledge" / "destinations.json"


class DestinationSearchInput(BaseModel):
    budget: str = Field(..., description="low, medium, high")
    style: str = Field(..., description="nightlife, relax, culture, adventure, family, food, nature, mixed")
    period: str = Field(default="any", description="season or month, e.g. summer, winter, spring, autumn")
    age_group: str = Field(default="any", description="18-25, 26-35, 36-50, 50+, or any")


class DestinationSearchTool(BaseTool):
    name: str = "destination_search_tool"
    description: str = (
        "Select the best destination from the local dataset based on budget, style, period and age group."
    )
    args_schema: Type[BaseModel] = DestinationSearchInput

    def _run(self, budget: str, style: str, period: str = "any", age_group: str = "any") -> str:
        if not DATA_PATH.exists():
            return "ERROR: destinations.json not found."

        with open(DATA_PATH, "r", encoding="utf-8") as f:
            destinations = json.load(f)

        budget = budget.lower().strip()
        style = style.lower().strip()
        period = period.lower().strip()
        age_group = age_group.lower().strip()

        budget_rank = {"low": 1, "medium": 2, "high": 3}

        ranked: list[tuple[int, dict]] = []

        for d in destinations:
            score = 0

            dest_budget = str(d.get("budget", "")).lower()
            if budget_rank.get(dest_budget, 0) <= budget_rank.get(budget, 0):
                score += 3

            styles = [s.lower() for s in d.get("styles", [])]
            if style == "mixed":
                score += 2
            elif style in styles:
                score += 4

            best_period = [p.lower() for p in d.get("best_period", [])]
            if period == "any" or "all year" in best_period or period in best_period:
                score += 2

            best_for_age = [a.lower() for a in d.get("best_for_age", [])]
            if age_group == "any" or age_group in best_for_age:
                score += 1

            ranked.append((score, d))

        ranked.sort(key=lambda x: x[0], reverse=True)
        top = ranked[:5]

        lines = ["Top destination matches:"]
        for score, d in top:
            lines.append(
                f"- {d['city']}, {d['country']} ({d['continent']}) | budget={d['budget']} | "
                f"styles={', '.join(d.get('styles', []))} | score={score}"
            )

        best = top[0][1]
        lines.append("")
        lines.append(f"Best candidate: {best['city']}, {best['country']}")
        lines.append(f"Why: {best.get('description', 'No description available.')}")

        return "\n".join(lines)