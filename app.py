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

st.set_page_config(page_title="Travel Planner", layout="wide")

st.markdown("""
<style>
.block-container {padding-top: 2.2rem; max-width: 1280px;}
[data-testid="stHeader"] {background: transparent;}
h1, h2, h3 {letter-spacing: -0.01em;}

/* sidebar */
.side-title {font-family: Fraunces, serif; font-size: 1.35rem; font-weight: 600; margin: 0 0 1rem;}
.side-label {font-size: 0.72rem; font-weight: 600; letter-spacing: 0.12em; text-transform: uppercase;
             color: #8a7f70; margin: 0.4rem 0 0.2rem;}

/* masthead */
.masthead {display: flex; justify-content: space-between; align-items: baseline; gap: 1rem;
           border-bottom: 1px solid #1e1b17; padding-bottom: 0.35rem;}
.mh-city {font-family: Fraunces, serif; font-size: 2.6rem; font-weight: 600; letter-spacing: 0.02em;
          text-transform: uppercase; line-height: 1.1;}
.mh-budget {font-size: 1.15rem; font-weight: 600; font-variant-numeric: tabular-nums;}
.mh-budget span {font-weight: 400; color: #8a7f70;}
.mh-budget.over {color: #8a2c1c;}
.mh-sub {color: #5f574c; margin: 0.45rem 0 0.9rem; font-size: 0.95rem;}
.lede {font-family: Fraunces, serif; font-size: 1.12rem; line-height: 1.55; color: #3a342d;
       max-width: 52rem; margin-bottom: 1.2rem;}
.trip-notes {border-left: 2px solid #8a2c1c; padding: 0.2rem 0 0.2rem 0.8rem; color: #5f574c;
             margin-bottom: 1rem; font-size: 0.92rem;}

/* day */
.day-head {display: flex; justify-content: space-between; align-items: baseline; gap: 1rem;
           margin-top: 1.4rem;}
.day-head h2 {font-family: Fraunces, serif; font-size: 1.7rem; margin: 0; padding: 0;}
.day-weather {color: #8a7f70; font-size: 0.9rem; text-align: right;}
.day-summary {font-style: italic; color: #5f574c; margin: 0.2rem 0 1rem;}

/* timeline */
.tl-total {font-size: 0.72rem; font-weight: 600; letter-spacing: 0.12em; text-transform: uppercase;
           color: #8a7f70; border-bottom: 1px solid #ddd3c4; padding-bottom: 0.4rem; margin-bottom: 0.8rem;}
.tl-time {font-variant-numeric: tabular-nums; font-weight: 600; line-height: 1.25;}
.tl-time span {display: block; font-weight: 400; color: #8a7f70; font-size: 0.85rem;}
.tl-name {font-family: Fraunces, serif; font-size: 1.08rem; font-weight: 600; line-height: 1.3;}
.tl-num {display: inline-block; min-width: 1.35rem; height: 1.35rem; line-height: 1.35rem; margin-right: 0.45rem;
         border-radius: 50%; background: #8a2c1c; color: #fff; text-align: center;
         font-family: Inter, sans-serif; font-size: 0.75rem; font-weight: 600; vertical-align: 0.12rem;}
.tl-meta {color: #5f574c; font-size: 0.86rem; margin-top: 0.15rem;}
.tl-reason {color: #3a342d; font-size: 0.9rem; margin-top: 0.25rem;}
.tl-hours {color: #8a7f70; font-size: 0.78rem; margin-top: 0.2rem;}
.tl-leg {color: #8a7f70; font-size: 0.8rem; margin: -0.3rem 0 0.5rem 4.6rem;
         padding-left: 0.7rem; border-left: 1px solid #c9bba7;}
hr.rule {border: 0; border-top: 1px solid #ddd3c4; margin: 2rem 0 1rem;}
</style>
""", unsafe_allow_html=True)

if not ANTHROPIC_API_KEY or ANTHROPIC_API_KEY == "your_key_here":
    st.error("No Anthropic API key found. Add `ANTHROPIC_API_KEY=...` to the `.env` file and restart.")
    st.stop()

init_db()

with st.sidebar:
    st.markdown("<div class='side-title'>Travel Planner</div>", unsafe_allow_html=True)
    city = city_section()
    st.divider()
    prefs = trip_form(city)

if prefs:
    n = len(prefs["dates"])
    with st.spinner(f"Planning {n} day{'s' if n > 1 else ''} in {short_name(city)}"
                    + (" — longer trips take a minute or two…" if n > 3 else "…")):
        try:
            st.session_state["result"] = run_trip(prefs)
            st.session_state["selected_day"] = prefs["dates"][0]
            st.session_state["day_strip"] = prefs["dates"][0]
            st.session_state.pop("pdf", None)
        except Exception as e:  # show any API / parsing error in the UI
            st.session_state.pop("result", None)
            st.error(f"Could not generate a plan: {e}")

result = st.session_state.get("result")
if not result or "prefs" not in result or result["prefs"]["city"] != city["name"]:
    st.markdown(
        f"<div class='masthead'><div class='mh-city'>{short_name(city)}</div></div>"
        "<p class='lede' style='margin-top:1rem'>Choose your dates, pace and what you'd like to see, "
        "and you'll get a day-by-day plan built from real places in the city — checked against "
        "opening hours, walking times and your budget, with the weather taken into account.</p>",
        unsafe_allow_html=True)
    st.stop()

render_trip(result, city["display_name"])
