"""Selected-day panel: big pin map (left) + timeline with swap buttons (right)."""

from __future__ import annotations

from datetime import date
from html import escape

import folium
import streamlit as st
from folium.plugins import BeautifyIcon
import streamlit.components.v1 as components

from data.db import get_all_places, get_place_by_id
from data.weather import weather_text
from planner.swap import apply_swap, swap_options
from ui.format import google_maps_url, money, travel_leg

PIN = "#e74c3c"


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
                   tiles="OpenStreetMap", control_scale=True,
                   # Let the mouse wheel scroll the page instead of zooming the map
                   # (zoom with +/-, double-click or pinch).
                   scrollWheelZoom=False)
    if len(pts) > 1:
        folium.PolyLine([(p["lat"], p["lon"]) for _, p in pts], color=PIN, weight=4,
                        opacity=0.8, dash_array="8 6").add_to(m)
    for i, (s, p) in enumerate(pts, 1):
        popup = (f"<b>{i}. {escape(s.get('name', ''))}</b><br>"
                 f"{escape(s.get('arrival', ''))}–{escape(s.get('departure', ''))}"
                 f" · {escape(money(float(s.get('cost', 0) or 0), cur))}")
        folium.Marker(
            (p["lat"], p["lon"]),
            icon=BeautifyIcon(icon_shape="marker", number=i, border_color=PIN,
                              background_color=PIN, text_color="#fff", inner_icon_style="font-weight:700"),
            tooltip=f"{i}. {s.get('name', '')}",
            popup=folium.Popup(popup, max_width=260),
        ).add_to(m)
    if len(pts) > 1:
        m.fit_bounds([[min(lats), min(lons)], [max(lats), max(lons)]], padding=(30, 30))
    return m


def _issues(v: dict) -> list[str]:
    out = [f"🕒 {x}" for x in v["hours_violations"]]
    out += [f"🚶 Travel time: {x}" for x in v["travel_violations"]]
    out += [f"❓ Not in database: {x}" for x in v["unknown_places"]]
    return out


def _swap_popover(result: dict, city_key: str, day_iso: str, idx: int, cur: str):
    with st.popover("⇄", help="Swap this stop for something nearby"):
        options = swap_options(city_key, result, day_iso, idx, places=_city_places(city_key))
        if not options:
            st.caption("No nearby alternatives of this kind are open at this time.")
            return
        st.markdown("**Swap for:**")
        pick = st.radio(
            "Alternatives", range(len(options)), label_visibility="collapsed",
            key=f"swap_pick_{day_iso}_{idx}",
            format_func=lambda i: (f"{options[i]['name']} — {options[i]['subcategory']} · "
                                   f"{options[i]['distance_km']:.1f} km · "
                                   + ("open ✅" if options[i]["open_status"] else "hours unknown")),
        )
        if st.button("Swap", key=f"swap_go_{day_iso}_{idx}", type="primary", use_container_width=True):
            st.session_state["result"] = apply_swap(result, day_iso, idx, options[pick])
            st.session_state.pop("pdf", None)
            st.rerun()


def render_day(result: dict, day: dict, cur: str):
    city_key = result["prefs"]["city"]
    stops = day["plan"].get("stops", [])
    places = [get_place_by_id(city_key, s.get("place_id", "")) or {} for s in stops]
    v = day["validation"]
    d = date.fromisoformat(day["date"])

    head_l, head_r = st.columns([3, 2])
    with head_l:
        st.markdown(f"## {day['day_of_week']}, {d.strftime('%d %B')}")
        if day["plan"].get("summary"):
            st.markdown(f"*{day['plan']['summary']}*")
    with head_r:
        st.markdown(f"<div class='weather-card'>{weather_text(day.get('weather'))}</div>",
                    unsafe_allow_html=True)

    issues = _issues(v)
    if issues:
        with st.expander(f"⚠️ {len(issues)} thing(s) to check on this day"):
            for x in issues:
                st.markdown(f"- {x}")

    if not stops:
        st.warning("No stops were planned for this day.")
        return

    map_col, list_col = st.columns([3, 2], gap="medium")
    with map_col:
        m = _pin_map(stops, places, cur)
        if m is None:
            st.caption("No coordinates available for these stops.")
        else:
            # Plain HTML embed: a fixed-height iframe that never talks back to Streamlit,
            # so it can't trigger reruns or resize loops that make the page jump.
            components.html(m.get_root().render(), height=600)
            st.caption("Zoom with + / −, double-click or pinch · click a pin for details")
        url = google_maps_url(places)
        if url:
            st.link_button("🗺️ Open this day in Google Maps", url, use_container_width=True)

    with list_col:
        st.markdown(f"**{len(stops)} stops · {money(v['total_cost'], cur)}**")
        for i, (s, p) in enumerate(zip(stops, places)):
            if i > 0:
                leg = travel_leg(places[i - 1], p)
                if leg:
                    st.markdown(f"<div class='leg'>{leg}</div>", unsafe_allow_html=True)
            with st.container(border=True):
                c_txt, c_btn = st.columns([6, 1])
                with c_txt:
                    kind = f" · {p['subcategory']}" if p.get("subcategory") else ""
                    st.markdown(
                        f"<span class='pin'>{i + 1}</span> <b>{escape(s.get('name', '?'))}</b><br>"
                        f"<span class='meta'>🕒 {escape(s.get('arrival', ''))}–{escape(s.get('departure', ''))}"
                        f" · {escape(money(float(s.get('cost', 0) or 0), cur))}{escape(kind)}</span>",
                        unsafe_allow_html=True)
                with c_btn:
                    _swap_popover(result, city_key, day["date"], i, cur)
                st.caption(s.get("reason", ""))
                details = [x for x in (p.get("address"),
                                       f"Hours: {p['opening_hours']}" if p.get("opening_hours") else None) if x]
                if details:
                    st.caption(" · ".join(details))
