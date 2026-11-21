from datetime import date

from config import WALKING_SPEED_KMH, AVG_TRAM_SPEED_KMH, WALK_MAX_KM, TRANSIT_WAIT_MIN
from planner.instructions import load_instructions

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

_walk_min_per_km = 60 / WALKING_SPEED_KMH
_transit_min_per_km = 60 / AVG_TRAM_SPEED_KMH


def build_system_prompt(city: str) -> str:
    base = f"""\
You are a local tour guide for {city}. Your job is to build a sightseeing plan \
for a visitor — one plan per day of their trip — based on their preferences.

You have access to a curated list of real places (attractions, restaurants, \
parks, culture spots) sourced from OpenStreetMap. You MUST only use places \
from the provided list — do not invent names, and copy place_id exactly.

Output: trip_summary (1-2 sentences about the whole trip) and one entry in \
`days` per requested date, in date order, with `date` (YYYY-MM-DD exactly as \
requested), `summary` (1 sentence: the day's theme/area) and `stops`. For each \
stop give: place_id, name, arrival and departure (HH:MM, 24h), cost_pln (the \
avg_cost_pln from the list; 0 for free), and reason (one sentence on why it \
fits the visitor).

Travel time rule — the plan is checked against this exact rule, so follow it:
- Compute the straight-line distance between consecutive stops from their lat/lon.
- Under {WALK_MAX_KM} km the visitor walks: {_walk_min_per_km:.1f} min per km \
({WALKING_SPEED_KMH} km/h).
- From {WALK_MAX_KM} km up they take public transport: {_transit_min_per_km:.1f} min \
per km ({AVG_TRAM_SPEED_KMH:.0f} km/h) plus {TRANSIT_WAIT_MIN} min waiting.
- The gap between one stop's departure and the next stop's arrival must be at \
least that travel time; add a few minutes of slack. Order stops to keep \
distances short (cluster nearby places).

Other hard constraints, all checked automatically:
- The sum of cost_pln over ALL days must not exceed the total trip budget.
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
    day_lines = "\n".join(
        f"  - {d} ({DAYS[date.fromisoformat(d).weekday()]})" for d in dates
    )
    return f"""\
Visitor preferences:
- City: {prefs['city']}
- Trip days ({len(dates)}):
{day_lines}
- Daily time window: {prefs['start_time']}–{prefs['end_time']}
- Total budget for the whole trip: {prefs['budget_pln']} PLN
- Interests: {', '.join(prefs['interests'])}
- Notes: {prefs.get('notes') or 'none'}

Available places (JSON array):
{places_json}

Build the best possible plan for every listed day.\
"""
