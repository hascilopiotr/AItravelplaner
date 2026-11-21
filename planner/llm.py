"""
Calls the LLM to generate a (multi-day) trip plan from preferences + available places.
Returns the parsed plan dict or raises ValueError.
"""

import json
import anthropic
from config import ANTHROPIC_API_KEY, MODEL
from planner.prompts import build_system_prompt, build_user_prompt

_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

STOP_SCHEMA = {
    "type": "object",
    "properties": {
        "place_id": {"type": "string"},
        "name": {"type": "string"},
        "arrival": {"type": "string", "description": "HH:MM, 24h"},
        "departure": {"type": "string", "description": "HH:MM, 24h"},
        "cost": {"type": "number", "description": "per person, in the trip currency"},
        "reason": {"type": "string"},
    },
    "required": ["place_id", "name", "arrival", "departure", "cost", "reason"],
    "additionalProperties": False,
}

TRIP_SCHEMA = {
    "type": "object",
    "properties": {
        "trip_summary": {"type": "string"},
        "days": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "date": {"type": "string", "description": "YYYY-MM-DD"},
                    "summary": {"type": "string"},
                    "stops": {"type": "array", "items": STOP_SCHEMA},
                },
                "required": ["date", "summary", "stops"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["trip_summary", "days"],
    "additionalProperties": False,
}


def _slim(places: list[dict]) -> str:
    slim_places = [
        {
            "place_id": p["id"],
            "name": p["name"],
            "category": p["category"],
            "subcategory": p["subcategory"],
            "usually_free": not p["avg_cost_pln"],
            "duration_min": p["duration_min"],
            "opening_hours": p["opening_hours"],
            "address": p["address"],
            "lat": round(p["lat"], 5),
            "lon": round(p["lon"], 5),
            "area": p.get("area"),
            "km_from_centre": p.get("km_from_centre"),
        }
        for p in places
    ]
    return json.dumps(slim_places, ensure_ascii=False, separators=(",", ":"))


def generate_trip(prefs: dict, places: list[dict]) -> dict:
    """prefs needs: city, dates (list of ISO dates), start_time, end_time,
    budget (whole trip, in `currency`), currency, interests, notes."""
    user_msg = build_user_prompt(prefs, _slim(places))

    # Streaming: an 11-day plan is a long response; streaming avoids HTTP timeouts.
    with _client.messages.stream(
        model=MODEL,
        max_tokens=32000,
        system=build_system_prompt(prefs["city"], prefs["currency"]),
        messages=[{"role": "user", "content": user_msg}],
        # Structured outputs: the API guarantees the reply is JSON matching
        # TRIP_SCHEMA, so the model can't wrap it in prose or markdown.
        output_config={"format": {"type": "json_schema", "schema": TRIP_SCHEMA}},
    ) as stream:
        message = stream.get_final_message()

    if message.stop_reason == "refusal":
        raise ValueError("The model declined to produce a plan for this request.")
    if message.stop_reason == "max_tokens":
        raise ValueError("The plan was cut off (max_tokens reached). Try fewer days.")

    raw = next((b.text for b in message.content if b.type == "text"), "")
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM returned invalid JSON: {e}\nRaw output:\n{raw[:300]}") from e
