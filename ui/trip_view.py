"""Trip page: masthead, trip notes, day selector, selected day, PDF export."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from html import escape

import streamlit as st

from config import PACES
from ui.day_view import render_day
from ui.format import money

_NUM = {1: "One day", 2: "Two days", 3: "Three days", 4: "Four days", 5: "Five days",
        6: "Six days", 7: "Seven days", 8: "Eight days", 9: "Nine days", 10: "Ten days",
        11: "Eleven days"}


def _date_span(first: date, last: date) -> str:
    if first == last:
        return first.strftime("%-d %B")
    if first.month == last.month:
        return f"{first.day}–{last.strftime('%-d %B')}"
    return f"{first.strftime('%-d %b')} – {last.strftime('%-d %b')}"


def _day_label(day: dict) -> str:
    d = date.fromisoformat(day["date"])
    w = day.get("weather")
    weather = f"  {w['tmax']:.0f}° {w['label'].lower()}" if w else ""
    flag = " *" if not day["validation"]["ok"] else ""
    return f"{d.strftime('%a %-d')}{flag}{weather}"


def _pdf_section(result: dict, city_label: str):
    key = hashlib.sha1(json.dumps(result["plan"], sort_keys=True, default=str).encode()).hexdigest()
    cached = st.session_state.get("pdf")
    if cached and cached[0] == key:
        name = f"trip-{result['prefs']['city']}-{result['prefs']['dates'][0]}.pdf".replace(" ", "-")
        st.download_button("Download PDF guide", cached[1], file_name=name,
                           mime="application/pdf", type="primary")
    elif st.button("Create PDF guide", help="A printable guide: overview plus one page per day with a map"):
        from ui.pdf import build_trip_pdf
        with st.spinner("Drawing the maps…"):
            st.session_state["pdf"] = (key, build_trip_pdf(result, city_label))
        st.rerun()


def render_trip(result: dict, city_label: str):
    prefs, tv = result["prefs"], result["trip_validation"]
    cur = prefs["currency"]
    days = {d["date"]: d for d in result["days"]}
    isos = prefs["dates"]
    first, last = date.fromisoformat(isos[0]), date.fromisoformat(isos[-1])
    city = city_label.split(" — ")[0].split(",")[0]
    over = tv["total_cost"] > tv["budget_limit"]

    # ── Masthead ──
    st.markdown(
        f"<div class='masthead'>"
        f"<div class='mh-city'>{escape(city)}</div>"
        f"<div class='mh-budget{' over' if over else ''}'>{escape(money(tv['total_cost'], cur))}"
        f"<span> of {escape(money(tv['budget_limit'], cur))}</span></div></div>"
        f"<div class='mh-sub'>{_NUM.get(len(isos), f'{len(isos)} days')} · {_date_span(first, last)}"
        f" · {PACES[prefs['pace']]['label'].lower()} pace · {prefs['start_time']}–{prefs['end_time']}</div>",
        unsafe_allow_html=True)
    if result["plan"].get("trip_summary"):
        st.markdown(f"<p class='lede'>{escape(result['plan']['trip_summary'])}</p>", unsafe_allow_html=True)

    notes = []
    if not tv["budget_ok"]:
        notes.append(f"The plan comes to {money(tv['total_cost'], cur)}, over your "
                     f"{money(tv['budget_limit'], cur)} budget.")
    notes += [f"{x} appears on two days." for x in tv["repeated_places"]]
    notes += [f"No plan came back for {x}." for x in tv["missing_days"]]
    if notes:
        st.markdown("<div class='trip-notes'>" + "<br>".join(escape(n) for n in notes) + "</div>",
                    unsafe_allow_html=True)

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
    if any(not d["validation"]["ok"] for d in days.values()):
        st.caption("\\* something to check on that day")

    render_day(result, days[selected], cur)

    st.markdown("<hr class='rule'>", unsafe_allow_html=True)
    _pdf_section(result, city_label)
