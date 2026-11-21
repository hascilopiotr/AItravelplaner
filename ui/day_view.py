"""Selected-day panel: map with numbered pins (left) + timeline (right)."""

from __future__ import annotations

from datetime import date
from html import escape

import folium
import streamlit as st
from folium.plugins import BeautifyIcon

from data.db import get_all_places, get_place_by_id
from data.weather import weather_text
from planner.swap import apply_swap, swap_options
from ui.components import (
    day_header, html, timetable_head, timetable_leg, timetable_stop, timetable_time,
)
from ui.format import google_maps_url, money, travel_leg

ACCENT = "#0F4C5C"


def _safe(text) -> str:
    """Escape text going into the map's HTML/JS. Place names come from OpenStreetMap
    and the AI, and folium puts them inside JavaScript template strings."""
    return escape(str(text)).replace("$", "&#36;").replace("`", "&#96;").replace("\\", "&#92;")


@st.cache_data(ttl=600, show_spinner=False)
def _city_places(city_key: str) -> list[dict]:
    return get_all_places(city_key)


def _pin_map(stops: list[dict], places: list[dict], cur: str) -> folium.Map | None:
    pts = [(s, p) for s, p in zip(stops, places) if p and p.get("lat") is not None]
    if not pts:
        return None
    lats = [p["lat"] for _, p in pts]
    lons = [p["lon"] for _, p in pts]
    m = folium.Map(location=[sum(lats) / len(lats), sum(lons) / len(lons)], zoom_start=14,
                   tiles="CartoDB positron", control_scale=True,
                   # Let the mouse wheel scroll the page instead of zooming the map
                   # (zoom with +/-, double-click or pinch).
                   scrollWheelZoom=False)
    if len(pts) > 1:
        folium.PolyLine([(p["lat"], p["lon"]) for _, p in pts], color=ACCENT, weight=3,
                        opacity=0.75, dash_array="2 7", line_cap="round").add_to(m)
    for i, (s, p) in enumerate(pts, 1):
        popup = (f"<div style=\"font-family:'IBM Plex Sans',sans-serif\"><b>{_safe(s.get('name', ''))}</b><br>"
                 f"{_safe(s.get('arrival', ''))}–{_safe(s.get('departure', ''))}"
                 f" · {_safe(money(float(s.get('cost', 0) or 0), cur))}</div>")
        folium.Marker(
            (p["lat"], p["lon"]),
            icon=BeautifyIcon(icon_shape="marker", number=i, border_color=ACCENT,
                              background_color=ACCENT, text_color="#fff",
                              inner_icon_style="font-family:'IBM Plex Mono',monospace;font-weight:600"),
            tooltip=f"{i}. {_safe(s.get('name', ''))}",
            popup=folium.Popup(popup, max_width=260),
        ).add_to(m)
    if len(pts) > 1:
        m.fit_bounds([[min(lats), min(lons)], [max(lats), max(lons)]], padding=(30, 30))
    return m


def _issues(v: dict) -> list[str]:
    out = list(v["hours_violations"])
    out += [f"Tight connection: {x}" for x in v["travel_violations"]]
    out += [f"Couldn't verify this place: {x}" for x in v["unknown_places"]]
    return out


def _swap_popover(result: dict, city_key: str, day_iso: str, idx: int):
    with st.popover("Swap", type="tertiary", help="See similar places nearby"):
        options = swap_options(city_key, result, day_iso, idx, places=_city_places(city_key))
        if not options:
            st.caption("Nothing similar within 1.5 km is open then.")
            return
        pick = st.radio(
            "Nearby alternatives", range(len(options)), key=f"swap_pick_{day_iso}_{idx}",
            format_func=lambda i: (f"{options[i]['name']} — {options[i]['subcategory'].replace('_', ' ')}, "
                                   f"{options[i]['distance_km']:.1f} km"
                                   + ("" if options[i]["open_status"] else " · hours not listed")),
        )
        if st.button("Use this instead", key=f"swap_go_{day_iso}_{idx}", type="primary"):
            st.session_state["result"] = apply_swap(result, day_iso, idx, options[pick])
            st.session_state.pop("pdf", None)
            st.rerun()


def render_day(result: dict, day: dict, cur: str):
    city_key = result["prefs"]["city"]
    stops = day["plan"].get("stops", [])
    places = [get_place_by_id(city_key, s.get("place_id", "")) or {} for s in stops]
    v = day["validation"]
    d = date.fromisoformat(day["date"])
    issues = _issues(v)

    html(day_header(
        title=f"{day['day_of_week']} {d.strftime('%-d %B')}",
        weather=weather_text(day.get("weather"), emoji=False),
        status=f"{len(issues)} to check" if issues else "Cleared",
        ok=not issues,
        summary=day["plan"].get("summary"),
    ))
    if issues:
        with st.expander("What to check"):
            for x in issues:
                st.markdown(f"- {x}")

    if not stops:
        st.warning("No stops came back for this day.")
        return

    map_col, list_col = st.columns([3, 2], gap="large")
    with map_col:
        m = _pin_map(stops, places, cur)
        if m is None:
            st.caption("No coordinates for these stops.")
        else:
            # Plain HTML embed: a fixed-height iframe that never talks back to Streamlit,
            # so it can't trigger reruns or resize loops that make the page jump.
            # (All text in the map is escaped by _safe(), since the iframe can run scripts.)
            st.iframe(m.get_root().render(), height=580)
        url = google_maps_url(places)
        if url:
            st.link_button("Open route in Google Maps", url, type="tertiary")

    with list_col:
        html(timetable_head(f"{len(stops)} stops · {money(v['total_cost'], cur)}"))
        for i, (s, p) in enumerate(zip(stops, places)):
            if i > 0:
                leg = travel_leg(places[i - 1], p)
                if leg:
                    html(timetable_leg(leg))
            c_time, c_body, c_swap = st.columns([1.1, 5, 1], vertical_alignment="top")
            with c_time:
                html(timetable_time(s.get("arrival", ""), s.get("departure", "")))
            with c_body:
                kind = (p.get("subcategory") or "").replace("_", " ").capitalize()
                html(timetable_stop(
                    n=i + 1, name=s.get("name", "?"),
                    price=money(float(s.get("cost", 0) or 0), cur),
                    meta=" · ".join(x for x in (kind, p.get("address")) if x),
                    reason=s.get("reason", ""),
                    hours=p.get("opening_hours"),
                ))
            with c_swap:
                _swap_popover(result, city_key, day["date"], i)
        html("<div class='tt-end'></div>")
