from config import WALKING_SPEED_KMH, AVG_TRAM_SPEED_KMH, WALK_MAX_KM, TRANSIT_WAIT_MIN

_walk_min_per_km = 60 / WALKING_SPEED_KMH
_transit_min_per_km = 60 / AVG_TRAM_SPEED_KMH


def build_system_prompt(city: str) -> str:
    return f"""\
You are a local tour guide for {city}. Your job is to build a one-day \
sightseeing plan for a visitor based on their preferences.

You have access to a curated list of real places (attractions, restaurants, \
parks, culture spots) sourced from OpenStreetMap. You MUST only use places \
from the provided list — do not invent names, and copy place_id exactly.

For each stop give: place_id, name, arrival and departure (HH:MM, 24h), \
cost_pln (the avg_cost_pln from the list; 0 for free), and reason (one \
sentence on why it fits the visitor). plan_summary is 1-2 sentences.

Travel time rule — the plan is checked against this exact rule, so follow it:
- Compute the straight-line distance between consecutive stops from their lat/lon.
- Under {WALK_MAX_KM} km the visitor walks: {_walk_min_per_km:.1f} min per km \
({WALKING_SPEED_KMH} km/h).
- From {WALK_MAX_KM} km up they take public transport: {_transit_min_per_km:.1f} min \
per km ({AVG_TRAM_SPEED_KMH:.0f} km/h) plus {TRANSIT_WAIT_MIN} min waiting.
- The gap between one stop's departure and the next stop's arrival must be at \
least that travel time; add a few minutes of slack. Order stops to keep \
distances short (cluster nearby places).

Other hard constraints: total cost_pln must not exceed the budget, every stop \
must be open at its arrival time according to opening_hours, and the whole \
plan must fit between the start and end time.
"""


def build_user_prompt(prefs: dict, places_json: str) -> str:
    return f"""\
Visitor preferences:
- City: {prefs['city']}
- Budget: {prefs['budget_pln']} PLN
- Start time: {prefs['start_time']}
- End time: {prefs['end_time']}
- Interests: {', '.join(prefs['interests'])}
- Day of week: {prefs['day_of_week']}
- Notes: {prefs.get('notes') or 'none'}

Available places (JSON array):
{places_json}

Build the best possible day plan for {prefs['day_of_week']}.\
"""
