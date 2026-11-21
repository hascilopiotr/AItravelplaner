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
from ui.components import section_label
from ui.format import default_budget, short_name

NEW_CITY = "New destination…"


def _select_loaded(record: dict):
    st.session_state["city"] = record["name"]
    st.session_state.pop("result", None)
    st.session_state.pop("city_matches", None)


def _run_download(label: str, fn, *args) -> bool:
    with st.spinner(f"Collecting places in {label} — about 30 seconds"):
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

    section_label("Destination")
    keys = list(by_key)
    choice = st.selectbox(
        "Destination", keys + [NEW_CITY], index=keys.index(st.session_state["city"]),
        format_func=lambda k: k if k == NEW_CITY else short_name(by_key[k]),
        label_visibility="collapsed",
    )
    if choice == NEW_CITY:
        with st.form("city_search"):
            query = st.text_input("City name", placeholder="Lisbon, Kraków, Porto…")
            searched = st.form_submit_button("Find", use_container_width=True)
        if searched and query.strip():
            try:
                st.session_state["city_matches"] = search_cities(query)
            except Exception as e:
                st.session_state["city_matches"] = []
                st.error(f"Couldn't reach the city search: {e}")
            st.session_state["city_query"] = query.strip()

        matches = st.session_state.get("city_matches")
        if matches is not None:
            if not matches:
                st.warning(f"No city called “{st.session_state.get('city_query', '')}”. "
                           "Try the local or English spelling.")
            else:
                idx = st.radio("Which one?", range(len(matches)),
                               format_func=lambda i: matches[i]["label"])
                picked = matches[idx]
                cached = by_key.get(picked["name"].strip().lower())
                if cached:
                    if st.button(f"Switch to {picked['name']}", type="primary",
                                 use_container_width=True):
                        _select_loaded(cached)
                        st.rerun()
                elif st.button(f"Add {picked['name']}", type="primary", use_container_width=True):
                    if _run_download(picked["name"], download_city, picked):
                        st.rerun()
        st.stop()
    elif choice != st.session_state["city"]:
        st.session_state["city"] = choice
        st.session_state.pop("result", None)

    city = by_key[st.session_state["city"]]
    st.caption(f"{city['n_places']:,} places · data from {city['fetched_at'][:10]}")
    c1, c2 = st.columns(2)
    if c1.button("Update data", type="tertiary", help="Download this city's places again from OpenStreetMap"):
        if _run_download(short_name(city), refresh_city, city["name"]):
            st.rerun()
    if c2.button("Remove", type="tertiary", disabled=len(by_key) < 2,
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
    section_label("Your trip")
    with st.form("prefs_form"):
        tomorrow = date.today() + timedelta(days=1)
        date_range = st.date_input(
            f"Dates · max {MAX_TRIP_DAYS} days", value=(tomorrow, tomorrow + timedelta(days=2)),
            min_value=date.today(), help="Pick the first and last day of the trip.",
        )
        c1, c2 = st.columns(2)
        start_t = c1.time_input("Out from", value=time(10, 0), step=timedelta(minutes=15))
        end_t = c2.time_input("Back by", value=time(19, 0), step=timedelta(minutes=15))
        pace = st.radio(
            "Pace", list(PACES), index=list(PACES).index(DEFAULT_PACE), horizontal=True,
            format_func=lambda k: PACES[k]["label"],
            help="  \n".join(f"{p['label']}: {p['stops'][0]}–{p['stops'][1]} stops a day, "
                              f"at least {p['buffer']} min between them" for p in PACES.values()),
        )
        b_default, b_step = default_budget(currency)
        budget = st.number_input(f"Budget per person · {currency}", min_value=0.0,
                                 value=b_default, step=b_step, format="%.0f",
                                 help="For the whole trip: tickets, food and drinks. Not accommodation.")
        interests = st.multiselect("Interested in", INTERESTS_OPTIONS, default=["museums", "food", "parks"])
        notes = st.text_area("Notes for the planner", placeholder="Two kids, vegetarian, avoid stairs…")
        submitted = st.form_submit_button("Plan trip", type="primary", use_container_width=True)

    if not submitted:
        return None
    dates = _trip_dates(date_range)
    if not dates:
        st.error("Pick a first and last day.")
    elif len(dates) > MAX_TRIP_DAYS:
        st.error(f"That’s {len(dates)} days — the limit is {MAX_TRIP_DAYS}.")
    elif end_t <= start_t:
        st.error("“Back by” has to be later than “Out from”.")
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
