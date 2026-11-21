"""
Calls the LLM to generate a day-plan from preferences + available places.
Returns a parsed plan dict or raises on bad JSON.
"""

import json
import anthropic
from config import ANTHROPIC_API_KEY, MODEL
from planner.prompts import SYSTEM_PROMPT, build_user_prompt

_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


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
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
    )

    raw = message.content[0].text.strip()
    # Strip accidental markdown fences
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    try:
        return json.loads(raw.strip())
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM returned invalid JSON: {e}\nRaw output:\n{raw[:300]}") from e
