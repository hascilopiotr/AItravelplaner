"""
Reusable presentation pieces (HTML built in one place, styled by ui/styles.css).
Every piece of text from data, OpenStreetMap or the AI goes through escape().
"""

from __future__ import annotations

import os
import unicodedata
from html import escape

import streamlit as st

_CSS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "styles.css")


def inject_styles():
    """Load ui/styles.css once per page run."""
    with open(_CSS_PATH, encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


def html(markup: str):
    st.markdown(markup, unsafe_allow_html=True)


def city_code(name: str) -> str:
    """Three-letter, departure-board style code: 'Kraków' -> 'KRA'."""
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    letters = [c for c in ascii_name.upper() if c.isalpha()]
    return "".join(letters[:3]) or "---"


def label(text: str, cls: str = "") -> str:
    return f"<span class='lbl {cls}'>{escape(text)}</span>"


def section_label(text: str):
    html(f"<div class='section-label'>{label(text)}</div>")


def brand():
    html("<div class='brand'>Trip planner</div>")


def boarding_pass(*, city: str, region: str, fields: list[tuple[str, str]], ref: str,
                  amount: str, of: str, state: str) -> str:
    """Trip summary as a boarding pass: route + fields on the left, budget stub on the right."""
    cells = "".join(f"<div>{label(k)}<div class='val'>{escape(v)}</div></div>" for k, v in fields)
    return (
        "<div class='pass' role='group' aria-label='Trip summary'>"
        "<div class='pass-main'>"
        f"<div class='pass-top'>{label('Itinerary')}{label(ref)}</div>"
        f"<div class='pass-route'><span class='pass-code'>{escape(city_code(city))}</span>"
        f"<span class='pass-city'>{escape(city)}</span>"
        f"<span class='pass-region'>{escape(region)}</span></div>"
        f"<div class='pass-fields'>{cells}</div>"
        "</div>"
        "<div class='pass-stub'>"
        f"<div>{label('Budget used')}<div class='pass-amount'>{escape(amount)}</div>"
        f"<div class='pass-of'>{escape(of)}</div></div>"
        f"<div class='pass-state'>{escape(state)}</div>"
        "</div></div>"
    )


def notes_block(title: str, lines: list[str]) -> str:
    body = "<br>".join(escape(x) for x in lines)
    return f"<div class='notes' role='note'>{label(title)}{body}</div>"


def stamp(text: str, ok: bool) -> str:
    """Passport-stamp status mark. The text carries the meaning, colour only reinforces it."""
    return f"<span class='stamp {'ok' if ok else 'check'}'>{escape(text)}</span>"


def day_header(title: str, weather: str, status: str, ok: bool, summary: str | None) -> str:
    out = (f"<div class='day-head'><h2>{escape(title)}</h2>{stamp(status, ok)}</div>"
           f"<div class='day-weather'>{escape(weather)}</div>")
    if summary:
        out += f"<p class='day-summary'>{escape(summary)}</p>"
    return out


def timetable_head(total: str) -> str:
    return (f"<div class='tt-head'>{label('Time')}{label('Stop')}"
            f"<span class='lbl' style='text-align:right'>{escape(total)}</span></div>")


def timetable_time(arrive: str, leave: str) -> str:
    return f"<div class='tt-time'>{escape(arrive)}<span>{escape(leave)}</span></div>"


def timetable_stop(n: int, name: str, price: str, meta: str, reason: str, hours: str | None) -> str:
    out = (f"<div class='tt-name'><b><span class='tt-num'>{n:02d}</span>{escape(name)}</b>"
           f"<span class='tt-price'>{escape(price)}</span></div>"
           f"<div class='tt-meta'>{escape(meta)}</div>"
           f"<div class='tt-reason'>{escape(reason)}</div>")
    if hours:
        out += f"<div class='tt-hours'>Hours {escape(hours)}</div>"
    return out


def timetable_leg(text: str) -> str:
    return f"<div class='tt-leg'>↓ {escape(text)}</div>"


def welcome(city: str):
    html(f"<div class='welcome'>{label('Planner')}<h1>{escape(city)}, day by day.</h1>"
         "<p>Set your dates, pace and what you'd like to see on the left. You'll get a plan "
         "built from real places in the city, checked against opening hours and walking times, "
         "with the forecast taken into account. It takes about half a minute.</p></div>")
