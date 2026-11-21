"""
Shared presentation pieces: stylesheet, icons, sidebar brand, welcome and loading screens.

Static HTML here is built from our own strings; anything that comes from the user,
OpenStreetMap or the AI goes through escape(). The interactive pieces (hero, day strip,
day board) live in ui/widgets.py and build their DOM with textContent.
"""

from __future__ import annotations

import os
import unicodedata
from html import escape

import streamlit as st

_CSS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "styles.css")

# Material Symbols name per place type (shown where the type of place matters).
PLACE_ICONS = {
    "museum": "museum", "gallery": "palette", "arts": "palette", "landmark": "location_on",
    "viewpoint": "landscape", "monument": "account_balance", "memorial": "account_balance",
    "historic": "account_balance", "castle": "castle", "church": "church",
    "park": "park", "garden": "local_florist", "beach": "beach_access", "marina": "sailing",
    "theatre": "theater_comedy", "cinema": "movie", "restaurant": "restaurant",
    "cafe": "local_cafe", "fast_food": "lunch_dining", "bar": "local_bar", "mall": "local_mall",
    "zoo": "pets", "aquarium": "water", "theme_park": "attractions", "water_park": "pool",
}


def place_icon_name(subcategory: str | None) -> str:
    return PLACE_ICONS.get(subcategory or "", "location_on")


def place_icon(subcategory: str | None) -> str:
    """Streamlit markdown form (':material/museum:') for native widgets."""
    return f":material/{place_icon_name(subcategory)}:"


def weather_icon_name(code: int | None) -> str:
    """WMO weather code -> Material Symbols name."""
    if code is None:
        return "thermostat"
    if code == 0:
        return "sunny"
    if code in (1, 2):
        return "partly_cloudy_day"
    if code == 3:
        return "cloud"
    if code in (45, 48):
        return "foggy"
    if code in (71, 73, 75, 77, 85, 86):
        return "weather_snowy"
    if code >= 95:
        return "thunderstorm"
    return "rainy"


def city_code(name: str) -> str:
    """Three-letter, departure-board style code: 'Kraków' -> 'KRA'."""
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    letters = [c for c in ascii_name.upper() if c.isalpha()]
    return ("".join(letters[:3]) or "---").ljust(3, "-")


def inject_styles():
    with open(_CSS_PATH, encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


def html(markup: str):
    st.markdown(markup, unsafe_allow_html=True)


_COMPASS = (
    "<svg viewBox='0 0 40 40' aria-hidden='true' class='tp-compass'>"
    "<circle cx='20' cy='20' r='18' fill='none' stroke='currentColor' stroke-width='1.2'/>"
    "<circle cx='20' cy='20' r='13' fill='none' stroke='currentColor' stroke-width='.6' stroke-dasharray='1 2.4'/>"
    "<path d='M20 4 L23 20 L20 36 L17 20 Z' fill='currentColor'/>"
    "<path d='M4 20 L20 17.5 L36 20 L20 22.5 Z' fill='currentColor' opacity='.45'/>"
    "<circle cx='20' cy='20' r='2' fill='#11293A'/></svg>"
)


def brand():
    html("<div class='tp-brand'>" + _COMPASS +
         "<div><div class='tp-brand-name'>Trip <em>planner</em></div>"
         "<div class='tp-brand-tag'>Itineraries, checked</div></div></div>")


def section_label(text: str):
    html(f"<div class='tp-section'><span>{escape(text)}</span></div>")


def loading(city: str, n_days: int) -> str:
    """Full-width 'boarding' animation shown while the plan is being built."""
    steps = ["Reading the forecast", "Shortlisting places", "Drafting each day",
             "Checking opening hours", "Measuring walking times", "Stamping the itinerary"]
    msgs = "".join(f"<span style='--i:{i}'>{escape(s)}…</span>" for i, s in enumerate(steps))
    eta = "about a minute" if n_days > 3 else "about 30 seconds"
    return (
        "<div class='tp-loading' role='status' aria-live='polite'>"
        f"<div class='tp-kicker'>Now boarding · {n_days} day{'s' if n_days > 1 else ''}</div>"
        f"<h2>Plotting {escape(city)}</h2>"
        "<div class='tp-loading-track'><svg viewBox='0 0 600 80' preserveAspectRatio='none' aria-hidden='true'>"
        "<path id='tp-load-path' d='M10 60 Q 300 -20 590 60' fill='none' stroke='currentColor' "
        "stroke-width='2' stroke-dasharray='2 9' stroke-linecap='round'/>"
        "<circle cx='10' cy='60' r='5' class='tp-dot-a'/><circle cx='590' cy='60' r='5' class='tp-dot-b'/>"
        "</svg><div class='tp-plane'><span class='material-symbols-rounded'>flight</span></div></div>"
        f"<div class='tp-loading-msgs'>{msgs}</div>"
        f"<div class='tp-loading-eta'>{eta}</div></div>"
    )
