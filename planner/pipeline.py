"""
Orchestrates: fetch places -> call LLM -> validate -> return result.
"""

from __future__ import annotations
import json
from datetime import datetime, date

from config import DEFAULT_CITY, INTEREST_SUBCATEGORIES

from data.db import get_all_places, get_place_by_id
from planner.llm import generate_trip
from planner.prompts import DAYS
from validator.checker import validate, ScheduledStop

MAX_TRIP_DAYS = 11


def run_trip(prefs: dict) -> dict:
    """
    prefs = {
        city: "Katowice",                    # optional, defaults to DEFAULT_CITY
        dates: ["2026-11-28", ...],          # ISO dates, 1..MAX_TRIP_DAYS
        budget_pln: float,                   # total for the whole trip
        start_time: "09:00", end_time: "20:00",   # same every day
        interests: ["museums", "food"],
        notes: "...",
    }
    Returns {
        plan: dict,                  # raw LLM output (trip_summary, days)
        days: [{date, day_of_week, plan: {summary, stops}, validation}],
        trip_validation: {ok, budget_ok, total_cost, budget_limit,
                          repeated_places, missing_days},
    }
    """
    dates = sorted(prefs["dates"])
    if not 1 <= len(dates) <= MAX_TRIP_DAYS:
        raise ValueError(f"A trip must be 1-{MAX_TRIP_DAYS} days long.")
    prefs = {**prefs, "dates": dates, "city": prefs.get("city") or DEFAULT_CITY}
    city = prefs["city"]

    all_places = get_all_places(city)
    if not all_places:
        raise ValueError(f"No places loaded for {city}. Run: python -m data.seed {city}")
    known_ids = {p["id"] for p in all_places}

    # Longer trips need more unique places to choose from.
    per_sub = min(40 + 8 * len(dates), 120)
    candidates = select_candidates(all_places, prefs.get("interests", []), per_sub)
    plan = generate_trip(prefs, candidates)

    by_date = {d.get("date"): d for d in plan.get("days", [])}
    days, missing, seen, repeated = [], [], {}, []
    for iso in dates:
        day_plan = by_date.get(iso)
        if day_plan is None:
            missing.append(iso)
            day_plan = {"summary": "", "stops": []}
        # Per-day checks; the budget is checked for the whole trip below.
        stops = _stops_from_plan(day_plan, iso, city)
        v = validate(stops, float("inf"), known_ids).as_dict()
        v["budget_limit"] = None
        window = _window_violations(day_plan, prefs["start_time"], prefs["end_time"])
        v["hours_violations"] += window
        v["ok"] = v["ok"] and not window

        for s in day_plan.get("stops", []):
            pid = s.get("place_id")
            if pid in seen and seen[pid] != iso:
                repeated.append(f"{s.get('name', pid)} ({seen[pid]} and {iso})")
            seen.setdefault(pid, iso)

        days.append({
            "date": iso,
            "day_of_week": DAYS[date.fromisoformat(iso).weekday()],
            "plan": day_plan,
            "validation": v,
        })

    total = sum(d["validation"]["total_cost"] for d in days)
    budget_ok = total <= prefs["budget_pln"]
    trip_validation = {
        "ok": budget_ok and not repeated and not missing and all(d["validation"]["ok"] for d in days),
        "budget_ok": budget_ok,
        "total_cost": total,
        "budget_limit": prefs["budget_pln"],
        "repeated_places": repeated,
        "missing_days": missing,
    }
    return {"plan": plan, "days": days, "trip_validation": trip_validation}


def run(prefs: dict) -> dict:
    """
    Single-day wrapper (used by the CLI and tests/evaluate.py).
    prefs = {city?, budget_pln, start_time, end_time, interests,
             visit_date: "2026-11-22", day_of_week, notes}
    Returns {plan: {plan_summary, stops}, validation: {...}} like before.
    """
    trip = run_trip({**prefs, "dates": [prefs["visit_date"]]})
    day = trip["days"][0]
    tv = trip["trip_validation"]
    validation = {
        **day["validation"],
        "budget_ok": tv["budget_ok"],
        "budget_limit": tv["budget_limit"],
        "unknown_places": day["validation"]["unknown_places"],
    }
    validation["ok"] = day["validation"]["ok"] and tv["budget_ok"] and not tv["missing_days"]
    return {
        "plan": {"plan_summary": day["plan"].get("summary") or trip["plan"].get("trip_summary", ""),
                 "stops": day["plan"].get("stops", [])},
        "validation": validation,
    }


def _window_violations(day_plan: dict, start: str, end: str) -> list[str]:
    """Stops that start before the daily start time or end after the end time."""
    out = []
    for s in day_plan.get("stops", []):
        if s.get("arrival", "99:99") < start:
            out.append(f"{s.get('name')} starts at {s['arrival']}, before the day starts ({start})")
        if s.get("departure", "00:00") > end:
            out.append(f"{s.get('name')} ends at {s['departure']}, after the day ends ({end})")
    return out


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
    Narrow the full DB (thousands of places) to the places relevant to the
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
