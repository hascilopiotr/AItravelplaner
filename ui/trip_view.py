"""Trip page: boarding-pass summary, notes, day selector, selected day, PDF export."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from html import escape

import streamlit as st

from config import PACES
from ui.components import boarding_pass, html, notes_block
from ui.day_view import render_day
from ui.format import money


def _day_label(day: dict) -> str:
    d = date.fromisoformat(day["date"])
    w = day.get("weather")
    weather = f" · {w['tmax']:.0f}° {w['label']}" if w else ""
    flag = " · check" if not day["validation"]["ok"] else ""
    return f"{d.strftime('%a %-d')}{weather}{flag}"


def _pdf_section(result: dict, city_label: str):
    key = hashlib.sha1(json.dumps(result["plan"], sort_keys=True, default=str).encode()).hexdigest()
    cached = st.session_state.get("pdf")
    if cached and cached[0] == key:
        name = f"trip-{result['prefs']['city']}-{result['prefs']['dates'][0]}.pdf".replace(" ", "-")
        st.download_button(f"Download PDF · {len(result['days']) + 1} pages", cached[1], file_name=name,
                           mime="application/pdf", type="secondary")
    elif st.button("Prepare printable guide", type="secondary",
                   help="One overview page, then a page per day with its map"):
        from ui.pdf import build_trip_pdf
        with st.spinner("Drawing the day maps…"):
            st.session_state["pdf"] = (key, build_trip_pdf(result, city_label))
        st.rerun()


def render_trip(result: dict, city_label: str):
    prefs, tv = result["prefs"], result["trip_validation"]
    cur = prefs["currency"]
    days = {d["date"]: d for d in result["days"]}
    isos = prefs["dates"]
    first, last = date.fromisoformat(isos[0]), date.fromisoformat(isos[-1])
    city, _, region = city_label.partition(" — ")
    city = city.split(",")[0]
    over = tv["total_cost"] > tv["budget_limit"]
    n_check = sum(1 for d in days.values() if not d["validation"]["ok"])

    # ── Boarding pass ──
    html(boarding_pass(
        city=city, region=region,
        ref=f"{first.strftime('%d%b').upper()}-{len(isos):02d}D",
        fields=[("Arrive", first.strftime("%a %-d %b")), ("Leave", last.strftime("%a %-d %b")),
                ("Days", f"{len(isos):02d}"), ("Pace", PACES[prefs["pace"]]["label"]),
                ("Out / back", f"{prefs['start_time']}–{prefs['end_time']}")],
        amount=money(tv["total_cost"], cur),
        of=f"of {money(tv['budget_limit'], cur)} per person",
        state="Over budget" if over else
              (f"{n_check} day{'s' if n_check != 1 else ''} to check" if n_check else "All days clear"),
    ))
    if result["plan"].get("trip_summary"):
        html(f"<p class='lede'>{escape(result['plan']['trip_summary'])}</p>")

    notes = []
    if not tv["budget_ok"]:
        notes.append(f"The plan comes to {money(tv['total_cost'], cur)}, "
                     f"{money(tv['total_cost'] - tv['budget_limit'], cur)} over budget.")
    notes += [f"{x} is on two days." for x in tv["repeated_places"]]
    notes += [f"No plan came back for {x}." for x in tv["missing_days"]]
    if notes:
        html(notes_block("Before you book", notes))

    # ── Day selector ──
    if st.session_state.get("day_strip") not in days:
        st.session_state["day_strip"] = isos[0]
    picked = st.segmented_control(
        "Day", isos, key="day_strip", label_visibility="collapsed",
        format_func=lambda iso: _day_label(days[iso]),
    )
    selected = picked if picked in days else st.session_state.get("selected_day", isos[0])
    if selected not in days:
        selected = isos[0]
    st.session_state["selected_day"] = selected

    render_day(result, days[selected], cur)

    html("<hr class='rule'>")
    _pdf_section(result, city_label)
