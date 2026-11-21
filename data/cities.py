"""
City search and per-city place cache.

Cities are found with Photon (OpenStreetMap-based, typo tolerant: "krakw" -> Kraków).
A city's places are downloaded the first time it is requested and kept in SQLite;
`ensure_city(..., refresh=True)` / `download_city(...)` re-download.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from math import cos, radians

import requests

from babel.numbers import get_territory_currencies

from data.db import (
    city_key, count_places, get_city, init_db, replace_city_places, save_city, set_city_currency,
)
from data.osm_fetcher import HEADERS, fetch_and_parse

PHOTON_URL = "https://photon.komoot.io/api/"

# Cap the search area so big cities/regions don't overload Overpass:
# at most this many km from the city centre in each direction.
MAX_RADIUS_KM = 10.0


class CityNotFound(ValueError):
    pass


def search_cities(query: str, limit: int = 6) -> list[dict]:
    """
    Typo-tolerant city/town search. Returns candidates, best match first:
    [{name, label, lat, lon, bbox}] where bbox = (lat_min, lon_min, lat_max, lon_max).
    """
    query = query.strip()
    if not query:
        return []
    resp = requests.get(
        PHOTON_URL,
        params=[("q", query), ("limit", limit),
                ("osm_tag", "place:city"), ("osm_tag", "place:town")],
        headers=HEADERS,
        timeout=20,
    )
    resp.raise_for_status()

    out, seen = [], set()
    for f in resp.json().get("features", []):
        p = f.get("properties", {})
        name = p.get("name")
        if not name:
            continue
        lon, lat = f["geometry"]["coordinates"]
        region = ", ".join(x for x in (p.get("state"), p.get("country")) if x)
        label = f"{name} — {region}" if region else name
        if label in seen:
            continue
        seen.add(label)
        extent = p.get("extent")  # [lon_min, lat_max, lon_max, lat_min]
        bbox = (extent[3], extent[0], extent[1], extent[2]) if extent else (lat, lon, lat, lon)
        out.append({"name": name, "label": label, "lat": lat, "lon": lon,
                    "bbox": _clip_bbox(bbox, lat, lon),
                    "currency": currency_for_country(p.get("countrycode"))})
    return out


def currency_for_country(country_code: str | None) -> str | None:
    """'US' -> 'USD', 'PL' -> 'PLN', 'DE' -> 'EUR'."""
    if not country_code:
        return None
    try:
        found = get_territory_currencies(country_code.upper())
    except Exception:
        return None
    return found[0] if found else None


def city_currency(city: dict) -> str:
    """Currency of a cached city; looks it up (and stores it) for cities cached
    before currencies were tracked. Falls back to EUR if it can't be determined."""
    if city.get("currency"):
        return city["currency"]
    name = city["display_name"].split(" — ")[0].split(",")[0]
    try:
        matches = search_cities(name, limit=1)
        currency = matches[0]["currency"] if matches else None
    except Exception:
        currency = None
    if currency:
        set_city_currency(city["name"], currency)
        return currency
    return "EUR"


def _clip_bbox(bbox, lat: float, lon: float):
    """Intersect bbox with a square of MAX_RADIUS_KM around the centre.
    A point-only bbox (no extent) becomes the full square."""
    dlat = MAX_RADIUS_KM / 111.0
    dlon = MAX_RADIUS_KM / (111.0 * max(cos(radians(lat)), 0.1))
    s, w, n, e = bbox
    if s == n and w == e:
        return (lat - dlat, lon - dlon, lat + dlat, lon + dlon)
    return (max(s, lat - dlat), max(w, lon - dlon), min(n, lat + dlat), min(e, lon + dlon))


def download_city(candidate: dict) -> dict:
    """Download places for a search_cities() candidate (or stored city) and cache them."""
    init_db()
    key = city_key(candidate["name"])
    places = fetch_and_parse(tuple(candidate["bbox"]))
    if not places:
        raise CityNotFound(f"No places found on OpenStreetMap for '{candidate['name']}'.")
    replace_city_places(key, places)
    save_city(key, candidate.get("label", candidate["name"]), candidate["lat"], candidate["lon"],
              datetime.now(timezone.utc).isoformat(timespec="seconds"),
              json.dumps(list(candidate["bbox"])), candidate.get("currency"))
    return get_city(key)


def refresh_city(key: str) -> dict:
    """Re-download a cached city using its stored search area."""
    city = get_city(key)
    if city is None:
        raise CityNotFound(f"'{key}' is not downloaded yet.")
    if city.get("bbox"):
        return download_city({"name": key, "label": city["display_name"], "lat": city["lat"],
                              "lon": city["lon"], "bbox": json.loads(city["bbox"])})
    return ensure_city(key, refresh=True)  # cached before bboxes were stored


def ensure_city(name: str, refresh: bool = False) -> dict:
    """
    Make sure places for `name` are cached and return the city record.
    Typos are fine: the name is resolved to the best search match.
    """
    init_db()
    key = city_key(name)
    city = get_city(key)
    if city and not refresh and count_places(key) > 0:
        return city

    matches = search_cities(name)
    if not matches:
        raise CityNotFound(f"Could not find a city called '{name}'.")
    best = matches[0]
    cached = get_city(city_key(best["name"]))
    if cached and not refresh and count_places(cached["name"]) > 0:
        return cached
    return download_city(best)
