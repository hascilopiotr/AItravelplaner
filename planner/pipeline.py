"""
Orchestrates: fetch places -> call LLM -> validate -> return result.
"""

from __future__ import annotations
import json
from datetime import datetime, date

from config import DEFAULT_CITY, INTEREST_SUBCATEGORIES

from data.db import get_all_places, get_place_by_id
from planner.llm import generate_plan
from validator.checker import validate, ScheduledStop, ValidationResult


def run(prefs: dict) -> dict:
    """
    prefs = {
        city: "Katowice",           # optional, defaults to DEFAULT_CITY
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
    prefs = {**prefs, "city": prefs.get("city") or DEFAULT_CITY}
    city = prefs["city"]
    all_places = get_all_places(city)
    if not all_places:
        raise ValueError(f"No places loaded for {city}. Run: python -m data.seed {city}")
    known_ids = {p["id"] for p in all_places}

    candidates = select_candidates(all_places, prefs.get("interests", []))
    plan = generate_plan(prefs, candidates)

    stops = _stops_from_plan(plan, prefs["visit_date"], city)
    result: ValidationResult = validate(stops, prefs["budget_pln"], known_ids)

    return {
        "plan": plan,
        "validation": result.as_dict(),
    }


# Always offer somewhere to eat, whatever the interests.
_ALWAYS_INCLUDE = {"restaurant", "cafe"}


def _richness(place: dict) -> int:
    """Prefer well-documented places: notable ones and those with known hours."""
    tags = json.loads(place.get("tags") or "{}")
    score = 0
    if "wikipedia" in tags or "wikidata" in tags:
        score += 3
    if place.get("opening_hours"):
        score += 2
    if place.get("description"):
        score += 1
    if place.get("address"):
        score += 1
    return score


def select_candidates(places: list[dict], interests: list[str], per_subcategory: int = 40) -> list[dict]:
    """
    Narrow the full DB (~1600 places, ~110k tokens) to the places relevant to the
    visitor's interests, keeping the richest `per_subcategory` of each kind.
    Unknown interests fall back to every subcategory.
    """
    wanted: set[str] = set()
    for interest in interests:
        wanted.update(INTEREST_SUBCATEGORIES.get(interest.strip().lower(), []))
    if not wanted:
        wanted = {p["subcategory"] for p in places}
    wanted |= _ALWAYS_INCLUDE

    by_sub: dict[str, list[dict]] = {}
    for p in places:
        if p["subcategory"] in wanted:
            by_sub.setdefault(p["subcategory"], []).append(p)

    selected = []
    for group in by_sub.values():
        group.sort(key=_richness, reverse=True)
        selected.extend(group[:per_subcategory])
    return selected


def _stops_from_plan(plan: dict, visit_date: str, city: str) -> list[ScheduledStop]:
    stops = []
    d = date.fromisoformat(visit_date)

    def parse_dt(t: str) -> datetime:
        h, m = t.split(":")
        return datetime(d.year, d.month, d.day, int(h), int(m))

    for s in plan.get("stops", []):
        db_place = get_place_by_id(city, s["place_id"])

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
