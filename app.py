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
from planner.pipeline import MAX_TRIP_DAYS, run_trip

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
    st.header("Your trip")
    with st.form("prefs_form"):
        tomorrow = date.today() + timedelta(days=1)
        date_range = st.date_input(
            f"Dates (up to {MAX_TRIP_DAYS} days)", value=(tomorrow, tomorrow + timedelta(days=2)),
            min_value=date.today(), help="Pick the first and last day of the trip.",
        )
        c1, c2 = st.columns(2)
        start_t = c1.time_input("Daily start", value=time(10, 0), step=timedelta(minutes=15))
        end_t = c2.time_input("Daily end", value=time(19, 0), step=timedelta(minutes=15))
        budget = st.slider("Trip budget (PLN, all days)", min_value=0, max_value=5000, value=450, step=50)
        interests = st.multiselect("Interests", INTERESTS_OPTIONS, default=["museums", "food", "parks"])
        notes = st.text_area("Notes (optional)", placeholder="e.g. travelling with kids, vegetarian, no stairs")
        submitted = st.form_submit_button("✨ Generate plan", type="primary", use_container_width=True)


# ── Generate ────────────────────────────────────────────────────────────────

def _trip_dates(rng) -> list[date]:
    if isinstance(rng, date):
        rng = (rng, rng)
    if not rng:
        return []
    start, end = rng[0], rng[-1]
    return [start + timedelta(days=i) for i in range((end - start).days + 1)]


if submitted:
    dates = _trip_dates(date_range)
    if not dates:
        st.sidebar.error("Pick the trip dates.")
    elif len(dates) > MAX_TRIP_DAYS:
        st.sidebar.error(f"Trips can be at most {MAX_TRIP_DAYS} days (you picked {len(dates)}).")
    elif end_t <= start_t:
        st.sidebar.error("Daily end time must be after the start time.")
    elif not interests:
        st.sidebar.error("Pick at least one interest.")
    else:
        prefs = {
            "city": city["name"],
            "dates": [d.isoformat() for d in dates],
            "budget_pln": float(budget),
            "start_time": start_t.strftime("%H:%M"),
            "end_time": end_t.strftime("%H:%M"),
            "interests": interests,
            "notes": notes.strip(),
        }
        n = len(dates)
        with st.spinner(f"Claude is planning your {n}-day trip"
                        + (" (longer trips take a minute or two)..." if n > 3 else "...")):
            try:
                st.session_state["result"] = run_trip(prefs)
                st.session_state["prefs"] = prefs
                st.session_state["selected_day"] = prefs["dates"][0]
            except Exception as e:  # show any API / parsing error in the UI
                st.session_state.pop("result", None)
                st.error(f"Could not generate a plan: {e}")

result = st.session_state.get("result")
if not result or "days" not in result:
    st.info("Pick your dates and preferences in the sidebar and press **Generate plan**.")
    st.stop()


# ── Helpers ─────────────────────────────────────────────────────────────────

def _issues(v: dict) -> list[str]:
    out = [f"🕒 {x}" for x in v["hours_violations"]]
    out += [f"🚶 Travel time: {x}" for x in v["travel_violations"]]
    out += [f"❓ Not in database: {x}" for x in v["unknown_places"]]
    return out


def _select_day(iso: str):
    st.session_state["selected_day"] = iso


def render_day(day: dict, city_key: str):
    plan, v = day["plan"], day["validation"]
    stops = plan.get("stops", [])
    d = date.fromisoformat(day["date"])

    st.subheader(f"{day['day_of_week']}, {d.strftime('%d %B %Y')}")
    if plan.get("summary"):
        st.write(plan["summary"])

    issues = _issues(v)
    if issues:
        with st.container(border=True):
            st.markdown("**Issues on this day**")
            for x in issues:
                st.markdown(f"- {x}")

    if not stops:
        st.warning("No stops were planned for this day.")
        return

    rows = []
    for i, s in enumerate(stops, 1):
        place = get_place_by_id(city_key, s.get("place_id", "")) or {}
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

    left, right = st.columns([1, 1], gap="large")
    with left:
        st.markdown(f"#### Itinerary · {len(stops)} stops · {v['total_cost']:.0f} PLN")
        for r in rows:
            with st.container(border=True):
                st.markdown(f"**{r['n']}. {r['name']}**  \n"
                            f"🕒 {r['arrival']}–{r['departure']} · 💰 {r['cost_pln']:.0f} PLN"
                            + (f" · _{r['subcategory']}_" if r["subcategory"] else ""))
                st.caption(r["reason"])
                st.caption(" · ".join(x for x in (r["address"], f"Hours: {r['opening_hours']}") if x))

    with right:
        st.markdown("#### Map")
        geo = df.dropna(subset=["lat", "lon"])
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


