"""
Validates a day-plan against three hard constraints:
  1. Total cost <= budget
  2. Every place is open at the scheduled time
  3. Travel time between consecutive stops fits the schedule
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from math import radians, cos, sin, asin, sqrt

from validator.opening_hours import is_open
from config import WALKING_SPEED_KMH, AVG_TRAM_SPEED_KMH, WALK_MAX_KM, TRANSIT_WAIT_MIN


@dataclass
class ScheduledStop:
    place_id: str
    name: str
    arrival: datetime
    departure: datetime
    cost_pln: float
    lat: float
    lon: float
    opening_hours: str | None = None


@dataclass
class ValidationResult:
    ok: bool = True
    budget_ok: bool = True
    total_cost: float = 0.0
    budget_limit: float = 0.0
    hours_violations: list[str] = field(default_factory=list)
    travel_violations: list[str] = field(default_factory=list)
    unknown_places: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "ok": self.ok,
            "budget_ok": self.budget_ok,
            "total_cost": self.total_cost,
            "budget_limit": self.budget_limit,
            "hours_violations": self.hours_violations,
            "travel_violations": self.travel_violations,
            "unknown_places": self.unknown_places,
        }


def _haversine_km(lat1, lon1, lat2, lon2) -> float:
    R = 6371.0
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 2 * R * asin(sqrt(a))


def _travel_minutes(km: float) -> int:
    if km < WALK_MAX_KM:
        return int((km / WALKING_SPEED_KMH) * 60)
    return int((km / AVG_TRAM_SPEED_KMH) * 60) + TRANSIT_WAIT_MIN


def validate(stops: list[ScheduledStop], budget_pln: float, known_ids: set[str]) -> ValidationResult:
    result = ValidationResult(budget_limit=budget_pln)

    # 1. Unknown places
    for stop in stops:
        if stop.place_id not in known_ids:
            result.unknown_places.append(stop.name)

    # 2. Budget
    result.total_cost = sum(s.cost_pln for s in stops)
    if result.total_cost > budget_pln:
        result.budget_ok = False

    # 3. Opening hours
    for stop in stops:
        open_status = is_open(stop.opening_hours, stop.arrival)
        if open_status is False:
            result.hours_violations.append(
                f"{stop.name} closed at {stop.arrival.strftime('%H:%M')}"
            )

    # 4. Travel time between consecutive stops
    for i in range(len(stops) - 1):
        cur, nxt = stops[i], stops[i + 1]
        km = _haversine_km(cur.lat, cur.lon, nxt.lat, nxt.lon)
        needed_min = _travel_minutes(km)
        gap_min = int((nxt.arrival - cur.departure).total_seconds() / 60)
        if gap_min < needed_min:
            result.travel_violations.append(
                f"{cur.name} → {nxt.name}: need {needed_min} min, have {gap_min} min"
            )

    result.ok = (
        result.budget_ok
        and not result.hours_violations
        and not result.travel_violations
        and not result.unknown_places
    )
    return result
