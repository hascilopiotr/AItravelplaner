"""Small formatting helpers shared by the UI modules."""

from __future__ import annotations

from urllib.parse import urlencode

from babel.numbers import format_currency, get_currency_symbol

from validator.checker import _haversine_km, _travel_minutes
from config import WALK_MAX_KM

# Rough value of one unit in PLN — only used to suggest a sensible default budget
# (~200 PLN per day for 3 days). Plans themselves are priced directly in the city's currency.
_APPROX_PLN = {"PLN": 1, "EUR": 4.3, "USD": 4.0, "GBP": 5.1, "CHF": 4.5, "CZK": 0.17,
               "HUF": 0.011, "SEK": 0.37, "NOK": 0.36, "DKK": 0.58, "JPY": 0.026,
               "CNY": 0.55, "CAD": 2.9, "AUD": 2.6, "TRY": 0.12, "UAH": 0.1, "RON": 0.86}


def short_name(city: dict) -> str:
    return city["display_name"].split(" — ")[0].split(",")[0]


def default_budget(cur: str) -> tuple[float, float]:
    """(default trip budget, input step) in the given currency."""
    if cur not in _APPROX_PLN:
        return 500.0, 10.0
    value = 600 / _APPROX_PLN[cur]
    mag = 10 ** max(len(str(int(value))) - 2, 0)
    return float(round(value / mag) * mag), float(max(mag, 1))


def money(x: float, cur: str) -> str:
    """$1,234 / €1,234 / 1,234 PLN (code after the amount when there's no symbol)."""
    if get_currency_symbol(cur, locale="en") == cur:
        return f"{x:,.0f} {cur}"
    return format_currency(x, cur, locale="en", format="¤#,##0", currency_digits=False)


def travel_leg(a: dict, b: dict) -> str | None:
    """'6 min walk · 0.4 km' / '14 min by tram or bus · 3.1 km' (None if unknown)."""
    if not a or not b or a.get("lat") is None or b.get("lat") is None:
        return None
    km = _haversine_km(a["lat"], a["lon"], b["lat"], b["lon"])
    how = "walk" if km < WALK_MAX_KM else "by public transport"
    return f"{max(_travel_minutes(km), 1)} min {how} · {km:.1f} km"


def google_maps_url(places: list[dict], walking: bool = True) -> str | None:
    """Google Maps directions link with every stop pinned (no API key needed)."""
    pts = [f"{p['lat']:.6f},{p['lon']:.6f}" for p in places if p and p.get("lat") is not None]
    if not pts:
        return None
    if len(pts) == 1:
        return "https://www.google.com/maps/search/?" + urlencode({"api": 1, "query": pts[0]})
    params = {"api": 1, "origin": pts[0], "destination": pts[-1],
              "travelmode": "walking" if walking else "transit"}
    if len(pts) > 2:
        params["waypoints"] = "|".join(pts[1:-1][:9])  # Google allows up to 9 waypoints
    return "https://www.google.com/maps/dir/?" + urlencode(params)
