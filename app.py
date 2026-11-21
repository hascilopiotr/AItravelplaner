"""
Streamlit frontend.
Usage: streamlit run app.py
"""

from datetime import date, time, timedelta

import pandas as pd
import pydeck as pdk
import streamlit as st

from config import ANTHROPIC_API_KEY, DEFAULT_CITY, INTERESTS_OPTIONS
from data.cities import CityNotFound, ensure_city
from data.db import delete_city, get_place_by_id, init_db, list_cities
from planner.pipeline import run

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
NEW_CITY = "➕ Add another city…"

st.set_page_config(page_title="AI Travel Planner", page_icon="🗺️", layout="wide")

if not ANTHROPIC_API_KEY or ANTHROPIC_API_KEY == "your_key_here":
    st.error("No Anthropic API key found. Add `ANTHROPIC_API_KEY=...` to the `.env` file and restart.")
    st.stop()

init_db()


def load_city(name: str, refresh: bool = False) -> bool:
    """Download (if needed) and select a city. Returns True on success."""
    verb = "Refreshing" if refresh else "Loading"
    with st.spinner(f"{verb} places for {name} from OpenStreetMap (~30 s the first time)..."):
        try:
            record = ensure_city(name, refresh=refresh)
        except CityNotFound as e:
            st.sidebar.error(str(e))
            return False
        except Exception as e:  # network / Overpass errors
            st.sidebar.error(f"Could not download places for {name}: {e}")
            return False
    st.session_state["city"] = record["name"]
    st.session_state.pop("result", None)
    return True


# First launch: make sure the default city is available.
cities = list_cities()
if not cities:
    if not load_city(DEFAULT_CITY):
        st.stop()
    cities = list_cities()

by_key = {c["name"]: c for c in cities}
if st.session_state.get("city") not in by_key:
    st.session_state["city"] = cities[0]["name"]


# ── Sidebar: city ───────────────────────────────────────────────────────────

with st.sidebar:
    st.header("City")
    keys = list(by_key)
    choice = st.selectbox(
        "City", keys + [NEW_CITY], index=keys.index(st.session_state["city"]),
        format_func=lambda k: k if k == NEW_CITY else by_key[k]["display_name"].split(",")[0],
        label_visibility="collapsed",
    )
    if choice == NEW_CITY:
        with st.form("new_city", clear_on_submit=True):
            new_name = st.text_input("City name", placeholder="e.g. Kraków, Wrocław, Prague")
            if st.form_submit_button("Download places", use_container_width=True) and new_name.strip():
                if load_city(new_name.strip()):
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
        if load_city(city["display_name"].split(",")[0], refresh=True):
            st.rerun()
    if c2.button("🗑️ Remove", use_container_width=True, disabled=len(by_key) < 2,
                 help="Delete this city's places from the local database"):
        delete_city(city["name"])
        st.session_state.pop("city", None)
        st.session_state.pop("result", None)
        st.rerun()

city_name = city["display_name"].split(",")[0]

st.title(f"🗺️ AI Travel Planner — {city_name}")
st.caption("A one-day plan built by Claude from real OpenStreetMap places, then checked "
           "against your budget, opening hours and travel times.")


# ── Sidebar: preferences ────────────────────────────────────────────────────

with st.sidebar:
    st.header("Your day")
    with st.form("prefs_form"):
        visit_date = st.date_input("Date", value=date.today() + timedelta(days=1), min_value=date.today())
        c1, c2 = st.columns(2)
        start_t = c1.time_input("Start", value=time(10, 0), step=timedelta(minutes=15))
        end_t = c2.time_input("End", value=time(19, 0), step=timedelta(minutes=15))
        budget = st.slider("Budget (PLN)", min_value=0, max_value=1000, value=150, step=10)
        interests = st.multiselect("Interests", INTERESTS_OPTIONS, default=["museums", "food", "parks"])
        notes = st.text_area("Notes (optional)", placeholder="e.g. travelling with kids, vegetarian, no stairs")
        submitted = st.form_submit_button("✨ Generate plan", type="primary", use_container_width=True)


# ── Generate ────────────────────────────────────────────────────────────────

