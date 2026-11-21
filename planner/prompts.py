SYSTEM_PROMPT = """\
You are a local tour guide for Katowice, Poland. Your job is to build a \
one-day sightseeing plan for a visitor based on their preferences.

You have access to a curated list of real places (attractions, restaurants, \
parks, culture spots) sourced from OpenStreetMap. You MUST only use places \
from the provided list — do not invent names.

For each stop include:
  - place_id  (from the list)
  - name
  - arrival   (HH:MM, 24h)
  - departure (HH:MM, 24h)
  - cost_pln  (use the avg_cost from the list; 0 for free)
  - reason    (one sentence why this fits the visitor)

Return ONLY valid JSON — no prose, no markdown fences — in this exact shape:
{
  "plan_summary": "...",
  "stops": [
    {
      "place_id": "...",
      "name": "...",
      "arrival": "HH:MM",
      "departure": "HH:MM",
      "cost_pln": 0.0,
      "reason": "..."
    }
  ]
}
"""

def build_user_prompt(prefs: dict, places_json: str) -> str:
    return f"""\
Visitor preferences:
- Budget: {prefs['budget_pln']} PLN
- Start time: {prefs['start_time']}
- End time: {prefs['end_time']}
- Interests: {', '.join(prefs['interests'])}
- Day of week: {prefs['day_of_week']}
- Notes: {prefs.get('notes', 'none')}

Available places (JSON array):
{places_json}

Build the best possible day plan. Stay within budget. \
Respect realistic walking/tram travel times between stops. \
Check that places are likely open on {prefs['day_of_week']}.\
"""
