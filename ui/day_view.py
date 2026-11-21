"""Selected day: the interactive itinerary + map board, and the swap dialog."""

from __future__ import annotations

from datetime import date, datetime
from html import escape

import streamlit as st

from data.db import get_all_places, get_place_by_id
from data.photos import place_photo
from planner.swap import apply_swap, swap_options
from ui.components import place_icon, place_icon_name, weather_icon_name
from ui.format import google_maps_url, money, travel_leg
from ui.widgets import day_board


@st.cache_data(ttl=600, show_spinner=False)
def _city_places(city_key: str) -> list[dict]:
    return get_all_places(city_key)


def _issues(v: dict) -> list[str]:
    out = list(v["hours_violations"])
    out += [f"Not enough travel time: {x}" for x in v["travel_violations"]]
    out += [f"Place not found in map data: {x}" for x in v["unknown_places"]]
    return out


def _minutes(a: str, b: str) -> str | None:
    try:
        m = int((datetime.strptime(b, "%H:%M") - datetime.strptime(a, "%H:%M")).total_seconds() // 60)
    except (TypeError, ValueError):
        return None
    if m <= 0:
        return None
    return f"{m} min" if m < 60 else f"{m // 60} h {m % 60:02d}" if m % 60 else f"{m // 60} h"


@st.dialog("Swap this stop", width="medium")
def _swap_dialog(result: dict, city_key: str, day_iso: str, idx: int):
    stop = result_stop(result, day_iso, idx)
    st.html(f"<div class='tp-dlg-from'><span>Replacing stop {idx + 1:02d}</span>"
            f"<b>{escape(stop.get('name') or '?')}</b>"
            f"<em>{escape(stop.get('arrival', ''))}–{escape(stop.get('departure', ''))}</em></div>")
    options = swap_options(city_key, result, day_iso, idx, places=_city_places(city_key))
    if not options:
        st.info("No similar places within 1.5 km are open at this time.", icon=":material/search_off:")
        return
    pick = st.radio(
        "Similar places nearby, open at this time", range(len(options)), key=f"swap_pick_{day_iso}_{idx}",
        format_func=lambda i: (f"{place_icon(options[i]['subcategory'])} **{options[i]['name']}** — "
                               f"{options[i]['subcategory'].replace('_', ' ')}, {options[i]['distance_km']:.1f} km away"
                               + ("" if options[i]["open_status"] else " · hours unknown")),
    )
    if st.button("Swap it in", type="primary", icon=":material/swap_horiz:", use_container_width=True):
        st.session_state["result"] = apply_swap(result, day_iso, idx, options[pick])
        st.session_state.pop("pdf", None)
        st.rerun()


def result_stop(result: dict, day_iso: str, idx: int) -> dict:
    day = next(d for d in result["days"] if d["date"] == day_iso)
    return day["plan"]["stops"][idx]


def _board_data(result: dict, day: dict, n: int, of: int) -> dict:
    city_key, cur = result["prefs"]["city"], result["prefs"]["currency"]
    stops = day["plan"].get("stops", [])
    places = [get_place_by_id(city_key, s.get("place_id", "")) or {} for s in stops]
    v, w = day["validation"], day.get("weather")
    d = date.fromisoformat(day["date"])

    out_stops = []
    for i, (s, p) in enumerate(zip(stops, places)):
        cost = float(s.get("cost", 0) or 0)
        leg = travel_leg(places[i - 1], p) if i > 0 else None
        out_stops.append({
            "name": s.get("name") or "?",
            "arrival": s.get("arrival", ""), "departure": s.get("departure", ""),
            "mins": _minutes(s.get("arrival"), s.get("departure")),
            "kind": (p.get("subcategory") or "").replace("_", " ").capitalize(),
            "icon": place_icon_name(p.get("subcategory")),
            "address": p.get("address") or "",
            "reason": s.get("reason") or "",
            "hours": p.get("opening_hours") or "",
            "price": "Free" if cost == 0 else money(cost, cur), "free": cost == 0,
            "photo": place_photo(p) if p else None,
            "lat": p.get("lat"), "lon": p.get("lon"),
            "leg": {"text": leg, "walk": " walk " in f" {leg} "} if leg else None,
        })

    return {
        "sig": f"{day['date']}:{[s.get('place_id') for s in stops]}",
        "day": {
            "n": n, "of": of, "weekday": day["day_of_week"], "date_long": d.strftime("%-d %B"),
            "weather": {
                "icon": weather_icon_name(w.get("code")), "label": w.get("label", ""),
                "range": f"{w['tmin']:.0f}–{w['tmax']:.0f}°C" if w.get("tmin") is not None else "",
                "rain": round(w["rain_prob"]) if w.get("rain_prob") is not None else None,
            } if w else None,
            "n_stops": len(stops), "cost": f"{money(v['total_cost'], cur)} pp",
            "summary": day["plan"].get("summary") or "", "issues": _issues(v),
        },
        "stops": out_stops,
        "route_url": google_maps_url(places),
    }


def render_day(result: dict, day: dict, n: int, of: int):
    swap = day_board(_board_data(result, day, n, of))
    if swap is not None:
        _swap_dialog(result, result["prefs"]["city"], day["date"], int(swap))
