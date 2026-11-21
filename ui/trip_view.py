"""Trip page: header, trip issues, day strip, selected day, PDF export."""

from __future__ import annotations

import hashlib
import json
from datetime import date

import streamlit as st

from config import PACES
from ui.day_view import render_day
from ui.format import money


def _day_button_label(day: dict) -> str:
    d = date.fromisoformat(day["date"])
    w = day.get("weather")
    weather = f" · {w['emoji']} {w['tmax']:.0f}°" if w else ""
    status = "✅" if day["validation"]["ok"] else "⚠️"
    return f"{d.strftime('%a %d')} {status}{weather}"


def _select_day(iso: str):
    st.session_state["selected_day"] = iso


def _pdf_section(result: dict, city_label: str):
    key = hashlib.sha1(json.dumps(result["plan"], sort_keys=True, default=str).encode()).hexdigest()
    cached = st.session_state.get("pdf")
    if cached and cached[0] == key:
        name = f"trip-{result['prefs']['city']}-{result['prefs']['dates'][0]}.pdf".replace(" ", "-")
        st.download_button("📄 Download PDF guide", cached[1], file_name=name,
                           mime="application/pdf", type="primary", use_container_width=True)
    elif st.button("📄 Create PDF guide", use_container_width=True,
                   help="Cover page plus one page per day with a route map"):
        from ui.pdf import build_trip_pdf
        with st.spinner("Building your PDF (drawing the maps)..."):
            st.session_state["pdf"] = (key, build_trip_pdf(result, city_label))
        st.rerun()


def render_trip(result: dict, city_label: str):
    prefs, tv = result["prefs"], result["trip_validation"]
    cur = prefs["currency"]
    days = {d["date"]: d for d in result["days"]}
    first, last = date.fromisoformat(prefs["dates"][0]), date.fromisoformat(prefs["dates"][-1])
    city = city_label.split(" — ")[0].split(",")[0]

    # ── Header bar ──
    over = tv["total_cost"] > tv["budget_limit"]
    st.markdown(
        f"<div class='trip-header'><div class='trip-title'>{city}</div>"
        f"<div class='trip-sub'>{len(days)} days · {first.strftime('%d %b')} – {last.strftime('%d %b %Y')}"
        f" · {prefs['start_time']}–{prefs['end_time']} · {PACES[prefs['pace']]['label']}</div>"
        f"<div class='trip-budget {'over' if over else ''}'>{money(tv['total_cost'], cur)}"
        f" <span>/ {money(tv['budget_limit'], cur)}</span></div></div>",
        unsafe_allow_html=True)
    if result["plan"].get("trip_summary"):
        st.markdown(result["plan"]["trip_summary"])

    trip_issues = []
    if not tv["budget_ok"]:
        trip_issues.append(f"💸 Over budget: {money(tv['total_cost'], cur)} planned, "
                           f"budget {money(tv['budget_limit'], cur)}")
    trip_issues += [f"🔁 Visited twice: {x}" for x in tv["repeated_places"]]
    trip_issues += [f"📭 No plan returned for {x}" for x in tv["missing_days"]]
    for x in trip_issues:
        st.warning(x)

    # ── Day strip ──
    selected = st.session_state.get("selected_day")
    if selected not in days:
        selected = prefs["dates"][0]
        st.session_state["selected_day"] = selected
    isos = prefs["dates"]
    for row_start in range(0, len(isos), 7):
        row = isos[row_start:row_start + 7]
        cols = st.columns(7)
        for col, iso in zip(cols, row):
            col.button(_day_button_label(days[iso]), key=f"day_{iso}",
                       type="primary" if iso == selected else "secondary",
                       on_click=_select_day, args=(iso,), use_container_width=True)

    st.write("")
    render_day(result, days[selected], cur)

    st.divider()
    c1, c2 = st.columns([1, 2])
    with c1:
        _pdf_section(result, city_label)
    with c2:
        with st.expander("Raw plan JSON"):
            st.json(result["plan"])
