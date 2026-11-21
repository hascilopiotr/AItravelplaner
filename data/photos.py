"""
Destination and place photos from Wikipedia (freely licensed, no API key).
Results — including "no photo" — are cached in SQLite so each lookup happens once.
"""

from __future__ import annotations

import json
import re
from urllib.parse import quote

import requests

from data.db import get_conn
from data.osm_fetcher import HEADERS

SUMMARY_URL = "https://{lang}.wikipedia.org/api/rest_v1/page/summary/{title}"
# Wikimedia only serves thumbnails at these widths; other sizes get HTTP 400.
STANDARD_WIDTHS = (120, 250, 330, 500, 960, 1280, 1920)


def _cache_get(key: str) -> tuple[bool, str | None]:
    conn = get_conn()
    conn.execute("CREATE TABLE IF NOT EXISTS photos (key TEXT PRIMARY KEY, url TEXT)")
    row = conn.execute("SELECT url FROM photos WHERE key=?", (key,)).fetchone()
    conn.close()
    return (row is not None, row["url"] if row else None)


def _cache_put(key: str, url: str | None):
    conn = get_conn()
    conn.execute("CREATE TABLE IF NOT EXISTS photos (key TEXT PRIMARY KEY, url TEXT)")
    conn.execute("INSERT OR REPLACE INTO photos (key, url) VALUES (?, ?)", (key, url))
    conn.commit()
    conn.close()


def _wiki_image(lang: str, title: str, width: int) -> str | None:
    width = next((w for w in STANDARD_WIDTHS if w >= width), STANDARD_WIDTHS[-1])
    key = f"{lang}:{title}:{width}"
    hit, url = _cache_get(key)
    if hit:
        return url
    url = None
    try:
        resp = requests.get(SUMMARY_URL.format(lang=lang, title=quote(title.replace(" ", "_"))),
                            headers=HEADERS, timeout=8)
        if resp.ok:
            data = resp.json()
            thumb = (data.get("thumbnail") or {}).get("source")
            original = data.get("originalimage") or {}
            if thumb:
                # Wikimedia thumbnails can be re-requested at any width up to the original.
                if original.get("width", 0) >= width and re.search(r"/\d+px-", thumb):
                    url = re.sub(r"/\d+px-", f"/{width}px-", thumb)
                else:
                    url = original.get("source") or thumb
    except (requests.RequestException, ValueError):
        return None  # network problem: don't cache, try again next time
    _cache_put(key, url)
    return url


def city_photo(city_name: str) -> str | None:
    return _wiki_image("en", city_name, 1920)


def place_photo(place: dict) -> str | None:
    """Photo for a place that has an OSM `wikipedia` tag like 'pl:Sukiennice w Krakowie'."""
    try:
        tags = json.loads(place.get("tags") or "{}")
    except ValueError:
        return None
    ref = tags.get("wikipedia")
    if not ref or ":" not in ref:
        return None
    lang, title = ref.split(":", 1)
    if not re.fullmatch(r"[a-z\-]{2,12}", lang):
        return None
    return _wiki_image(lang, title, 330)