# ── Trip overview ───────────────────────────────────────────────────────────

prefs, tv = st.session_state["prefs"], result["trip_validation"]
days = {d["date"]: d for d in result["days"]}
first, last = date.fromisoformat(prefs["dates"][0]), date.fromisoformat(prefs["dates"][-1])

st.subheader(f"{len(days)}-day trip · {first.strftime('%d %b')} – {last.strftime('%d %b %Y')} · "
             f"{prefs['start_time']}–{prefs['end_time']} daily")
st.write(result["plan"].get("trip_summary", ""))

n_issue_days = sum(1 for d in days.values() if not d["validation"]["ok"])
m1, m2, m3, m4 = st.columns(4)
m1.metric("Days", len(days))
m2.metric("Stops", sum(len(d["plan"].get("stops", [])) for d in days.values()))
m3.metric("Total cost", f"{tv['total_cost']:.0f} PLN",
          delta=f"{tv['budget_limit'] - tv['total_cost']:.0f} PLN left",
          delta_color="normal" if tv["budget_ok"] else "inverse")
m4.metric("Validation", "✅ Passed" if tv["ok"] else f"⚠️ Issues on {n_issue_days} day(s)"
          if n_issue_days else "⚠️ Trip issues")

trip_issues = []
if not tv["budget_ok"]:
    trip_issues.append(f"💸 Trip budget exceeded: {tv['total_cost']:.0f} PLN > {tv['budget_limit']:.0f} PLN")
trip_issues += [f"🔁 Visited twice: {x}" for x in tv["repeated_places"]]
trip_issues += [f"📭 No plan returned for {x}" for x in tv["missing_days"]]
if trip_issues:
    with st.container(border=True):
        st.markdown("**Trip issues**")
        for x in trip_issues:
            st.markdown(f"- {x}")


# ── Week grid ───────────────────────────────────────────────────────────────

st.markdown("#### Your week")
st.caption("Click a day to see its plan.")

header = st.columns(7)
for col, name in zip(header, DAYS):
    col.markdown(f"<div style='text-align:center;font-weight:600'>{name[:3]}</div>",
                 unsafe_allow_html=True)

week_start = first - timedelta(days=first.weekday())
selected = st.session_state.get("selected_day", prefs["dates"][0])
while week_start <= last:
    cols = st.columns(7)
    for i, col in enumerate(cols):
        d = week_start + timedelta(days=i)
        iso = d.isoformat()
        with col:
            if iso in days:
                day = days[iso]
                v = day["validation"]
                n_stops = len(day["plan"].get("stops", []))
                with st.container(border=True):
                    st.markdown(f"**{d.strftime('%d %b')}** {'✅' if v['ok'] else '⚠️'}")
                    st.caption(f"{n_stops} stops · {v['total_cost']:.0f} PLN")
                    st.button("Viewing" if iso == selected else "Open", key=f"day_{iso}",
                              type="primary" if iso == selected else "secondary",
                              on_click=_select_day, args=(iso,), use_container_width=True)
            else:
                st.markdown(
                    f"<div style='text-align:center;color:#999;padding:2.2rem 0;"
                    f"border:1px dashed #ddd;border-radius:0.5rem'>{d.strftime('%d %b')}</div>",
                    unsafe_allow_html=True)
    week_start += timedelta(days=7)

st.divider()
render_day(days.get(selected) or days[prefs["dates"][0]], prefs["city"])

with st.expander("Raw plan JSON"):
    st.json(result["plan"])
