"""
Swap one stop of a generated trip for a nearby alternative — no AI call.
"""

from __future__ import annotations

import copy
from datetime import datetime, date

from data.db import get_all_places, get_place_by_id
from planner.pipeline import _richness, evaluate_trip
from validator.checker import _haversine_km
from validator.opening_hours import is_open

MAX_SWAP_KM = 1.5

# Places are interchangeable within these groups.
_GROUPS = {"food": "food", "attraction": "sights", "culture": "sights",
           "nature": "nature", "shopping": "shopping"}


def _group(place: dict) -> str:
    return _GROUPS.get(place.get("category"), place.get("category"))


def _used_ids(result: dict) -> set[str]:
    return {s.get("place_id") for d in result["days"] for s in d["plan"].get("stops", [])}


def swap_options(city: str, result: dict, day_iso: str, idx: int, k: int = 4,
                 places: list[dict] | None = None) -> list[dict]:
    """
    Up to k alternatives for stop `idx` on `day_iso`: same kind of place, within
    MAX_SWAP_KM, open (or hours unknown) at the stop's arrival time, not used
    anywhere else in the trip. Each option gets `distance_km` and `open_status`.
    """
    day = next(d for d in result["days"] if d["date"] == day_iso)
    stop = day["plan"]["stops"][idx]
    current = get_place_by_id(city, stop["place_id"])
    if current is None:
        return []

    d = date.fromisoformat(day_iso)
    h, m = stop["arrival"].split(":")
    arrival = datetime(d.year, d.month, d.day, int(h), int(m))
    used = _used_ids(result)
    group = _group(current)

    options = []
    for p in places if places is not None else get_all_places(city):
        if p["id"] in used or _group(p) != group:
            continue
        km = _haversine_km(current["lat"], current["lon"], p["lat"], p["lon"])
        if km > MAX_SWAP_KM:
            continue
        status = is_open(p["opening_hours"], arrival)
        if status is False:
            continue
        options.append({**p, "distance_km": round(km, 2), "open_status": status})

    # Prefer the same subcategory, known-open places, rich entries, then distance.
    options.sort(key=lambda p: (p["subcategory"] != current["subcategory"],
                                p["open_status"] is not True,
                                -_richness(p), p["distance_km"]))
    return options[:k]


def apply_swap(result: dict, day_iso: str, idx: int, place: dict) -> dict:
    """Return a new result with stop `idx` on `day_iso` replaced by `place`
    (same time slot), re-validated."""
    new = copy.deepcopy(result)
    day = next(d for d in new["plan"]["days"] if d.get("date") == day_iso)
    old = day["stops"][idx]
    day["stops"][idx] = {
        "place_id": place["id"],
        "name": place["name"],
        "arrival": old["arrival"],
        "departure": old["departure"],
        # Free places stay free; otherwise keep the AI's price estimate for the slot.
        "cost": 0.0 if not place.get("avg_cost_pln") else float(old.get("cost", 0) or 0),
        "reason": f"Swapped in by you (instead of {old.get('name')}).",
    }
    return evaluate_trip(new["prefs"], new["plan"])
