"""
City lookup and per-city place cache.

A city's places are downloaded from OpenStreetMap the first time it is
requested and kept in SQLite; `ensure_city(..., refresh=True)` re-downloads.
"""

from __future__ import annotations

from datetime import datetime, timezone
from math import cos, radians

import requests

from data.db import (
    city_key, count_places, get_city, init_db, replace_city_places, save_city,
)
from data.osm_fetcher import HEADERS, fetch_and_parse

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

# Cap the search area so big cities/regions don't overload Overpass:
# at most this many km from the city centre in each direction.
MAX_RADIUS_KM = 10.0


class CityNotFound(ValueError):
    pass


def geocode_city(name: str) -> dict:
    """Resolve a city name to its centre and (clipped) bounding box via Nominatim."""
    resp = requests.get(
        NOMINATIM_URL,
        params={"q": name, "format": "jsonv2", "limit": 1, "featureType": "city"},
        headers=HEADERS,
        timeout=20,
    )
    resp.raise_for_status()
    results = resp.json()
    if not results:
        raise CityNotFound(f"Could not find a city called '{name}'.")
    r = results[0]
    lat, lon = float(r["lat"]), float(r["lon"])
    s, n, w, e = (float(x) for x in r["boundingbox"])
    return {
        "display_name": r.get("display_name", name),
        "lat": lat,
        "lon": lon,
        "bbox": _clip_bbox((s, w, n, e), lat, lon),
    }


def _clip_bbox(bbox, lat: float, lon: float):
    """Intersect bbox with a square of MAX_RADIUS_KM around the centre."""
    dlat = MAX_RADIUS_KM / 111.0
    dlon = MAX_RADIUS_KM / (111.0 * max(cos(radians(lat)), 0.1))
    s, w, n, e = bbox
    return (max(s, lat - dlat), max(w, lon - dlon), min(n, lat + dlat), min(e, lon + dlon))


def ensure_city(name: str, refresh: bool = False) -> dict:
    """
    Make sure places for `name` are in the DB and return the city record.
    Downloads from OpenStreetMap if the city is new or refresh=True.
    """
    init_db()
    key = city_key(name)
    city = get_city(key)
    if city and not refresh and count_places(key) > 0:
        return city

    info = geocode_city(name)
    places = fetch_and_parse(info["bbox"])
    if not places:
        raise CityNotFound(f"No places found on OpenStreetMap for '{name}'.")
    replace_city_places(key, places)
    save_city(key, info["display_name"], info["lat"], info["lon"],
              datetime.now(timezone.utc).isoformat(timespec="seconds"))
    return get_city(key)
