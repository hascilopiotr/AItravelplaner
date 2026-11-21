"""
Streamlit frontend.
Usage: streamlit run app.py
"""

import streamlit as st

from config import ANTHROPIC_API_KEY
from data.db import init_db
from planner.pipeline import run_trip
from ui.format import short_name
from ui.sidebar import city_section, trip_form
from ui.trip_view import render_trip

st.set_page_config(page_title="AI Travel Planner", page_icon="🗺️", layout="wide")

st.markdown("""
<style>
.block-container {padding-top: 2rem;}
.trip-header {display:flex; align-items:baseline; gap:1.2rem; flex-wrap:wrap;
              padding:0.9rem 1.2rem; border-radius:0.8rem; margin-bottom:0.6rem;
              background:linear-gradient(90deg,#fdecea,#fff6f0);}
.trip-title {font-size:2rem; font-weight:800; color:#c0392b;}
.trip-sub {color:#555; flex:1;}
.trip-budget {font-size:1.3rem; font-weight:700; color:#27ae60;}
.trip-budget.over {color:#c0392b;}
.trip-budget span {font-size:0.95rem; font-weight:400; color:#777;}
.weather-card {text-align:right; font-size:1.1rem; padding-top:1.1rem; color:#444;}
.pin {display:inline-block; width:1.5rem; height:1.5rem; line-height:1.5rem; border-radius:50%;
      background:#e74c3c; color:#fff; text-align:center; font-weight:700; font-size:0.85rem;}
.meta {color:#666; font-size:0.9rem;}
.leg {color:#888; font-size:0.85rem; margin:-0.4rem 0 -0.4rem 0.9rem;
      border-left:2px dashed #e0b4ae; padding-left:0.8rem;}
</style>
""", unsafe_allow_html=True)

if not ANTHROPIC_API_KEY or ANTHROPIC_API_KEY == "your_key_here":
    st.error("No Anthropic API key found. Add `ANTHROPIC_API_KEY=...` to the `.env` file and restart.")
    st.stop()

init_db()

with st.sidebar:
    st.markdown("## 🗺️ AI Travel Planner")
    city = city_section()
    st.divider()
    prefs = trip_form(city)

if prefs:
    n = len(prefs["dates"])
    with st.spinner(f"Claude is planning your {n}-day trip to {short_name(city)}"
                    + (" — longer trips take a minute or two..." if n > 3 else "...")):
        try:
            st.session_state["result"] = run_trip(prefs)
            st.session_state["selected_day"] = prefs["dates"][0]
            st.session_state.pop("pdf", None)
        except Exception as e:  # show any API / parsing error in the UI
            st.session_state.pop("result", None)
            st.error(f"Could not generate a plan: {e}")

result = st.session_state.get("result")
if not result or "prefs" not in result or result["prefs"]["city"] != city["name"]:
    st.markdown(f"# Plan your trip to {short_name(city)}")
    st.markdown(
        "Pick your **dates**, **pace**, **budget** and **interests** in the sidebar and press "
        "**✨ Plan my trip**.\n\n"
        "- Claude builds a day-by-day plan from real OpenStreetMap places, using the weather forecast\n"
        "- every day is checked for opening hours, travel times and budget\n"
        "- swap any stop with **⇄**, open a day in **Google Maps**, or download a **PDF guide**")
    st.stop()

render_trip(result, city["display_name"])
