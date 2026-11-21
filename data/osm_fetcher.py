"""
Fetches attractions, restaurants, and leisure spots for Katowice
from the Overpass API and stores them in SQLite.
"""

from __future__ import annotations

import requests
import json
import hashlib
from config import CITY_BBOX

# Public Overpass endpoints, tried in order. The main server frequently
# returns 502/504 when at capacity, so fall back to mirrors.
OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]
# Overpass rejects generic library User-Agents (HTTP 406), so identify the app.
HEADERS = {"User-Agent": "AItravelplaner/0.1 (Katowice trip planner)"}

# Maps OSM tags -> our category + estimated visit duration + avg cost
CATEGORY_RULES = [
    # (osm_key, osm_value, category, subcategory, duration_min, avg_cost_pln)
    ("tourism", "museum",          "attraction", "museum",      90,  20.0),
    ("tourism", "gallery",         "attraction", "gallery",     60,  10.0),
    ("tourism", "attraction",      "attraction", "landmark",    30,   0.0),
    ("tourism", "viewpoint",       "attraction", "viewpoint",   20,   0.0),
    ("historic", "monument",       "attraction", "monument",    20,   0.0),
    ("historic", "memorial",       "attraction", "memorial",    15,   0.0),
    ("historic", "building",       "attraction", "historic",    30,   0.0),
    ("leisure", "park",            "nature",     "park",        60,   0.0),
    ("leisure", "garden",          "nature",     "garden",      45,   0.0),
    ("amenity", "theatre",         "culture",    "theatre",    120,  50.0),
    ("amenity", "cinema",          "culture",    "cinema",     120,  25.0),
    ("amenity", "arts_centre",     "culture",    "arts",        60,  15.0),
    ("amenity", "restaurant",      "food",       "restaurant",  60,  40.0),
    ("amenity", "cafe",            "food",       "cafe",        45,  25.0),
    ("amenity", "fast_food",       "food",       "fast_food",   20,  15.0),
    ("amenity", "bar",             "food",       "bar",         60,  30.0),
    ("shop", "mall",               "shopping",   "mall",        90,   0.0),
]


def _build_query() -> str:
    lat_min, lon_min, lat_max, lon_max = CITY_BBOX
    bbox = f"{lat_min},{lon_min},{lat_max},{lon_max}"

    tag_filters = ""
    seen = set()
    for key, val, *_ in CATEGORY_RULES:
        pair = (key, val)
        if pair not in seen:
            seen.add(pair)
            tag_filters += f'  node["{key}"="{val}"]({bbox});\n'
            tag_filters += f'  way["{key}"="{val}"]({bbox});\n'

    return f"""
[out:json][timeout:60];
(
{tag_filters});
out center tags;
"""


def _make_id(osm_type: str, osm_id: int) -> str:
    return f"{osm_type[0]}{osm_id}"


def _classify(tags: dict) -> tuple | None:
    for key, val, category, subcategory, duration, cost in CATEGORY_RULES:
        if tags.get(key) == val:
            return category, subcategory, duration, cost
    return None


def _extract_coords(element: dict) -> tuple[float, float] | None:
    if element["type"] == "node":
        return element.get("lat"), element.get("lon")
    if element["type"] == "way":
        center = element.get("center", {})
        return center.get("lat"), center.get("lon")
    return None, None


def _post_overpass(query: str) -> list[dict]:
    errors = []
    for url in OVERPASS_URLS:
        try:
            resp = requests.post(url, data={"data": query}, headers=HEADERS, timeout=120)
            resp.raise_for_status()
            return resp.json().get("elements", [])
        except (requests.RequestException, ValueError) as e:
            errors.append(f"{url}: {e}")
    raise RuntimeError("All Overpass endpoints failed:\n  " + "\n  ".join(errors))


def fetch_and_parse() -> list[dict]:
    query = _build_query()
    elements = _post_overpass(query)

    places = []
    for el in elements:
        tags = el.get("tags", {})
        name = tags.get("name") or tags.get("name:pl") or tags.get("name:en")
        if not name:
            continue

        result = _classify(tags)
        if result is None:
            continue
        category, subcategory, duration, cost = result

        lat, lon = _extract_coords(el)
        if lat is None or lon is None:
            continue

        place_id = _make_id(el["type"], el["id"])

        places.append({
            "id": place_id,
            "name": name,
            "category": category,
            "subcategory": subcategory,
            "lat": lat,
            "lon": lon,
            "address": _build_address(tags),
            "opening_hours": tags.get("opening_hours"),
            "avg_cost_pln": cost,
            "duration_min": duration,
            "description": tags.get("description") or tags.get("description:en"),
            "tags": json.dumps({k: v for k, v in tags.items() if k not in ("name",)}),
        })

    return places


def _build_address(tags: dict) -> str | None:
    parts = [
        tags.get("addr:street"),
        tags.get("addr:housenumber"),
    ]
    parts = [p for p in parts if p]
    return " ".join(parts) if parts else None
