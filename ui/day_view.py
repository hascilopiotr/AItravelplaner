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
from ui.format import google_maps_url, money, travel_leg

ACCENT = "#8a2c1c"


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
        popup = (f"<div style='font-family:Inter,sans-serif'><b>{_safe(s.get('name', ''))}</b><br>"
                 f"{_safe(s.get('arrival', ''))}–{_safe(s.get('departure', ''))}"
                 f" · {_safe(money(float(s.get('cost', 0) or 0), cur))}</div>")
        folium.Marker(
            (p["lat"], p["lon"]),
            icon=BeautifyIcon(icon_shape="marker", number=i, border_color=ACCENT,
                              background_color=ACCENT, text_color="#fff",
                              inner_icon_style="font-family:Inter,sans-serif;font-weight:600"),
            tooltip=f"{i}. {_safe(s.get('name', ''))}",
            popup=folium.Popup(popup, max_width=260),
        ).add_to(m)
    if len(pts) > 1:
        m.fit_bounds([[min(lats), min(lons)], [max(lats), max(lons)]], padding=(30, 30))
    return m


def _issues(v: dict) -> list[str]:
    out = list(v["hours_violations"])
    out += [f"Tight connection: {x}" for x in v["travel_violations"]]
    out += [f"Not in the place database: {x}" for x in v["unknown_places"]]
    return out


def _swap_popover(result: dict, city_key: str, day_iso: str, idx: int):
    with st.popover("Swap", type="tertiary", help="Replace with something nearby"):
        options = swap_options(city_key, result, day_iso, idx, places=_city_places(city_key))
        if not options:
            st.caption("Nothing similar nearby is open at this time.")
            return
        pick = st.radio(
            "Replace with", range(len(options)), key=f"swap_pick_{day_iso}_{idx}",
            format_func=lambda i: (f"{options[i]['name']} — {options[i]['subcategory'].replace('_', ' ')}, "
                                   f"{options[i]['distance_km']:.1f} km"
                                   + ("" if options[i]["open_status"] else " (hours unknown)")),
        )
        if st.button("Replace", key=f"swap_go_{day_iso}_{idx}", type="primary"):
            st.session_state["result"] = apply_swap(result, day_iso, idx, options[pick])
            st.session_state.pop("pdf", None)
            st.rerun()


def render_day(result: dict, day: dict, cur: str):
    city_key = result["prefs"]["city"]
    stops = day["plan"].get("stops", [])
    places = [get_place_by_id(city_key, s.get("place_id", "")) or {} for s in stops]
    v = day["validation"]
    d = date.fromisoformat(day["date"])

    st.markdown(
        f"<div class='day-head'><h2>{day['day_of_week']}, {d.strftime('%-d %B')}</h2>"
        f"<div class='day-weather'>{escape(weather_text(day.get('weather'), emoji=False))}</div></div>"
        + (f"<p class='day-summary'>{escape(day['plan']['summary'])}</p>" if day["plan"].get("summary") else ""),
        unsafe_allow_html=True)

    issues = _issues(v)
    if issues:
        with st.expander(f"{len(issues)} thing{'s' if len(issues) > 1 else ''} to check"):
            for x in issues:
                st.markdown(f"- {x}")

    if not stops:
        st.warning("No stops were planned for this day.")
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
            st.link_button("Open in Google Maps", url, type="tertiary")

    with list_col:
        st.markdown(f"<div class='tl-total'>{len(stops)} stops · {escape(money(v['total_cost'], cur))}</div>",
                    unsafe_allow_html=True)
        for i, (s, p) in enumerate(zip(stops, places)):
            if i > 0:
                leg = travel_leg(places[i - 1], p)
                if leg:
                    st.markdown(f"<div class='tl-leg'>{escape(leg)}</div>", unsafe_allow_html=True)
            c_time, c_body, c_swap = st.columns([1.1, 5, 1.2], vertical_alignment="top")
            with c_time:
                st.markdown(f"<div class='tl-time'>{escape(s.get('arrival', ''))}"
                            f"<span>{escape(s.get('departure', ''))}</span></div>", unsafe_allow_html=True)
            with c_body:
                kind = (p.get("subcategory") or "").replace("_", " ")
                meta = " · ".join(x for x in (kind.capitalize(), p.get("address"),
                                              money(float(s.get("cost", 0) or 0), cur)) if x)
                hours = f"<div class='tl-hours'>Open {escape(p['opening_hours'])}</div>" \
                    if p.get("opening_hours") else ""
                st.markdown(
                    f"<div class='tl-name'><span class='tl-num'>{i + 1}</span>{escape(s.get('name', '?'))}</div>"
                    f"<div class='tl-meta'>{escape(meta)}</div>"
                    f"<div class='tl-reason'>{escape(s.get('reason', ''))}</div>{hours}",
                    unsafe_allow_html=True)
            with c_swap:
                _swap_popover(result, city_key, day["date"], i)
