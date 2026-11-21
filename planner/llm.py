"""
Calls the LLM to generate a day-plan from preferences + available places.
Returns a parsed plan dict or raises on bad JSON.
"""

import json
import anthropic
from config import ANTHROPIC_API_KEY, MODEL
from planner.prompts import SYSTEM_PROMPT, build_user_prompt

_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "plan_summary": {"type": "string"},
        "stops": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "place_id": {"type": "string"},
                    "name": {"type": "string"},
                    "arrival": {"type": "string", "description": "HH:MM, 24h"},
                    "departure": {"type": "string", "description": "HH:MM, 24h"},
                    "cost_pln": {"type": "number"},
                    "reason": {"type": "string"},
                },
                "required": ["place_id", "name", "arrival", "departure", "cost_pln", "reason"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["plan_summary", "stops"],
    "additionalProperties": False,
}


def generate_plan(prefs: dict, places: list[dict]) -> dict:
    slim_places = [
        {
            "place_id": p["id"],
            "name": p["name"],
            "category": p["category"],
            "subcategory": p["subcategory"],
            "avg_cost_pln": p["avg_cost_pln"],
            "duration_min": p["duration_min"],
            "opening_hours": p["opening_hours"],
            "address": p["address"],
        }
        for p in places
    ]

    places_json = json.dumps(slim_places, ensure_ascii=False, separators=(",", ":"))
    user_msg = build_user_prompt(prefs, places_json)

    message = _client.messages.create(
        model=MODEL,
        max_tokens=16000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
        # Structured outputs: the API guarantees the reply is JSON matching
        # PLAN_SCHEMA, so the model can't wrap it in prose or markdown.
        output_config={"format": {"type": "json_schema", "schema": PLAN_SCHEMA}},
    )

    if message.stop_reason == "refusal":
        raise ValueError("The model declined to produce a plan for this request.")
    if message.stop_reason == "max_tokens":
        raise ValueError("The plan was cut off (max_tokens reached). Try a shorter day or fewer interests.")

    raw = next((b.text for b in message.content if b.type == "text"), "")
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM returned invalid JSON: {e}\nRaw output:\n{raw[:300]}") from e
