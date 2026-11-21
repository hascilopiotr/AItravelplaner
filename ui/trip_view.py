"""Trip page: destination poster, day tickets, the selected day, PDF export."""

from __future__ import annotations

import hashlib
import json
from datetime import date

import streamlit as st

from config import PACES
from data.photos import city_photo
from ui.components import city_code, weather_icon_name
from ui.day_view import render_day
from ui.format import money
from ui.widgets import day_strip, hero


def _sig(obj) -> str:
    return hashlib.sha1(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()[:12]


def _n_issues(v: dict) -> int:
    return len(v["hours_violations"]) + len(v["travel_violations"]) + len(v["unknown_places"])


def _hero_data(result: dict, city: str, region: str) -> dict:
    prefs, tv = result["prefs"], result["trip_validation"]
    cur, isos = prefs["currency"], prefs["dates"]
    first, last = date.fromisoformat(isos[0]), date.fromisoformat(isos[-1])
    n_stops = sum(len(d["plan"].get("stops", [])) for d in result["days"])
    left = tv["budget_limit"] - tv["total_cost"]
    limit = tv["budget_limit"] or 0
    span = (first.strftime("%a %-d %b") if first == last
            else f"{first.strftime('%a %-d %b')} – {last.strftime('%a %-d %b %Y')}")

    notices = []
    if not tv["budget_ok"]:
        notices.append({"kind": "error", "text": f"Over budget by {money(-left, cur)} per person."})
    notices += [{"kind": "warn", "text": f"Planned twice: {x}"} for x in tv["repeated_places"]]
    notices += [{"kind": "warn", "text": f"No plan for {x}"} for x in tv["missing_days"]]

    return {
        "sig": _sig([prefs, result["plan"]]),
        "city": city, "region": region, "code": city_code(city), "photo": city_photo(city),
        "dates": span,
        "ref": f"{first.strftime('%d%b').upper()}-{len(isos):02d}D",
        "postmark": f"{city.upper()} · {first.strftime('%d %b %Y').upper()} · ",
        "stats": [
            {"label": "Days", "value": len(isos), "icon": "calendar_month",
             "note": f"{prefs['start_time']}–{prefs['end_time']} daily"},
            {"label": "Stops", "value": n_stops, "icon": "pin_drop",
             "note": f"about {n_stops / len(isos):.0f} a day"},
            {"label": "Pace", "text": PACES[prefs["pace"]]["label"], "icon": "directions_walk",
             "note": ", ".join(prefs.get("interests", [])[:3])},
        ],
        "budget": {
            "used": money(tv["total_cost"], cur),
            "pct": 100 * tv["total_cost"] / limit if limit else 0,
            "over": left < 0,
            "note": (f"{money(abs(left), cur)} {'left of' if left >= 0 else 'over'} "
                     f"{money(limit, cur)}"),
        },
        "lede": result["plan"].get("trip_summary") or "",
        "notices": notices,
    }


def _strip_data(result: dict, selected: str) -> dict:
    days = []
    for d in result["days"]:
        dt = date.fromisoformat(d["date"])
        w = d.get("weather")
        days.append({
            "iso": d["date"], "d": dt.strftime("%-d"), "dow": dt.strftime("%a").upper(),
            "mon": dt.strftime("%b").upper(), "long": dt.strftime("%A %-d %B"),
            "wx_icon": weather_icon_name(w.get("code")) if w else None,
            "temp": f"{w['tmax']:.0f}°" if w and w.get("tmax") is not None else None,
            "weather": w.get("label") if w else None,
            "stops": len(d["plan"].get("stops", [])),
            "issues": _n_issues(d["validation"]),
        })
    return {"sig": _sig([result["prefs"], [x["iso"] for x in days]]), "selected": selected, "days": days}


def _pdf_section(result: dict, city_label: str):
    key = _sig(result["plan"])
    st.html("<div class='tp-pdf-head'><span class='material-symbols-rounded'>luggage</span>"
            "<div><b>Take it offline</b><span>An overview page, then one page per day with its map.</span></div></div>")
    cached = st.session_state.get("pdf")
    if cached and cached[0] == key:
        name = f"trip-{result['prefs']['city']}-{result['prefs']['dates'][0]}.pdf".replace(" ", "-")
        st.download_button(f"Download PDF · {len(result['days']) + 1} pages", cached[1], file_name=name,
                           mime="application/pdf", icon=":material/download:", type="primary")
    elif st.button("Prepare pocket guide", icon=":material/picture_as_pdf:"):
        from ui.pdf import build_trip_pdf
        with st.spinner("Drawing the day maps…"):
            st.session_state["pdf"] = (key, build_trip_pdf(result, city_label))
        st.rerun()


def _pick_day(iso: str):
    st.session_state["selected_day"] = iso


def render_trip(result: dict, city_label: str):
    days = {d["date"]: d for d in result["days"]}
    isos = result["prefs"]["dates"]
    city, _, region = city_label.partition(" — ")
    city = city.split(",")[0]

    hero(_hero_data(result, city, region))

    if st.session_state.get("selected_day") not in days:
        st.session_state["selected_day"] = isos[0]
    selected = st.session_state["selected_day"]

    if len(isos) > 1:
        day_strip(_strip_data(result, selected), on_pick=_pick_day)

    render_day(result, days[selected], isos.index(selected) + 1, len(isos))

    with st.container(key="tp_pdf"):
        _pdf_section(result, city_label)
