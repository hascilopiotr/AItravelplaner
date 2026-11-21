"""Sidebar: city search / selection and the trip preferences form."""

from __future__ import annotations

from datetime import date, time, timedelta

import streamlit as st

from config import DEFAULT_CITY, DEFAULT_PACE, INTERESTS_OPTIONS, PACES
from data.cities import (
    CityNotFound, city_currency, download_city, ensure_city, refresh_city, search_cities,
)
from data.db import delete_city, list_cities
from planner.pipeline import MAX_TRIP_DAYS
from ui.format import default_budget, short_name

NEW_CITY = "➕ Add another city…"


def _select_loaded(record: dict):
    st.session_state["city"] = record["name"]
    st.session_state.pop("result", None)
    st.session_state.pop("city_matches", None)


def _run_download(label: str, fn, *args) -> bool:
    with st.spinner(f"Downloading places for {label} from OpenStreetMap (~30 s)..."):
        try:
            record = fn(*args)
        except CityNotFound as e:
            st.sidebar.error(str(e))
            return False
        except Exception as e:  # network / Overpass errors
            st.sidebar.error(f"Could not download places for {label}: {e}")
            return False
    _select_loaded(record)
    return True


def city_section() -> dict:
    """Render the city picker; returns the selected city record (stops the script
    while the user is adding a new city)."""
    cities = list_cities()
    if not cities:
        if not _run_download(DEFAULT_CITY, ensure_city, DEFAULT_CITY):
            st.stop()
        cities = list_cities()

    by_key = {c["name"]: c for c in cities}
    if st.session_state.get("city") not in by_key:
        st.session_state["city"] = cities[0]["name"]

    st.markdown("### 📍 City")
    keys = list(by_key)
    choice = st.selectbox(
        "City", keys + [NEW_CITY], index=keys.index(st.session_state["city"]),
        format_func=lambda k: k if k == NEW_CITY else short_name(by_key[k]),
        label_visibility="collapsed",
    )
    if choice == NEW_CITY:
        with st.form("city_search"):
            query = st.text_input("Search for a city", placeholder="e.g. Kraków, Wroclaw, Prague")
            searched = st.form_submit_button("🔍 Search", use_container_width=True)
        if searched and query.strip():
            try:
                st.session_state["city_matches"] = search_cities(query)
            except Exception as e:
                st.session_state["city_matches"] = []
                st.error(f"City search failed: {e}")
            st.session_state["city_query"] = query.strip()

        matches = st.session_state.get("city_matches")
        if matches is not None:
            if not matches:
                st.warning(f"No city found for '{st.session_state.get('city_query', '')}'. "
                           "Check the spelling or try the English/local name.")
            else:
                idx = st.radio("Did you mean:", range(len(matches)),
                               format_func=lambda i: matches[i]["label"])
                picked = matches[idx]
                cached = by_key.get(picked["name"].strip().lower())
                if cached:
                    if st.button(f"Use {picked['name']} (already downloaded)", type="primary",
                                 use_container_width=True):
                        _select_loaded(cached)
                        st.rerun()
                elif st.button(f"⬇️ Download {picked['name']}", type="primary", use_container_width=True):
                    if _run_download(picked["name"], download_city, picked):
                        st.rerun()
        st.stop()
    elif choice != st.session_state["city"]:
        st.session_state["city"] = choice
        st.session_state.pop("result", None)

    city = by_key[st.session_state["city"]]
    st.caption(f"{city['display_name']}  \n{city['n_places']} places · "
               f"updated {city['fetched_at'][:10]}")
    c1, c2 = st.columns(2)
    if c1.button("🔄 Refresh", use_container_width=True, help="Re-download places from OpenStreetMap"):
        if _run_download(short_name(city), refresh_city, city["name"]):
            st.rerun()
    if c2.button("🗑️ Remove", use_container_width=True, disabled=len(by_key) < 2,
                 help="Delete this city's places from the local database"):
        delete_city(city["name"])
        st.session_state.pop("city", None)
        st.session_state.pop("result", None)
        st.rerun()
    return city


def _trip_dates(rng) -> list[date]:
    if isinstance(rng, date):
        rng = (rng, rng)
    if not rng:
        return []
    start, end = rng[0], rng[-1]
    return [start + timedelta(days=i) for i in range((end - start).days + 1)]


def trip_form(city: dict) -> dict | None:
    """Render the trip form; returns validated prefs when submitted, else None."""
    currency = city_currency(city)
    st.markdown("### 🧳 Your trip")
    with st.form("prefs_form"):
        tomorrow = date.today() + timedelta(days=1)
        date_range = st.date_input(
            f"Dates (up to {MAX_TRIP_DAYS} days)", value=(tomorrow, tomorrow + timedelta(days=2)),
            min_value=date.today(), help="Pick the first and last day of the trip.",
        )
        c1, c2 = st.columns(2)
        start_t = c1.time_input("Day starts", value=time(10, 0), step=timedelta(minutes=15))
        end_t = c2.time_input("Day ends", value=time(19, 0), step=timedelta(minutes=15))
        pace = st.radio(
            "Pace", list(PACES), index=list(PACES).index(DEFAULT_PACE), horizontal=True,
            format_func=lambda k: PACES[k]["label"],
            help=" · ".join(f"{p['label']}: {p['stops'][0]}–{p['stops'][1]} stops/day, "
                            f"{p['buffer']}+ min breaks" for p in PACES.values()),
        )
        b_default, b_step = default_budget(currency)
        budget = st.number_input(f"Budget per person, whole trip ({currency})", min_value=0.0,
                                 value=b_default, step=b_step, format="%.0f")
        interests = st.multiselect("Interests", INTERESTS_OPTIONS, default=["museums", "food", "parks"])
        notes = st.text_area("Notes (optional)", placeholder="e.g. travelling with kids, vegetarian, no stairs")
        submitted = st.form_submit_button("✨ Plan my trip", type="primary", use_container_width=True)

    if not submitted:
        return None
    dates = _trip_dates(date_range)
    if not dates:
        st.error("Pick the trip dates.")
    elif len(dates) > MAX_TRIP_DAYS:
        st.error(f"Trips can be at most {MAX_TRIP_DAYS} days (you picked {len(dates)}).")
    elif end_t <= start_t:
        st.error("The day must end after it starts.")
    elif not interests:
        st.error("Pick at least one interest.")
    else:
        return {
            "city": city["name"],
            "dates": [d.isoformat() for d in dates],
            "budget": float(budget),
            "currency": currency,
            "pace": pace,
            "start_time": start_t.strftime("%H:%M"),
            "end_time": end_t.strftime("%H:%M"),
            "interests": interests,
            "notes": notes.strip(),
        }
    return None
