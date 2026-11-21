"""
Orchestrates: fetch places -> call LLM -> validate -> return result.
"""

from __future__ import annotations
from datetime import datetime, date

from data.db import get_all_places, get_place_by_id
from planner.llm import generate_plan
from validator.checker import validate, ScheduledStop, ValidationResult


def run(prefs: dict) -> dict:
    """
    prefs = {
        budget_pln: float,
        start_time: "09:00",
        end_time: "20:00",
        interests: ["museums", "food"],
        day_of_week: "Saturday",
        visit_date: "2026-11-22",   # ISO date string
        notes: "..."
    }
    Returns {
        plan: dict,          # raw LLM output
        validation: dict,    # ValidationResult.as_dict()
    }
    """
    all_places = get_all_places()
    known_ids = {p["id"] for p in all_places}

    plan = generate_plan(prefs, all_places)

    stops = _stops_from_plan(plan, prefs["visit_date"])
    result: ValidationResult = validate(stops, prefs["budget_pln"], known_ids)

    return {
        "plan": plan,
        "validation": result.as_dict(),
    }


def _stops_from_plan(plan: dict, visit_date: str) -> list[ScheduledStop]:
    stops = []
    d = date.fromisoformat(visit_date)

    def parse_dt(t: str) -> datetime:
        h, m = t.split(":")
        return datetime(d.year, d.month, d.day, int(h), int(m))

    for s in plan.get("stops", []):
        db_place = get_place_by_id(s["place_id"])

        stops.append(ScheduledStop(
            place_id=s["place_id"],
            name=s["name"],
            arrival=parse_dt(s["arrival"]),
            departure=parse_dt(s["departure"]),
            cost_pln=float(s.get("cost_pln", 0)),
            lat=db_place["lat"] if db_place else 0.0,
            lon=db_place["lon"] if db_place else 0.0,
            opening_hours=db_place["opening_hours"] if db_place else None,
        ))

    return stops
