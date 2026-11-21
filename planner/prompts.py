from datetime import date

from config import (WALKING_SPEED_KMH, AVG_TRAM_SPEED_KMH, WALK_MAX_KM, TRANSIT_WAIT_MIN,
                    AREA_GRID_KM, PACES, DEFAULT_PACE)
from data.weather import weather_text
from planner.instructions import load_instructions

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

_walk_min_per_km = 60 / WALKING_SPEED_KMH
_transit_min_per_km = 60 / AVG_TRAM_SPEED_KMH


def build_system_prompt(city: str, currency: str, pace: str = DEFAULT_PACE) -> str:
    pc = PACES.get(pace, PACES[DEFAULT_PACE])
    lo, hi = pc["stops"]
    base = f"""\
You are a local tour guide for {city}. Your job is to build a sightseeing plan \
for a visitor — one plan per day of their trip — based on their preferences.

You have access to a curated list of real places (attractions, restaurants, \
parks, culture spots) sourced from OpenStreetMap. You MUST only use places \
from the provided list — do not invent names, and copy place_id exactly.

Output: trip_summary (1-2 sentences about the whole trip) and one entry in \
`days` per requested date, in date order, with `date` (YYYY-MM-DD exactly as \
requested), `summary` (1 sentence: the day's theme/area) and `stops`. For each \
stop give: place_id, name, arrival and departure (HH:MM, 24h), cost, and reason \
(one sentence on why it fits the visitor).

Prices — all money is in {currency}:
- `cost` is your realistic estimate of what ONE visitor spends at that stop, in \
{currency}, based on typical prices in {city} (entry ticket, a meal, a coffee...).
- Places with usually_free=true (parks, monuments, landmarks) cost 0 unless you \
know they charge entry.

Areas — keep each day's route compact:
- Every place has `area`: a {AREA_GRID_KM} km grid cell relative to the city centre, \
e.g. "centre", "1N", "2S 1E" (2 cells south, 1 cell east). Neighbouring areas differ \
by one step. `km_from_centre` is the distance to the centre.
- Keep each day inside one area plus its direct neighbours, and move through them \
in one direction (no back-and-forth). Use different areas on different days.

Pace — the visitor chose "{pace}": {pc['note']}.
- Plan {lo}–{hi} stops per day (meals count as stops).
- Leave at least {pc['buffer']} minutes of buffer between stops on top of travel time.

Travel time rule — consecutive stops are checked against this rule:
- Compute the straight-line distance between consecutive stops from their lat/lon.
- Under {WALK_MAX_KM} km the visitor walks: {_walk_min_per_km:.1f} min per km \
({WALKING_SPEED_KMH} km/h).
- From {WALK_MAX_KM} km up they take public transport: {_transit_min_per_km:.1f} min \
per km ({AVG_TRAM_SPEED_KMH:.0f} km/h) plus {TRANSIT_WAIT_MIN} min waiting.
- Between departure and the next arrival, allow that travel time PLUS the pace's \
buffer ({pc['buffer']} min).

Other hard constraints, all checked automatically:
- The sum of `cost` over ALL days must not exceed the total trip budget.
- Every stop must be open at its arrival time on that day's weekday, according \
to opening_hours.
- Each day must fit between the daily start and end time.
- No place may appear on more than one day.
"""
    guidance = load_instructions(city)
    if guidance:
        base += "\n\n# Planning guidance\n\n" + guidance + "\n"
    return base


def build_user_prompt(prefs: dict, places_json: str) -> str:
    dates = prefs["dates"]
    weather = prefs.get("weather") or {}
    day_lines = "\n".join(
        f"  - {d} ({DAYS[date.fromisoformat(d).weekday()]}) — weather: "
        f"{weather_text(weather.get(d), emoji=False)}"
        for d in dates
    )
    return f"""\
Visitor preferences:
- City: {prefs['city']}
- Trip days ({len(dates)}):
{day_lines}
- Daily time window: {prefs['start_time']}–{prefs['end_time']}
- Pace: {prefs.get('pace', DEFAULT_PACE)}
- Total budget for the whole trip: {prefs['budget']:g} {prefs['currency']} (per person)
- Interests: {', '.join(prefs['interests'])}
- Notes: {prefs.get('notes') or 'none'}

Available places (JSON array):
{places_json}

Build the best possible plan for every listed day.\
"""
