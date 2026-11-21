"""
Streamlit frontend.
Usage: streamlit run app.py
"""

import streamlit as st

from config import ANTHROPIC_API_KEY
from data.db import init_db
from planner.pipeline import run_trip
from ui.components import brand, inject_styles, welcome
from ui.format import short_name
from ui.sidebar import city_section, trip_form
from ui.trip_view import render_trip

st.set_page_config(page_title="Trip planner", layout="wide")

inject_styles()

if not ANTHROPIC_API_KEY or ANTHROPIC_API_KEY == "your_key_here":
    st.error("No Anthropic key found. Add `ANTHROPIC_API_KEY=…` to `.env`, then restart the app.")
    st.stop()

init_db()

with st.sidebar:
    brand()
    city = city_section()
    prefs = trip_form(city)

if prefs:
    n = len(prefs["dates"])
    with st.spinner(f"Checking opening hours and walking times for {n} day{'s' if n > 1 else ''} "
                    f"in {short_name(city)}" + (" — about a minute" if n > 3 else " — about 30 seconds")):
        try:
            st.session_state["result"] = run_trip(prefs)
            st.session_state["selected_day"] = prefs["dates"][0]
            st.session_state["day_strip"] = prefs["dates"][0]
            st.session_state.pop("pdf", None)
        except Exception as e:  # show any API / parsing error in the UI
            st.session_state.pop("result", None)
            st.error(f"The plan didn't come through: {e}")

result = st.session_state.get("result")
if not result or "prefs" not in result or result["prefs"]["city"] != city["name"]:
    welcome(short_name(city))
    st.stop()

render_trip(result, city["display_name"])