if submitted:
    if end_t <= start_t:
        st.sidebar.error("End time must be after start time.")
    elif not interests:
        st.sidebar.error("Pick at least one interest.")
    else:
        prefs = {
            "city": city["name"],
            "budget_pln": float(budget),
            "start_time": start_t.strftime("%H:%M"),
            "end_time": end_t.strftime("%H:%M"),
            "interests": interests,
            "day_of_week": DAYS[visit_date.weekday()],
            "visit_date": visit_date.isoformat(),
            "notes": notes.strip(),
        }
        with st.spinner("Claude is planning your day..."):
            try:
                st.session_state["result"] = run(prefs)
                st.session_state["prefs"] = prefs
            except Exception as e:  # show any API / parsing error in the UI
                st.session_state.pop("result", None)
                st.error(f"Could not generate a plan: {e}")

result = st.session_state.get("result")
if not result:
    st.info("Set your preferences in the sidebar and press **Generate plan**.")
    st.stop()


# ── Results ─────────────────────────────────────────────────────────────────

plan, validation, prefs = result["plan"], result["validation"], st.session_state["prefs"]
stops = plan.get("stops", [])

rows = []
for i, s in enumerate(stops, 1):
    place = get_place_by_id(prefs["city"], s.get("place_id", "")) or {}
    rows.append({
        "n": i,
        "name": s.get("name", "?"),
        "arrival": s.get("arrival", ""),
        "departure": s.get("departure", ""),
        "cost_pln": float(s.get("cost_pln", 0) or 0),
        "reason": s.get("reason", ""),
        "subcategory": place.get("subcategory", ""),
        "address": place.get("address") or "",
        "opening_hours": place.get("opening_hours") or "unknown",
        "lat": place.get("lat"),
        "lon": place.get("lon"),
    })
df = pd.DataFrame(rows)

st.subheader(f"{prefs['day_of_week']}, {prefs['visit_date']} · {prefs['start_time']}–{prefs['end_time']}")
st.write(plan.get("plan_summary", ""))

m1, m2, m3 = st.columns(3)
m1.metric("Stops", len(stops))
m2.metric("Total cost", f"{validation['total_cost']:.0f} PLN",
          delta=f"{validation['budget_limit'] - validation['total_cost']:.0f} PLN left",
          delta_color="normal" if validation["budget_ok"] else "inverse")
m3.metric("Validation", "✅ Passed" if validation["ok"] else "⚠️ Issues")

if not validation["ok"]:
    with st.container(border=True):
        st.markdown("**Validation issues**")
        if not validation["budget_ok"]:
            st.markdown(f"- 💸 Budget exceeded: {validation['total_cost']:.0f} PLN "
                        f"> {validation['budget_limit']:.0f} PLN")
        for v in validation["hours_violations"]:
            st.markdown(f"- 🕒 Opening hours: {v}")
        for v in validation["travel_violations"]:
            st.markdown(f"- 🚶 Travel time: {v}")
        for v in validation["unknown_places"]:
            st.markdown(f"- ❓ Not in database: {v}")

left, right = st.columns([1, 1], gap="large")

with left:
    st.markdown("#### Itinerary")
    for r in rows:
        with st.container(border=True):
            st.markdown(f"**{r['n']}. {r['name']}**  \n"
                        f"🕒 {r['arrival']}–{r['departure']} · 💰 {r['cost_pln']:.0f} PLN"
                        + (f" · _{r['subcategory']}_" if r["subcategory"] else ""))
            st.caption(r["reason"])
            details = [x for x in (r["address"], f"Hours: {r['opening_hours']}") if x]
            st.caption(" · ".join(details))

with right:
    st.markdown("#### Map")
    geo = df.dropna(subset=["lat", "lon"]) if not df.empty else df
    if geo.empty:
        st.caption("No coordinates available for these stops.")
    else:
        path = [{"path": geo[["lon", "lat"]].values.tolist()}]
        layers = [
            pdk.Layer("PathLayer", path, get_path="path", get_color=[255, 140, 0],
                      width_min_pixels=3),
            pdk.Layer("ScatterplotLayer", geo, get_position=["lon", "lat"],
                      get_fill_color=[220, 30, 60], get_radius=60, radius_min_pixels=7,
                      pickable=True),
            pdk.Layer("TextLayer", geo.assign(label=geo["n"].astype(str)),
                      get_position=["lon", "lat"], get_text="label", get_size=14,
                      get_color=[255, 255, 255], get_alignment_baseline="'center'"),
        ]
        view = pdk.ViewState(latitude=geo["lat"].mean(), longitude=geo["lon"].mean(), zoom=13)
        st.pydeck_chart(pdk.Deck(layers=layers, initial_view_state=view,
                                 tooltip={"text": "{n}. {name}\n{arrival}–{departure}"}))

with st.expander("Raw plan JSON"):
    st.json(plan)
